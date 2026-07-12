# M10 Controller Report

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

## Controller Result

The controller is continuing the same active M10 goal and the same `m10_myops_training_executor`. This is not a new milestone, not a new executor, not follow-up planning, and not Wave 3.

## Wave 2 Replacement Status

The original seven Wave 2 jobs remain permanently recorded as `STARTUP_FAILED` with zero training, optimizer-step, and train-loop-second credit. They do not count toward the M10 minimum-effective-training budget.

After the `env_CARE` dependency repair, the user explicitly authorized a three-partition preflight race across `htzhulab`, `a100-gpu`, and `volta-gpu`. The successful enhanced compute-node preflight was job `58700751` on `volta-gpu`, completed `0:0` in `00:02:45`; log `logs/M10W2Preflight_volta-gpu_58700751_20260712_060557.log`. It verified `mpmath 1.3.0`, `sympy 1.14.0`, `optimizer_ok`, CUDA visibility, config parse, writable roots, code/config/split fingerprints, phase listing, and per-phase print-contract output.

The controller then submitted the original seven formal Wave 2 replacement jobs without changing variants, formulas, budgets, split, case set, evaluation rules, checkpoint-selection rules, result paths, executor count, or wave graph. Training-to-training dependencies use `afterok`; the Wave 2 finalizer uses `afterany`.

| Phase | Old job | Replacement job | Dependency | Current state |
| --- | ---: | ---: | --- | --- |
| D0 static matched control | `58644072` | `58700815` | none after preflight | `PENDING (Resources)` |
| D1 spatial BR2 | `58644073` | `58700821` | `afterok:58700815` | `PENDING (Dependency)` |
| D2 hierarchical PSIP | `58644074` | `58700822` | `afterok:58700821` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58644106` | `58700826` | `afterok:58700822` | `PENDING (Dependency)` |
| Hard-negative refresh | `58644107` | `58700827` | `afterok:58700826` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58644108` | `58700828` | `afterok:58700827` | `PENDING (Dependency)` |
| Alignment control | `58644109` | `58700832` | `afterok:58700828` | `PENDING (Dependency)` |

Wave 2 finalizer job: `58700842`, dependency `afterany` over all old and replacement jobs.

## Terminal State

```text
controller_run_status: NEEDS_MONITOR
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: NOT_REVIEWED
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_REPLACEMENT_SUBMISSION_MONITOR_PACKET_COMMIT
git_commit_decision: COMMIT_LOCAL_PACKET
git_push_decision: SKIP_PUSH
review_md_written: false
```

Blocked actions: Wave 3, review, push, validation packaging/upload, hosted claims, route promotion, scientific stop, and M11.

Next required action: monitor replacement jobs until terminal accounting, then run Wave 2 post-job aggregation and continue the original M10 state machine only if evidence gates pass.
