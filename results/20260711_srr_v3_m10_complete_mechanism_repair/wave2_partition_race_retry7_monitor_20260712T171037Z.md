# M10 Wave 2 Retry7 128G Monitor

Checkpoint time: `2026-07-12T17:10:37Z`

This is a monitor packet for the same active M10 goal and the same `m10_myops_training_executor`. It is not a new milestone, not a new executor, not Wave 3, and not a normal review request.

## Submission Basis

Retry6 D1 `58714634` failed as `OUT_OF_MEMORY 0:125` with `ReqMem=96G` and batch `MaxRSS=100661736K`. Retry7 increases only the Slurm memory request to `128G`; code, config, split, variants, budgets, formulas, result paths, executor count, and wave graph remain unchanged.

Retry7 compute-node preflight `58719811` completed `0:0` on `htzhulab` with `ReqMem=128G`.

## Job State

| Phase | Old job | Replacement job | Dependency | State |
| --- | ---: | ---: | --- | --- |
| D0 static matched control | `58706293` | retained | verified completed upstream | `COMPLETED 0:0` |
| D1 spatial BR2 | `58714634` | `58719835` | `afterok:58719811` | `RUNNING` on `g1807htzh01` |
| D2 hierarchical PSIP | `58714635` | `58719836` | `afterok:58719835` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58714636` | `58719837` | `afterok:58719836` | `PENDING (Dependency)` |
| Hard-negative refresh | `58714637` | `58719838` | `afterok:58719837` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58714638` | `58719839` | `afterok:58719838` | `PENDING (Dependency)` |
| Alignment control | `58714639` | `58719840` | `afterok:58719839` | `PENDING (Dependency)` |

Retry7 finalizer job `58719841` is `PENDING (Dependency)` with `afterany` over old, superseded, failed, cancelled, preflight, D0, and retry7 replacement jobs. Its aggregation command is recorded as a single string.

## Decision

Current state is `NEEDS_MONITOR`, not complete and not reviewable.

No `review.md` was written. No push was performed. Wave 3 remains blocked until D1-through-alignment reaches terminal state, finalizer accounting runs, and Wave 2 post-job aggregation produces a successful completion receipt.
