# M10 Completion Check

Completion state: `NEEDS_MONITOR`

This packet is not complete and is not ready for independent review. It records that the original Wave 2 jobs are permanently `STARTUP_FAILED` with zero training credit, the repaired compute-node preflight succeeded, the authorized replacement Wave 2 formal jobs were submitted, and those jobs are currently pending/running/dependency-waiting under Slurm.

## Required Gates

| Gate | Status |
| --- | --- |
| Old failed job accounting | pass: seven old jobs recorded as `STARTUP_FAILED`, zero credit |
| Replacement preflight | pass: job `58700751` completed `0:0` on `volta-gpu` |
| Replacement formal jobs | monitor: jobs `58700815`, `58700821`, `58700822`, `58700826`, `58700827`, `58700828`, `58700832` submitted |
| Training dependency policy | pass: training-to-training dependencies use `afterok` |
| Wave 2 finalizer dependency | pass: finalizer job `58700842` uses `afterany` over all old and replacement jobs |
| Post-job aggregation | pending: wait for terminal runtime outputs |
| Review | blocked: no `review.md` until final packet after aggregation |

## Decision

Current controller state is `NEEDS_MONITOR`, not blocked and not complete. D0 is pending on `htzhulab` resources, downstream jobs are dependency-pending, and the Wave 2 finalizer is dependency-pending.

No `review.md` was written. No push was performed. Wave 3, validation packaging/upload, hosted metric claims, route promotion, route-negative conclusion, and M11 remain blocked until Wave 2 terminal accounting and aggregation succeed.

## Three-Partition Race Check

| Gate | Status |
| --- | --- |
| Superseded pending htz chain | pass: jobs `58700815`, `58700821`, `58700822`, `58700826`, `58700827`, `58700828`, `58700832` cancelled before training start, zero credit |
| Formal race isolation | pass: `M10_RUNTIME_ROOT` is partition-specific and job aggregation is deferred in mirror jobs |
| Race preflight | pass for winner: `58701110` completed `0:0` on `volta-gpu` |
| Race winner | monitor: `volta-gpu`, D0 job `58701111` is `RUNNING` |
| Loser mirrors | pass: watcher `58701118` cancelled pending `htzhulab` and `a100-gpu` chains |
| Race finalizer | monitor: job `58701119` waits with `afterany` |

Decision remains `NEEDS_MONITOR`, not blocked and not complete.

## Htz/A100 Retry Check

| Gate | Status |
| --- | --- |
| Volta D0 accounting | pass: `58701111` failed with unsupported V100 CUDA kernel execution, zero credit |
| Preflight hardening | pass: `wave2_env_preflight.sh` now includes CUDA kernel execution probe |
| Htz/A100 retry submission | monitor: htz preflight `58701195`, a100 preflight `58701203` pending |
| Retry watcher | superseded: `58701211` cancelled after user authorized adding `volta-gpu` |
| Retry finalizer | superseded: `58701212` cancelled before terminal accounting |

Decision remains `NEEDS_MONITOR`.

## User-Authorized Volta Add-On Check

| Gate | Status |
| --- | --- |
| User authorization | pass: user explicitly authorized adding `volta-gpu` to the current goal's routing race |
| Three-partition retry3 submission | pass: existing htz/a100 chains retained; added volta preflight `58701281` and afterok chain `58701282`-`58701288` |
| Volta compute preflight | failed as designed: `58701281` failed `1:0` after CUDA kernel probe hit unsupported V100 execution |
| Volta training credit | pass: `58701282`-`58701288` were cancelled by unmet `afterok`; training, optimizer-step, and train-loop-second credit remain zero |
| Active effective race | monitor: htz preflight `58701195` and a100 preflight `58701203` remain pending; their D0 jobs `58701196` and `58701204` remain dependency-pending |
| Retry3 watcher | monitor: `58701289` running and reading all three D0 jobs |
| Retry3 finalizer | monitor: `58701290` dependency-pending with `afterany` over old, superseded, failed, cancelled, and active retry jobs |

Decision remains `NEEDS_MONITOR`, not blocked and not complete.

## Retry3 Two-Hour Monitor Check 1

Checkpoint time: `2026-07-12T12:53:05Z`

| Gate | Status |
| --- | --- |
| htz preflight | monitor: `58701195` remains `PENDING (Priority)` |
| htz formal chain | monitor: `58701196`-`58701202` remain `PENDING (Dependency)` |
| a100 preflight | monitor: `58701203` remains `PENDING (Priority)` |
| a100 formal chain | monitor: `58701204`-`58701210` remain `PENDING (Dependency)` |
| retry3 watcher | monitor: `58701289` running for `02:00:03` |
| retry3 finalizer | monitor: `58701290` remains `PENDING (Dependency)` |
| scheduler block threshold | not met: this is pending-only two-hour check `1/12` |
| post-job aggregation | pending: no winner and no terminal runtime outputs |

Decision remains `NEEDS_MONITOR`, not blocked and not complete. The next legal pending-only monitor check for this retry3 race is no earlier than `2026-07-12T14:53Z`.
