# Nationwide original-feature ablation

All **2,835 configurations** completed and passed validation: 45 states × 3 horizons (1, 7, 14 days) × 3 models × 7 variants. This extends the pilot geographically; it does not add the four intermediate horizons from the manuscript’s separate seven-horizon panel.

## Protocol

Supplied 2019–2025 state-day aggregates; original 27 primary predictors only. Full model, removal of each of the calendar/year, CO₂-history and operational groups, and each group alone. All models and variants share the full model’s complete-case origins and targets within each state/horizon. Missing calendar dates are reindexed; measurements remain missing, with no interpolation or filling. Original 12-setting prospective tuning grids and 14-calendar-day retraining retained. Two worker processes, one native compute thread each; timings are single-run and affected by concurrent execution.

The 189 overlapping pilot configurations reproduce the saved pilot predictions within the specified numerical tolerance. Inputs, pilot outputs and manuscript hashes are unchanged.

## Mean R² across 45 states

| Horizon | Model | Full | Without calendar/year | Without CO₂ history | Without operational |
|---:|---|---:|---:|---:|---:|
| 1 | RIDGE | 0.8218 | 0.8125 | 0.7971 | 0.8202 |
| 1 | GAM | 0.8123 | 0.8016 | 0.8052 | 0.8147 |
| 1 | HGB | 0.8145 | 0.7959 | 0.8054 | 0.8126 |
| 7 | RIDGE | 0.4296 | 0.4178 | 0.3850 | 0.4268 |
| 7 | GAM | 0.4789 | 0.3986 | 0.4687 | 0.4730 |
| 7 | HGB | 0.4667 | 0.4005 | 0.4572 | 0.4668 |
| 14 | RIDGE | 0.3352 | 0.3071 | 0.2980 | 0.3335 |
| 14 | GAM | 0.4230 | 0.2863 | 0.4263 | 0.4222 |
| 14 | HGB | 0.4219 | 0.2765 | 0.4288 | 0.4221 |

## Paired group-removal effects

Equal-weight averages across 135 state/horizon cases per model. Positive R² loss or RMSE change means removal worsened performance.

| Model | Removed group | Mean R² loss | Mean RMSE change | Cases worsened /135 |
|---|---|---:|---:|---:|
| RIDGE | calendar | +0.0164 | +2.23% | 122 |
| RIDGE | co2_history | +0.0355 | +4.70% | 133 |
| RIDGE | operational | +0.0020 | +0.24% | 79 |
| GAM | calendar | +0.0759 | +7.49% | 126 |
| GAM | co2_history | +0.0046 | +1.01% | 85 |
| GAM | operational | +0.0014 | -0.04% | 74 |
| HGB | calendar | +0.0767 | +8.01% | 127 |
| HGB | co2_history | +0.0039 | +1.10% | 85 |
| HGB | operational | +0.0005 | +0.11% | 71 |

## Group-only comparisons

| Model | Full mean R² | Calendar only | CO₂ history only | Operational only |
|---|---:|---:|---:|---:|
| RIDGE | 0.5289 | 0.1404 | 0.5125 | 0.4693 |
| GAM | 0.5714 | 0.3685 | 0.4958 | 0.4607 |
| HGB | 0.5677 | 0.3984 | 0.4940 | 0.4600 |

## Limits

These are descriptive, retrospective finalized-data results for the 45 eligible states, not all US jurisdictions or demonstrated live forecasting performance. No formal significance, confidence interval or causal-importance claim is made. Calendar includes year and seasonal/weekday encodings; this study does not isolate those components. CO₂ history includes current emissions. Correlated groups can substitute for one another, and every variant is retuned. Complete-case filtering varies the evaluated population across states/horizons. National means give equal weight to states rather than emissions volume.

The corrected protocol differs from the original manuscript’s saved evaluation; differences from its tables cannot be attributed solely to one correction. The original seven-horizon benchmark and formal statistical analyses would need separate comparable reruns to support all manuscript claims. Raw facility exports were unavailable, so supplied aggregation and eligibility were not independently reconstructed.

## Outputs

`results/paired_changes.csv`, `horizon_summary.csv`, `state_distribution.csv`, `coverage.csv`, `verification.json`, per-configuration `checkpoints/`, `predictions/`, and tuning/cutoff audit JSON. No manuscript was edited or published.
