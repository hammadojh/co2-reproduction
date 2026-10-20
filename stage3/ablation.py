"""Frozen eight-variant pilot; one complete run per configuration."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[key]='1'
import sys,json,time,hashlib,subprocess,random,platform,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'stage2'),str(ROOT/'stage1'),str(ROOT/'stage0')]
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits,threadpool_info
from features import engineer,FULL_FEATURES,NEW_FEATURES,VARIANTS,feature_columns
from benchmark import model_for,peak_mib
from baseline import DATA,eligible_training,prepare
from original_definitions import RIDGE_ALPHA_GRID,HGB_GRID,metrics
OUT=ROOT/'stage3/results'

def case(state,h,variant,model):
 sd=pd.read_csv(DATA/'extended_state_daily'/f'{state}.csv')
 t=time.perf_counter();full=engineer(sd,h);prep_s=time.perf_counter()-t
 d=full.dropna(subset=FULL_FEATURES+NEW_FEATURES+['target']).reset_index(drop=True)
 cols=feature_columns(variant)
 dates=pd.date_range(pd.to_datetime(sd.date).min()+pd.Timedelta(days=30),pd.to_datetime(sd.date).max());start=dates[len(dates)//2]
 dev=eligible_training(d,start);val=dev.iloc[-max(int(len(dev)*.15),20):];tr=eligible_training(dev,val.date.iloc[0])
 assert tr.target_date.max()<=val.date.min() and val.target_date.max()<=start
 xt=tr[cols].to_numpy();yt=tr.target.to_numpy();xv=val[cols].to_numpy();yv=val.target.to_numpy()
 grid=HGB_GRID if model=='hgb' else RIDGE_ALPHA_GRID
 # Untimed per-case warmup; complete workload timings below are single observations.
 m=model_for(model,grid[0]);m.fit(xt[:100],yt[:100]);m.predict(xv[:1]);del m
 t=time.perf_counter();scores=[]
 for setting in grid:
  m=model_for(model,setting);m.fit(xt,yt);scores.append(metrics(yv,m.predict(xv))['R2'])
 best=grid[int(np.argmax(scores))];tuning_s=time.perf_counter()-t
 pred=[];audit=[];fit_s=prediction_s=0.
 for block in pd.date_range(start,d.date.max(),freq='14D'):
  test=d[(d.date>=block)&(d.date<block+pd.Timedelta(days=14))]
  if test.empty:continue
  train=eligible_training(d,block);assert train.target_date.max()<=block
  a=train[cols].to_numpy();b=train.target.to_numpy();c=test[cols].to_numpy()
  m=model_for(model,best);t=time.perf_counter();m.fit(a,b);fit_s+=time.perf_counter()-t
  t=time.perf_counter();p=m.predict(c);prediction_s+=time.perf_counter()-t
  frame=test[['date','target_date','target']].copy();frame['prediction']=p;pred.append(frame)
  audit.append(dict(fit_date=str(block),last_training_target=str(train.target_date.max()),n_train=len(train),n_test=len(test)))
 predictions=pd.concat(pred,ignore_index=True)
 times=[]
 for _ in range(100):
  t=time.perf_counter();m.predict(c[:1]);times.append(time.perf_counter()-t)
 reference=pd.read_csv(ROOT/'stage0/results/pilot'/f'{state}_h{h}_predictions.csv');reference=reference[reference.model==model].copy();reference['date']=pd.to_datetime(reference.date)
 n_original=len(reference);same_dates=list(reference.date)==list(predictions.date)
 # Only compare predictions to old baseline if both evaluation AND development populations match.
 old=prepare(sd,h);same_population=list(old.date)==list(d.date)
 baseline_error=None
 if variant=='baseline' and same_population:
  assert same_dates
  baseline_error=float(np.max(np.abs(reference.prediction.to_numpy()-predictions.prediction.to_numpy())))
  np.testing.assert_allclose(reference.prediction,predictions.prediction,rtol=1e-10,atol=1e-7)
 key=f'{state}_h{h}_{model}_{variant}'
 predictions.to_csv(OUT/'predictions'/f'{key}.csv',index=False)
 (OUT/f'{key}_audit.json').write_text(json.dumps(dict(settings=best,validation_scores=scores,inner_train_target_end=str(tr.target_date.max()),validation_start=str(val.date.min()),validation_target_end=str(val.target_date.max()),selection_cutoff=str(start),fits=audit),indent=2))
 return dict(state=state,horizon=h,model=model,variant=variant,n_features=len(cols),n=len(predictions),n_original=n_original,original_population_equal=same_population,baseline_max_error=baseline_error,development_n=len(dev),origin_hash=hashlib.sha256(predictions.date.astype(str).str.cat(sep='|').encode()).hexdigest(),**metrics(predictions.target,predictions.prediction),full_feature_construction_s=prep_s,tuning_s=tuning_s,rolling_fit_s=fit_s,rolling_prediction_s=prediction_s,fit_ms_per_retrain=fit_s/len(audit)*1000,single_prediction_us=float(np.median(times)*1e6),n_fits=len(audit))

def main():
 p=argparse.ArgumentParser();p.add_argument('--worker',nargs=2);a=p.parse_args()
 if a.worker:
  variant,model=a.worker
  with threadpool_limits(limits=1):
   for state in ['TX','PA','CA']:
    for h in [1,7,14]:print(json.dumps({'case':case(state,h,variant,model)}),flush=True)
   print(json.dumps({'memory':dict(variant=variant,model=model,process_peak_rss_mib=peak_mib(),threads=threadpool_info())}),flush=True)
  return
 plan=json.loads((ROOT/'stage2/results/candidate_plan.json').read_text())
 assert all(hashlib.sha256((ROOT/'stage2'/p).read_bytes()).hexdigest()==v for p,v in plan['source_hashes'].items())
 manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'stage2/features.py',ROOT/'stage1/benchmark.py',ROOT/'stage0/baseline.py',ROOT/'stage0/original_definitions.py',ROOT/'stage0/requirements.lock.txt',ROOT/'stage2/results/candidate_plan.json']}
 (OUT/'environment.json').write_text(json.dumps(dict(platform=platform.platform(),python=platform.python_version(),source_hashes=manifest,threads=1,repeats=1,memory_scope='one process per model/variant, all nine pilot cases',timing_scope='single full run per case; 100 final-model one-row prediction calls'),indent=2))
 tasks=[(v,m) for v in VARIANTS for m in ['ridge','gam','hgb']];random.Random(42).shuffle(tasks);rows=[];memory=[]
 for v,m in tasks:
  proc=subprocess.Popen([sys.executable,__file__,'--worker',v,m],stdout=subprocess.PIPE,text=True)
  for line in proc.stdout:
   message=json.loads(line)
   if 'case' in message:
    r=message['case'];rows.append(r);pd.DataFrame(rows).to_csv(OUT/'metrics.csv',index=False)
    print(f"{len(rows)}/216 {r['state']} h={r['horizon']} {m} {v}",flush=True)
   else:memory.append(message['memory']);(OUT/'memory.json').write_text(json.dumps(memory,indent=2))
  if proc.wait()!=0:raise RuntimeError(f'Worker failed: {v} {m}')
if __name__=='__main__':main()
