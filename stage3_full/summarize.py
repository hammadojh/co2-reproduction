"""Validate and combine all seven nationwide horizons without mixing feature scopes."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='1'
import sys,json,hashlib,time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent;OUT=BASE/'results'
sys.path.insert(0,str(ROOT/'stage3_original'))
from groups import VARIANTS,GROUPS,FULL_FEATURES
HORIZONS=[1,2,3,5,7,10,14];MODELS=['ridge','gam','hgb']
sources={h:ROOT/('stage3_nationwide' if h in [1,7,14] else 'stage3_full')/'results' for h in HORIZONS}
states=sorted(pd.read_csv(ROOT/'Manuscript V1/Data/extended_eligibility.csv').query('eligible').state)
assert len(states)==45 and len(FULL_FEATURES)==27
assert set(sum(GROUPS.values(),[]))==set(FULL_FEATURES)
expected=[(s,h,m,v) for s in states for h in HORIZONS for m in MODELS for v in VARIANTS]
missing=[f'{s}_h{h}_{m}_{v}' for s,h,m,v in expected if not (sources[h]/'checkpoints'/f'{s}_h{h}_{m}_{v}.json').exists()]
if missing:raise SystemExit(f'Not complete: {len(missing)} of 6615 checkpoints missing; no final report generated.')
rows=[];population={};pilot_checked=0;max_pilot_error=0.;start=time.monotonic()
for i,(s,h,m,v) in enumerate(expected):
 key=f'{s}_h{h}_{m}_{v}';src=sources[h];r=json.loads((src/'checkpoints'/f'{key}.json').read_text())
 assert (r['state'],r['horizon'],r['model'],r['variant'])==(s,h,m,v)
 assert r['n_features']==len(VARIANTS[v]) and all(t['num_threads']==1 for t in r['native_threads'])
 p=pd.read_csv(src/'predictions'/f'{key}.csv',parse_dates=['date','target_date'])
 assert len(p)==r['n'] and not p.date.duplicated().any() and p.date.is_monotonic_increasing
 assert ((p.target_date-p.date).dt.days==h).all() and np.isfinite(p[['target','prediction']].to_numpy()).all()
 assert hashlib.sha256(p.date.astype(str).str.cat(sep='|').encode()).hexdigest()==r['origin_hash']
 pop=p[['date','target_date','target']]
 if (s,h) in population:pd.testing.assert_frame_equal(population[s,h],pop)
 else:population[s,h]=pop
 e=p.target.to_numpy()-p.prediction.to_numpy();denom=np.sum((p.target-p.target.mean())**2)
 for name,value in [('R2',1-np.sum(e**2)/denom),('RMSE',np.sqrt(np.mean(e**2))),('MAE',np.mean(np.abs(e)))]:np.testing.assert_allclose(value,r[name],rtol=1e-10,atol=1e-8)
 a=json.loads((src/f'{key}_audit.json').read_text());assert len(a['validation_scores'])==12
 assert pd.Timestamp(a['inner_train_target_end'])<=pd.Timestamp(a['validation_start'])
 assert pd.Timestamp(a['validation_target_end'])<=pd.Timestamp(a['selection_cutoff'])
 assert len(a['fits'])==r['n_fits'] and sum(f['n_test'] for f in a['fits'])==len(p)
 assert all(pd.Timestamp(f['last_training_target'])<=pd.Timestamp(f['fit_date']) for f in a['fits'])
 pilot=ROOT/'stage3_original/results/predictions'/f'{key}.csv'
 if pilot.exists():
  old=pd.read_csv(pilot,parse_dates=['date','target_date']);pd.testing.assert_frame_equal(old[['date','target_date','target']],pop)
  np.testing.assert_allclose(old.prediction,p.prediction,rtol=1e-10,atol=1e-7)
  max_pilot_error=max(max_pilot_error,float(np.max(np.abs(old.prediction-p.prediction))));pilot_checked+=1
 rows.append({k:val for k,val in r.items() if k!='native_threads'})
 if (i+1)%315==0:print(f'Validated {i+1}/6615 predictions, metrics and cutoff files ({time.monotonic()-start:.1f}s)',flush=True)
# Verify source/data identities from both runners.
for folder in ['stage3_nationwide','stage3_full']:
 for rel,expected_hash in json.loads((ROOT/folder/'source_manifest.json').read_text()).items():
  actual=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest();assert actual==expected_hash,rel
assert pilot_checked==189
D=pd.DataFrame(rows);D.to_csv(OUT/'full_metrics.csv',index=False)
keys=['state','horizon','model'];b=D[D.variant=='baseline'][keys+['R2','RMSE','MAE']]
c=D.merge(b,on=keys,suffixes=('','_full'),validate='many_to_one')
c['delta_R2']=c.R2-c.R2_full;c['R2_loss']=c.R2_full-c.R2
c['RMSE_change_pct']=(c.RMSE/c.RMSE_full-1)*100;c['MAE_change_pct']=(c.MAE/c.MAE_full-1)*100
c.to_csv(OUT/'full_paired_changes.csv',index=False)
cols=['R2','R2_loss','delta_R2','RMSE_change_pct','MAE_change_pct']
n=c.groupby(['model','variant'])[cols].mean();n.to_csv(OUT/'full_model_variant_summary.csv')
h=c.groupby(['model','variant','horizon'])[cols].mean();h.to_csv(OUT/'full_horizon_summary.csv')
dist=c.groupby(['model','variant','horizon']).agg(mean_R2_loss=('R2_loss','mean'),median_R2_loss=('R2_loss','median'),min_R2_loss=('R2_loss','min'),max_R2_loss=('R2_loss','max'),states_worsened=('R2_loss',lambda x:int((x>0).sum())),states=('state','nunique'));dist.to_csv(OUT/'full_state_distribution.csv')
coverage=[]
for (s,hor),p in sorted(population.items()):
 sd=pd.read_csv(ROOT/'Manuscript V1/Data/extended_state_daily'/f'{s}.csv');dates=pd.to_datetime(sd.date)
 all_dates=pd.date_range(dates.min()+pd.Timedelta(days=30),dates.max());cut=all_dates[len(all_dates)//2]
 expected_days=len(pd.date_range(cut,dates.max()-pd.Timedelta(days=hor)))
 coverage.append(dict(state=s,horizon=hor,input_rows=len(sd),missing_calendar_days=len(pd.date_range(dates.min(),dates.max()))-len(sd),possible_calendar_origins=expected_days,evaluation_origins=len(p),evaluation_coverage_pct=100*len(p)/expected_days,first_origin=str(p.date.min().date()),last_origin=str(p.date.max().date())))
pd.DataFrame(coverage).to_csv(OUT/'full_coverage.csv',index=False)
# Three-panel removal effects across all horizons.
variants=['without_'+g for g in GROUPS]
arrays=[np.array([[h.loc[(m,v,x),'R2_loss'] for x in HORIZONS] for v in variants]) for m in MODELS]
bound=max(np.max(np.abs(a)) for a in arrays)
fig,axs=plt.subplots(1,3,figsize=(16,4.2),sharey=True,layout='constrained')
for ax,m,a in zip(axs,['Ridge','GAM','HGB'],arrays):
 im=ax.imshow(a,cmap='RdBu_r',vmin=-bound,vmax=bound,aspect='auto');ax.set_title(m);ax.set_xticks(range(7),[str(x) for x in HORIZONS]);ax.set_xlabel('Forecast horizon (days)');ax.set_yticks(range(3),['Remove calendar/year','Remove CO₂ history','Remove operational'])
 for ii in range(3):
  for jj in range(7):ax.text(jj,ii,f'{a[ii,jj]:+.3f}',ha='center',va='center',fontsize=8,color='white' if abs(a[ii,jj])>bound*.6 else 'black')
fig.colorbar(im,ax=axs,label='Mean R² loss after removal (positive = worse)',shrink=.8)
fig.suptitle('Original-feature ablation · all 45 states',fontsize=15);fig.savefig(OUT/'nationwide_ablation.png',dpi=180);fig.savefig(OUT/'nationwide_ablation.pdf');plt.close(fig)
colors={'ridge':'#22577a','gam':'#269488','hgb':'#c46b32'}
fig,axs=plt.subplots(1,2,figsize=(11,4.5),sharey=True,layout='constrained')
for ax,v,title in zip(axs,['baseline','without_calendar'],['All original features','Without calendar/year']):
 for m in MODELS:ax.plot(HORIZONS,[h.loc[(m,v,x),'R2'] for x in HORIZONS],marker='o',label=m.upper(),color=colors[m])
 ax.set_title(title);ax.set_xlabel('Forecast horizon (days)');ax.set_xticks(HORIZONS);ax.grid(alpha=.2);ax.legend()
axs[0].set_ylabel('Mean R² (equal state weights)');fig.suptitle('How calendar/year features change the model comparison',fontsize=14);fig.savefig(OUT/'calendar_comparison.png',dpi=180);fig.savefig(OUT/'calendar_comparison.pdf');plt.close(fig)
verification=dict(configurations=6615,states=45,horizons=HORIZONS,models=MODELS,variants=7,original_27_features_only=True,all_metrics_recomputed_from_predictions=True,paired_dates_targets_and_counts=True,temporal_cutoffs_verified=True,pilot_cases_reproduced=pilot_checked,max_pilot_prediction_error=max_pilot_error,source_data_and_prior_artifacts_unchanged=True,failed_configurations=0)
(OUT/'full_verification.json').write_text(json.dumps(verification,indent=2)+'\n')
lines=['# Full-dataset original-feature ablation','','Completed and validated **6,615 configurations**: 45 eligible states × 7 horizons (1,2,3,5,7,10,14 days) × 3 models × 7 variants. All results use the paper’s original 27 primary features; none of our Stage 2 additions is included.','','## National mean R²','','States receive equal weight. These are descriptive scores under the corrected evaluation protocol.','','| Days | Model | Full | Without calendar/year | Without CO₂ history | Without operational |','|---:|---|---:|---:|---:|---:|']
for hor in HORIZONS:
 for m in MODELS:lines.append(f'| {hor} | {m.upper()} | '+' | '.join(f'{h.loc[(m,v,hor),"R2"]:.4f}' for v in ['baseline']+variants)+' |')
lines+=['','![National removal effects](results/nationwide_ablation.png)','','![Calendar comparison](results/calendar_comparison.png)','','## Original-group removal, averaged across 315 state/horizon cases','','Positive loss means removal hurt. Counts describe direction, not statistical significance.','','| Model | Removed group | Mean R² loss | Mean RMSE change | Cases worsened /315 |','|---|---|---:|---:|---:|']
for m in MODELS:
 for g in GROUPS:
  v='without_'+g;r=n.loc[(m,v)];count=int(((c.model==m)&(c.variant==v)&(c.R2_loss>0)).sum());lines.append(f'| {m.upper()} | {g} | {r.R2_loss:+.4f} | {r.RMSE_change_pct:+.2f}% | {count} |')
lines+=['','## Group-only comparison','','| Model | Full mean R² | Calendar only | CO₂ history only | Operational only |','|---|---:|---:|---:|---:|']
for m in MODELS:lines.append('| '+m.upper()+' | '+' | '.join(f'{n.loc[(m,v),"R2"]:.4f}' for v in ['baseline','calendar_only','co2_history_only','operational_only'])+' |')
lines+=['','## Protocol and validation','','Supplied daily 2019–2025 aggregates; daily calendar reindexing; no imputation; targets constructed before row filtering; all variants use full-baseline complete-case dates. Training targets must be observed at each end-of-day forecast origin, including inner tuning cutoffs. Original 12-choice grids are retuned for each variant; models refit every 14 calendar days. Seven variants partition calendar/year (8), CO₂ history (13, including today), and operational inputs (6).','','Every forecast file was checked for finite values, exact horizon, unique dates and identical targets/dates across variants. R², RMSE and MAE were recalculated from predictions. All saved fitting/tuning cutoffs were checked. All 189 pilot configurations reproduce their prior predictions to numerical tolerance. Source/data/prior-output hashes were verified.','','The earlier run produced horizons 1,7,14 in stage3_nationwide/results; this extension produced 2,3,5,10 in stage3_full/results. Outputs were combined only after checking completeness and protocol identities. Both runners checkpoint each configuration.','','## Limits','','These are retrospective finalized-data comparisons, not a demonstration of real-time data access. Original facility exports and historical dependency lock were unavailable; supplied aggregation and eligibility were not independently reconstructed. Complete-case filtering changes coverage across states, especially those with missing records or load inputs; see full_coverage.csv. All feature variants within a state/horizon nevertheless use identical dates.','','Removal measures conditional predictive value, not causality. Correlated groups can substitute for one another. Calendar/year encodings are bundled, so effects cannot be attributed to seasonality alone. Every variant is retuned; removal effects include model adaptation. National averages can hide state differences, so medians/ranges/direction counts are supplied in full_state_distribution.csv.','','No confidence intervals, multiplicity-adjusted significance tests or causal claims are made. This completes the descriptive full-dataset ablation, not every statistical analysis in the manuscript. Corrected scores differ from the original manuscript protocol; their difference cannot be assigned solely to one repair.','','Concurrent execution and an earlier machine/filesystem interruption contaminate runtime observations. Do not use these timings for computational-cost claims; Stage 1’s controlled pilot benchmark remains separate. No manuscript has been edited or published.','','## Outputs and reproduction','','Full metrics and paired changes: full_metrics.csv and full_paired_changes.csv. Summary, horizon, state-distribution, coverage and verification files are in results/. Per-origin predictions, audits and checkpoints are retained in their originating runner directories.','','```sh','.venv/bin/python -B stage3_nationwide/run.py','.venv/bin/python -B stage3_full/run.py','.venv/bin/python -B stage3_full/summarize.py','```','','The runners are locked and resumable. They refuse a resume if protected sources change. Use the Stage 0 locked environment.']
from interpretation import section
lines.insert(3,'\n'+section())
(BASE/'REPORT.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(verification),flush=True);print(h.loc[(slice(None),['baseline','without_calendar'],slice(None)),['R2','R2_loss']].round(4).to_string(),flush=True)
