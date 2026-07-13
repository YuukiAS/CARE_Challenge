# M10 Wave 2 Retry10 Terminal OOM

State: `NEEDS_EVIDENCE`

This is terminal accounting for retry10. It is not M10 completion evidence and is not ready for independent review.

## Terminal Accounting

| Phase | Job ID | Terminal state | Credit |
| --- | ---: | --- | --- |
| compute preflight | `58743253` | `COMPLETED 0:0`, elapsed `00:00:19`, node `g1807htzh01` | preflight pass |
| D0 static matched control | `58706293` | retained `COMPLETED 0:0` from prior valid attempt | retained upstream evidence |
| D1 spatial BR2 | `58743282` | `OUT_OF_MEMORY`, exit `0:125`, elapsed `06:09:20`, node `g1807htzh01` | zero D1 minimum-effective-training credit |
| D2 hierarchical PSIP | `58743287` | did not run, elapsed `00:00:00`, no node assigned | zero credit |
| D3 full memory PropRef | `58743290` | did not run, elapsed `00:00:00`, no node assigned | zero credit |
| hard-negative refresh | `58743292` | did not run, elapsed `00:00:00`, no node assigned | zero credit |
| no-nnU-Net-context control | `58743294` | did not run, elapsed `00:00:00`, no node assigned | zero credit |
| alignment control | `58743295` | did not run, elapsed `00:00:00`, no node assigned | zero credit |
| Wave 2 finalizer | `58743452` | wrote `finalizer_state.json` and `care_milestone_finalizer_58743452.log` | terminal accounting only |

The finalizer classified this attempt as:

```text
final_state=RUNTIME_FAILURE
failure_class=OUT_OF_MEMORY_NEEDS_REVISION
suggested_next_state=NEEDS_REVISION
retryable=false
aggregation_exit_code=None
```

## Runtime Evidence

Retry10 D1 wrote checkpoints through step 21658:

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
checkpoint_best.pt
```

Retry10 D1 did not write final `training_log.csv`, `validation_events.csv`, `summary.json`, or `runtime_manifest.json`. It also did not reach the D1 minimum optimizer-step floor of `25000`, and downstream D2-through-alignment phases were blocked by the failed `afterok` dependency.

## Decision

Wave 2 retry10 is terminal and unsuccessful. The controller state is `NEEDS_EVIDENCE`, not `NEEDS_MONITOR`, not complete, and not reviewable, because retry10 D1 terminated before final runtime outputs and post-job aggregation evidence were produced. The finalizer classifies any further retry as requiring revision first: `failure_class=OUT_OF_MEMORY_NEEDS_REVISION`, `suggested_next_state=NEEDS_REVISION`, `retryable=false`.

Wave 3, validation packaging/upload, hosted metric claims, route promotion, route-negative conclusion, and M11 remain blocked.

No `review.md` was written and no push was performed.
