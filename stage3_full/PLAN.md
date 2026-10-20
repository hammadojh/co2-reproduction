# Complete nationwide original-feature ablation

Scope: 45 eligible states, 2019–2025 daily data, seven horizons (1,2,3,5,7,10,14 days), seven original-feature variants, three models: 6,615 configurations.

The existing stage3_nationwide run supplies horizons 1,7,14 (2,835 configurations). This complementary run supplies horizons 2,3,5,10 (3,780). The exact same case.py implementation and original 27 features are used; no new features or altered tuning protocol. Output directories and locks are separate, so the two runs cannot overwrite one another.

Initially there were two workers in the existing run and three in the extension. Both were resumed from checkpoints using scheduling-only wrappers: three workers for horizons 1,7,14 and six for horizons 2,3,5,10. Each limits native thread pools to one. Source feature/evaluation code and completed checkpoints were retained unchanged; actual scheduling overrides are recorded in each protocol.json. Predictions/accuracy are deterministic. Timings from concurrent runs, laptop suspension, and filesystem interruptions are unsuitable for hardware benchmarking; Stage 1 remains the source for controlled pilot timings.

Both runners checkpoint every completed configuration. Full summaries require all 6,615 unique configurations and validation of saved predictions, paired dates/targets, temporal cutoffs and source hashes. Intermediate progress is not a final result.

After the four-horizon extension completed, the remaining 1/7/14-day jobs were resumed with eight workers, preserving all completed checkpoints and unchanged evaluation code. All 6,615 configurations then completed; combined validation is recorded in results/full_verification.json.
