# M10 Wave 2 Retry11 Hard-Negative Completion Monitor

State: `NEEDS_MONITOR`

This is a monitor packet, not completion evidence and not a request for independent review.

## Live Slurm State

Checkpoint time: `2026-07-13T16:59:11Z`

| Phase | Job ID | State | Evidence |
| --- | ---: | --- | --- |
| hard-negative refresh | `58775068` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `01:39:59`, node `g1807htzh01` |
| no-nnU-Net-context control | `58775069` | `RUNNING` | `htzhulab`, elapsed `00:01:52`, node `g1807htzh01` |
| alignment control | `58775070` | `PENDING (Dependency)` | waits on no-context control `afterok` |
| Wave 2 finalizer | `58775071` | `PENDING (Dependency)` | waits with `afterany` |

No-context live memory accounting for `58775069.batch`:

```text
MaxRSS=10817848K
AveRSS=10634252K
MaxVMSize=0
AveVMSize=0
```

## Hard-Negative Completion Evidence

Hard-negative refresh produced final runtime outputs under:

```text
results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor/partition_race_retry11/htzhulab/variants/m10_d3_hard_negative_refresh/
```

Key summary fields:

| Field | Value |
| --- | ---: |
| `actual_optimizer_steps` | `20000` |
| `train_loop_seconds` | `5684.537394266925` |
| `process_wall_seconds` | `5665.014930574` |
| `validation_event_count` | `10` |
| `eval_cases` | `44` |
| `stop_reason` | `max_steps_min_train_loop_seconds_satisfied` |
| `best_step` | `14000` |
| `best_val_patch_loss` | `1.157816195487976` |
| `first_train_loss` | `4.220096588134766` |
| `last_train_loss` | `0.4855440557003021` |
| `loss_decrease` | `3.7345525324344635` |
| `one_batch_overfit.status` | `PASS` |

Final lightweight runtime files:

| File | Size / rows |
| --- | ---: |
| `summary.json` | `25770` bytes |
| `training_log.csv` | `212` lines including header |
| `validation_events.csv` | `11` lines including header |
| `retrieval_usage.csv` | `54673` lines including header; `6980066` bytes |

## No-Context Monitor Evidence

No-context control has started and written early sanity files:

```text
one_batch_overfit.csv
one_batch_overfit.json
prototype_bank_summary.json
prototype_update_sanity.csv
```

At this checkpoint no-context control has not yet produced final `training_log.csv`, `validation_events.csv`, or `summary.json`.

## Decision

Current state remains `NEEDS_MONITOR`, not complete and not reviewable. Hard-negative refresh completed successfully, no-context control is running, and alignment remains correctly blocked by `afterok`. Wave 3, validation packaging/upload, hosted metric claims, route promotion, route-negative conclusion, review, push, and M11 remain blocked until Wave 2 terminal accounting and post-job aggregation succeed.
