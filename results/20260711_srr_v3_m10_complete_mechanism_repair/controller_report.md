# M10 Controller Report

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

## Current Controller State

The controller has completed and merged Wave 2 for controller purposes. Wave 2 terminal accounting now records the current effective formal chain as completed:

```text
58706293
58775065
58775066
58775067
58775068
58775069
58775070
```

`finalizer_state.json` records `final_state: READY_FOR_MAPPER_FINAL` and `aggregation_exit_code: 0`. `wave2_partition_race_retry11_finalization.json` records `status: TERMINAL_RUNTIME_EVIDENCE`. `wave2_merge_receipt.md` records `WAVE2_READY_FOR_CONTROLLER_MERGE_ACCEPTED`.

The milestone is not complete. The next controller action is to re-ground and start Wave 3 under the original `m10_cine_temporal_executor` contract. Review, push, validation packaging/upload, hosted metric claims, route promotion, route-negative conclusion, scientific stop, and M11 remain blocked.

Current pre-review decisions:

```text
controller_run_status: WAVE2_MERGED_WAVE3_PENDING
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: NOT_REVIEWED
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
git_push_decision: SKIP_PUSH
review_md_written: false
```

## Superseded Historical Log

The sections below are retained as chronological provenance for prior monitor/retry states and may contain superseded `NEEDS_MONITOR` snapshots.

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

## Retry3 Two-Hour Monitor Check 1

At `2026-07-12T12:53:05Z`, the controller performed the first formal two-hour pending-only checkpoint for retry3:

| Partition | Preflight | Formal chain | State |
| --- | ---: | --- | --- |
| `htzhulab` | `58701195` | `58701196`-`58701202` | preflight `PENDING (Priority)`, chain `PENDING (Dependency)` |
| `a100-gpu` | `58701203` | `58701204`-`58701210` | preflight `PENDING (Priority)`, chain `PENDING (Dependency)` |

Watcher `58701289` remains `RUNNING` and finalizer `58701290` remains `PENDING (Dependency)`. No partition has started D0 and no terminal runtime output exists. This is pending-only checkpoint `1/12`; the 24-hour scheduler saturation threshold is not met. Current state remains `NEEDS_MONITOR`, not blocked and not reviewable. The next legal pending-only checkpoint is no earlier than `2026-07-12T14:53Z`.

## Retry3 Terminal Accounting

At `2026-07-12T13:49:48Z`, the retry3 Slurm graph had no active queued/running jobs. `htzhulab` preflight `58701195` completed, htz D0 `58701196` started and failed after `00:00:56`, htz downstream jobs were cancelled by `afterok`, the a100 mirror was cancelled by watcher `58701289`, and finalizer `58701290` failed after propagating the unsuccessful runtime state.

The D0 log `logs/M10D0MyoPS_58701196_20260712_090210.log` fails with `KeyError: 'correction_opportunity_loss'` in `scripts/training/run_srr_propref_myops_fold0.py` during metrics logging. Local finalizer aggregation replay exited `2` and wrote `wave2_partition_race_retry3_finalization.json`, which records status `NEEDS_EVIDENCE`.

Current controller state is `NEEDS_EVIDENCE`. Wave 2 did not produce valid formal training evidence and Wave 3 remains blocked. No `review.md` was written and no push was performed.

## Wave 2 Operational Repair

The controller repaired the owned M10 wrapper after identifying that the D0 failure was a log-metric compatibility gap, not a shared architecture/loss defect. `scripts/training/run_srr_v3_m10_complete_repair.py` now wraps the imported legacy `propref_loss` and supplies missing `correction_opportunity_loss` as a zero tensor for M10 variants. This avoids editing the forbidden legacy script and does not alter optimized losses or scientific design.

Verification passed for M10 wrapper compile/contract/smoke and the required repository validators. A broader legacy pytest invocation retains the known direct-legacy `args.variant` failure; this is recorded as external compatibility under the Wave 2 prompt and does not block the owned M10 entrypoint repair.

At the repair checkpoint, the next required controller action was to commit the lightweight repair packet, run compute-node preflight under the repaired code, and submit the unchanged Wave 2 replacement chain only if preflight exited `0`.

## Retry4 Repaired-Code Monitor State

At `2026-07-12T14:11:10Z`, the repaired-code `htzhulab` preflight `58706079` had completed `0:0`, and the pending a100 mirror preflight `58706080` had been cancelled. The controller then submitted the unchanged Wave 2 formal chain on `htzhulab`:

| Phase | Job ID | State |
| --- | ---: | --- |
| `d0_control` | `58706293` | `RUNNING` |
| `d1_spatial_br2` | `58706294` | `PENDING (Dependency)` |
| `d2_hierarchical_psip` | `58706295` | `PENDING (Dependency)` |
| `d3_full_propref` | `58706296` | `PENDING (Dependency)` |
| `hard_negative_refresh` | `58706297` | `PENDING (Dependency)` |
| `no_context_control` | `58706298` | `PENDING (Dependency)` |
| `alignment_control` | `58706299` | `PENDING (Dependency)` |

Retry4 finalizer `58706300` is pending with `afterany`. D0 has started on `g1807htzh01` and has already written early runtime artifacts under `results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor/partition_race_retry4/htzhulab`.

```text
controller_run_status: NEEDS_MONITOR
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: NOT_REVIEWED
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_RETRY4_MONITOR_PACKET_COMMIT
git_commit_decision: COMMIT_LOCAL_PACKET
git_push_decision: SKIP_PUSH
review_md_written: false
```

Next required action is to monitor `58706293` through terminal state, then let the `afterok` chain and finalizer proceed. If the full chain completes, run/inspect Wave 2 post-job aggregation and continue the original M10 state machine. If a job fails, record zero-credit terminal accounting and either perform an allowed same-scope operational repair or return the precise failure state required by the M10 contract.

## Retry4 Terminal State And Owned-Wrapper Repair

At `2026-07-12T16:24:12Z`, retry4 reached terminal accounting. D0 `58706293` completed successfully and produced formal D0 runtime evidence. D1 `58706294` failed after `00:00:58`; D2 through alignment were cancelled by unmet `afterok`; finalizer `58706300` failed fail-closed.

The D1 failure was a retrieval-usage logging compatibility defect:

```text
TypeError: float() argument must be a string or a real number, not 'list'
```

The controller repaired only `scripts/training/run_srr_v3_m10_complete_repair.py`, adding an M10 wrapper monkeypatch for `legacy.record_gate_usage` that flattens nested/list gate weights into scalar CSV rows. This is an operational logging repair. It does not alter training semantics, losses, model formulas, data split, budgets, result paths, executor count, or wave graph.

```text
controller_run_status: NEEDS_EVIDENCE
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: NOT_REVIEWED
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_RETRY4_TERMINAL_REPAIR_PACKET_COMMIT
git_commit_decision: COMMIT_LOCAL_PACKET
git_push_decision: SKIP_PUSH
review_md_written: false
```

Next required action is repaired-code compute-node preflight. Only if that preflight exits `0` may the controller submit the D1-through-alignment replacement chain using afterok dependencies, retaining D0 `58706293` as the successful upstream phase.

## Retry5 D1-Through-Alignment Monitor State

At `2026-07-12T16:37:37Z`, repaired-code compute-node preflight job `58714000` had completed `0:0`, and D0 `58706293` was machine-verified as the retained successful upstream phase. The controller submitted only the D1-through-alignment replacement chain under the same `m10_myops_training_executor` and the same Wave 2 scientific contract.

| Phase | Job ID | State |
| --- | ---: | --- |
| retained `d0_control` | `58706293` | `COMPLETED 0:0` |
| `d1_spatial_br2` | `58714023` | `RUNNING` |
| `d2_hierarchical_psip` | `58714024` | `PENDING (Dependency)` |
| `d3_full_propref` | `58714025` | `PENDING (Dependency)` |
| `hard_negative_refresh` | `58714026` | `PENDING (Dependency)` |
| `no_context_control` | `58714027` | `PENDING (Dependency)` |
| `alignment_control` | `58714028` | `PENDING (Dependency)` |

Retry5 finalizer `58714029` is pending with `afterany`. The current state is:

```text
controller_run_status: NEEDS_MONITOR
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: NOT_REVIEWED
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_RETRY5_MONITOR_PACKET_COMMIT
git_commit_decision: COMMIT_LOCAL_PACKET
git_push_decision: SKIP_PUSH
review_md_written: false
```

Next required action is to monitor `58714023` through terminal state. If D1 succeeds, the afterok chain should continue through D2, D3, hard-negative refresh, no-context control, and alignment control, then finalizer accounting and Wave 2 post-job aggregation must be inspected before any Wave 3 handoff.

## Retry5 OOM And Retry6 96G Monitor State

Retry5 is terminal and unsuccessful. D1 `58714023` reached `OUT_OF_MEMORY 0:125` after `00:07:50` with `ReqMem=64G` and batch `MaxRSS=67107264K`; D2 through alignment were cancelled by unmet `afterok`, and finalizer `58714029` failed fail-closed. The local finalization replay wrote `wave2_partition_race_retry5_finalization.json` with `status: NEEDS_EVIDENCE`.

Because this is a Slurm resource request failure and not a scientific/model/split change, the controller submitted retry6 with `--mem=96G` and unchanged code/config/split fingerprints. Preflight `58714615` completed `0:0`. Current retry6 state:

| Phase | Job ID | State |
| --- | ---: | --- |
| retained `d0_control` | `58706293` | `COMPLETED 0:0` |
| `d1_spatial_br2` | `58714634` | `RUNNING` |
| `d2_hierarchical_psip` | `58714635` | `PENDING (Dependency)` |
| `d3_full_propref` | `58714636` | `PENDING (Dependency)` |
| `hard_negative_refresh` | `58714637` | `PENDING (Dependency)` |
| `no_context_control` | `58714638` | `PENDING (Dependency)` |
| `alignment_control` | `58714639` | `PENDING (Dependency)` |
| retry6 finalizer | `58714640` | `PENDING (Dependency)` |

```text
controller_run_status: NEEDS_MONITOR
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: NOT_REVIEWED
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_RETRY6_MONITOR_PACKET_COMMIT
git_commit_decision: COMMIT_LOCAL_PACKET
git_push_decision: SKIP_PUSH
review_md_written: false
```

Next required action is to monitor retry6 through terminal state, then inspect finalizer accounting and Wave 2 aggregation before any Wave 3 handoff.

## Retry6 OOM And Retry7 128G Monitor State

Retry6 is terminal and unsuccessful. D1 `58714634` reached `OUT_OF_MEMORY 0:125` after `00:12:46` with `ReqMem=96G` and batch `MaxRSS=100661736K`; D2 through alignment were cancelled by unmet `afterok`. Finalizer `58714640` failed with exit `2:0` because the controller submitted `--aggregation-command` as split argv. The controller replayed retry6 finalization locally with Slurm accounting and wrote `wave2_partition_race_retry6_finalization.json` with `status: NEEDS_EVIDENCE`.

Because this remains a Slurm resource request failure and not a scientific/model/split change, the controller submitted retry7 with `--mem=128G` and unchanged code/config/split fingerprints. Preflight `58719811` completed `0:0`. Current retry7 state:

| Phase | Job ID | State |
| --- | ---: | --- |
| retained `d0_control` | `58706293` | `COMPLETED 0:0` |
| `d1_spatial_br2` | `58719835` | `RUNNING` |
| `d2_hierarchical_psip` | `58719836` | `PENDING (Dependency)` |
| `d3_full_propref` | `58719837` | `PENDING (Dependency)` |
| `hard_negative_refresh` | `58719838` | `PENDING (Dependency)` |
| `no_context_control` | `58719839` | `PENDING (Dependency)` |
| `alignment_control` | `58719840` | `PENDING (Dependency)` |
| retry7 finalizer | `58719841` | `PENDING (Dependency)` |

```text
controller_run_status: NEEDS_MONITOR
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: NOT_REVIEWED
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_RETRY7_MONITOR_PACKET_COMMIT
git_commit_decision: COMMIT_LOCAL_PACKET
git_push_decision: SKIP_PUSH
review_md_written: false
```

Next required action is to monitor retry7 through terminal state, then inspect finalizer accounting and Wave 2 aggregation before any Wave 3 handoff.

## Retry7 OOM And Retry8 160G Monitor State

Retry7 is terminal and unsuccessful. D1 `58719835` reached `OUT_OF_MEMORY 0:125` after `00:18:06` with `ReqMem=128G` and batch `MaxRSS=134216104K`; D2 through alignment were cancelled by unmet `afterok`; finalizer `58719841` failed fail-closed. The controller replayed retry7 finalization locally and wrote `wave2_partition_race_retry7_finalization.json` with `status: NEEDS_EVIDENCE`.

The first 160G preflight attempt under `gpu_access` was rejected by Slurm because that QoS has `MaxTRESPerJob mem=128G`. The controller verified that the user association allows `gpu_access_patron` and submitted retry8 with `--qos=gpu_access_patron --mem=160G`. Current retry8 state:

| Phase | Job ID | State |
| --- | ---: | --- |
| retained `d0_control` | `58706293` | `COMPLETED 0:0` |
| `d1_spatial_br2` | `58720458` | `RUNNING` |
| `d2_hierarchical_psip` | `58720459` | `PENDING (Dependency)` |
| `d3_full_propref` | `58720460` | `PENDING (Dependency)` |
| `hard_negative_refresh` | `58720461` | `PENDING (Dependency)` |
| `no_context_control` | `58720462` | `PENDING (Dependency)` |
| `alignment_control` | `58720463` | `PENDING (Dependency)` |
| retry8 finalizer | `58720464` | `PENDING (Dependency)` |

```text
controller_run_status: NEEDS_MONITOR
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: NOT_REVIEWED
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_RETRY8_MONITOR_PACKET_COMMIT
git_commit_decision: COMMIT_LOCAL_PACKET
git_push_decision: SKIP_PUSH
review_md_written: false
```

Next required action is to monitor retry8 through terminal state, then inspect finalizer accounting and Wave 2 aggregation before any Wave 3 handoff.
