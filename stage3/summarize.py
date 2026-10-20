from pathlib import Path
import sys,json,hashlib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'stage2'))
from features import VARIANTS,GROUPS
BASE=Path(__file__).parent;OUT=BASE/'results'
d=pd.read_csv(OUT/'metrics.csv');keys=['state','horizon','model']
assert len(d)==216 and not d.duplicated(keys+['variant']).any()
assert (d.groupby(['state','horizon']).origin_hash.nunique()==1).all()
assert (d.groupby(['state','horizon']).n.nunique()==1).all()
ref=d[d.variant=='baseline'][keys+['R2','RMSE','MAE','fit_ms_per_retrain','tuning_s','single_prediction_us']]
c=d.merge(ref,on=keys,suffixes=('','_baseline'),validate='many_to_one')
c['delta_R2']=c.R2-c.R2_baseline;c['RMSE_change_pct']=(c.RMSE/c.RMSE_baseline-1)*100;c['MAE_change_pct']=(c.MAE/c.MAE_baseline-1)*100
c['fit_cost_ratio']=c.fit_ms_per_retrain/c.fit_ms_per_retrain_baseline;c['prediction_cost_ratio']=c.single_prediction_us/c.single_prediction_us_baseline
c.to_csv(OUT/'paired_changes.csv',index=False)
columns=['R2','delta_R2','RMSE_change_pct','MAE_change_pct','fit_ms_per_retrain','fit_cost_ratio','single_prediction_us','prediction_cost_ratio','tuning_s']
s=c.groupby(['model','variant'])[columns].mean();s.to_csv(OUT/'model_variant_summary.csv')
h=c.groupby(['model','variant','horizon'])[columns].mean();h.to_csv(OUT/'horizon_summary.csv')
win=c.assign(improved=c.delta_R2>0).groupby(['model','variant']).improved.sum();win.to_csv(OUT/'case_improvement_counts.csv')
contributions=[]
for model in ['ridge','gam','hgb']:
 for group in GROUPS:
  add=c[(c.model==model)&(c.variant=='add_'+group)]
  full=c[(c.model==model)&(c.variant=='all')]
  without=c[(c.model==model)&(c.variant=='without_'+group)]
  paired=full.merge(without,on=['state','horizon'],suffixes=('_all','_without'))
  contributions.append(dict(model=model,group=group,add_to_baseline_mean_delta_R2=add.delta_R2.mean(),add_improved_cases=int((add.delta_R2>0).sum()),full_minus_without_mean_delta_R2=(paired.R2_all-paired.R2_without).mean(),removal_worsens_cases=int((paired.R2_all>paired.R2_without).sum())))
g=pd.DataFrame(contributions);g.to_csv(OUT/'group_contributions.csv',index=False)
# Explicitly paired, descriptive display; no significance inference.
variants=[v for v in VARIANTS if v!='baseline'];labels=['Add relative changes','Add weekday history','Add operational history','All groups','All minus relative changes','All minus weekday history','All minus operational history']
arrays=[np.array([[h.loc[(m,v,x),'delta_R2'] for x in [1,7,14]] for v in variants]) for m in ['ridge','gam','hgb']]
bound=max(np.max(np.abs(a)) for a in arrays)
fig,axs=plt.subplots(1,3,figsize=(12,6),sharey=True,layout='constrained')
for ax,m,a in zip(axs,['Ridge','GAM','HGB'],arrays):
 im=ax.imshow(a,cmap='RdBu',vmin=-bound,vmax=bound,aspect='auto');ax.set_title(m);ax.set_xticks(range(3),['1 day','7 days','14 days']);ax.set_yticks(range(7),labels)
 for i in range(7):
  for j in range(3):ax.text(j,i,f'{a[i,j]:+.3f}',ha='center',va='center',fontsize=9,color='white' if abs(a[i,j])>bound*.6 else 'black')
fig.colorbar(im,ax=axs,label='Mean change in R² vs paired baseline (positive is better)',shrink=.75)
fig.suptitle('Feature ablation: mean changes across TX, PA, CA',fontsize=14)
fig.savefig(OUT/'ablation.png',dpi=180);fig.savefig(OUT/'ablation.pdf');plt.close(fig)
# Verify complete artifact set and original preservation.
for _,r in d.iterrows():
 key=f"{r.state}_h{r.horizon}_{r.model}_{r.variant}"
 p=pd.read_csv(OUT/'predictions'/f'{key}.csv',parse_dates=['date','target_date'])
 assert len(p)==r.n and ((p.target_date-p.date).dt.days==r.horizon).all()
 assert np.isfinite(p[['target','prediction']].to_numpy()).all()
 a=json.loads((OUT/f'{key}_audit.json').read_text())
 assert pd.Timestamp(a['inner_train_target_end'])<=pd.Timestamp(a['validation_start'])
 assert pd.Timestamp(a['validation_target_end'])<=pd.Timestamp(a['selection_cutoff'])
 assert all(pd.Timestamp(f['last_training_target'])<=pd.Timestamp(f['fit_date']) for f in a['fits'])
memory=json.loads((OUT/'memory.json').read_text());assert len(memory)==24
assert all(t['num_threads']==1 for p in memory for t in p['threads'])
original=json.loads((ROOT/'stage0/source_manifest.json').read_text());assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in original.items())
plan=json.loads((ROOT/'stage2/results/candidate_plan.json').read_text());assert all(hashlib.sha256((ROOT/'stage2'/p).read_bytes()).hexdigest()==v for p,v in plan['source_hashes'].items())
verification=dict(configurations=216,paired_dates_verified=True,temporal_cutoffs_verified=True,original_files_unchanged=len(original),candidate_plan_unchanged=True,baseline_population_matches_original=int(d[d.variant=='baseline'].original_population_equal.sum()),baseline_max_prediction_error=float(d.baseline_max_error.max()),memory_workers=24,single_native_thread_verified=True)
(OUT/'verification.json').write_text(json.dumps(verification,indent=2))
# Detailed report avoids selecting winners solely from averaged test performance.
lines=['# Stage 3 pilot ablation results','','## Scope','',
'Completed the eight frozen variants × three models × three states × three horizons (216 configurations). All comparisons use identical valid origin dates within a state/horizon. Each configuration was tuned prospectively with the original 12-setting budget, then evaluated with corrected 14-calendar-day retraining. No feature group was changed after observing these results.','',
'Each full configuration was run once. Cost measurements are exploratory single-run timings, not the repeated timing benchmark used in Stage 1. Prediction latency uses 100 calls to the final fitted model. Memory is one whole-process high-water mark per model/variant across all nine state/horizon cases; it is not per-case or model-only memory. Full candidate feature construction is timed for every variant to establish the common population; it is NOT the incremental construction cost of a selected feature group.','',
'## Mean changes relative to paired baseline','','Each mean weights the nine state/horizon cases equally. Negative RMSE/MAE percentage change is better. Improved counts refer to R², without significance tests.','',
'| Model | Variant | ΔR² | RMSE change | MAE change | Cases improved /9 | Fit cost ratio |','|---|---|---:|---:|---:|---:|---:|']
for model in ['ridge','gam','hgb']:
 for v in variants:
  r=s.loc[(model,v)];lines.append(f'| {model.upper()} | {v} | {r.delta_R2:+.4f} | {r.RMSE_change_pct:+.2f}% | {r.MAE_change_pct:+.2f}% | {win.loc[(model,v)]} | {r.fit_cost_ratio:.2f}× |')
lines+=['','![Feature ablation](results/ablation.png)','','## Contribution checks','','Positive add-one change means the group helps against baseline. Positive full-minus-without means removing it worsens performance. These effects include prospective retuning and do not isolate a causal effect of the features.','','| Model | Group | Add-one ΔR² | Full minus without ΔR² |','|---|---|---:|---:|']
for _,r in g.iterrows():lines.append(f'| {r.model.upper()} | {r.group} | {r.add_to_baseline_mean_delta_R2:+.4f} | {r.full_minus_without_mean_delta_R2:+.4f} |')
lines+=['','## Limits and next decision','','This remains a three-state pilot on an already inspected retrospective evaluation period. Rankings are descriptive, not statistically established winners or nationwide claims. No intervals or multiple-comparison-adjusted significance tests were calculated. Test-set rankings must not trigger another round of feature invention on this same test period.','',
'Feature effects may depend on model, horizon and state; inspect horizon_summary.csv and paired_changes.csv rather than relying solely on the aggregate. Current operational inputs still assume finalized end-of-day availability. The Delaware missingness issue from Stage 2 remains relevant to nationwide expansion.','',
'The next planned stage is a decision-support prototype using these observed trade-offs. It should expose scope and uncertainty rather than present a universally optimal model. No prototype or user study was performed in this stage.','',
'## Reproduce','','```sh','.venv/bin/python stage3/ablation.py','.venv/bin/python stage3/summarize.py','```','',
'Use the Stage 0 locked environment. These commands overwrite Stage 3 outputs. Saved artifacts include per-origin predictions, tuning scores/settings and cutoff audits for every configuration, all raw metrics, paired deltas, summaries, workload memory/thread metadata and verification results.']
interpretation = '''## Main findings

- No broad improvement from adding all eight features: mean change in R² is -0.00154 for Ridge, +0.00045 for GAM and -0.01039 for HGB.
- Relative dynamics is the clearest small candidate for GAM: mean R² +0.00390; mean RMSE change -1.28%; six of nine cases improve. Average fit-cost ratio is 1.12. By horizon, mean R² changes are +0.00629 at one day, +0.00553 at seven days and -0.00011 at fourteen days. This is modest and horizon-dependent.
- GAM with relative dynamics plus operational history has the highest aggregate GAM R² among the tested variants (+0.00493 vs baseline), but improves only five of nine cases and costs about 1.22 times as much to fit. Its higher retrospective mean does not establish it as the best deployment choice.
- Weekday history does not provide consistent gains; it lowers average R² for GAM and HGB. Operational history alone lowers HGB R² in all nine cases.
- These results do not demonstrate that engineered features let Ridge close the nonlinear-model gap. They show that feature usefulness depends on model and horizon, and that extra inputs can hurt.
- If advancing a compact candidate for further validation, retain GAM plus relative dynamics as a hypothesis, not a proven winner. Avoid another feature-search loop against these same evaluation outcomes.

'''
lines.insert(2,interpretation)
pd.DataFrame([{k:v for k,v in r.items() if k!='threads'} for r in memory]).to_csv(OUT/'memory_summary.csv',index=False)
(BASE/'REPORT.md').write_text('\n'.join(lines)+'\n')
print(s[['delta_R2','RMSE_change_pct','fit_cost_ratio']].round(4).to_string());print('\nGROUPS\n',g.round(4).to_string(index=False));print(verification)
