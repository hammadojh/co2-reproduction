# Stage 2 readiness report

Eight candidate features are implemented in three groups: relative emissions dynamics (3), target-weekday history (2), and operational history (3). Combined with the 27 existing features, the full candidate set has 35 features. No models were fit and no accuracy gain is claimed.

## Verified

- Six regression tests passed: formulas; horizon/weekday alignment; future-input invariance; calendar gaps; zero-denominator behavior; unchanged baseline values and equal variant populations.
- Development-only feature/coverage audit completed for all 315 state–horizon combinations. Observations were truncated at the existing July 17, 2022 selection cutoff before constructing features/targets; no later outcomes were profiled.
- TX, PA, CA lose zero additional development origins for the planned 1-, 7-, 14-day pilot.
- Delaware loses 416 development origins per horizon (35.6–36.0%) when requiring every candidate feature. Missing load history drives this exclusion. Massachusetts loses 13 per horizon (about 1%). Other states lose none beyond baseline requirements.
- Facility-count change is constant in development data for eight states (AR, KS, ND, NE, NV, UT, WA, WY), across all seven horizons. It cannot distinguish observations there; retain the fixed group for the pilot rather than tune the feature list by test results.
- Dates excluded by candidate missingness must also be excluded from the baseline in the paired ablation. This protects comparison fairness but narrows the evaluated population; it does not resolve missing-data bias.

## Frozen comparisons

Baseline; baseline plus each of three groups separately; all groups; all minus each group. Eight variants in total. For the pilot this means 216 model/variant/state/horizon configurations. The source hashes and precise feature lists are saved in `results/candidate_plan.json`.

See `PLAN.md` for equations, hypotheses, leakage controls, measurement requirements and limitations. Stage 3 has not started. Nationwide extension should explicitly address the Delaware coverage problem before generalizing results.
