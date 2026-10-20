"""Validate every nationwide case before generating descriptive summaries."""
import os
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import sys,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent;OUT=BASE/'results'
sys.path.insert(0,str(ROOT/'stage3_original'))
from groups import VARIANTS,FULL_FEATURES
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
protocol=json.loads((OUT/'protocol.json').read_text());d=pd.read_csv(OUT/'metrics.csv')
keys=['state','horizon','model'];expected={(s,h,m,v) for s in protocol['states'] for h in protocol['horizons'] for m in protocol['models'] for v in VARIANTS}
assert set(d[keys+['variant']].itertuples(index=False,name=None))==expected
assert len(d)==len(expected)==2835 and not d.duplicated(keys+['variant']).any()
assert (d.groupby(['state','horizon']).origin_hash.nunique()==1).all()
assert (d.groupby(['state','horizon']).n.nunique()==1).all()
population={};pilot_checked=0;max_pilot_error=0.
for r in d.itertuples():
 key=f'{r.state}_h{r.horizon}_{r.model}_{r.variant}'
 p=pd.read_csv(OUT/'predictions'/f'{key}.csv',parse_dates=['date','target_date'])
 assert len(p)==r.n and not p.date.duplicated().any()
 assert ((p.target_date-p.date).dt.days==r.horizon).all()
 assert np.isfinite(p[['target','prediction']].to_numpy()).all()
 assert r.n_features==len(VARIANTS[r.variant])
 actual_hash=hashlib.sha256(p.date.astype(str).str.cat(sep='|').encode()).hexdigest()
 assert actual_hash==r.origin_hash
 group=(r.state,r.horizon)
 pop=p[['date','target_date','target']]
 if group in population:pd.testing.assert_frame_equal(population[group],pop)
 else:population[group]=pop
 a=json.loads((OUT/f'{key}_audit.json').read_text())
 assert len(a['validation_scores'])==12
 assert pd.Timestamp(a['inner_train_target_end'])<=pd.Timestamp(a['validation_start'])
 assert pd.Timestamp(a['validation_target_end'])<=pd.Timestamp(a['selection_cutoff'])
 assert all(pd.Timestamp(f['last_training_target'])<=pd.Timestamp(f['fit_date']) for f in a['fits'])
 cp=json.loads((OUT/'checkpoints'/f'{key}.json').read_text())
 assert all(t['num_threads']==1 for t in cp['native_threads'])
 pilot=ROOT/'stage3_original/results/predictions'/f'{key}.csv'
 if pilot.exists():
  old=pd.read_csv(pilot,parse_dates=['date','target_date']);pd.testing.assert_frame_equal(old[['date','target_date','target']],pop)
  np.testing.assert_allclose(old.prediction,p.prediction,rtol=1e-10,atol=1e-7)
  max_pilot_error=max(max_pilot_error,float(np.max(np.abs(old.prediction-p.prediction))));pilot_checked+=1
for rel,h in json.loads((BASE/'source_manifest.json').read_text()).items():assert digest(ROOT/rel)==h,rel
baseline=d[d.variant=='baseline'][keys+['R2','RMSE','MAE']]
c=d.merge(baseline,on=keys,suffixes=('','_full'),validate='many_to_one')
c['delta_R2']=c.R2-c.R2_full;c['RMSE_change_pct']=(c.RMSE/c.RMSE_full-1)*100;c['MAE_change_pct']=(c.MAE/c.MAE_full-1)*100
c.to_csv(OUT/'paired_changes.csv',index=False)
summary=c.groupby(['model','variant'])[['R2','delta_R2','RMSE_change_pct','MAE_change_pct']].mean();summary.to_csv(OUT/'model_variant_summary.csv')
h=c.groupby(['model','variant','horizon'])[['R2','delta_R2','RMSE_change_pct','MAE_change_pct']].mean();h.to_csv(OUT/'horizon_summary.csv')
distribution=c.groupby(['model','variant','horizon']).agg(mean_delta_R2=('delta_R2','mean'),median_delta_R2=('delta_R2','median'),min_delta_R2=('delta_R2','min'),max_delta_R2=('delta_R2','max'),states_worsened=('delta_R2',lambda x:int((x<0).sum())),states=('state','nunique'));distribution.to_csv(OUT/'state_distribution.csv')
coverage=[]
for (s,hor),p in sorted(population.items()):
 sd=pd.read_csv(ROOT/'Manuscript V1/Data/extended_state_daily'/f'{s}.csv');dates=pd.to_datetime(sd.date)
 coverage.append(dict(state=s,horizon=hor,input_rows=len(sd),missing_calendar_days=len(pd.date_range(dates.min(),dates.max()))-len(sd),evaluation_origins=len(p),first_origin=str(p.date.min().date()),last_origin=str(p.date.max().date()),last_target=str(p.target_date.max().date())))
pd.DataFrame(coverage).to_csv(OUT/'coverage.csv',index=False)
verification=dict(configurations=len(d),states=45,horizons=protocol['horizons'],models=protocol['models'],variants=7,paired_dates_targets_and_counts=True,temporal_cutoffs_valid=True,finite_predictions=True,original_27_features_only=True,pilot_configurations_reproduced=pilot_checked,max_pilot_prediction_error=max_pilot_error,protected_source_and_pilot_hashes_unchanged=True,native_threads_per_worker=1,failed_configurations=0)
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
lines=['# Nationwide original-feature ablation','','All **2,835 configurations** completed and passed validation: 45 states × 3 horizons (1, 7, 14 days) × 3 models × 7 variants. This extends the pilot geographically; it does not add the four intermediate horizons from the manuscript’s separate seven-horizon panel.','','## Protocol','','Supplied 2019–2025 state-day aggregates; original 27 primary predictors only. Full model, removal of each of the calendar/year, CO₂-history and operational groups, and each group alone. All models and variants share the full model’s complete-case origins and targets within each state/horizon. Missing calendar dates are reindexed; measurements remain missing, with no interpolation or filling. Original 12-setting prospective tuning grids and 14-calendar-day retraining retained. Two worker processes, one native compute thread each; timings are single-run and affected by concurrent execution.','','The 189 overlapping pilot configurations reproduce the saved pilot predictions within the specified numerical tolerance. Inputs, pilot outputs and manuscript hashes are unchanged.','','## Mean R² across 45 states','','| Horizon | Model | Full | Without calendar/year | Without CO₂ history | Without operational |','|---:|---|---:|---:|---:|---:|']
for hor in protocol['horizons']:
 for m in protocol['models']:lines.append(f'| {hor} | {m.upper()} | '+' | '.join(f'{h.loc[(m,v,hor),"R2"]:.4f}' for v in ['baseline','without_calendar','without_co2_history','without_operational'])+' |')
lines+=['','## Paired group-removal effects','','Equal-weight averages across 135 state/horizon cases per model. Positive R² loss or RMSE change means removal worsened performance.','','| Model | Removed group | Mean R² loss | Mean RMSE change | Cases worsened /135 |','|---|---|---:|---:|---:|']
for m in protocol['models']:
 for g in ['calendar','co2_history','operational']:
  v='without_'+g;r=summary.loc[(m,v)];w=int(((c.model==m)&(c.variant==v)&(c.delta_R2<0)).sum());lines.append(f'| {m.upper()} | {g} | {-r.delta_R2:+.4f} | {r.RMSE_change_pct:+.2f}% | {w} |')
lines+=['','## Group-only comparisons','','| Model | Full mean R² | Calendar only | CO₂ history only | Operational only |','|---|---:|---:|---:|---:|']
for m in protocol['models']:lines.append('| '+m.upper()+' | '+' | '.join(f'{summary.loc[(m,v),"R2"]:.4f}' for v in ['baseline','calendar_only','co2_history_only','operational_only'])+' |')
lines+=['','## Limits','','These are descriptive, retrospective finalized-data results for the 45 eligible states, not all US jurisdictions or demonstrated live forecasting performance. No formal significance, confidence interval or causal-importance claim is made. Calendar includes year and seasonal/weekday encodings; this study does not isolate those components. CO₂ history includes current emissions. Correlated groups can substitute for one another, and every variant is retuned. Complete-case filtering varies the evaluated population across states/horizons. National means give equal weight to states rather than emissions volume.','','The corrected protocol differs from the original manuscript’s saved evaluation; differences from its tables cannot be attributed solely to one correction. The original seven-horizon benchmark and formal statistical analyses would need separate comparable reruns to support all manuscript claims. Raw facility exports were unavailable, so supplied aggregation and eligibility were not independently reconstructed.','','## Outputs','','`results/paired_changes.csv`, `horizon_summary.csv`, `state_distribution.csv`, `coverage.csv`, `verification.json`, per-configuration `checkpoints/`, `predictions/`, and tuning/cutoff audit JSON. No manuscript was edited or published.']
(BASE/'REPORT.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(verification),flush=True)
print(h[['R2','delta_R2','RMSE_change_pct']].round(4).to_string(),flush=True)
