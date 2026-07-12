# M10 Wave 2 Retry6 96G Monitor

Checkpoint time: `2026-07-12T16:47:36Z`

This is a monitor packet for the same active M10 goal and the same `m10_myops_training_executor`. It is not a new milestone, not a new executor, not Wave 3, and not a normal review request.

## Submission Basis

Retry5 D1 `58714023` failed as `OUT_OF_MEMORY 0:125` with `ReqMem=64G` and batch `MaxRSS=67107264K`. Retry6 increases only the Slurm memory request to `96G`; code, config, split, variants, budgets, formulas, result paths, executor count, and wave graph remain unchanged.

Retry6 compute-node preflight `58714615` completed `0:0` on `htzhulab` with `ReqMem=96G`.

## Job State

| Phase | Old job | Replacement job | Dependency | State |
| --- | ---: | ---: | --- | --- |
| D0 static matched control | `58706293` | retained | verified completed upstream | `COMPLETED 0:0` |
| D1 spatial BR2 | `58714023` | `58714634` | `afterok:58714615` | `RUNNING` on `g1807htzh01` |
| D2 hierarchical PSIP | `58714024` | `58714635` | `afterok:58714634` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58714025` | `58714636` | `afterok:58714635` | `PENDING (Dependency)` |
| Hard-negative refresh | `58714026` | `58714637` | `afterok:58714636` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58714027` | `58714638` | `afterok:58714637` | `PENDING (Dependency)` |
| Alignment control | `58714028` | `58714639` | `afterok:58714638` | `PENDING (Dependency)` |

Retry6 finalizer job `58714640` is `PENDING (Dependency)` with `afterany` over old, superseded, failed, cancelled, preflight, D0, and retry6 replacement jobs.

## Decision

Current state is `NEEDS_MONITOR`, not complete and not reviewable.

No `review.md` was written. No push was performed. Wave 3 remains blocked until D1-through-alignment reaches terminal state, finalizer accounting runs, and Wave 2 post-job aggregation produces a successful completion receipt.
