# EPA CAMPD Power-Sector CO2 Forecasting — Reproducible Package

Accompanies *"Optimal Forecast-Model Complexity Increases With Horizon in
Power-Sector CO2 Emissions: A Multihorizon, Seven-Year, 45-State
Benchmark."*

## The central finding

Across 45 U.S. states, seven years (2019-2025), and seven forecast
horizons (1, 2, 3, 5, 7, 10, 14 days; 315 state-horizon comparisons), the
relative performance of ridge regression versus histogram gradient
boosting (HGB) traces a smooth, nearly monotonic **crossover**: ridge
favored at one day (mean R2(HGB)-R2(ridge) = -0.0065), crossing to HGB
favored by three days, reaching +0.108 at fourteen days. This is
significant under cluster-robust regression clustered by Census region (4
clusters, p=0.0026) or by state (45 clusters, p<1e-6) — not just a
bootstrap CI or a two-point binomial test.

The crossover tracks a specific, tested mechanism: it coincides with the
decay of autoregressive persistence (median persistence R2 falls from
0.81 at one day to 0.44 at three days, near the crossover, to 0.04 by
fourteen days; correlation with the ridge-HGB gap across all 315
observations: r=-0.68). A genuine generalized additive model (smooth
per-feature splines, zero interaction terms) fit for TX/PA/CA at all seven
horizons closes nearly all of the ridge-to-HGB gap at long horizons,
isolating the mechanism: the value of complexity as persistence decays
reflects **smooth univariate nonlinearity**, not the higher-order
interactions only a tree ensemble can represent.

This nationwide, multihorizon, mechanistically grounded result is built on
top of an earlier, narrower two-horizon (1-day, 7-day), 47-state benchmark
and a detailed three-state case study (TX, PA, CA) that together show why
single-state or single-horizon superiority claims are fragile even when
nominally significant: the one comparison that appeared statistically
robust there (CA, one day) does not survive a substantially larger
hyperparameter search.

## Two corrections at the core of the three-state case study

1. **Feature-reconstruction asymmetry (redundant target encoding).** A
   feature set containing both contemporaneous load and an
   emissions-intensity ratio (co2_mass/load) lets a nonlinear model
   reconstruct current CO2 mass as their product — an interaction a linear
   model cannot form. Fix: current CO2 mass is an explicit feature
   (`co2_mass_lag0`); the reconstructable ratio features are excluded from
   the primary "full" specification and retained only for a diagnostic
   ablation.
2. **Hyperparameter-selection chronology.** Selecting a hyperparameter
   from a validation window chronologically later than some forecast
   origins introduces future information into model selection. Fix:
   `select_hyperparameters()` (Section 3 of the consolidated pipeline file)
   selects and freezes ridge and HGB hyperparameters (equal 12-point grids)
   using only data available before each evaluation design's own test period.

## Scope

**Three-state case study (TX/PA/CA, 2023-2025):** Persistence, ridge, and
HGB, symmetrically and prospectively tuned, tested with Diebold-Mariano
(Newey-West HAC, HLN small-sample correction) plus Holm/Benjamini-Hochberg
correction, plus mechanism-level diagnostics (feature-group ablation,
aligned-window protocol test, feature-representation/hyperparameter-
chronology sensitivity analysis, nested-CV retuning check).

**Two-horizon nationwide benchmark (47 states, 2023-2025):** the identical
pipeline applied to every state/district meeting five eligibility criteria
specified before the comparisons were run, at 1-day and 7-day horizons,
with Holm/BH correction across the full 94-test family, a paired
within-state test, a Census-region breakdown, and an expanded-search
robustness check.

**Multihorizon benchmark (45 states, 2019-2025, primary result):** the
identical pipeline extended to seven forecast horizons (1-14 days) on a
seven-year window, re-screened against the same five eligibility criteria
(45 of 51 states qualify over this longer window; two states that
qualified over 3 years — Idaho, Maine — do not qualify over 7). Includes
the national crossover figure, the persistence-decay mechanism check, a
cluster-robust regression of the horizon effect, and a three-state GAM
decomposition isolating smooth nonlinearity from interactions.

XGBoost and LSTM/LSTM-autoencoder results are retained for reference only
— produced on a different computing setup and not on equal methodological
footing with the primary results. Classical statistical baselines
(seasonal-naive, ARIMA) and a second boosting implementation were not
evaluated (see manuscript Limitations).

## Directory layout

```
code/
  epa_co2_forecasting_pipeline.py          Single consolidated file containing all analysis code (see below)

data/
  state_daily_TX_PA_CA_2023_2025.csv        Core three-state dataset (1,096 rows x 3 states)
  nationwide_eligibility.csv                Eligibility screening, all 51 states/districts, 2023-2025 window
  nationwide_state_daily/                   Per-state daily series, 47 eligible states, 2023-2025
  nationwide_predictions.csv, nationwide_summary.csv, nationwide_hyperparameter_log.csv
  nationwide_dm_tests[.csv|_corrected.csv]  Raw + Holm/BH-corrected DM tests, 1-day/7-day (Table 10, Figures 8-9)
  nationwide_direction_binomial_test.csv    Binomial test of the directional split at each horizon
  nationwide_paired_horizon_effect.csv      Paired within-state Delta_s(7)-Delta_s(1) Wilcoxon/t-test
  nationwide_regional_breakdown.csv, nationwide_region_assignment.csv   Census-region robustness check (Table 11)
  nationwide_expanded_summary.csv, nationwide_expanded_dm_tests[_corrected].csv   47-state expanded (30-ridge/60-HGB) search
  nationwide_expanded_hyperparameter_log.csv, nationwide_expanded_vs_primary_comparison.csv
  extended_eligibility.csv                  Eligibility screening, all 51 states/districts, full 2019-2025 window (45 eligible)
  extended_state_daily/                     Per-state daily series, 45 eligible states, 2019-2025 (2,557 days each)
  multihorizon_summary.csv                  Primary result: 45 states x 7 horizons, 315 rows (R2_ridge, R2_HGB, R2_persist, DM test)
  multihorizon_national_summary.csv         Bootstrapped national mean/CI of the ridge-HGB gap by horizon (Table 13, Figure 11)
  multihorizon_cluster_robust_regression.csv   Cluster-robust OLS of the horizon effect, region- and state-clustered (Table 14)
  gam_case_study_results.csv                GAM (spline+ridge, no interactions) results, TX/PA/CA x 7 horizons
  gam_national_summary.csv                  GAM results, all 45 multihorizon-eligible states x 7 horizons (315 rows)
  gam_national_vs_ridge_hgb.csv             Merged national ridge/GAM/HGB comparison (Table 15b, Figures 16-17)
  multihorizon_dm_tests_corrected.csv       Holm/BH correction across the full 315-test multihorizon DM family (Table 16b)
  wild_cluster_bootstrap_region.csv         Exact wild-cluster permutation test, region-clustered horizon regression
  gam_vs_ridge_vs_hgb.csv                   Merged ridge/GAM/HGB comparison by state-horizon (Table 15, Figure 12)
  single_split_benchmark.csv, single_split_hyperparameter_log.csv
  rolling_origin_predictions[.csv|_7day.csv], rolling_origin_summary[.csv|_7day.csv]
  rolling_origin_hyperparameter_log[.csv|_7day.csv]
  rolling_origin_dm_tests_full.csv, dm_tests_hln_corrected_both_designs.csv
  aligned_window_protocol_comparison.csv    Fixed-vs-rolling retraining on identical dates/hyperparameters (Table 4b)
  protocol_interaction_test.csv             Direct HAC test of the retraining-protocol effect (Table 4c)
  effect_size_block_sensitivity_consistent.csv, dm_lag_sensitivity.csv
  ramp_hac_regression_test.csv              Formal ramp-mechanism test (Section 3.6)
  rolling_origin_ablation.csv               Feature-group ablation under rolling-origin (Table 2)
  h1_incremental_operational_value_test.csv, h1_block_bootstrap_check.csv   (Table 2b)
  balanced_panel_forecast_comparison.csv, high_coverage_panel_forecast_comparison_7day.csv   (Table 7)
  high_coverage_panel_descriptive_stats.csv
  ca_reversal_decomposition.csv             Factorial sensitivity raw output (Table 8)
  nested_cv_retuning_robustness.csv         Expanded hyperparameter search robustness check, CA/TX (Table 8b)
  dataset_audit.csv, facility_level_missingness.csv, annual_state_summary.csv, state_trend_2023_2025.csv
  fair_one_day_benchmark_results.csv, fair_seven_day_benchmark_results.csv, exploratory_sequence_results.csv   Reference only

figures/
  fig1, fig2   Descriptive: daily series, annual totals (TX/PA/CA)
  fig3         DM p-values, single split vs. rolling-origin (Figure 4)
  fig4, fig5   Rolling-origin R2 with block-bootstrap CIs (1-day, 7-day)
  fig6         Feature-group ablation under rolling-origin
  fig7         Ramp-mechanism HAC-regression test
  fig8         Nationwide point-estimate direction, 47 states, 1-day/7-day
  fig9         Nationwide summary counts at three evidentiary standards
  fig10        Paired within-state horizon-effect shift, 47 states
  fig11        THE SIGNATURE FIGURE: R2(HGB)-R2(ridge) vs. horizon, 45 state trajectories + national mean/CI
  fig13        Primary vs. expanded-tuning crossover comparison (Table 16)
  fig14        State x horizon heatmap of the ridge-HGB crossover, grouped by Census region
  fig16        National GAM decomposition: mean R2 by horizon for ridge/GAM/HGB, all 45 states (Table 15b)
  fig17        State x horizon heatmap of R2(GAM)-R2(ridge), all 45 states (near-identical to fig14)
  fig18        U.S. tile-grid map (matplotlib patches, no shapefile) of the crossover at 4 horizons
  fig19        U.S. tile-grid map of the descriptive, censored estimated per-state crossover horizon
  fig20        Model architecture overview: structural comparison of ridge, GAM, and HGB (Section 2.7)
  fig21        GAM-ridge vs. total HGB-ridge gap identity plot, all 45 states x 7 horizons (replaces
               the former fig12/fig15, which duplicated fig16/fig14 in chart type -- see note below)
  fig22        Persistence mechanism, 2-panel: (a) persistence R2 decay by horizon, (b) persistence R2
               vs. the ridge-HGB gap scatter (r=-0.68), all 315 observations -- Section 3.13
  fig23        Horizon-dependent crossover by U.S. Census region: reveals the West lagging the other
               three regions from 3 days onward -- Section 3.13
  fig24        Distribution (box+strip) of the ridge-HGB gap across all 45 states, by horizon --
               cross-sectional complement to fig11's per-state trajectories -- Section 3.12
  fig25        BH-significant state counts favoring ridge vs. HGB, by horizon -- visualizes the
               corrected Table 16b (see note below) -- Section 3.12
  schematic_pipeline.png   Pipeline schematic embedded in Section 2.1 (unnumbered, separate from the Figure series);
               shows the ridge<->HGB primary benchmark and ridge<->GAM<->HGB mechanism analysis, both run on
               all 45 states; horizon-effect (cluster-robust) inference is scoped to the ridge<->HGB branch only

manuscript/
  Revised_Manuscript_EPA_ThreeYear_Validation.docx
```

## A note on figure redundancy and the Table 16b correction

Figures 12 and 15 (both TX/PA/CA-specific restatements of chart types
already shown at national scale in Figures 14/16/17) were removed this
round as duplicative, per explicit feedback, and replaced with five new
figures (21-25) chosen to reveal distinct aspects -- mechanism (21, 22),
spatial heterogeneity (23), distributional shape (24), and multiplicity-
corrected evidence (25) -- rather than restating existing chart types.
All five were verified against the underlying CSVs before being written
into any figure; building Figure 25 in the process surfaced a real error
in Table 16b, whose "Direction" column had claimed "All HGB" for several
horizons (2, 3, 5, 7) when the BH-significant subset at those horizons
actually included some ridge-favoring states too (only the smaller,
more conservative Holm-significant subset was genuinely single-direction
at every horizon). Table 16b now reports the ridge/HGB split for both
corrections directly instead of a single ambiguous label. All edits from
this round are rendered in red font in the manuscript, per request, so
they are visually distinguishable from prior content.

## Code: multi-script pipeline

All analysis code lives in `code/` as 25 focused, independently runnable
scripts organised by analysis stage. Each script imports from the shared core
modules (`pipeline.py`, `models.py`, `select_hyperparameters.py`,
`dependent_error_tests.py`) and writes its results directly to `data/`.

> **Note:** Earlier versions of this README referred to a single consolidated
> file `epa_co2_forecasting_pipeline.py`. That file does not exist in this
> package — the analysis is distributed across the 25 scripts listed in the
> Directory Layout section above.

Run any stage directly:
```
python code/<script_name>.py [batch_size]
```
or from the notebook `code/MoussaV2.ipynb` using the `run_stage()` helper.
Resumable nationwide/multihorizon stages accept an optional `[batch_size]`
to process only the first N not-yet-done states or state-horizon
combinations — all are safe to interrupt and re-run.

Script inventory by stage:

| Script | Stage |
|--------|-------|
| `build_three_year_state_dataset.py` | Build TX/PA/CA state-day dataset |
| `build_nationwide_eligibility.py` | Screen all 51 states, 2023-2025 |
| `build_extended_eligibility.py` | Screen all 51 states, 2019-2025 |
| `run_rolling_origin_backtest.py` | Three-state rolling-origin backtest |
| `run_validation_analysis.py` | Bootstrap CIs, ablations, alpha sensitivity |
| `run_single_split_benchmark.py` | Single-split reference benchmark |
| `run_corrected_benchmark.py` | Corrected single-split benchmark |
| `run_nationwide_benchmark.py` | 47-state 1/7-day benchmark (resumable) |
| `run_nationwide_expanded_tuning.py` | 47-state expanded HP search |
| `run_nationwide_horizon_sweep.py` | 47-state horizon sweep |
| `run_multihorizon_sweep.py` | 45-state 7-horizon primary sweep (resumable) |
| `run_multihorizon_expanded_tuning.py` | 45-state expanded HP search |
| `run_gam_national.py` | GAM decomposition, all 45 states |
| `run_matched_tabular_benchmarks_with_xgboost.py` | XGBoost reference |
| `run_dependent_error_analysis.py` | Dependent-error DM analysis |
| `decompose_ca_reversal.py` | CA factorial sensitivity |
| `run_validation_analysis.py` | Validation and robustness |
| `make_validation_figures.py` | Figures |
| `wild_cluster_bootstrap_region.py` | Wild-cluster permutation test |
| `calibrate_simulation_from_campd.py` | Simulation calibration |
| `select_hyperparameters.py` | Shared HP selection (library) |
| `dependent_error_tests.py` | DM / NW / bootstrap tests (library) |
| `models.py` | Ridge / HGB / metrics (library) |
| `pipeline.py` | Feature engineering (library) |

Consolidation was verified: after the multi-file reorganization, four
representative code paths spanning the riskiest renamed functions (the
core single-split pipeline, the multihorizon-specific path, the
nationwide-specific path, and the wild-cluster bootstrap) were re-run
and their outputs compared against the previously saved results.

## A note on manuscript structure

As of this round, Results and Discussion are merged into a single "3.
Results and Discussion" section, with interpretation woven directly into
each result rather than presented separately afterward. The former
Discussion subsections (4.1-4.6) are now distributed across the relevant
Results subsections; two of them (the CA factorial-sensitivity analysis
and the expanded-search robustness check, formerly Discussion-only
content) are now proper Results subsections in their own right (3.6a,
3.6b), since they present new tables and findings rather than pure
interpretation. Limitations remains a distinct final subsection of
Section 3. The Conclusion is renumbered from Section 5 to Section 4.

## A note on the wild-cluster bootstrap correction

An earlier round of this analysis reported the region-clustered (G=4) cluster-robust
regression as significant based on the asymptotic CR1 p-value (p=0.0026). Verifying this
before finalizing it showed the asymptotic approximation is not trustworthy at G=4: an
exact wild-cluster sign-flip permutation test (Cameron, Gelbach & Miller 2008), enumerating
all 2^4=16 possible cluster-level sign assignments exactly, gives p=0.125 -- not significant.
The manuscript's headline horizon-effect claim now rests on the state-clustered test (G=45,
p<10^-6), which is on much firmer asymptotic ground; the region-clustered result is reported
alongside it with this caveat rather than as independent confirmation. See Section 14 of `code/epa_co2_forecasting_pipeline.py`
(stage `wild_cluster_bootstrap`) and `data/wild_cluster_bootstrap_region.csv`.

## A note on equation formatting

All formal equations (RMSE/MAE/MAPE/R2/DeltaRMSE%, the DM and DM* statistics, the ramp
HAC regression, the Delta-d protocol-interaction test, the Delta(s,h) cluster-robust
regression target, and the CR1 correction factor) are built as native Word equation
objects (OMML, via the `docx` npm package's `Math`/`MathRun`/`MathFraction`/etc. classes),
not italicized plain text. Each equation's underlying XML was checked for well-formedness
and correct element nesting (no math component illegally nested inside a text node) after
every edit.

LibreOffice -- the only rendering engine available for this project's own visual
verification -- does not display OMML content: converting the .docx to PDF via LibreOffice
renders each equation as blank space with only its trailing number (e.g. "(1)") visible,
even though the equation's XML is well-formed and uses the correct namespace. This appears
to be a LibreOffice/OMML compatibility gap rather than a malformed-document issue, since
OMML is Word's own native equation format. The equations should display correctly in
Microsoft Word; this could not be independently confirmed as part of this package's
verification and is worth a manual check in Word before submission.
## To reproduce from raw data

All stages below are run from `code/epa_co2_forecasting_pipeline.py` via
`python epa_co2_forecasting_pipeline.py <stage> [batch_size]` (see "Code:
single consolidated file" above for the full stage list).

1. Place the raw `daily-emissions-facility-aggregation*.csv` CAMPD exports
   (one per year, 2019-2025) in one folder (referenced as
   `/mnt/user-data/uploads` by default; adjust `UPLOAD_DIR` in the file if needed).
2. Three-state case study: stage `build_dataset`, then `single_split` and
   `rolling_origin`.
3. Two-horizon nationwide benchmark: stage `nationwide_eligibility`, then
   `nationwide_benchmark` (resumable: pass a batch size, e.g.
   `python epa_co2_forecasting_pipeline.py nationwide_benchmark 10`; skips
   states already in `nationwide_summary.csv`), then `nationwide_expanded`
   the same way.
4. Multihorizon benchmark (primary result): stage `extended_eligibility`
   to screen all 51 states over 2019-2025 and build
   `data/extended_state_daily/`, then `multihorizon_sweep` (resumable the
   same way; flushes to disk after every state, so a mid-batch timeout
   loses at most one state's progress), then `multihorizon_expanded` and
   `gam_national` the same way.
5. Downstream analyses (DM tests, multiplicity correction, effect sizes,
   ramp regression, balanced panel, ablations, aligned-window and
   nested-CV robustness checks, the persistence-decay/cluster-robust
   regression, the GAM decomposition, the wild-cluster permutation test)
   are built on the core library functions in Sections 1-4 of the same
   file; see the manuscript's Methods section for the exact specification
   of each.

Random seed 42 is used throughout for every stochastic operation.
