# M10 Wave 2 Retry8 160G Monitor

Checkpoint time: `2026-07-12T17:44:44Z`

This is a monitor packet for the same active M10 goal and the same `m10_myops_training_executor`. It is not a new milestone, not a new executor, not Wave 3, and not a normal review request.

## Submission Basis

Retry7 D1 `58719835` failed as `OUT_OF_MEMORY 0:125` with `ReqMem=128G` and batch `MaxRSS=134216104K`. A 160G request under `gpu_access` was rejected by `QOSMaxMemoryPerJob`; `gpu_access` has `MaxTRESPerJob mem=128G`. The user association allows `gpu_access_patron`, so retry8 uses `--qos=gpu_access_patron --mem=160G`.

This changes only Slurm resource routing. Code, config, split, variants, budgets, formulas, result paths, executor count, and wave graph remain unchanged.

Retry8 compute-node preflight `58720440` completed `0:0` on `htzhulab` with `ReqMem=160G`.

## Job State

| Phase | Old job | Replacement job | Dependency | State |
| --- | ---: | ---: | --- | --- |
| D0 static matched control | `58706293` | retained | verified completed upstream | `COMPLETED 0:0` |
| D1 spatial BR2 | `58719835` | `58720458` | `afterok:58720440` | `RUNNING` on `g1807htzh01` |
| D2 hierarchical PSIP | `58719836` | `58720459` | `afterok:58720458` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58719837` | `58720460` | `afterok:58720459` | `PENDING (Dependency)` |
| Hard-negative refresh | `58719838` | `58720461` | `afterok:58720460` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58719839` | `58720462` | `afterok:58720461` | `PENDING (Dependency)` |
| Alignment control | `58719840` | `58720463` | `afterok:58720462` | `PENDING (Dependency)` |

Retry8 finalizer job `58720464` is `PENDING (Dependency)` with `afterany` over old, superseded, failed, cancelled, preflight, D0, and retry8 replacement jobs.

## Decision

Current state is `NEEDS_MONITOR`, not complete and not reviewable.

No `review.md` was written. No push was performed. Wave 3 remains blocked until D1-through-alignment reaches terminal state, finalizer accounting runs, and Wave 2 post-job aggregation produces a successful completion receipt.
