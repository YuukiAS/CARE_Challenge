# M10 Wave 2 Retry11 D2 Completion Monitor

State: `NEEDS_MONITOR`

This is a monitor packet, not completion evidence and not a request for independent review.

## Live Slurm State

Checkpoint time: `2026-07-13T11:15:19Z`

| Phase | Job ID | State | Evidence |
| --- | ---: | --- | --- |
| D1 spatial BR2 | `58775065` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `02:35:16`, node `g1807htzh01` |
| D2 hierarchical PSIP | `58775066` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `02:34:22`, node `g1807htzh01` |
| D3 full memory PropRef | `58775067` | `RUNNING` | `htzhulab`, elapsed `00:03:51`, node `g1807htzh01` |
| hard-negative refresh | `58775068` | `PENDING (Dependency)` | waits on D3 `afterok` |
| no-nnU-Net-context control | `58775069` | `PENDING (Dependency)` | waits on hard-negative refresh `afterok` |
| alignment control | `58775070` | `PENDING (Dependency)` | waits on no-context control `afterok` |
| Wave 2 finalizer | `58775071` | `PENDING (Dependency)` | waits with `afterany` |

D3 live memory accounting for `58775067.batch`:

```text
MaxRSS=10929272K
AveRSS=10904836K
MaxVMSize=0
AveVMSize=0
```

## D2 Completion Evidence

D2 retry11 produced final runtime outputs under:

```text
results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor/partition_race_retry11/htzhulab/variants/m10_d2_hierarchical_psip_formal/
```

Key summary fields:

| Field | Value |
| --- | ---: |
| `actual_optimizer_steps` | `31810` |
| `train_loop_seconds` | `9000.034213767038` |
| `process_wall_seconds` | `8967.458665733999` |
| `validation_event_count` | `19` |
| `eval_cases` | `44` |
| `stop_reason` | `max_steps_min_train_loop_seconds_satisfied` |
| `best_step` | `25000` |
| `best_val_patch_loss` | `1.0838948488235474` |
| `first_train_loss` | `4.220096588134766` |
| `last_train_loss` | `0.8512778878211975` |
| `loss_decrease` | `3.368818700313568` |
| `one_batch_overfit.status` | `PASS` |

Final lightweight runtime files:

| File | Size / rows |
| --- | ---: |
| `summary.json` | `34007` bytes |
| `training_log.csv` | `339` lines including header |
| `validation_events.csv` | `20` lines including header |
| `retrieval_usage.csv` | `86769` lines including header; `11374754` bytes |

## D3 Monitor Evidence

D3 retry11 has started on the same htzhulab node. It has written early sanity files:

```text
one_batch_overfit.csv
one_batch_overfit.json
prototype_bank_summary.json
prototype_update_sanity.csv
```

At this checkpoint D3 has not yet produced final `training_log.csv`, `validation_events.csv`, or `summary.json`.

## Decision

Current state remains `NEEDS_MONITOR`, not complete and not reviewable. D2 completed successfully, D3 is running, and downstream stages remain correctly blocked by `afterok`. Wave 3, validation packaging/upload, hosted metric claims, route promotion, route-negative conclusion, review, push, and M11 remain blocked until Wave 2 terminal accounting and post-job aggregation succeed.
