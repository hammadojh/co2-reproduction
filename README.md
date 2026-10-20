# CO2 forecasting reproduction package

Code, input aggregates, summary results and author revision materials for the corrected nationwide original-feature ablation and the fourteen-day calendar-component follow-up.

## Download the complete reproducible snapshot

**[Download the full package from release v1.0.0](https://github.com/hammadojh/co2-reproduction/releases/tag/v1.0.0)**

The release ZIP is the complete, validated snapshot, including every saved prediction, fitting audit, checkpoint and integrity manifest. This Git repository is a browsable subset: it omits bulky per-case predictions, checkpoints and audits. For the supported reproduction commands, extract the release ZIP and work inside its `Yusuf_CO2_reproduction` folder. Do not run archive verification from this smaller Git checkout.

The release also provides a SHA-256 checksum. See [reproduction instructions](REPRODUCING.md) for setup, validation, smoke testing and full refitting commands.

## Findings and documents

- [Author revision note](AUTHOR_REVISION_NOTE.md) and [Word version](AUTHOR_REVISION_NOTE.docx).
- [Nationwide original-feature ablation](stage3_full/REPORT.md): 45 states, seven horizons, three models, seven variants — 6,615 configurations.
- [Calendar-component follow-up](stage4_calendar/REPORT.md): 45 states, fourteen-day horizon, three models, seven removals — 945 configurations.
- [Packaging validation](VALIDATION.md): all 7,560 archived configurations verified; 12 freshly refitted configurations reproduced predictions exactly in an independent copy and clean environment. Full training was not repeated during packaging.

## Used code

- `stage0/original_definitions.py`: original features and tuning grids.
- `stage0/baseline.py`: corrected calendar alignment and temporal cutoffs.
- `stage1/benchmark.py`: model constructors and controlled pilot cost benchmark.
- `stage3_original/groups.py`: original feature groups.
- `stage3_nationwide/case.py`: shared tuning and rolling forecasting engine.
- `stage4_calendar/run.py`: calendar-component experiment.
- `reproduce.py`: packaged verification, smoke testing and full rerun entry point.

Earlier Stage 2 and Stage 3 new-feature experiments are retained as provenance; they are not inputs to the two original-feature studies above. Raw facility-level acquisition and aggregation are not reproduced: supplied daily state aggregates are included. Findings are descriptive, and the further investigations listed in the revision note remain proposed work.

This repository is private. Access to the repository and release assets requires permission from its owner.
