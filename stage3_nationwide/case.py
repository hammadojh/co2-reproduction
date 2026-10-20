"""Original-feature ablation: seven variants, no newly engineered predictors."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[key]='1'
import sys,json,time,hashlib,subprocess,random,platform,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'stage3_original'),str(ROOT/'stage1'),str(ROOT/'stage0')]
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits,threadpool_info
from groups import FULL_FEATURES,GROUPS,VARIANTS,feature_columns
from benchmark import model_for,peak_mib
from baseline import DATA,eligible_training,prepare
from original_definitions import RIDGE_ALPHA_GRID,HGB_GRID,metrics
OUT=ROOT/'stage3_nationwide/results'

def case(state,h,variant,model):
 sd=pd.read_csv(DATA/'extended_state_daily'/f'{state}.csv')
 t=time.perf_counter();d=prepare(sd,h);prep_s=time.perf_counter()-t
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
 reference_path=ROOT/'stage0/results/pilot'/f'{state}_h{h}_predictions.csv'
 n_original=None;same_population=None;baseline_error=None
 if reference_path.exists():
  reference=pd.read_csv(reference_path);reference=reference[reference.model==model].copy();reference['date']=pd.to_datetime(reference.date)
  n_original=len(reference);same_population=list(reference.date)==list(predictions.date)
  assert same_population
  if variant=='baseline':
   baseline_error=float(np.max(np.abs(reference.prediction.to_numpy()-predictions.prediction.to_numpy())))
   np.testing.assert_allclose(reference.prediction,predictions.prediction,rtol=1e-10,atol=1e-7)
 # Compare every overlapping pilot variant, not just full models.
 pilot_path=ROOT/'stage3_original/results/predictions'/f'{state}_h{h}_{model}_{variant}.csv'
 if pilot_path.exists():
  pilot=pd.read_csv(pilot_path,parse_dates=['date','target_date'])
  assert list(pilot.date)==list(predictions.date)
  np.testing.assert_allclose(pilot.target,predictions.target,rtol=0,atol=0)
  np.testing.assert_allclose(pilot.prediction,predictions.prediction,rtol=1e-10,atol=1e-7)
 key=f'{state}_h{h}_{model}_{variant}'
 predictions.to_csv(OUT/'predictions'/f'{key}.csv',index=False)
 (OUT/f'{key}_audit.json').write_text(json.dumps(dict(settings=best,validation_scores=scores,inner_train_target_end=str(tr.target_date.max()),validation_start=str(val.date.min()),validation_target_end=str(val.target_date.max()),selection_cutoff=str(start),fits=audit),indent=2))
 return dict(state=state,horizon=h,model=model,variant=variant,n_features=len(cols),n=len(predictions),n_original=n_original,original_population_equal=same_population,baseline_max_error=baseline_error,development_n=len(dev),origin_hash=hashlib.sha256(predictions.date.astype(str).str.cat(sep='|').encode()).hexdigest(),**metrics(predictions.target,predictions.prediction),full_feature_construction_s=prep_s,tuning_s=tuning_s,rolling_fit_s=fit_s,rolling_prediction_s=prediction_s,fit_ms_per_retrain=fit_s/len(audit)*1000,single_prediction_us=float(np.median(times)*1e6),n_fits=len(audit))
