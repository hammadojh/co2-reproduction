from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, NullFormatter
BASE=Path(__file__).parent;OUT=BASE/'results'
d=pd.read_csv(OUT/'raw_measurements.csv')
assert len(d)==81 and len(d.groupby(['state','horizon','model']))==27
assert (d.groupby(['state','horizon','model']).size()==3).all()
d['fit_ms_per_retrain']=d.rolling_fit_s/d.n_fits*1000
d['compute_s']=d.tuning_s+d.rolling_fit_s+d.rolling_prediction_s
metrics=['tuning_s','rolling_fit_s','rolling_prediction_s','fit_ms_per_retrain','single_prediction_us','compute_s','R2','process_peak_rss_mib','pre_fit_peak_rss_mib']
c=d.groupby(['state','horizon','model'])[metrics].median().reset_index();c.to_csv(OUT/'combination_medians.csv',index=False)
a=c.groupby('model')[metrics].mean();a.to_csv(OUT/'model_summary.csv')
h=c.groupby(['horizon','model'])[metrics].mean();h.to_csv(OUT/'horizon_summary.csv')
ranges=d.groupby(['state','horizon','model'])[metrics[:6]].agg(['min','max']);ranges.to_csv(OUT/'repeat_ranges.csv')
colors={'ridge':'#22577a','gam':'#269488','hgb':'#c46b32'}
fig,axs=plt.subplots(1,3,figsize=(12,4.3),sharey=True)
for ax,horizon in zip(axs,[1,7,14]):
 for m in ['ridge','gam','hgb']:
  r=h.loc[(horizon,m)];ax.scatter(r.fit_ms_per_retrain,r.R2,s=85,color=colors[m]);ax.annotate(m.upper(),(r.fit_ms_per_retrain,r.R2),xytext=(6,5),textcoords='offset points',fontsize=9)
 ax.set_xscale('log');ax.set_xlim(.7,200);ax.set_ylim(.39,.93);ax.set_xticks([1,10,100]);ax.xaxis.set_major_formatter(ScalarFormatter());ax.xaxis.set_minor_formatter(NullFormatter());ax.set_title(f'{horizon}-day horizon');ax.set_xlabel('Mean fit time per retrain (ms, log scale)');ax.grid(alpha=.18)
axs[0].set_ylabel('Mean test R² across TX, PA, CA')
fig.suptitle('Pilot accuracy versus training cost',fontsize=15)
fig.text(.5,.015,'Single-thread local measurements; median of 3 repeats per case. Descriptive results, not significance tests.',ha='center',fontsize=9)
fig.tight_layout(rect=[0,.055,1,.93]);fig.savefig(OUT/'accuracy_cost.png',dpi=180);fig.savefig(OUT/'accuracy_cost.pdf');plt.close(fig)
metadata=json.loads((OUT/'environment.json').read_text())
rows=[]
for m in ['ridge','gam','hgb']:
 r=a.loc[m];rows.append(f"| {m.upper()} | {r.tuning_s:.3f} | {r.fit_ms_per_retrain:.2f} | {r.single_prediction_us:.0f} | {r.process_peak_rss_mib:.1f} |")
accuracy=[]
for horizon in [1,7,14]:accuracy.append('| '+str(horizon)+' | '+' | '.join(f'{h.loc[(horizon,m)].R2:.4f}' for m in ['ridge','gam','hgb'])+' |')
report='''# Stage 1 computational practicality benchmark

## Scope and outcome

Completed the planned three-state pilot: TX, PA, CA × 1, 7, 14 days × Ridge, GAM, HGB. Every one of the 27 workloads ran three times (81 trials). Each model/case ran in its own sequential subprocess. Hyperparameters and predictions were verified against Stage 0 on every trial. No features were changed and Stage 2 has not begun.

## Cost results

Each entry below averages nine case medians (three timing repeats per case). Tuning covers the full original 12-choice search, including validation prediction/scoring. Fit time is per 14-day retraining event; each event uses the growing available history. Single prediction latency includes preprocessing and uses the final fitted model, measured with 100 one-row calls per repeat.

| Model | Tuning (s) | Fit per retrain (ms) | One prediction (µs) | Process peak RSS (MiB) |
|---|---:|---:|---:|---:|
'''+ '\n'.join(rows)+'''

Memory is the lifetime resident-memory high-water mark of the whole isolated Python process, including imports, loaded/prepared data, tuning and all three repeats. It is NOT model-only memory and cannot be assigned separately to tuning or fitting. Pre-fit high-water marks are recorded for context; subtracting two high-water marks would not provide a reliable incremental memory estimate. Memory readings are one per case/process, not three independent replicates.

## Accuracy

Equal-weight state mean R². These reproduce Stage 0 results to numerical tolerance, with no benchmark-specific retuning protocol.

| Horizon (days) | Ridge | GAM | HGB |
|---|---:|---:|---:|
'''+ '\n'.join(accuracy)+'''

![Accuracy and fit cost](results/accuracy_cost.png)

## Measurement protocol

- Corrected Stage 0 calendar alignment, information cutoffs, 27 features, evaluation dates and hyperparameter grids retained.
- Preprocessing arrays and date selection are outside timed sections. Fitting includes learned preprocessing (scaling and GAM splines); prediction includes those transformations.
- Twelve tuning settings per model, selected on the same development splits as Stage 0.
- Untimed small warmup, then three complete tuning/backtest repeats within each model/case subprocess.
- Fixed shuffled workload order, one worker at a time, native thread pools limited to one.
- Timing uses perf_counter wall time. This machine was not reserved exclusively; operating-system/background activity can affect measurements. Min/max repeat ranges are supplied.
- End-to-end compute totals exclude interpreter startup, imports, I/O and feature construction. Stored block-prediction cost is for up to 14 rows; single-origin latency is measured separately.
- No energy consumption, GPU cost, cloud price, national-scale runtime or user-decision improvement was measured.

## Interpretation

Ridge is the cheapest to fit and has the highest mean one-day R² in the pilot. GAM has slightly higher mean R² than HGB at seven and fourteen days and fits about eight times faster when averaged across the nine cases. However, GAM uses a higher whole-process memory peak and takes longer per single prediction than HGB. It is therefore not a universal winner across resource dimensions.

All three models fit in well under one second per retraining event on average and single predictions take under one millisecond on average. At this pilot scale, absolute computational cost alone gives little reason to reject any model. These data support measuring the practical trade-off, not claiming a deployment bottleneck or energy advantage.

## Interpretation limits

This is a small state-level tabular task. Ratios can look large even when all absolute costs are modest. Model selection should consider actual deployment constraints rather than assume that a slower model is impractical. Hardware and single-thread settings affect the ranking; these results should not be generalized to all implementations or deployment scales. Three repeats describe timing variability, not statistical uncertainty in model accuracy.

The original evaluation period has already been inspected. It must not become the iterative feature-selection set in Stage 2; choose features using development data and freeze the comparison before evaluating them.

## Reproduce

From the workspace root:

```sh
.venv/bin/python stage1/benchmark.py
.venv/bin/python stage1/summarize.py
```

Use the Stage 0 locked environment. Running again overwrites Stage 1 results. Raw per-case JSON includes native thread-pool details; CSVs include all repeats, per-case medians, ranges and model/horizon summaries. `environment.json` records machine details and benchmark/source hashes.

Hardware: '''+metadata['cpu']+f"; {metadata['memory_bytes']/1024**3:.0f} GiB physical memory; Python {metadata['python']}.\n"
(BASE/'REPORT.md').write_text(report)
print(a.round(4).to_string());print('\nACCURACY');print(h.R2.unstack().round(4).to_string())
