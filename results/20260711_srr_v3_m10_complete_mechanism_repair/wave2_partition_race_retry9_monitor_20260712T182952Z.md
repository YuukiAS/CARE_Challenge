# M10 Wave 2 Retry9 1200G Monitor

Checkpoint time: `2026-07-12T18:29:52Z`

This is a monitor packet for the same active M10 goal and the same `m10_myops_training_executor`. It is not a new milestone, not a new executor, not Wave 3, and not a normal review request.

## Submission Basis

Retry8 D1 `58720458` failed as `OUT_OF_MEMORY 0:125` with `ReqMem=160G`, `QOS=gpu_access_patron`, and batch `MaxRSS=167770540K`. Earlier D1 retries failed at 64G, 96G, and 128G. D0 `58706293` remains valid completed runtime evidence.

Retry9 changes only Slurm resource routing: D1-through-alignment now request `--qos=gpu_access_patron --mem=1200G` on `htzhulab`. Code, config, split, variants, budgets, formulas, result paths, executor count, and wave graph remain unchanged.

Retry9 compute-node preflight `58728960` completed `0:0` on `htzhulab` with `ReqMem=1200G`.

## Job State

| Phase | Old job | Replacement job | Dependency | State |
| --- | ---: | ---: | --- | --- |
| D0 static matched control | `58706293` | retained | verified completed upstream | `COMPLETED 0:0` |
| D1 spatial BR2 | `58720458` | `58732391` | `afterok:58728960` | `RUNNING` on `g1807htzh01` |
| D2 hierarchical PSIP | `58720459` | `58732393` | `afterok:58732391` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58720460` | `58732395` | `afterok:58732393` | `PENDING (Dependency)` |
| Hard-negative refresh | `58720461` | `58732397` | `afterok:58732395` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58720462` | `58732399` | `afterok:58732397` | `PENDING (Dependency)` |
| Alignment control | `58720463` | `58732400` | `afterok:58732399` | `PENDING (Dependency)` |

Retry9 finalizer job `58733769` is `PENDING (Dependency)` with `afterany` over old, superseded, failed, cancelled, preflight, retained D0, and retry9 replacement jobs.

At this checkpoint, `sstat -j 58732391.batch` reports `MaxRSS=22162040K` and `AveRSS=22135320K`, which is early runtime monitoring only and not completion evidence.

## Decision

Current state is `NEEDS_MONITOR`, not complete and not reviewable.

No `review.md` was written. No push was performed. Wave 3 remains blocked until D1-through-alignment reaches terminal state, finalizer accounting runs, and Wave 2 post-job aggregation produces a successful completion receipt.
