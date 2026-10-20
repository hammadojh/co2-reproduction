# Reproducing the CO2 forecasting ablation report

This package contains the code actually used, supplied input data, per-forecast predictions, fitting audits, checkpoints, summary tables, figures and the author revision note. It reproduces the corrected analyses discussed in the note, not the uncorrected manuscript scores.

## Start here

1. Read `AUTHOR_REVISION_NOTE.docx` or the Markdown version.
2. Install the pinned environment below.
3. Run `python reproduce.py verify` to verify all supplied results without retraining.
4. Run `python reproduce.py smoke` to refit 12 representative configurations and compare every prediction with the supplied reference.
5. Run either full study when ready. No new data download, credentials or API keys are needed after installing the dependencies.

## Environment

The recorded execution environment is CPython 3.14.0 on macOS Apple Silicon. Package versions are pinned in `requirements.txt`, copied unchanged from `stage0/requirements.lock.txt`. Use Python 3.14; older Python versions may not support these pins. macOS and Linux are the intended environments. The inherited benchmarking module uses the Unix `resource` module, so native Windows execution is not supported; use WSL if needed. Different operating systems or numerical libraries may produce small numerical differences. The package records versions and checks predictions rather than assuming cross-platform identity.

From the extracted `Yusuf_CO2_reproduction` folder:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python reproduce.py verify
python reproduce.py smoke --workers 2
```

The smoke check fits all three models at TX horizon 1 with full features, and at TX horizon 14 with full features, both annual encodings removed, and year removed: 12 configurations. It is an execution/regression check, not a replacement for nationwide validation. Verification reconstructs metrics from all 7,560 saved prediction files and checks paired populations, exact calendar horizons and temporal cutoffs. It also verifies the package SHA-256 manifest.

## Refit the studies

```bash
# Original 27-feature group ablation: 45 states x 7 horizons x 3 models x 7 variants
python reproduce.py run --study original --workers 2

# Calendar component follow-up: 45 states x 14-day horizon x 3 models x 7 removals
python reproduce.py run --study calendar --workers 2

# Or run both studies together
python reproduce.py run --study all --workers 2
```

Choose one of the separate-study or combined approaches; their output directories are separate, so using both duplicates work. Each worker uses one native numerical thread. Two workers is a conservative default; more workers can speed execution at higher CPU and memory cost. A full refit may take substantial time depending on hardware. This package does not claim a portable runtime estimate.

Fresh output goes to `reruns/<study>/`; smoke output goes to `reruns/smoke/`. Supplied results remain unchanged. Each completed configuration is checkpointed. Repeating the same command resumes verified checkpoints and refuses a resume if the code, input data, environment or task list changed. If the process was force-killed, confirm no runner is active before removing its stale `RUNNING.lock`. Do not launch two runs into the same output directory.

Each fresh configuration is compared with its archived predictions and selected tuning setting. Prediction tolerance is `rtol=1e-10, atol=1e-7`; failure is reported rather than hidden. If another platform fails this strict comparison, retain its outputs and inspect the differences before making reproducibility claims. To conduct new experiments, use a separate copy and adapt the comparison logic deliberately; this entry point is for reproducing the existing results.

## What is included

| Location | Purpose |
|---|---|
| `reproduce.py` | New packaging entry point; calls the unchanged fitting engine and adds verification, safe output separation and checkpointing |
| `Manuscript V1/Data/extended_state_daily/` | 45 supplied state-level daily aggregate CSVs used in the nationwide analyses |
| `Manuscript V1/Data/extended_eligibility.csv` | Supplied eligibility decisions |
| `Manuscript V1/EPA_CO2_Forecasting_Pipeline.ipynb` | Original notebook for provenance; contains old paths and historical issues, not the recommended execution entry point |
| `stage0/original_definitions.py` | Original feature definitions and tuning grids |
| `stage0/baseline.py` | Corrected calendar-aligned target construction and available-outcome training filters |
| `stage1/benchmark.py` | Model constructors used by the fitting engine; also original controlled pilot cost benchmark |
| `stage3_original/groups.py` | Partition of the 27 original predictors and seven group variants |
| `stage3_nationwide/case.py` | Unchanged per-configuration tuning and rolling prediction engine used in both studies |
| `stage3_nationwide/results/` | Original-feature results at horizons 1, 7 and 14 |
| `stage3_full/results/` | Original-feature results at horizons 2, 3, 5 and 10, plus combined seven-horizon summaries |
| `stage4_calendar/` | Calendar-component code and 945 completed follow-up configurations at 14 days |
| `stage0`, `stage1`, `stage2`, `stage3`, `stage3_original` | Earlier baseline, cost, proposed-feature and pilot work retained for provenance and historical manifest dependencies |
| `PACKAGE_MANIFEST.json` | SHA-256 of every distributed payload file except the manifest itself |
| `SOURCE_PROVENANCE.json` | Identity of copied source material; no original workspace paths needed |

The newly proposed features in `stage2` and `stage3` are earlier exploratory work and are NOT inputs to either main study in this report. The `stage4_calendar` folder is an ablation follow-up, not a decision-support prototype. Original manuscripts and other supplied data are retained for context. Historical launcher, watcher, timing and status metadata are archival; use `reproduce.py` as the supported package entry point.

## Protocol to preserve

- Daily calendar reindexing without interpolation or imputation.
- Target at exactly t+h calendar days, constructed before incomplete rows are removed.
- All variants use the full 27-feature baseline complete-case population within a state/horizon.
- Training origins precede the fitting origin, with training target dates no later than that fitting origin. The same availability restriction applies to tuning.
- Common evaluation start from the midpoint of the calendar after the 30-day warmup; refitting every 14 calendar days and forecasts on eligible daily origins.
- Original 12-setting tuning grids; each variant retuned prospectively before evaluation.
- Calendar features describe origin date t. End-of-day availability is assumed, including current-day CO2 and operational observations.
- Equal state weights for reported national mean R2; these are not pooled national R2 scores.

The original groups are calendar/year (8), CO2 history (13) and operational inputs (6). Seven variants use all groups, remove each group, or retain each group alone. The calendar follow-up removes month sine/cosine, weekday sine/cosine, day-of-year sine/cosine, weekend, numeric year, both annual pairs together, or all weekly inputs together.

## Expected headline checks

At 14 days, full-feature mean R2 is Ridge 0.3352, GAM 0.4230, HGB 0.4219. Removing both annual encodings yields 0.3122, 0.2786 and 0.2681 respectively. Removing numeric year alone yields 0.3353, 0.4241 and 0.4192. Full original-feature results favor Ridge at 1–2 days and GAM at 3–14 days; HGB first exceeds Ridge at the tested five-day horizon.

`reproduce.py verify` writes newly reconstructed `metrics.csv`, `paired_changes.csv`, `horizon_summary.csv` and `verification.json` to `reproduced_summaries/`. Original summaries, plots and narrative reports remain in their stage directories. Fresh runs create the same summary file types under their rerun directory. Paired losses use the supplied full-feature baseline, which fresh baseline cases are independently checked against.

## Limits

The package starts from supplied historical aggregates. Raw facility-level exports and an independently rebuilt eligibility pipeline are unavailable, so this does not reproduce raw-data acquisition or aggregation. The dependency lock describes the corrected analyses, not necessarily the original manuscript environment. Finalized data availability does not establish real-time deployment feasibility. Component-level findings are currently limited to 14 days. No causal conclusions, new confidence intervals or statistical-significance claims are established. Proposed further analyses in the author note have not been completed.

The earlier concurrent run timings are not suitable for computational-cost claims; the controlled Stage 1 pilot remains separate. No cloud service, scheduler, email sender or paid external job is invoked by the supported reproduction commands.
