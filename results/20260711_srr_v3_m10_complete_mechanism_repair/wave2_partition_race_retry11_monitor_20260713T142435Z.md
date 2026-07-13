# M10 Wave 2 Retry11 D3 Step40500 Monitor

State: `NEEDS_MONITOR`

This is a monitor packet, not completion evidence and not a request for independent review.

## Live Slurm State

Checkpoint time: `2026-07-13T14:24:35Z`

| Phase | Job ID | State | Evidence |
| --- | ---: | --- | --- |
| D1 spatial BR2 | `58775065` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `02:35:16`, node `g1807htzh01` |
| D2 hierarchical PSIP | `58775066` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `02:34:22`, node `g1807htzh01` |
| D3 full memory PropRef | `58775067` | `RUNNING` | `htzhulab`, elapsed `03:13:14`, node `g1807htzh01` |
| hard-negative refresh | `58775068` | `PENDING (Dependency)` | waits on D3 `afterok` |
| no-nnU-Net-context control | `58775069` | `PENDING (Dependency)` | waits on hard-negative refresh `afterok` |
| alignment control | `58775070` | `PENDING (Dependency)` | waits on no-context control `afterok` |
| Wave 2 finalizer | `58775071` | `PENDING (Dependency)` | waits with `afterany` |

Live memory accounting for `58775067.batch`:

```text
MaxRSS=19616664K
AveRSS=19512660K
MaxVMSize=0
AveVMSize=0
```

## D3 Runtime Progress

D3 retry11 has written scheduled validation checkpoints through step `40500`, including:

```text
checkpoint_validation_step_32720.pt
checkpoint_validation_step_34765.pt
checkpoint_validation_step_36810.pt
checkpoint_validation_step_38855.pt
checkpoint_validation_step_40500.pt
checkpoint_best.pt
```

D3 variant directory size at this checkpoint is approximately `9.0G`.

At this checkpoint D3 has not yet produced final `training_log.csv`, `validation_events.csv`, or `summary.json`.

## Decision

Current state remains `NEEDS_MONITOR`, not complete and not reviewable. D3 is still running and downstream stages remain correctly blocked by `afterok`. Wave 3, validation packaging/upload, hosted metric claims, route promotion, route-negative conclusion, review, push, and M11 remain blocked until Wave 2 terminal accounting and post-job aggregation succeed.
