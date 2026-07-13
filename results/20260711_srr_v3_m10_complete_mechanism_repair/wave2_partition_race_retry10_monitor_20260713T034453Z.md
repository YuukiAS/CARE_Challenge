# M10 Wave 2 Retry10 D1 Step18326 Monitor

Checkpoint time: `2026-07-13T03:44:53Z`

This is a monitor packet, not completion evidence. Wave 2 retry10 D1 is still running; downstream stages and the Wave 2 finalizer remain dependency-pending.

## Live Slurm State

| Phase | Job ID | State | Evidence |
| --- | ---: | --- | --- |
| compute preflight | `58743253` | `COMPLETED 0:0` | `sacct` elapsed `00:00:19`, node `g1807htzh01` |
| D0 static matched control | `58706293` | retained `COMPLETED 0:0` | valid upstream runtime evidence retained from retry9 |
| D1 spatial BR2 | `58743282` | `RUNNING` | `squeue` elapsed `04:42:31/8:00:00`, node `g1807htzh01`; `sacct` elapsed `04:42:57`, `ReqMem=1200G` |
| D2 hierarchical PSIP | `58743287` | `PENDING` | dependency on D1 `afterok` |
| D3 full memory PropRef | `58743290` | `PENDING` | dependency on D2 `afterok` |
| hard-negative refresh | `58743292` | `PENDING` | dependency on D3 `afterok` |
| no-nnU-Net-context control | `58743294` | `PENDING` | dependency on hard-negative refresh `afterok` |
| alignment control | `58743295` | `PENDING` | dependency on no-context control `afterok` |
| Wave 2 finalizer | `58743452` | `PENDING` | `afterany` over old and retry10 jobs |

Live memory accounting for `58743282.batch`:

```text
MaxRSS=1070713496K
AveRSS=1070713496K
MaxVMSize=0
AveVMSize=0
```

## Runtime Progress

Retry10 D1 has written validation checkpoints through step 18326:

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
checkpoint_best.pt
```

No final `training_log.csv`, `validation_events.csv`, `summary.json`, `runtime_manifest.json`, or post-job aggregation evidence was present at this checkpoint.

## Decision

Current state remains `NEEDS_MONITOR`, not complete and not reviewable. Wave 3 remains blocked until Wave 2 terminal accounting and post-job aggregation succeed. No `review.md` was written and no push was performed.
