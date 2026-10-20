# Original-feature ablation

This corrects the scope of the prior ablation, which tested newly proposed features. That earlier work remains separate and is not evidence about removing the original feature groups.

Use only the paper's original 27 primary features, partitioned exactly by the original feature definitions:

- Calendar: 8 (seven calendar encodings plus year).
- CO₂ history: 13 (current emissions, historical lags, rolling means and standard deviations).
- Operational: 6 (load, heat input, SO₂, NOx, facility count and heat/load ratio).

Seven variants: full baseline; full minus each group; each group alone. Feature counts: 27, 19, 14, 21, 8, 13, 6 respectively. All models receive identical feature subsets in each variant. None of the eight Stage 2 additions enters this experiment. The paper's two emissions-ratio diagnostic predictors are not part of its primary 27 features, so they are excluded here too.

Scope: TX, PA, CA; 1-, 7-, 14-day horizons; Ridge, GAM, HGB; 189 configurations. Use Stage 0's corrected calendar alignment and observed-target cutoffs. Select hyperparameters anew for each variant using the existing 12-setting budget and prospective validation. Keep the same dates for all variants using the full baseline's complete-case population. Group-only variants therefore cannot gain extra, easier forecast dates by requiring fewer inputs.

Keep current emissions in the history group; removing history also removes today's emissions. This asks the incremental value of the entire history group, not solely older lags. Operational variables can proxy emissions, and correlated groups can substitute for one another. Leave-one-group-out measures conditional predictive value; group-only models measure stand-alone predictive ability, not causal importance.

Save paired predictions, tuning settings, split audits and error metrics. Report group removal changes by model and horizon, as well as pooled means. Computational times are exploratory single runs. Process memory spans nine cases per model/variant; it is not model-only memory. No significance or nationwide claims follow from this pilot.
