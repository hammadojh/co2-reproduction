# Stage 0: corrected forecasting baseline

This directory preserves the supplied package and implements a separate, reproducible baseline. It does not add features or measure the Stage 1 performance trade-off.

## Protocol

- Data: supplied extended daily state series, 2019–2025.
- Original feature engineering and Ridge/HGB/GAM definitions are extracted into `original_definitions.py`; all 27 original features are retained.
- Reindex each state to daily calendar dates before lagging. Missing observations stay missing; no forward filling or interpolation.
- Construct the outcome at the exact calendar date t+h BEFORE dropping rows with missing predictors/outcomes.
- Complete-case evaluation: only origins with all required inputs and observed targets are scored. Missingness may change the evaluated population; report coverage rather than interpreting dropped days as random.
- Fixed evaluation start: midpoint of the calendar after the original 30-day warmup, shared across horizons. This deliberately differs from the notebook's horizon-dependent midpoint of retained rows.
- End-of-day information assumption: a target dated t is known at origin t. This is a retrospective finalized-data benchmark, not proof of real-time public data availability.
- For every fit at t, include only earlier origin rows whose target date is at or before t. Retrain every 14 CALENDAR days. Between retrains, issue daily forecasts using each day's observed features, not all block features at block start.
- Select settings once before the evaluation period using the final 15% of available development rows as validation. Purge inner training targets later than the first validation origin. All tuning validation targets must be observable at the outer selection cutoff.
- Retain original 12-choice grids for Ridge, HGB and GAM alpha; original GAM uses five cubic-spline knots. No new hyperparameter search.
- Compare all models on exactly the same origins within each state/horizon. Different horizons may have different available end dates.
- Single native compute thread; fixed original random seed 42. Dependency versions are locked. No original historical environment lock exists, so exact cross-version manuscript reproduction is not guaranteed.

## Commands (from workspace root)

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r stage0/requirements.lock.txt
.venv/bin/python -m unittest discover -s stage0 -v
.venv/bin/python stage0/baseline.py
```

Default pilot: TX, PA, CA at 1, 7, 14 days. To check missing-date behavior on real data:

```sh
.venv/bin/python stage0/baseline.py --states WA DE --horizons 7 --output results/gap_checks
```

Outputs include predictions, exact training cutoff audit trails, selected settings, metrics, and environment metadata. `source_manifest.json` records hashes of the original input package. Existing outputs are overwritten only within the selected Stage 0 output directory; choose a new `--output` for separate runs.

## Scope and remaining limits

Stage 0 validates this corrected primary baseline. It does not refresh the manuscript, expanded-grid analysis, statistical significance tests, or all 315 national comparisons. The original saved scores and corrected scores use different evaluation protocols, so their difference is not a controlled estimate of the effect of leakage alone. A national rerun is required before asserting a corrected nationwide crossover. Future feature selection must use development data, not repeatedly optimize against this test period.
