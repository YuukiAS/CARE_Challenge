# M10 Wave 2 Retry9 Progress Monitor

Checkpoint time: `2026-07-12T19:11:38Z`

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

`sacct` reports retry9 D1 `58732391` running for `00:43:51` with `ReqMem=1200G`. `sstat` reports `MaxRSS=280730920K` and `AveRSS=280694048K`.

The D1 runtime has progressed beyond every previous D1 OOM window:

| Attempt | Job ID | ReqMem | Terminal/runtime state | Elapsed |
| --- | ---: | ---: | --- | ---: |
| retry5 | `58714023` | `64G` | `OUT_OF_MEMORY` | `00:07:50` |
| retry6 | `58714634` | `96G` | `OUT_OF_MEMORY` | `00:12:46` |
| retry7 | `58719835` | `128G` | `OUT_OF_MEMORY` | `00:18:06` |
| retry8 | `58720458` | `160G` | `OUT_OF_MEMORY` | `00:23:41` |
| retry9 | `58732391` | `1200G` | `RUNNING` | `00:43:51` |

D1 has written scheduled validation checkpoints:

```text
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
```

This is progress but not completion. D1 has not written final `training_log.csv`, `validation_events.csv`, `summary.json`, or post-job aggregation evidence yet.

## Decision

Current state is `NEEDS_MONITOR`, not complete and not reviewable. Wave 3 remains blocked until D1-through-alignment reaches terminal successful accounting and Wave 2 post-job aggregation succeeds.
