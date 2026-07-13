# M10 Wave 2 Retry11 D3 Time-Floor Monitor

State: `NEEDS_MONITOR`

This is a monitor packet, not completion evidence and not a request for independent review.

## Live Slurm State

Checkpoint time: `2026-07-13T15:16:07Z`

| Phase | Job ID | State | Evidence |
| --- | ---: | --- | --- |
| D1 spatial BR2 | `58775065` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `02:35:16`, node `g1807htzh01` |
| D2 hierarchical PSIP | `58775066` | `COMPLETED` | `htzhulab`, exit `0:0`, elapsed `02:34:22`, node `g1807htzh01` |
| D3 full memory PropRef | `58775067` | `RUNNING` | `htzhulab`, elapsed `04:04:45`, node `g1807htzh01` |
| hard-negative refresh | `58775068` | `PENDING (Dependency)` | waits on D3 `afterok` |
| no-nnU-Net-context control | `58775069` | `PENDING (Dependency)` | waits on hard-negative refresh `afterok` |
| alignment control | `58775070` | `PENDING (Dependency)` | waits on no-context control `afterok` |
| Wave 2 finalizer | `58775071` | `PENDING (Dependency)` | waits with `afterany` |

## D3 Runtime Progress

D3 retry11 has crossed the declared `14400` second minimum train-loop floor by Slurm elapsed time and has started writing full-case evaluation outputs for `checkpoint_best`:

```text
component_hd_by_case_checkpoint_best.csv
crop_bounds_checkpoint_best.csv
prediction_sanity_checkpoint_best.csv
proposal_pr_sweep_checkpoint_best.csv
roi_coverage_checkpoint_best.csv
subgroup_metrics_checkpoint_best.csv
```

At this checkpoint D3 has not yet produced final `training_log.csv`, `validation_events.csv`, or `summary.json`, and downstream stages remain pending.

## Decision

Current state remains `NEEDS_MONITOR`, not complete and not reviewable. D3 is in post-step/time-floor runtime work, and downstream stages remain correctly blocked by `afterok`. Wave 3, validation packaging/upload, hosted metric claims, route promotion, route-negative conclusion, review, push, and M11 remain blocked until Wave 2 terminal accounting and post-job aggregation succeed.
