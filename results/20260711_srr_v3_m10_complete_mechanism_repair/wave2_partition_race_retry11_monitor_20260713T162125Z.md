# M10 Wave 2 Retry11 Hard-Negative Step12000 Monitor

State: `NEEDS_MONITOR`

This is a monitor packet, not completion evidence and not a request for independent review.

## Live Slurm State

Checkpoint time: `2026-07-13T16:21:25Z`

| Phase | Job ID | State | Evidence |
| --- | ---: | --- | --- |
| hard-negative refresh | `58775068` | `RUNNING` | `htzhulab`, elapsed `01:04:07`, node `g1807htzh01` |
| no-nnU-Net-context control | `58775069` | `PENDING (Dependency)` | waits on hard-negative refresh `afterok` |
| alignment control | `58775070` | `PENDING (Dependency)` | waits on no-context control `afterok` |
| Wave 2 finalizer | `58775071` | `PENDING (Dependency)` | waits with `afterany` |

Live memory accounting for `58775068.batch`:

```text
MaxRSS=13780820K
AveRSS=13645008K
MaxVMSize=0
AveVMSize=0
```

## Hard-Negative Runtime Progress

Hard-negative refresh has written scheduled validation checkpoints through step `12000`:

```text
checkpoint_validation_step_2000.pt
checkpoint_validation_step_4000.pt
checkpoint_validation_step_6000.pt
checkpoint_validation_step_8000.pt
checkpoint_validation_step_10000.pt
checkpoint_validation_step_12000.pt
checkpoint_best.pt
```

Hard-negative variant directory size at this checkpoint is approximately `2.8G`.

At this checkpoint hard-negative refresh has not yet produced final `training_log.csv`, `validation_events.csv`, or `summary.json`.

## Decision

Current state remains `NEEDS_MONITOR`, not complete and not reviewable. Hard-negative refresh is running with valid checkpoint progress and downstream stages remain correctly blocked by `afterok`. Wave 3, validation packaging/upload, hosted metric claims, route promotion, route-negative conclusion, review, push, and M11 remain blocked until Wave 2 terminal accounting and post-job aggregation succeed.
