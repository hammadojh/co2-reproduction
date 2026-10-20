# Package validation

Validated on 20 October 2026 using a separate copy outside the project workspace and a newly created Python 3.14 virtual environment. All pinned requirements installed successfully.

- Every distributed payload hash verified.
- All 7,560 archived configurations passed prediction, metric, paired-population and temporal-cutoff checks.
- Regenerated horizon summaries matched both original-feature and calendar-component reference summaries to 1e-12 tolerance.
- All 12 fresh smoke configurations reproduced archived predictions and selected hyperparameters. Maximum absolute prediction difference: 0.0.
- All five existing Stage 0 temporal regression tests passed.

The complete 7,560-configuration training workload was not rerun during packaging. Full results were verified from the saved predictions; 12 configurations were freshly refitted. This establishes the recorded local reproduction check, not an execution test on every operating system.
