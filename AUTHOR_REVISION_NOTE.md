# Revision note: what the nationwide original-feature ablation adds

Dear Yusuf,

We have completed a nationwide ablation using the paper’s **original 27 primary features**. No newly proposed features were included. The analysis covers 45 eligible states, seven forecast horizons (1, 2, 3, 5, 7, 10 and 14 days), three models and seven feature variants: **6,615 configurations, with zero failed configurations**.

The main message is that **the original short-horizon versus longer-horizon pattern broadly survives, but its interpretation should become more specific**. Ridge performs best on average at one and two days. Nonlinear models become more competitive further ahead, and their advantage depends strongly on the original calendar/year inputs.

## What the results show

With all original features, the national mean R² values are:

| Forecast horizon | Ridge | GAM | HGB |
|---|---:|---:|---:|
| 1 day | 0.8218 | 0.8123 | 0.8145 |
| 2 days | 0.6697 | 0.6662 | 0.6658 |
| 3 days | 0.5774 | 0.5846 | 0.5761 |
| 5 days | 0.4779 | 0.5107 | 0.4971 |
| 7 days | 0.4296 | 0.4789 | 0.4667 |
| 10 days | 0.3677 | 0.4450 | 0.4359 |
| 14 days | 0.3352 | 0.4230 | 0.4219 |

These are equally weighted averages across states, not pooled national R² scores. The rankings are descriptive; differences have not been tested for statistical significance.

Three findings matter for the revision:

1. **The HGB crossover needs updating.** Under the corrected evaluation, HGB first exceeds Ridge at the tested five-day horizon. At three days, HGB is slightly below Ridge. The previous three-day crossover claim should therefore not be carried over unchanged.
2. **GAM has the highest average R² from three through fourteen days.** This supports discussing the usefulness of additive nonlinear effects. It does not establish that interactions are unnecessary in general, or that GAM is significantly better than HGB.
3. **Removing calendar/year inputs reverses the average model ranking.** Without this group, Ridge has the highest mean R² at every tested horizon. The longer-horizon nonlinear advantage is therefore strongly dependent on the available time-related predictors.

At fourteen days, the comparison is particularly clear:

| Feature condition | Ridge | GAM | HGB |
|---|---:|---:|---:|
| All original features | 0.3352 | 0.4230 | 0.4219 |
| Without calendar/year | 0.3071 | 0.2863 | 0.2765 |

Removing calendar/year reduces fourteen-day R² in **43 of 45 states for GAM** and **44 of 45 states for HGB**. This is a widespread pattern, rather than a result driven only by a few states.

Across all state–horizon cases, removing CO₂ history has the largest average effect on Ridge; removing calendar/year has the largest average effect on GAM and HGB. Removing operational inputs has a comparatively small average effect when the other groups remain. This does not mean operational inputs are useless: correlated predictors can supply overlapping information.

## Suggested changes to the manuscript

1. **Methods:** add an original-feature ablation subsection. Define the three groups—calendar/year (8 features), CO₂ history (13, including the current day) and operational inputs (6). Explain the seven conditions: all features, each group removed separately, and each group used alone. State that variants are retuned and evaluated on identical dates and targets within each state and horizon.
2. **Evaluation protocol:** explicitly document daily calendar alignment, construction of the target before complete-case filtering, and the requirement that training outcomes be observed by the fitting origin, including during tuning. Models are refitted every fourteen calendar days. These corrections must be disclosed when presenting the new results.
3. **Results:** add the nationwide ablation table or figure and update the model rankings and HGB crossover. Reconcile affected tables, figures, abstract statements and conclusions with the corrected evaluation. Existing significance claims cannot automatically be transferred to these new scores.
4. **Discussion:** explain that the benefit of nonlinear models depends on both forecast horizon and predictor availability. The ablation adds evidence about which original inputs support the observed ranking, beyond simply comparing model complexity.
5. **Limitations:** retain descriptive wording. The follow-up component ablation below isolates annual and weekly encodings and numeric year at fourteen days; this finer attribution has not been tested at the other horizons. The analysis uses finalized historical data and does not establish real-time input availability or operational decision benefits.

## Suggested manuscript paragraph

> A nationwide ablation of the 27 original predictors showed that the relationship between model performance and forecast horizon depended strongly on the calendar/year feature group. Under the corrected evaluation protocol, Ridge achieved the highest mean state-level R² at one and two days, whereas GAM achieved the highest mean at the tested horizons from three to fourteen days. HGB first exceeded Ridge at the tested five-day horizon. When calendar/year predictors were removed, Ridge achieved the highest mean R² at every tested horizon. At fourteen days, GAM and HGB mean R² decreased from 0.4230 and 0.4219 to 0.2863 and 0.2765, respectively; performance declined in 43 and 44 of the 45 states. These descriptive findings indicate that the longer-horizon advantage of nonlinear models depends strongly on their use of the available time-related predictors. They do not establish a causal mechanism or statistically significant differences between models.

## Scope and supporting material

The broad original conclusion remains useful: simple models perform well at short horizons, while nonlinear models offer gains further ahead. The stronger contribution from this analysis is showing **which original feature group supports that advantage**, while refining the crossover and model rankings.

These results use supplied 2019–2025 daily aggregates and a corrected evaluation protocol. Changes from the previous manuscript scores should not be attributed solely to one correction: evaluation choices and software versions also differ. Original facility-level aggregation and eligibility were not independently reconstructed. No confidence intervals or new significance tests were produced for this ablation.

Supporting files in the project package:

- Full report: `stage3_full/REPORT.md`.
- Horizon results: `stage3_full/results/full_horizon_summary.csv`.
- State-level distributions: `stage3_full/results/full_state_distribution.csv`.
- Figures: `stage3_full/results/calendar_comparison.png` and `stage3_full/results/nationwide_ablation.png`.
- Validation record: `stage3_full/results/full_verification.json`.

Saved predictions were checked for matching dates and targets across variants, exact forecast horizons and valid temporal cutoffs. Metrics were recomputed from predictions, and all 189 overlapping pilot configurations reproduced exactly. This note proposes revisions; the manuscript itself has not been changed as part of preparing it.


## Follow-up: which calendar components matter? (20 October 2026)

A further 945 configurations tested seven calendar-component removals across all 45 states and all three models, specifically at the fourteen-day horizon. Each model was retuned using the same protocol, with unchanged forecast dates and targets. All predictions, metrics and temporal cutoffs passed validation.

**The dominant predictive contribution comes from the annual-cycle encodings (month and day-of-year together), not the numeric year variable.** Removing both annual encodings leaves Ridge ahead of GAM and HGB on national mean R², even though year and all weekly inputs remain.

| Removed inputs | Ridge mean R² | GAM mean R² | HGB mean R² |
|---|---:|---:|---:|
| None (full baseline) | 0.3352 | 0.4230 | 0.4219 |
| Numeric year | 0.3353 | 0.4241 | 0.4192 |
| Month sine/cosine | 0.3351 | 0.4269 | 0.4202 |
| Day-of-year sine/cosine | 0.3330 | 0.3792 | 0.3923 |
| Both annual pairs | 0.3122 | 0.2786 | 0.2681 |
| All weekly inputs (weekday pair and weekend) | 0.3279 | 0.4109 | 0.4123 |

Removing both annual pairs worsens GAM in 43/45 states and HGB in 44/45 states. Their mean R² losses are 0.1444 and 0.1537, with median losses of 0.1409 and 0.1499. Removing year alone produces only small average changes. Weekly encodings have a smaller conditional contribution.

The overlap between annual encodings matters: removing month alone has little average effect, but removing month together with day-of-year has a large effect. Month can provide useful remaining annual information when day-of-year is absent. Individual removal effects therefore should not be added or interpreted as independent shares of importance.

Suggested addition to the Discussion:

> A component-level follow-up at the fourteen-day horizon localized the calendar-group effect primarily to the annual-cycle encodings. Removing both month and day-of-year sine/cosine pairs reduced GAM and HGB mean state-level R² to 0.2786 and 0.2681, respectively, below Ridge at 0.3122. In contrast, removing numeric year alone changed the corresponding full-model scores only slightly. These results support a predictive role for annual calendar patterns in the longer-horizon nonlinear advantage. They do not identify the physical causes of those patterns, establish statistical significance, or demonstrate the same component-level attribution at other horizons.

This follow-up refines the earlier bundled-group interpretation. It does not show that a calendar-only model is sufficient: each removal variant retains all original CO₂-history and operational predictors. The fourteen-day horizon was chosen because the prior nationwide analysis showed a strong effect there; this is an exploratory follow-up.

Full component results and validation: `stage4_calendar/REPORT.md`, `stage4_calendar/results/summary.csv`, and `stage4_calendar/results/verification.json`. Figure: `stage4_calendar/results/calendar_components.png`. Despite the directory name, this is an ablation follow-up, not the skipped decision-support prototype.

## Request for deeper investigation before finalizing the revision

Yusuf, please investigate this finding further rather than treating the component ablation as a complete explanation. The key question is: **does the longer-horizon advantage mainly reflect better modeling of recurring annual patterns, and how consistently does that explanation hold across horizons, states and years?**

The following checks would strengthen the revision, in priority order:

1. **Extend the component ablation across horizons.** Repeat the annual-pair, day-of-year, month and year removals at the remaining tested horizons (1, 2, 3, 5, 7 and 10 days), using the same paired evaluation protocol. Establish when dependence on annual patterns emerges and whether it coincides with the model crossover.
2. **Check stability across states and evaluation years.** Report paired losses by state and year, including exceptions. Assess whether annual encodings help consistently or whether their apparent benefit is concentrated in particular periods or states. Keep all fitting and tuning chronological.
3. **Quantify uncertainty in the comparisons.** Use a paired procedure that respects temporal dependence and dependence across states; account for multiple comparisons where applicable. In particular, assess the full-versus-no-annual contrast and the model ranking differences. Do not treat daily forecast errors as independent observations.
4. **Examine what the models learn from the annual encodings.** Plot GAM responses and suitable HGB response summaries for representative states. Vary each sine/cosine pair jointly along valid calendar dates, rather than changing one coordinate independently. Inspect month and day-of-year jointly for an annual profile, and check year-end continuity. These plots describe fitted associations, not physical causes.
5. **Test whether a richer seasonal baseline explains the gain.** Compare against a parsimonious regression with additional annual Fourier terms and regularization selected using training data only. This would help distinguish a benefit from flexible seasonal representation from a broader benefit of the model class.
6. **Check calendar alignment explicitly.** The current features describe the forecast origin date, not the target date. Compare a clearly specified target-date calendar variant, whose values are also known in advance, while holding other inputs and evaluation dates fixed. This is a sensitivity analysis, not an assumption that the existing origin-date encoding is invalid.

Please use these checks to decide how strongly the paper can explain the observed model-by-horizon pattern. If further analyses are not included, retain the narrower conclusion: **at fourteen days, removing the annual-cycle encodings eliminates the nonlinear models’ advantage in national mean R² under the tested protocol.** Avoid extending that component-level explanation to all horizons or attributing it to weather, demand or other physical mechanisms without additional evidence.

The checks above are proposed follow-up work for the revision; they have not been completed in the current analysis.
