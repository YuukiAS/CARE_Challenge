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

## Latest Three-Partition Formal Race

After the user explicitly authorized adding `volta-gpu` to the formal routing race, the controller cancelled the superseded pending `htzhulab` replacement chain `58700815`, `58700821`, `58700822`, `58700826`, `58700827`, `58700828`, `58700832` and old finalizer `58700842`. These jobs had not started and remain zero-credit superseded attempts.

The controller submitted isolated runtime-root mirrors to `htzhulab`, `a100-gpu`, and `volta-gpu`, each with its own compute-node preflight followed by the unchanged seven-stage Wave 2 `afterok` training chain. Mirror jobs run with `M10_DEFER_AGGREGATION=1`; only the winning partition runtime is aggregated into the formal result paths.

Race outcome: `volta-gpu` won. Preflight job `58701110` completed `0:0`; D0 job `58701111` is `RUNNING` on `volta-gpu`; downstream jobs `58701112` through `58701117` are dependency-pending. Watcher job `58701118` completed `0:0` after cancelling all still-pending `htzhulab` and `a100-gpu` mirrors. New Wave 2 finalizer job `58701119` waits with `afterany` over old failed jobs, superseded jobs, all race jobs, and the watcher.

Current state remains `NEEDS_MONITOR`, not complete and not reviewable. No `review.md` was written and no push was performed.

## Volta Hardware Failure And Htz/A100 Retry

The `volta-gpu` D0 job `58701111` failed after `00:04:15` with `CUDA error: no kernel image is available for execution on the device`; the log shows the installed PyTorch build does not support Tesla V100 compute capability 7.0. This is an operational hardware compatibility failure, not M10 training evidence. Jobs `58701111` through `58701117` receive zero effective-training credit.

The controller added a CUDA kernel smoke to `wave2_env_preflight.sh` so future preflights must prove that a visible GPU can execute kernels. A same-scope replacement race was submitted only to `htzhulab` and `a100-gpu`: htz preflight `58701195`, htz chain `58701196`-`58701202`; a100 preflight `58701203`, a100 chain `58701204`-`58701210`; watcher `58701211`; finalizer `58701212`.

Current state remains `NEEDS_MONITOR`: both new preflights are pending, watcher `58701211` is running, and finalizer `58701212` is dependency-pending.

## User-Authorized Retry3 Volta Add-On

The user then explicitly authorized adding `volta-gpu` back into the current M10 goal's routing race. The controller did not create a new milestone, executor, scientific design, budget, split, formula, or wave graph. It retained the active htz/a100 jobs and added a volta mirror guarded by the hardened compute-node preflight.

New retry3 jobs:

| Partition | Preflight | Formal chain | Current outcome |
| --- | ---: | --- | --- |
| `htzhulab` | `58701195` | `58701196`-`58701202` | preflight pending |
| `a100-gpu` | `58701203` | `58701204`-`58701210` | preflight pending |
| `volta-gpu` | `58701281` | `58701282`-`58701288` | preflight failed; formal chain cancelled by `afterok` |

The volta preflight log `logs/M10W2Preflight_volta-gpu_58701281_20260712_065303.log` confirms `mpmath 1.3.0`, `sympy 1.14.0`, and `optimizer_ok`, then fails at the CUDA kernel probe because `torch 2.11.0+cu130` does not support Tesla V100 compute capability 7.0. This is zero-credit operational hardware incompatibility, not training evidence.

The superseded two-partition watcher/finalizer `58701211` and `58701212` were cancelled after the retry3 watcher/finalizer were submitted. Active monitor jobs are watcher `58701289` and finalizer `58701290`. Current state remains `NEEDS_MONITOR`, not complete and not reviewable. No `review.md` was written and no push was performed.
