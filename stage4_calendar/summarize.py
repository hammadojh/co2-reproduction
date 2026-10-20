import sys,json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'stage4_calendar/results'
sys.path.insert(0,str(ROOT/'stage0'))
from original_definitions import metrics
rows=[json.loads(p.read_text()) for p in (OUT/'checkpoints').glob('*.json')]
d=pd.DataFrame(rows)
assert len(d)==945 and not d.duplicated(['state','horizon','model','variant']).any()
b=pd.read_csv(ROOT/'stage3_full/results/full_metrics.csv');b=b[(b.horizon==14)&(b.variant=='baseline')]
for r in rows:
 key=f"{r['state']}_h14_{r['model']}_{r['variant']}"
 p=pd.read_csv(OUT/'predictions'/f'{key}.csv',parse_dates=['date','target_date'])
 ref=pd.read_csv(ROOT/'stage3_nationwide/results/predictions'/f"{r['state']}_h14_{r['model']}_baseline.csv",parse_dates=['date','target_date'])
 assert p[['date','target_date','target']].equals(ref[['date','target_date','target']])
 assert p.date.is_unique and p.date.is_monotonic_increasing and ((p.target_date-p.date).dt.days==14).all()
 assert np.isfinite(p[['target','prediction']].to_numpy()).all()
 for k,v in metrics(p.target,p.prediction).items(): np.testing.assert_allclose(v,r[k],rtol=1e-10,atol=1e-8)
 a=json.loads((OUT/f'{key}_audit.json').read_text())
 assert pd.Timestamp(a['inner_train_target_end'])<=pd.Timestamp(a['validation_start'])
 assert pd.Timestamp(a['validation_target_end'])<=pd.Timestamp(a['selection_cutoff'])
 assert all(pd.Timestamp(f['last_training_target'])<=pd.Timestamp(f['fit_date']) for f in a['fits'])
p=d.merge(b[['state','model','R2','RMSE']],on=['state','model'],suffixes=('','_full'))
p['R2_loss']=p.R2_full-p.R2;p['RMSE_change_pct']=100*(p.RMSE/p.RMSE_full-1)
p.to_csv(OUT/'paired_changes.csv',index=False)
s=p.groupby(['model','variant']).agg(mean_R2=('R2','mean'),mean_R2_loss=('R2_loss','mean'),median_R2_loss=('R2_loss','median'),states_worsened=('R2_loss',lambda x:int((x>0).sum())),mean_RMSE_change_pct=('RMSE_change_pct','mean')).reset_index();s.to_csv(OUT/'summary.csv',index=False)
text=['# Calendar component ablation: fourteen-day forecasts','', 'Completed 945 configurations: 45 states × 3 models × 7 removals. Original features only; each variant retuned under the existing corrected protocol. Positive R² loss means removal hurt. States receive equal weight.','', '| Model | Removed | Mean R² | Mean R² loss | Median loss | States worsened /45 |','|---|---|---:|---:|---:|---:|']
for r in s.itertuples():text.append(f'| {r.model} | {r.variant.removeprefix("drop_")} | {r.mean_R2:.4f} | {r.mean_R2_loss:+.4f} | {r.median_R2_loss:+.4f} | {r.states_worsened} |')
text+=['','Annual removes both month and day-of-year sine/cosine pairs; weekly removes weekday sine/cosine and weekend. Year is removed separately. All other original inputs remain.','', 'Interpretation is restricted to the tested fourteen-day horizon. Overlapping predictors can replace one another; removal effects are conditional, are not additive importance shares, and include retuning. No causal or statistical-significance claims are made. Calendar features describe the forecast origin date.','', 'Validation: every saved prediction was checked against baseline dates and targets; horizons, finite values, recomputed metrics and fitting/tuning cutoffs were checked. Source and data hashes are saved by the runner.']
(ROOT/'stage4_calendar/REPORT.md').write_text('\n'.join(text)+'\n')
(OUT/'verification.json').write_text(json.dumps(dict(configurations=len(rows),paired_dates_targets=True,metrics_recomputed=True,temporal_cutoffs_checked=True),indent=2))
print(s.to_string(index=False))
