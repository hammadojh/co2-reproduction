from pathlib import Path
import sys,json,hashlib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(Path(__file__).parent))
from groups import VARIANTS,GROUPS,FULL_FEATURES
BASE=Path(__file__).parent;OUT=BASE/'results'
d=pd.read_csv(OUT/'metrics.csv');keys=['state','horizon','model']
assert len(d)==189 and not d.duplicated(keys+['variant']).any()
assert (d.groupby(['state','horizon']).origin_hash.nunique()==1).all()
assert (d.groupby(['state','horizon']).n.nunique()==1).all()
assert all(set(v)<=set(FULL_FEATURES) for v in VARIANTS.values())
b=d[d.variant=='baseline'][keys+['R2','RMSE','MAE','fit_ms_per_retrain']]
c=d.merge(b,on=keys,suffixes=('','_full'),validate='many_to_one')
c['delta_R2']=c.R2-c.R2_full;c['RMSE_change_pct']=(c.RMSE/c.RMSE_full-1)*100;c['MAE_change_pct']=(c.MAE/c.MAE_full-1)*100;c['fit_cost_ratio']=c.fit_ms_per_retrain/c.fit_ms_per_retrain_full
c.to_csv(OUT/'paired_changes.csv',index=False)
cols=['R2','delta_R2','RMSE_change_pct','MAE_change_pct','fit_ms_per_retrain','fit_cost_ratio','single_prediction_us','tuning_s']
s=c.groupby(['model','variant'])[cols].mean();s.to_csv(OUT/'model_variant_summary.csv')
h=c.groupby(['model','variant','horizon'])[cols].mean();h.to_csv(OUT/'horizon_summary.csv')
w=c.assign(worsened=c.delta_R2<0).groupby(['model','variant']).worsened.sum();w.to_csv(OUT/'cases_worsened.csv')
# Plot losses, so positive means removing the group hurt.
variants=['without_'+g for g in GROUPS];arrays=[np.array([[-h.loc[(m,v,x),'delta_R2'] for x in [1,7,14]] for v in variants]) for m in ['ridge','gam','hgb']]
bound=max(np.max(np.abs(a)) for a in arrays)
fig,axs=plt.subplots(1,3,figsize=(11,3.8),sharey=True,layout='constrained')
for ax,m,a in zip(axs,['Ridge','GAM','HGB'],arrays):
 im=ax.imshow(a,cmap='RdBu_r',vmin=-bound,vmax=bound,aspect='auto');ax.set_title(m);ax.set_xticks(range(3),['1 day','7 days','14 days']);ax.set_yticks(range(3),['Remove calendar','Remove CO₂ history','Remove operational'])
 for i in range(3):
  for j in range(3):ax.text(j,i,f'{a[i,j]:+.3f}',ha='center',va='center',fontsize=10,color='white' if abs(a[i,j])>bound*.6 else 'black')
fig.colorbar(im,ax=axs,label='R² loss after removal (positive = worse)',shrink=.85)
fig.suptitle('Original-feature ablation · TX, PA, CA mean',fontsize=14)
fig.savefig(OUT/'original_ablation.png',dpi=180);fig.savefig(OUT/'original_ablation.pdf');plt.close(fig)
# Validate every saved forecast and cutoff, and feature counts.
for _,r in d.iterrows():
 assert r.n_features==len(VARIANTS[r.variant])
 key=f'{r.state}_h{r.horizon}_{r.model}_{r.variant}'
 p=pd.read_csv(OUT/'predictions'/f'{key}.csv',parse_dates=['date','target_date'])
 assert len(p)==r.n and ((p.target_date-p.date).dt.days==r.horizon).all()
 assert np.isfinite(p[['target','prediction']].to_numpy()).all()
 a=json.loads((OUT/f'{key}_audit.json').read_text())
 assert pd.Timestamp(a['inner_train_target_end'])<=pd.Timestamp(a['validation_start'])
 assert pd.Timestamp(a['validation_target_end'])<=pd.Timestamp(a['selection_cutoff'])
 assert all(pd.Timestamp(f['last_training_target'])<=pd.Timestamp(f['fit_date']) for f in a['fits'])
memory=json.loads((OUT/'memory.json').read_text());assert len(memory)==21
assert all(t['num_threads']==1 for p in memory for t in p['threads'])
pd.DataFrame([{k:v for k,v in p.items() if k!='threads'} for p in memory]).to_csv(OUT/'memory_summary.csv',index=False)
original=json.loads((ROOT/'stage0/source_manifest.json').read_text());assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in original.items())
env=json.loads((OUT/'environment.json').read_text());assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in env['source_hashes'].items())
verification=dict(configurations=189,original_primary_features_only=True,paired_dates_and_counts=True,temporal_checks=True,baseline_predictions_max_error=float(d.baseline_max_error.max()),original_files_unchanged=len(original),source_hashes_verified=True,models=['ridge','gam','hgb'],states=['TX','PA','CA'],horizons=[1,7,14])
(OUT/'verification.json').write_text(json.dumps(verification,indent=2))
lines=['# Ablation of the paper’s original features','','## Scope correction','','This experiment removes or isolates the paper’s ORIGINAL feature groups. It uses none of the eight features developed in Stage 2. The earlier Stage 3 experiment measured our proposed additions and is a separate study; its results must not be described as ablation of the paper’s original predictors.','','## Design','','Three groups partition the original 27 predictors: calendar (8, including year), CO₂ history (13, including current emissions), and operational inputs (6). Seven variants: full model; full minus each group; each group alone. The paper’s two excluded diagnostic emissions-ratio features are not part of this primary feature set.','','All 189 configurations were run: seven variants × three models × three states × three horizons. Every variant uses identical full-baseline complete-case dates, and receives prospective tuning using the original 12-choice grid. Stage 0 temporal corrections are retained. All 27 full-model cases reproduce the corrected Stage 0 predictions.','','## Removing original groups','','Equal-weight means across nine state/horizon cases. Positive R² loss and positive RMSE change mean removing the group worsens performance.','','| Model | Removed group | Mean R² loss | Mean RMSE change | Cases worsened /9 |','|---|---|---:|---:|---:|']
for m in ['ridge','gam','hgb']:
 for g in GROUPS:
  v='without_'+g;r=s.loc[(m,v)];lines.append(f'| {m.upper()} | {g} | {-r.delta_R2:+.4f} | {r.RMSE_change_pct:+.2f}% | {w.loc[(m,v)]} |')
lines+=['','![Original-feature removal](results/original_ablation.png)','','## Group-only models','','The full baseline is repeated for reference. These models use the same dates as full models, not every date available to their smaller feature sets.','','| Model | Full R² | Calendar only R² | CO₂ history only R² | Operational only R² |','|---|---:|---:|---:|---:|']
for m in ['ridge','gam','hgb']:lines.append('| '+m.upper()+' | '+' | '.join(f'{s.loc[(m,v),"R2"]:.4f}' for v in ['baseline','calendar_only','co2_history_only','operational_only'])+' |')
lines+=['','## Interpretation boundaries','','Removal measures predictive contribution conditional on the remaining groups, not causal importance. Correlated operational/history predictors can substitute for each other. Removing CO₂ history removes today’s emissions as well as older lags. The models are retuned for every variant, so differences include adaptation to the remaining inputs.','','These are three-state retrospective pilot results, with three horizons and no uncertainty intervals or multiplicity-adjusted significance tests. Do not infer a national ranking or use tiny descriptive differences as proof. Group-only or reduced models can outperform the full set in individual cases; report them rather than assume more features always help.','','## Cost and reproducibility','','One complete run per configuration; fit/tuning timing is exploratory, unlike the repeated Stage 1 benchmark. Peak RSS is whole-process memory across nine cases per model/variant. Original data and previous stages remain unchanged. Full metrics, per-origin predictions, tuning choices, cutoff audits and machine/source hashes are saved under results/.','','```sh','.venv/bin/python stage3_original/ablation.py','.venv/bin/python stage3_original/summarize.py','```','','Use the locked Stage 0 environment. Rerunning overwrites this experiment’s outputs. No prototype work is included.']
findings='''## Main findings

The original calendar/year group accounts for much of the nonlinear models' advantage in this pilot, conditional on the evaluation and tuning protocol. At fourteen days, full-model mean R² is 0.4277 (Ridge), 0.5525 (GAM) and 0.5470 (HGB). After removing calendar/year features it becomes 0.4022, 0.4047 and 0.3991 respectively. Thus GAM/HGB's sizeable descriptive advantage over Ridge nearly disappears. The group includes year plus seasonal/weekday encodings; this experiment does not separate those components or establish causality.

At seven days, removing calendar/year features also erases the nonlinear-model advantage: Ridge 0.5005, GAM 0.4905, HGB 0.4814, compared with full-model 0.5155, 0.5827 and 0.5805. This provides a more specific hypothesis about the source of the horizon-dependent performance gap than a general claim that complexity helps.

Removing operational inputs has a small average effect: R² changes by -0.0070 (Ridge), -0.0006 (GAM) and +0.0034 (HGB). These measurements do not establish that operational data are unimportant generally; emissions history may substitute for them.

Removing CO₂ history has model- and horizon-dependent effects. GAM's pooled change is approximately zero, despite changes of opposite sign at seven and fourteen days. Current operational measurements may proxy emissions, so this must not be interpreted as proof that emissions history contains no useful signal.

These are corrected three-state pilot findings, not yet national results. No formal statistical significance is claimed. A focused statement about the conditional role of calendar/year predictors is supported descriptively; the paper's national mechanism claim still requires a national rerun and appropriate uncertainty analysis.

'''
lines.insert(2,findings)
(BASE/'REPORT.md').write_text('\n'.join(lines)+'\n')
print(s[['R2','delta_R2','RMSE_change_pct']].round(4).to_string());print('\nHORIZONS\n',h.loc[(slice(None),variants,slice(None)),['R2','delta_R2']].round(4).to_string());print(verification)
