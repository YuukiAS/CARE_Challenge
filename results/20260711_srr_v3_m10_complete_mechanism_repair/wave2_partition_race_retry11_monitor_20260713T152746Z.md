# M10 Wave 2 Retry11 D3 Completion Monitor

State: `NEEDS_MONITOR`

This is a monitor packet, not completion evidence and not a request for independent review.

## Live Slurm State

Checkpoint time: `2026-07-13T15:27:46Z`

| Phase | Job ID | State | Evidence |
| --- | ---: | --- | --- |
| D1 spatial BR2 | `58775065` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `02:35:16`, node `g1807htzh01` |
| D2 hierarchical PSIP | `58775066` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `02:34:22`, node `g1807htzh01` |
| D3 full memory PropRef | `58775067` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `04:05:39`, node `g1807htzh01` |
| hard-negative refresh | `58775068` | `RUNNING` | `htzhulab`, elapsed `00:10:31`, node `g1807htzh01` |
| no-nnU-Net-context control | `58775069` | `PENDING (Dependency)` | waits on hard-negative refresh `afterok` |
| alignment control | `58775070` | `PENDING (Dependency)` | waits on no-context control `afterok` |
| Wave 2 finalizer | `58775071` | `PENDING (Dependency)` | waits with `afterany` |

Hard-negative refresh live memory accounting for `58775068.batch`:

```text
MaxRSS=11516900K
AveRSS=11426424K
MaxVMSize=0
AveVMSize=0
```

## D3 Completion Evidence

D3 retry11 produced final runtime outputs under:

```text
results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor/partition_race_retry11/htzhulab/variants/m10_d3_full_memory_propref_formal/
```

Key summary fields:

| Field | Value |
| --- | ---: |
| `actual_optimizer_steps` | `50820` |
| `train_loop_seconds` | `14400.138177286019` |
| `process_wall_seconds` | `14352.67503921` |
| `validation_event_count` | `26` |
| `eval_cases` | `44` |
| `stop_reason` | `max_steps_min_train_loop_seconds_satisfied` |
| `best_step` | `20450` |
| `best_val_patch_loss` | `1.1212197542190552` |
| `first_train_loss` | `4.220096588134766` |
| `last_train_loss` | `0.5372716188430786` |
| `loss_decrease` | `3.682824969291687` |
| `one_batch_overfit.status` | `PASS` |

Final lightweight runtime files:

| File | Size / rows |
| --- | ---: |
| `summary.json` | `40657` bytes |
| `training_log.csv` | `536` lines including header |
| `validation_events.csv` | `27` lines including header |
| `retrieval_usage.csv` | `138449` lines including header; `18444638` bytes |

## Hard-Negative Refresh Monitor Evidence

Hard-negative refresh has started and written early sanity files:

```text
one_batch_overfit.csv
one_batch_overfit.json
prototype_bank_summary.json
prototype_update_sanity.csv
```

At this checkpoint hard-negative refresh has not yet produced final `training_log.csv`, `validation_events.csv`, or `summary.json`.

## Decision

Current state remains `NEEDS_MONITOR`, not complete and not reviewable. D3 completed successfully, hard-negative refresh is running, and downstream stages remain correctly blocked by `afterok`. Wave 3, validation packaging/upload, hosted metric claims, route promotion, route-negative conclusion, review, push, and M11 remain blocked until Wave 2 terminal accounting and post-job aggregation succeed.
