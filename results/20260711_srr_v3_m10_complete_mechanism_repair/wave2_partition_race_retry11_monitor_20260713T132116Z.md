# M10 Wave 2 Retry11 D3 Step27000 Monitor

State: `NEEDS_MONITOR`

This is a monitor packet, not completion evidence and not a request for independent review.

## Live Slurm State

Checkpoint time: `2026-07-13T13:21:16Z`

| Phase | Job ID | State | Evidence |
| --- | ---: | --- | --- |
| D1 spatial BR2 | `58775065` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `02:35:16`, node `g1807htzh01` |
| D2 hierarchical PSIP | `58775066` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `02:34:22`, node `g1807htzh01` |
| D3 full memory PropRef | `58775067` | `RUNNING` | `htzhulab`, elapsed `02:09:52`, node `g1807htzh01` |
| hard-negative refresh | `58775068` | `PENDING (Dependency)` | waits on D3 `afterok` |
| no-nnU-Net-context control | `58775069` | `PENDING (Dependency)` | waits on hard-negative refresh `afterok` |
| alignment control | `58775070` | `PENDING (Dependency)` | waits on no-context control `afterok` |
| Wave 2 finalizer | `58775071` | `PENDING (Dependency)` | waits with `afterany` |

Live memory accounting for `58775067.batch`:

```text
MaxRSS=17031176K
AveRSS=16937860K
MaxVMSize=0
AveVMSize=0
```

## D3 Runtime Progress

D3 retry11 has written scheduled validation checkpoints through step `27000`:

```text
checkpoint_validation_step_2045.pt
checkpoint_validation_step_4090.pt
checkpoint_validation_step_6135.pt
checkpoint_validation_step_8180.pt
checkpoint_validation_step_9000.pt
checkpoint_validation_step_10225.pt
checkpoint_validation_step_12270.pt
checkpoint_validation_step_14315.pt
checkpoint_validation_step_16360.pt
checkpoint_validation_step_18405.pt
checkpoint_validation_step_20450.pt
checkpoint_validation_step_22495.pt
checkpoint_validation_step_24540.pt
checkpoint_validation_step_26585.pt
checkpoint_validation_step_27000.pt
checkpoint_best.pt
```

D3 variant directory size at this checkpoint is approximately `6.3G`.

D3 has exceeded the step floor but has not yet crossed the `9000` second minimum train-loop floor by Slurm elapsed time. At this checkpoint D3 has not yet produced final `training_log.csv`, `validation_events.csv`, or `summary.json`.

## Decision

Current state remains `NEEDS_MONITOR`, not complete and not reviewable. D3 is running after crossing the step floor and downstream stages remain correctly blocked by `afterok`. Wave 3, validation packaging/upload, hosted metric claims, route promotion, route-negative conclusion, review, push, and M11 remain blocked until Wave 2 terminal accounting and post-job aggregation succeed.
