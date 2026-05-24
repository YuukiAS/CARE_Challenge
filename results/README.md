# CARE Results Directory

`results/` contains generated outputs, local diagnostics, metrics, predictions,
and submission packages. Most heavy or reproducible artifacts are intentionally
ignored by git; durable conclusions should be mirrored in `docs/notes/` or the
main runbook.

## Layout

| Path | Purpose | Git policy |
| --- | --- | --- |
| `diagnostics/care_myocardium/` | Current CARE Myocardium lane/round diagnostics. Round directories are zero-padded where needed, for example `laneA_myops/round02_edema_postprocess_smoke` through `laneA_myops/round15_deepresearch_portfolio`. | Ignored; track summaries under `docs/notes/`. |
| `diagnostics/baseline_paper_models/` | Historical paper-baseline diagnostics for MyoPS-Net, U-MyoPS, and CineMyoPS. | Ignored. |
| `metrics/unified/` | Unified Dice/HD/HD95 evaluation outputs. Canonical baseline metric summaries may be tracked explicitly; ad-hoc variants are ignored by `.gitignore`. |
| `predictions/` | Local model predictions and postprocessed variants. | Ignored. |
| `checkpoints/` | Local training checkpoints and run outputs. | Ignored. |
| `submissions/care_myocardium_validation/upload_ready/` | Validation package directories. Directories are timestamp-first: `<YYYYMMDD_HHMMSS>__<run_label>`. | Package trees/zips ignored; policy README files may be tracked. |
| `experiments/` | Lightweight iteration logs. | Track when they summarize decisions or experiment history. |
| `leaderboard/` | CARE2026 leaderboard snapshots fetched locally. | Generated snapshots ignored. |

## CARE Myocardium Diagnostics Root

Use this root for new lane diagnostics:

```text
results/diagnostics/care_myocardium/
```

Current lane layout:

```text
results/diagnostics/care_myocardium/
  failure_registry/
  laneA_myops/
    round02_edema_postprocess_smoke/
    round03_trainable_smoke/
    round04_fold0_short_train/
    ...
    round15_deepresearch_portfolio/
  laneB_cine/
    round02_topology_lcc/
    round03_hosted_calibration/
    round03_pretrained_screening_metadata/
  laneC_da/
```

Do not add new CARE Myocardium outputs under legacy or ambiguous names such as
legacy phase-style roots, bare `round3`, or top-level `CineMyoPS_roundX`.
