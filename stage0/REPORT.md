# Stage 0 readiness report

## Outcome

The corrected local baseline is implemented and validated on a three-state pilot (TX, PA, CA; horizons 1, 7, 14), plus WA and DE at seven days to exercise actual missing-date/input cases. The original notebook, manuscripts and data are unchanged. This is pilot readiness, not completion of the nationwide reanalysis or manuscript revision.

## Corrections

1. Reindex to calendar dates before constructing lag and rolling features.
2. Construct targets before complete-case filtering so dropped input rows cannot shift the forecast target.
3. Exclude training outcomes dated after the fitting origin, including inside hyperparameter tuning.
4. Freeze hyperparameters before evaluation; use a common calendar evaluation start and 14-calendar-day retraining blocks.
5. Preserve model definitions, feature set, seed and original tuning grids; isolate outputs from originals.

The common calendar start and cadence are deliberate protocol standardizations in addition to leakage fixes. Differences from saved manuscript scores therefore reflect multiple changes, potentially including dependency versions, not solely removal of leakage.

## Pilot results

Mean R² across TX, PA and CA; higher is better. Means weight each state equally.

| Horizon | Ridge | GAM | HGB | Persistence |
|---|---:|---:|---:|---:|
| 1 day | 0.8725 | 0.8663 | 0.8698 | 0.8326 |
| 7 days | 0.5155 | 0.5827 | 0.5805 | 0.3495 |
| 14 days | 0.4277 | 0.5525 | 0.5470 | 0.1752 |

The broad short-vs-long horizon pattern persists in this pilot. GAM slightly exceeds HGB at seven and fourteen days on average. These descriptive differences are not significance tests, do not establish the crossover location, and do not validate the nationwide conclusions.

Mean R² changes across the nine pilot combinations relative to the supplied saved results: Ridge -0.0031, GAM -0.0052, HGB -0.0117, persistence -0.0020. See the per-state comparison for differences in evaluation sample counts.

## Verification

- Five temporal regression tests: exact target dates across missing days; no unavailable training targets; no future-input influence on past features; no target displacement after missing-input removal; valid inner and outer tuning cutoffs.
- All 315 extended state/horizon data constructions audited for exact calendar target dates.
- Nine pilot combinations and two missingness cases fitted for Ridge, HGB, GAM and persistence.
- Every fitting cutoff and final tuning split recorded for inspection.
- Original package hashes checked against the pre-work manifest.
- Repeat-run and output consistency checks recorded in `results/verification.json`.

## Remaining boundaries

The protocol still assumes finalized measurements at the end of each origin day; actual publication delay is not modeled. Complete-case filtering excludes unavailable origins, so missingness affects coverage. The raw facility exports and historical dependency lock are absent. The corrected national 315-combination model run, inferential tests and manuscript update remain outstanding. The pilot is sufficient to begin designing Stage 1 measurements, not to replace national manuscript results.

## Files

- `baseline.py`: corrected runnable implementation.
- `original_definitions.py`: extracted original features and model definitions.
- `test_baseline.py`: temporal regression tests.
- `requirements.lock.txt`: exact local dependency versions.
- `results/data_audit.csv`: nationwide data-construction audit.
- `results/pilot/summary.csv`: pilot scores.
- `results/pilot/original_vs_corrected.csv`: saved-vs-corrected descriptive comparison.
- Per-combination prediction CSVs, cutoff CSVs, settings JSON, and run environment metadata are in the result directories.

Next stage: instrument isolated tuning, training, prediction and memory measurements. Current elapsed times are execution logs, not a controlled computational benchmark.
