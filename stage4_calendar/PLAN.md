# Calendar component investigation

This is a forecasting analysis, not the previously skipped decision-support prototype.

Scope fixed before results: all 45 eligible states, all three models, 14-day horizon; seven removal variants (945 fits/evaluations). Remove sine/cosine pairs together. Separately remove month, weekday, day-of-year, weekend, year, both annual pairs, and all weekly encodings. Compare against existing full-feature and no-calendar results on identical dates. Reuse unchanged original-feature runner, tuning, complete-case population and temporal cutoffs. Retune each variant. No new features.

The fourteen-day horizon is selected because the previous nationwide ablation showed a strong effect there. Findings are conditional predictive comparisons for this horizon, not causal attribution or evidence across all horizons. Overlapping calendar representations make single-component removals insufficient, hence joint annual/weekly removals. No new significance tests are planned. Preserve saved predictions and verify metrics and paired dates before reporting.
