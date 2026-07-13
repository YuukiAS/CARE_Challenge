# M10 Wave 2 Retry11 D1 Completion Monitor

State: `NEEDS_MONITOR`

This is a monitor packet, not completion evidence and not a request for independent review.

## Live Slurm State

Checkpoint time: `2026-07-13T08:42:03Z`

| Phase | Job ID | State | Evidence |
| --- | ---: | --- | --- |
| D1 spatial BR2 | `58775065` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `02:35:16`, node `g1807htzh01` |
| D2 hierarchical PSIP | `58775066` | `RUNNING` | `htzhulab`, started `2026-07-13T04:37:07`, node `g1807htzh01` |
| D3 full memory PropRef | `58775067` | `PENDING (Dependency)` | waits on D2 `afterok` |
| hard-negative refresh | `58775068` | `PENDING (Dependency)` | waits on D3 `afterok` |
| no-nnU-Net-context control | `58775069` | `PENDING (Dependency)` | waits on hard-negative refresh `afterok` |
| alignment control | `58775070` | `PENDING (Dependency)` | waits on no-context control `afterok` |
| Wave 2 finalizer | `58775071` | `PENDING (Dependency)` | waits with `afterany` |

Live memory accounting for `58775066.batch`:

```text
MaxRSS=11024568K
AveRSS=10926244K
MaxVMSize=0
AveVMSize=0
```

## D1 Completion Evidence

D1 retry11 produced final runtime outputs under:

```text
results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor/partition_race_retry11/htzhulab/variants/m10_d1_spatial_br2_formal/
```

Key summary fields:

| Field | Value |
| --- | ---: |
| `actual_optimizer_steps` | `31778` |
| `train_loop_seconds` | `9000.150148481014` |
| `process_wall_seconds` | `8965.185634936` |
| `validation_event_count` | `19` |
| `eval_cases` | `44` |
| `stop_reason` | `max_steps_min_train_loop_seconds_satisfied` |
| `best_step` | `25000` |
| `best_val_patch_loss` | `1.0741549551486969` |
| `first_train_loss` | `4.220096588134766` |
| `last_train_loss` | `0.7205723524093628` |
| `loss_decrease` | `3.499524235725403` |
| `one_batch_overfit.status` | `PASS` |

Final lightweight runtime files:

| File | Size / rows |
| --- | ---: |
| `summary.json` | `33469` bytes |
| `training_log.csv` | `338` lines including header |
| `validation_events.csv` | `20` lines including header |
| `retrieval_usage.csv` | `86497` lines including header; `10820647` bytes |

The repaired gate-usage evidence logging did not reproduce the retry10 `156G` `retrieval_usage.csv` expansion.

## D2 Monitor Evidence

D2 retry11 has started on the same htzhulab node. It has written early sanity files:

```text
one_batch_overfit.csv
one_batch_overfit.json
prototype_bank_summary.json
prototype_update_sanity.csv
```

At this checkpoint D2 has not yet produced final `training_log.csv`, `validation_events.csv`, or `summary.json`.

## Decision

Current state remains `NEEDS_MONITOR`, not complete and not reviewable. Wave 3, validation packaging/upload, hosted metric claims, route promotion, route-negative conclusion, review, push, and M11 remain blocked until Wave 2 terminal accounting and post-job aggregation succeed.
