"""Sequential, process-isolated model cost benchmark on the Stage 0 pilot."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='1'
import sys,json,time,resource,platform,subprocess,hashlib,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'stage0'))
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler,SplineTransformer
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score
from threadpoolctl import threadpool_limits,threadpool_info
from baseline import prepare,eligible_training,DATA,FULL_FEATURES
from original_definitions import RIDGE_ALPHA_GRID,HGB_GRID
OUT=ROOT/'stage1/results'

def model_for(name,setting):
    if name=='ridge':return make_pipeline(StandardScaler(),Ridge(alpha=setting,random_state=42))
    if name=='gam':return make_pipeline(StandardScaler(),SplineTransformer(n_knots=5,degree=3,include_bias=False),Ridge(alpha=setting,random_state=42))
    return HistGradientBoostingRegressor(random_state=42,**setting)

def arrays(d):return d[FULL_FEATURES].to_numpy(),d.target.to_numpy()
def peak_mib():return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024)

def worker(state,horizon,name):
    sd=pd.read_csv(DATA/'extended_state_daily'/f'{state}.csv');d=prepare(sd,horizon)
    dates=pd.date_range(pd.to_datetime(sd.date).min()+pd.Timedelta(days=30),pd.to_datetime(sd.date).max());start=dates[len(dates)//2]
    available=eligible_training(d,start);val=available.iloc[-max(int(len(available)*.15),20):];tr=eligible_training(available,val.date.iloc[0]);xt,yt=arrays(tr);xv,yv=arrays(val)
    blocks=[]
    for t in pd.date_range(start,d.date.max(),freq='14D'):
        te=d[(d.date>=t)&(d.date<t+pd.Timedelta(days=14))]
        if len(te):
            a,b=arrays(eligible_training(d,t));c,e=arrays(te);blocks.append((a,b,c,e,te.date))
    grid=HGB_GRID if name=='hgb' else RIDGE_ALPHA_GRID
    baseline_peak=peak_mib();records=[]
    ref=pd.read_csv(ROOT/'stage0/results/pilot'/f'{state}_h{horizon}_predictions.csv');ref=ref[ref.model==name]
    expected=json.loads((ROOT/'stage0/results/pilot'/f'{state}_h{horizon}_settings.json').read_text())['settings'][name]
    with threadpool_limits(limits=1):
        # Untimed warmup reduces one-time library initialization effects.
        warm=model_for(name,grid[0]);warm.fit(xt[:100],yt[:100]);warm.predict(xv[:1]);del warm
        for repeat in range(3):
            t=time.perf_counter();scores=[]
            for s in grid:
                m=model_for(name,s);m.fit(xt,yt);scores.append(r2_score(yv,m.predict(xv)))
            best=grid[int(np.argmax(scores))];tune_s=time.perf_counter()-t
            assert best==expected,(name,best,expected)
            fit_s=pred_s=0.;preds=[];actual=[];origins=[]
            for a,b,c,e,origin_dates in blocks:
                m=model_for(name,best);t=time.perf_counter();m.fit(a,b);fit_s+=time.perf_counter()-t
                t=time.perf_counter();pr=m.predict(c);pred_s+=time.perf_counter()-t
                preds.extend(pr);actual.extend(e);origins.extend(origin_dates)
            assert list(pd.to_datetime(ref.date))==origins
            error=float(np.max(np.abs(np.array(preds)-ref.prediction.to_numpy())))
            np.testing.assert_allclose(preds,ref.prediction,rtol=1e-10,atol=1e-7)
            # Typical single-origin inference latency using the final fitted model.
            single=[]
            for _ in range(100):
                t=time.perf_counter();m.predict(c[:1]);single.append(time.perf_counter()-t)
            records.append(dict(state=state,horizon=horizon,model=name,repeat=repeat+1,tuning_s=tune_s,rolling_fit_s=fit_s,rolling_prediction_s=pred_s,n_fits=len(blocks),n_predictions=len(preds),single_prediction_us=float(np.median(single)*1e6),R2=r2_score(actual,preds),max_prediction_difference=error))
    return dict(records=records,process_peak_rss_mib=peak_mib(),pre_fit_peak_rss_mib=baseline_peak,threads=threadpool_info())

def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',nargs=3);a=p.parse_args()
    if a.worker:
        state,h,name=a.worker;print(json.dumps(worker(state,int(h),name)));return
    OUT.mkdir(parents=True,exist_ok=True)
    files=[ROOT/'stage0/baseline.py',ROOT/'stage0/original_definitions.py',Path(__file__),ROOT/'stage0/requirements.lock.txt']
    metadata=dict(platform=platform.platform(),python=platform.python_version(),cpu=subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip(),logical_cpus=os.cpu_count(),memory_bytes=int(subprocess.check_output(['sysctl','-n','hw.memsize'],text=True)),repeats=3,source_hashes={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
    (OUT/'environment.json').write_text(json.dumps(metadata,indent=2));allrows=[]
    tasks=[(s,h,m) for s in ['TX','PA','CA'] for h in [1,7,14] for m in ['ridge','gam','hgb']]
    # Fixed shuffled order spreads model order across the run; no concurrent workers.
    import random;random.Random(42).shuffle(tasks)
    for i,(s,h,m) in enumerate(tasks):
        r=subprocess.run([sys.executable,__file__,'--worker',s,str(h),m],capture_output=True,text=True,check=True)
        result=json.loads(r.stdout);(OUT/f'{s}_h{h}_{m}.json').write_text(json.dumps(result,indent=2))
        for row in result['records']:
            row['process_peak_rss_mib']=result['process_peak_rss_mib'];row['pre_fit_peak_rss_mib']=result['pre_fit_peak_rss_mib'];allrows.append(row)
        pd.DataFrame(allrows).to_csv(OUT/'raw_measurements.csv',index=False)
        print(f'{i+1}/27 {s} h={h} {m} verified',flush=True)
if __name__=='__main__':main()
