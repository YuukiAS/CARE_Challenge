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
