# M10 Completion Check

Completion state: `NEEDS_EVIDENCE`

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

## Retry3 Terminal Accounting Check

Checkpoint time: `2026-07-12T13:49:48Z`

| Gate | Status |
| --- | --- |
| active Slurm queue | pass: no retry3 jobs remain queued or running |
| htz preflight | pass: `58701195 COMPLETED 0:0` |
| htz D0 runtime | fail: `58701196 FAILED 1:0` after `00:00:56` |
| htz downstream chain | fail-closed: `58701197`-`58701202 CANCELLED 0:0` by `afterok` |
| a100 mirror | zero credit: `58701203`-`58701210 CANCELLED by 397557` after watcher selected htz D0 |
| retry3 watcher | pass: `58701289 COMPLETED 0:0`, winner `htzhulab` |
| retry3 finalizer | fail-closed: `58701290 FAILED 1:0` |
| aggregation replay | fail-closed: `finalize_wave2_partition_race.py` exited `2` and wrote `wave2_partition_race_retry3_finalization.json` |
| runtime failure cause | fail: D0 log raises `KeyError: 'correction_opportunity_loss'` in `scripts/training/run_srr_propref_myops_fold0.py` metrics logging |
| effective training evidence | fail: no valid D0 runtime evidence and no completed Wave 2 chain |
| Wave 3 | blocked: Wave 2 did not complete successfully |
| Review | blocked: this is not a completion packet |

Decision is `NEEDS_EVIDENCE`. This is terminal accounting for the retry3 Wave 2 attempt, not successful M10 completion.

## Owned-Wrapper Operational Repair Check

Repair time: `2026-07-12T14:00:16Z`

| Gate | Status |
| --- | --- |
| write scope | pass: only `scripts/training/run_srr_v3_m10_complete_repair.py` was changed |
| forbidden shared files | pass: no edits to `src/care_myocardium/models/`, `src/care_myocardium/losses/`, legacy `run_srr_propref_myops_fold0.py`, prompts, wiki, or `review.md` |
| scientific contract | pass: no change to variants, budgets, split, formulas, result paths, executor count, or wave graph |
| targeted metric compatibility | pass: M10 `propref_loss` smoke returns finite loss and `correction_opportunity_loss=0.0` |
| M10 entrypoint contracts | pass: `--list-phases` and `--phase d0_control --print-contract` |
| validators | pass: executor plan, handoff policy, architecture wiki strict/history, generated wiki check, and `git diff --check` |
| broader legacy pytest | external known failure: direct legacy `propref_loss` test lacks `args.variant`; M10-specific tests passed |

At the repair checkpoint, decision remained `NEEDS_EVIDENCE`; formal replacement jobs were still gated on repaired-code compute-node preflight.

## Retry4 Repaired-Code Submission Check

Checkpoint time: `2026-07-12T14:11:10Z`

| Gate | Status |
| --- | --- |
| repaired-code htz preflight | pass: `58706079 COMPLETED 0:0` after `00:00:22` |
| a100 mirror preflight | zero credit: `58706080 CANCELLED by 397557` while pending after htz preflight succeeded |
| formal chain submission | pass: `58706293`-`58706299` submitted unchanged on `htzhulab` |
| dependency policy | pass: D1-D3 and controls use `afterok`; retry4 finalizer `58706300` uses `afterany` |
| active runtime | monitor: D0 `58706293 RUNNING` on `g1807htzh01`; downstream stages dependency-pending |
| runtime artifacts | monitor: D0 contract and early sanity/prototype files exist under the retry4 htz runtime root |
| post-job aggregation | pending: wait for terminal Slurm accounting and finalizer aggregation |
| review | blocked: no `review.md` until final packet after successful terminal aggregation |

Decision is `NEEDS_MONITOR`, not blocked and not complete. This is not a pending-only scheduler block checkpoint because D0 has started running.

## Retry4 Terminal D1 Failure Check

Checkpoint time: `2026-07-12T16:24:12Z`

| Gate | Status |
| --- | --- |
| D0 terminal state | pass: `58706293 COMPLETED 0:0` after `02:09:10` |
| D0 minimum budget | pass: `summary.json` records `actual_optimizer_steps=36746`, `elapsed_seconds=7200.021336678998`, `eval_cases=44` |
| D1 terminal state | fail: `58706294 FAILED 1:0` after `00:00:58` |
| D1 failure cause | operational logging failure: nested/list gate usage reached legacy scalar `float(value)` |
| downstream stages | fail-closed: `58706295`-`58706299 CANCELLED` by unmet `afterok` |
| finalizer | fail-closed: `58706300 FAILED 1:0` |
| repair scope | pass: only owned M10 wrapper changed; no shared model/loss/wiki/prompt/review edits |
| local repair smoke | pass: nested gate usage compatibility produces scalar rows |
| review | blocked: no `review.md`; packet is not complete |

Decision is `NEEDS_EVIDENCE`. D0 evidence is retained, but Wave 2 is not complete because D1 failed and downstream formal phases did not run.
