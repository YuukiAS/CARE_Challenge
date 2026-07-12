# M10 Wave 2 Retry9 D1 Final-Checkpoint Running Monitor

Checkpoint time: `2026-07-12T22:01:54Z`

This is a monitor packet for the same active M10 goal and the same `m10_myops_training_executor`. It is not completion evidence and not a normal review request.

## Live State

| Phase | Job ID | State |
| --- | ---: | --- |
| D0 static matched control | `58706293` | retained `COMPLETED 0:0` |
| D1 spatial BR2 | `58732391` | `RUNNING` on `g1807htzh01` |
| D2 hierarchical PSIP | `58732393` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58732395` | `PENDING (Dependency)` |
| Hard-negative refresh | `58732397` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58732399` | `PENDING (Dependency)` |
| Alignment control | `58732400` | `PENDING (Dependency)` |
| Finalizer | `58733769` | `PENDING (Dependency)` |

`sacct` reports retry9 D1 `58732391` running for `03:34:05` with `ReqMem=1200G`. `sstat` reports `MaxRSS=889579444K` and `AveRSS=889579444K`.

## Runtime Progress

D1 has written final-checkpoint and training-log artifacts:

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
checkpoint_best.pt
checkpoint_final.pt
training_log.csv
validation_events.csv
```

D1 has not written `summary.json`, and Slurm still reports the job as `RUNNING`. Post-job aggregation has not run.

## Decision

Current state is `NEEDS_MONITOR`, not complete and not reviewable. Wave 3 remains blocked until D1-through-alignment reaches terminal successful accounting and Wave 2 post-job aggregation succeeds.
