"""Portable entry point around the unchanged fitting code used for the report."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[name]='1'
import argparse,hashlib,json,sys,platform
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'stage3_nationwide'))
import case as engine
import numpy as np
import pandas as pd
import sklearn,scipy
ORIGINAL={k:list(v) for k,v in engine.VARIANTS.items()}
REMOVALS={'month':['month_sin','month_cos'],'weekday':['dow_sin','dow_cos'],
 'day_of_year':['doy_sin','doy_cos'],'weekend':['is_weekend'],'year':['year'],
 'annual':['month_sin','month_cos','doy_sin','doy_cos'],
 'weekly':['dow_sin','dow_cos','is_weekend']}
CALENDAR={'drop_'+k:[f for f in engine.FULL_FEATURES if f not in v] for k,v in REMOVALS.items()}
STATES=sorted(pd.read_csv(ROOT/'Manuscript V1/Data/extended_eligibility.csv').query('eligible').state)
HORIZONS=[1,2,3,5,7,10,14];MODELS=['ridge','gam','hgb']

def key(t):
    s,h,v,m=t
    return f'{s}_h{h}_{m}_{v}'

def reference(t):
    s,h,v,m=t
    if v in CALENDAR: folder=ROOT/'stage4_calendar/results';cp=f'{s}_{h}_{v}_{m}.json'
    else: folder=ROOT/('stage3_nationwide' if h in [1,7,14] else 'stage3_full')/'results';cp=key(t)+'.json'
    return folder,folder/'checkpoints'/cp

def tasks(study):
    output=[]
    if study in ['all','original']:output += [(s,h,v,m) for s in STATES for h in HORIZONS for v in ORIGINAL for m in MODELS]
    if study in ['all','calendar']:output += [(s,14,v,m) for s in STATES for v in CALENDAR for m in MODELS]
    return output

def atomic(path,obj):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n');tmp.replace(path)

def validate(t,folder,row,compare=True):
    s,h,v,m=t
    assert (row['state'],row['horizon'],row['variant'],row['model'])==t
    assert row['n_features']==len((CALENDAR if v in CALENDAR else ORIGINAL)[v])
    p=pd.read_csv(folder/'predictions'/f'{key(t)}.csv',parse_dates=['date','target_date'])
    assert len(p)==row['n'] and p.date.is_unique and p.date.is_monotonic_increasing
    assert ((p.target_date-p.date).dt.days==h).all()
    assert np.isfinite(p[['target','prediction']].to_numpy()).all()
    for name,value in engine.metrics(p.target,p.prediction).items():np.testing.assert_allclose(value,row[name],rtol=1e-10,atol=1e-8)
    basefolder,_=reference((s,h,'baseline',m))
    baseline=pd.read_csv(basefolder/'predictions'/f'{s}_h{h}_{m}_baseline.csv',parse_dates=['date','target_date'])
    pd.testing.assert_frame_equal(p[['date','target_date','target']],baseline[['date','target_date','target']])
    a=json.loads((folder/f'{key(t)}_audit.json').read_text())
    assert len(a['validation_scores'])==12
    assert pd.Timestamp(a['inner_train_target_end'])<=pd.Timestamp(a['validation_start'])
    assert pd.Timestamp(a['validation_target_end'])<=pd.Timestamp(a['selection_cutoff'])
    assert sum(f['n_test'] for f in a['fits'])==len(p) and len(a['fits'])==row['n_fits']
    assert all(pd.Timestamp(f['last_training_target'])<=pd.Timestamp(f['fit_date']) for f in a['fits'])
    error=0.
    if compare:
        refdir,_=reference(t);old=pd.read_csv(refdir/'predictions'/f'{key(t)}.csv')
        error=float(np.max(np.abs(p.prediction-old.prediction)))
        np.testing.assert_allclose(p.prediction,old.prediction,rtol=1e-10,atol=1e-7)
        original_audit=json.loads((refdir/f'{key(t)}_audit.json').read_text())
        assert a['settings']==original_audit['settings']
    return error

def summarize(rows,out):
    frame=pd.DataFrame(rows);frame.to_csv(out/'metrics.csv',index=False)
    baseline=pd.read_csv(ROOT/'stage3_full/results/full_metrics.csv').query('variant=="baseline"')
    paired=frame.merge(baseline[['state','horizon','model','R2','RMSE']],on=['state','horizon','model'],suffixes=('','_full'),validate='many_to_one')
    paired['R2_loss']=paired.R2_full-paired.R2
    paired['RMSE_change_pct']=100*(paired.RMSE/paired.RMSE_full-1)
    paired.to_csv(out/'paired_changes.csv',index=False)
    paired.groupby(['horizon','model','variant']).agg(mean_R2=('R2','mean'),mean_R2_loss=('R2_loss','mean'),median_R2_loss=('R2_loss','median'),states=('state','nunique'),states_worsened=('R2_loss',lambda x:int((x>0).sum())),mean_RMSE_change_pct=('RMSE_change_pct','mean')).to_csv(out/'horizon_summary.csv')

def verify_reference():
    manifest=json.loads((ROOT/'PACKAGE_MANIFEST.json').read_text())
    for name,digest in manifest.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    rows=[]
    for n,t in enumerate(tasks('all'),1):
        folder,cp=reference(t);r=json.loads(cp.read_text());validate(t,folder,r,compare=False);rows.append(r)
        if n%945==0:print(f'Validated {n}/7560 configurations',flush=True)
    out=ROOT/'reproduced_summaries';out.mkdir(exist_ok=True);summarize(rows,out)
    atomic(out/'verification.json',dict(configurations=len(rows),package_hashes_checked=True,metrics_recomputed=True,dates_targets_paired=True,temporal_cutoffs_checked=True))
    print('PASS: 7,560 archived configurations verified; summaries regenerated.',flush=True)

def worker(task,output):
    engine.OUT=Path(output)
    engine.VARIANTS.update(CALENDAR)
    with engine.threadpool_limits(limits=1):r=engine.case(*task)
    r['reproduction_max_prediction_error']=validate(task,engine.OUT,r)
    return r

def run(study,workers,smoke):
    selected=tasks(study)
    if smoke:selected=[('TX',1,'baseline',m) for m in MODELS]+[('TX',14,v,m) for v in ['baseline','drop_annual','drop_year'] for m in MODELS]
    out=ROOT/'reruns'/('smoke' if smoke else study)
    for p in [out,out/'predictions',out/'checkpoints']:p.mkdir(parents=True,exist_ok=True)
    # A stale lock after a forced termination can be removed only once no runner is active.
    lock=out/'RUNNING.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        protected=[ROOT/'reproduce.py',ROOT/'stage3_nationwide/case.py',ROOT/'stage3_original/groups.py',ROOT/'stage0/baseline.py',ROOT/'stage0/original_definitions.py',ROOT/'stage1/benchmark.py']+list((ROOT/'Manuscript V1/Data/extended_state_daily').glob('*.csv'))
        signature=dict(hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected},python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,sklearn=sklearn.__version__,scipy=scipy.__version__,tasks=selected)
        signature=json.loads(json.dumps(signature))
        protocol=out/'protocol.json'
        if protocol.exists():assert json.loads(protocol.read_text())==signature,'Resume refused: code, input, environment or task selection changed.'
        else:atomic(protocol,signature)
        pending=[];rows=[]
        for t in selected:
            cp=out/'checkpoints'/f'{key(t)}.json'
            if cp.exists():r=json.loads(cp.read_text());validate(t,out,r);rows.append(r)
            else:pending.append(t)
        with ProcessPoolExecutor(max_workers=workers) as pool:
            jobs={pool.submit(worker,t,str(out)):t for t in pending}
            for f in as_completed(jobs):
                t=jobs[f];r=f.result();atomic(out/'checkpoints'/f'{key(t)}.json',r);rows.append(r)
                print(f'{len(rows)}/{len(selected)} {key(t)} matches supplied predictions',flush=True)
        summarize(rows,out)
        atomic(out/'verification.json',dict(configurations=len(rows),all_predictions_match_reference=True,max_prediction_error=max(r['reproduction_max_prediction_error'] for r in rows)))
    finally:lock.unlink(missing_ok=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['verify','smoke','run']);p.add_argument('--study',choices=['original','calendar','all'],default='all');p.add_argument('--workers',type=int,default=2);args=p.parse_args()
    if args.workers<1:p.error('--workers must be positive')
    if args.command=='verify':verify_reference()
    else:run(args.study,args.workers,args.command=='smoke')
