# Stage 2 candidate features and frozen ablation plan

## Purpose

Test whether explicit representations of recent relative change, weekly history and operating conditions improve the accuracy–cost trade-off. These are proposed extensions to this supplied feature set, not claims of novel feature-engineering methods. No accuracy screening or model fitting is performed in Stage 2.

## Existing baseline

27 features: seven calendar encodings plus year; CO₂ lags 0, 1, 2, 3, 7, 14, 30; prior-day-shifted rolling mean and standard deviation over 7, 14, 30 days; current load, heat input, SO₂, NOx, reporting-facility count and heat input/(load+1).

The baseline already captures weekly lags and rolling emissions patterns. Adding those again would not constitute a new feature group. Raw differences of existing lags are linearly representable by Ridge, although reparameterizing them can alter its regularization; they should not be described as new information.

## Candidate groups: eight features

Let C(t) denote emissions, L(t) gross load, H(t) heat input, N(t) facility count. All dates are calendar dates, not retained-row positions. Inputs at t are assumed finalized and available at the end of day t, as in Stage 0.

| Group | Feature | Exact definition | Hypothesis |
|---|---|---|---|
| Relative dynamics | One-day relative change | [C(t)−C(t−1)] / C(t−1) | Recent proportional changes may transfer across emission levels. |
| Relative dynamics | Seven-day relative change | [C(t)−C(t−7)] / C(t−7) | Represent change relative to the previous week. |
| Relative dynamics | Departure from recent level | [C(t)−mean(C(t−7)…C(t−1))] / mean(C(t−7)…C(t−1)) | Distinguish unusually high or low current emissions relative to recent history. |
| Weekday history | Target-weekday mean | Mean of four most recent observed-calendar positions with the same weekday as t+h, all at or before t | Explicitly represent the weekly pattern relevant to the day being forecast. |
| Weekday history | Target-weekday standard deviation | Sample standard deviation of the same four positions | Describe variability of that weekday's historical emissions. |
| Operational history | Relative load week change | [mean(L(t−6)…L(t))−mean(L(t−13)…L(t−7))] / mean(L(t−13)…L(t−7)) | Represent changes in recent generation rather than only today's level. |
| Operational history | Seven-day mean heat/load ratio | mean(H(s)/(L(s)+1)), s=t−6…t | Represent recent operating conditions; retain the baseline ratio definition. |
| Operational history | Seven-day facility-count change | N(t)−N(t−7) | Represent changes in the reporting/operating population. This cannot distinguish missing reporting from genuine operation. |

For weekday history, offset = (−h) mod 7; use t−offset, t−offset−7, t−offset−14 and t−offset−21. For h=1 these are lags 6,13,20,27; for h=7 or 14, lags 0,7,14,21. Today's value is allowed by the end-of-day information assumption. No future observation is used. Mean and standard deviation require all four positions, not any four available records.

Relative dynamics re-express existing observations nonlinearly; they do not introduce new raw information. Weekday/operational groups also expose historical values and summaries not supplied explicitly in the baseline. If Ridge improves, this tests representation as well as model flexibility; it does not show that nonlinear relationships are unnecessary.

Nonpositive denominators produce missing values rather than arbitrary epsilon adjustments. No global normalization, imputation, clipping or feature selection is learned from the test period. Missing dates remain missing; all rolling windows require every calendar value.

## Prespecified Stage 3 comparisons

Eight variants, applied to Ridge, GAM and HGB:

1. Baseline: 27 original features.
2. Baseline + relative dynamics: 30.
3. Baseline + weekday history: 29.
4. Baseline + operational history: 30.
5. Baseline + all candidate groups: 35.
6. All minus relative dynamics: 32.
7. All minus weekday history: 33.
8. All minus operational history: 32.

Use the intersection of dates valid for all eight variants, in both development and evaluation, so comparisons are paired. Rerun the baseline on that same population; do not simply subtract Stage 0 scores if dates differ. Report excluded dates and coverage separately. Fit preprocessing only on training data. Retune each model/variant prospectively with the existing 12-setting grid and unchanged temporal cutoffs; preserve the Stage 0 selection cutoff and retraining cadence.

Begin with TX/PA/CA at horizons 1,7,14: 8 variants × 3 models × 9 cases = 216 model/variant/case configurations. Compare R², MAE and RMSE, together with feature-construction, tuning, training, prediction costs and clearly scoped memory measurements. Report per-case changes as well as equal-state aggregates; no nationwide claims from the pilot. Do not declare a winner from timing or tiny accuracy differences alone.

The prior test outcomes have already been seen in Stages 0–1. These are frozen confirmatory comparisons within that existing retrospective benchmark, not an untouched external validation. Do not iteratively add or drop features in response to test results; any later redesign needs a separate validation strategy. No statistical-significance claim is prespecified here without an appropriate dependent-error and multiple-comparison analysis.

## Readiness checks

Six tests check hand-calculated formulas, weekday alignment across all seven horizons, future-input invariance, actual calendar gaps, zero-denominator handling, baseline preservation and common variant dates. `audit.py` profiles only data at or before the established development cutoff for all 45 states and seven horizons. `results/candidate_plan.json` records groups, variants and source hashes before the ablation.

```sh
.venv/bin/python -m unittest discover -s stage2 -v
.venv/bin/python stage2/audit.py
```

Stage 3 model experiments have not started. No candidate is claimed to improve accuracy yet.
