# M10 Wave 2 Retry11 D2 Step25000 Monitor

State: `NEEDS_MONITOR`

This is a monitor packet, not completion evidence and not a request for independent review.

## Live Slurm State

Checkpoint time: `2026-07-13T10:41:23Z`

| Phase | Job ID | State | Evidence |
| --- | ---: | --- | --- |
| D1 spatial BR2 | `58775065` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `02:35:16`, node `g1807htzh01` |
| D2 hierarchical PSIP | `58775066` | `RUNNING` | `htzhulab`, elapsed `02:05:09`, node `g1807htzh01` |
| D3 full memory PropRef | `58775067` | `PENDING (Dependency)` | waits on D2 `afterok` |
| hard-negative refresh | `58775068` | `PENDING (Dependency)` | waits on D3 `afterok` |
| no-nnU-Net-context control | `58775069` | `PENDING (Dependency)` | waits on hard-negative refresh `afterok` |
| alignment control | `58775070` | `PENDING (Dependency)` | waits on no-context control `afterok` |
| Wave 2 finalizer | `58775071` | `PENDING (Dependency)` | waits with `afterany` |

Live memory accounting for `58775066.batch`:

```text
MaxRSS=18913780K
AveRSS=18385052K
MaxVMSize=0
AveVMSize=0
```

## D2 Runtime Progress

D2 retry11 has written scheduled validation checkpoints through step `25000`:

```text
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
checkpoint_validation_step_4998.pt
checkpoint_validation_step_5000.pt
checkpoint_validation_step_6664.pt
checkpoint_validation_step_8330.pt
checkpoint_validation_step_9996.pt
checkpoint_validation_step_11662.pt
checkpoint_validation_step_13328.pt
checkpoint_validation_step_14994.pt
checkpoint_validation_step_15000.pt
checkpoint_validation_step_16660.pt
checkpoint_validation_step_18326.pt
checkpoint_validation_step_19992.pt
checkpoint_validation_step_21658.pt
checkpoint_validation_step_22500.pt
checkpoint_validation_step_23324.pt
checkpoint_validation_step_24990.pt
checkpoint_validation_step_25000.pt
checkpoint_best.pt
```

D2 variant directory size at this checkpoint is approximately `7.8G`.

D2 has reached the `25000` step floor but has not yet crossed the `9000` second minimum train-loop floor by Slurm elapsed time. At this checkpoint D2 has not yet produced final `training_log.csv`, `validation_events.csv`, or `summary.json`.

## Decision

Current state remains `NEEDS_MONITOR`, not complete and not reviewable. D2 is running after reaching the step floor and downstream stages remain correctly blocked by `afterok`. Wave 3, validation packaging/upload, hosted metric claims, route promotion, route-negative conclusion, review, push, and M11 remain blocked until Wave 2 terminal accounting and post-job aggregation succeed.
