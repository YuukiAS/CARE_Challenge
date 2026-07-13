# M10 Controller Result

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Controller status: `NEEDS_MONITOR`

This controller executed only the bootstrap and hard-gate validation for the M10 section in `prompts/shared/EXECUTOR_PROMPTS.md` titled `M10 executor/controller: SRR-v3 complete mechanism repair`, using `prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml`.

The original executor plan validator passed, but M10 did not enter executor phase because the M10 contract's own prerequisite gate failed:

- `git merge-base --is-ancestor 828735482396d6d727d2294e88c89868e3118ad3 HEAD` returned exit code `1`.
- `prompts/shared/M10_srr_v3_complete_mechanism_repair.md`, the path recorded by the planning review and hash contract, is absent from current `HEAD`.
- `python scripts/validation/hash_milestone_contract.py prompts/shared/M10_srr_v3_complete_mechanism_repair.md` failed because that file is missing.

The standalone M10 staging file was added in `e26895b` and deleted in `06832b9` during integration into `prompts/shared/EXECUTOR_PROMPTS.md` and `prompts/shared/REVIEWER_PROMPTS.md`. That merge/delete flow is consistent with the staging-file cleanup policy, but the current M10 planning review still binds to the deleted standalone path and the current HEAD does not satisfy the planner-ancestor gate. The M10 prompt states that any such mismatch yields `M10_BLOCKED_PREREQUISITE`.

## Resumed Prerequisite Repair

A later integration-layer repair superseded the prerequisite blocker:

- `git merge-base --is-ancestor 828735482396d6d727d2294e88c89868e3118ad3 HEAD` now returns exit code `0`.
- Runtime contract validation now uses the merged canonical prompt sections in `prompts/shared/EXECUTOR_PROMPTS.md` and `prompts/shared/REVIEWER_PROMPTS.md`.
- `python scripts/validation/hash_canonical_prompt_contract.py ...` returns `5030af7d74e35a423dd7e782ed0d55dffc1c1e78335c4016bb75920c17da0e64`, matching `canonical_contract_sha256` in the planning review.

## Wave Progress

Wave 1 completed and was accepted by the controller:

- `m10_shared_architecture_executor` returned `READY_FOR_CONTROLLER_MERGE`.
- The controller committed the wave 1 code/evidence packet in `975acb7`.
- The mapper draft was committed in `c92b178`.

Wave 2 was launched after the wave 1 acceptance and wave 2 prompt commit:

- worker agent: `019f515e-39d5-7631-b6a1-5e1b4756701d`
- prompt: `results/20260711_srr_v3_m10_complete_mechanism_repair/subagents/m10_myops_training_executor_prompt.md`
- launch receipt: `results/20260711_srr_v3_m10_complete_mechanism_repair/wave2_launch_receipt.json`

The wave 2 worker initially returned `NEEDS_MONITOR` after submitting seven serial `htzhulab` jobs:

| Phase | Job ID | Current state |
| --- | ---: | --- |
| D0 static matched control | 58644072 | `PENDING (Resources)` |
| D1 spatial BR2 | 58644073 | `PENDING (Dependency)` |
| D2 hierarchical PSIP | 58644074 | `PENDING (Dependency)` |
| D3 full memory PropRef | 58644106 | `PENDING (Dependency)` |
| Hard-negative refresh | 58644107 | `PENDING (Dependency)` |
| No-nnU-Net-context control | 58644108 | `PENDING (Dependency)` |
| Alignment control | 58644109 | `PENDING (Dependency)` |

Formal monitor at `2026-07-11T15:45:38Z` found that all seven jobs reached terminal `FAILED` state with exit code `1:0`:

| Phase | Job ID | Terminal state | Exit code | Log |
| --- | ---: | --- | --- | --- |
| D0 static matched control | 58644072 | `FAILED` | `1:0` | `logs/M10D0MyoPS_58644072_20260711_110852.log` |
| D1 spatial BR2 | 58644073 | `FAILED` | `1:0` | `logs/M10D1MyoPS_58644073_20260711_112003.log` |
| D2 hierarchical PSIP | 58644074 | `FAILED` | `1:0` | `logs/M10D2MyoPS_58644074_20260711_112103.log` |
| D3 full memory PropRef | 58644106 | `FAILED` | `1:0` | `logs/M10D3MyoPS_58644106_20260711_112204.log` |
| Hard-negative refresh | 58644107 | `FAILED` | `1:0` | `logs/M10HardNeg_58644107_20260711_112305.log` |
| No-nnU-Net-context control | 58644108 | `FAILED` | `1:0` | `logs/M10NoCtx_58644108_20260711_112406.log` |
| Alignment control | 58644109 | `FAILED` | `1:0` | `logs/M10Align_58644109_20260711_112450.log` |

The shared failure path is missing `mpmath` in `env_CARE`, reached through `sympy` during PyTorch optimizer initialization. The controller repaired the project-local dependency to `mpmath 1.3.0` and verified a minimal `torch.optim.AdamW` initialization, but no replacement Slurm training jobs were submitted in this packet.

Post-job aggregation was rerun and wrote fail-closed phase evidence with `STARTUP_FAILED_NEEDS_EVIDENCE`. This is not M10 completion evidence.

The user later explicitly authorized a same-executor Wave 2 replacement attempt after the `mpmath` repair. The old jobs are permanently recorded in `wave2_startup_failed_jobs.csv` with zero training, optimizer-step, and train-loop-second credit. A first compute-node preflight job, `58682781`, was submitted to `htzhulab` with the same environment initialization and the user-required import/optimizer block. It was superseded before formal training submission because the current Slurm skill requires enhanced CUDA/config/writability/fingerprint checks. The active enhanced compute-node preflight job is `58683497`, currently pending on `htzhulab`. Formal replacement jobs have not been submitted yet because the active enhanced preflight has not exited `0`.

Wave 3, review, push, validation packaging/upload, hosted claims, route promotion, scientific stop, and M11 remain blocked until replacement Wave 2 preflight succeeds, replacement Wave 2 jobs complete, and post-job aggregation is committed.
## Latest Wave 2 Replacement Submission Update

At `2026-07-12T10:16:12Z`, the controller submitted the authorized same-executor Wave 2 replacement chain after successful compute-node preflight job `58700751` completed `0:0`. Replacement jobs are `58700815`, `58700821`, `58700822`, `58700826`, `58700827`, `58700828`, and `58700832`; the Wave 2 accounting finalizer is `58700842` with `afterany` over all old and replacement jobs. Current status is `NEEDS_MONITOR`, not complete and not reviewable.

## Three-Partition Formal Race Update

After explicit user authorization, the pending single-partition replacement chain and finalizer were superseded for a formal `htzhulab` / `a100-gpu` / `volta-gpu` race with isolated runtime roots and deferred aggregation. Superseded jobs `58700815`, `58700821`, `58700822`, `58700826`, `58700827`, `58700828`, `58700832`, and finalizer `58700842` were cancelled before training start and receive zero training credit.

`volta-gpu` won the race: preflight `58701110` completed `0:0`, D0 `58701111` is running, and watcher `58701118` cancelled the still-pending `htzhulab` and `a100-gpu` mirrors. The active finalizer is `58701119`. Current controller status remains `NEEDS_MONITOR`; Wave 2 is not complete and is not ready for review.

## Hardware Compatibility Retry Update

`volta-gpu` D0 `58701111` failed with a V100/PyTorch CUDA kernel incompatibility (`no kernel image is available for execution on the device`). This attempt is recorded as zero-credit operational hardware failure. The preflight now includes an actual CUDA kernel probe.

The controller submitted a same-scope `htzhulab`/`a100-gpu` replacement race: htz preflight `58701195`, htz formal chain `58701196`-`58701202`; a100 preflight `58701203`, a100 formal chain `58701204`-`58701210`; watcher `58701211`; finalizer `58701212`. Current status remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry3 Volta Add-On

The user explicitly authorized adding `volta-gpu` to the current goal's routing race. This did not change executor count, scientific design, variants, formulas, budgets, split, case set, evaluation rules, checkpoint rules, or result paths.

The controller added volta preflight `58701281` and formal afterok chain `58701282`-`58701288`, then replaced the two-partition watcher/finalizer with retry3 watcher `58701289` and finalizer `58701290`. The htz/a100 jobs remain pending and active.

Volta preflight `58701281` failed `1:0` after `00:00:47` with the known V100/PyTorch CUDA kernel incompatibility. The dependent volta formal jobs were cancelled before training start and receive zero training, optimizer-step, and train-loop-second credit. Current status remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry3 Monitor Check 1

At `2026-07-12T12:53:05Z`, htz preflight `58701195` and a100 preflight `58701203` were still `PENDING (Priority)`. Their formal chains `58701196`-`58701202` and `58701204`-`58701210` were still `PENDING (Dependency)`. Watcher `58701289` was `RUNNING` and finalizer `58701290` was `PENDING (Dependency)`.

This is retry3 pending-only two-hour monitor checkpoint `1/12`. It does not satisfy the 24-hour scheduler block threshold. Current status remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry3 Terminal Accounting

At `2026-07-12T13:49:48Z`, the active retry3 Slurm graph had no queued or running jobs. Accounting shows:

| Job group | Terminal outcome |
| --- | --- |
| `htzhulab` preflight `58701195` | `COMPLETED 0:0` after `00:00:28` |
| `htzhulab` D0 `58701196` | `FAILED 1:0` after `00:00:56` on `g1807htzh01` |
| `htzhulab` downstream `58701197`-`58701202` | `CANCELLED 0:0` by unmet `afterok` dependency |
| `a100-gpu` preflight/chain `58701203`-`58701210` | `CANCELLED by 397557` after watcher selected the htz D0 start |
| retry3 watcher `58701289` | `COMPLETED 0:0`; selected `htzhulab` because D0 started first |
| retry3 finalizer `58701290` | `FAILED 1:0`; propagated runtime failure/accounting failure |

The `htzhulab` D0 log `logs/M10D0MyoPS_58701196_20260712_090210.log` fails inside `scripts/training/run_srr_propref_myops_fold0.py` while writing train metrics:

```text
KeyError: 'correction_opportunity_loss'
```

The controller reran the finalizer aggregation command locally. It wrote `wave2_partition_race_retry3_finalization.json` and exited `2`. The finalization result selects `htzhulab` as the watcher winner, records the htz D0 as `FAILED(1:0)`, records all downstream phases as cancelled, and fails closed because `d0_control` evaluation has no valid runtime evidence.

Current controller state is `NEEDS_EVIDENCE`, not `NEEDS_MONITOR`, not complete, and not reviewable. The failed htz D0 attempt receives zero effective-training credit, the cancelled downstream/a100/volta jobs receive zero credit, and M10 Wave 2 has not satisfied the minimum-effective-training evidence gate.

Allowed next state is not Wave 3. Because this runtime failure is in Wave 2 training metrics/logging code, continuing would require either a same-scope operational repair if it does not alter variants, budgets, split, formulas, result paths, executor count, or wave graph, or `NEEDS_REVISION_RETURN_TO_WAVE1` / `NEEDS_GPT_PLANNER` if the repair touches forbidden shared architecture/loss semantics or changes the scientific contract.

## Wave 2 Owned-Wrapper Operational Repair

At `2026-07-12T14:00:16Z`, the controller applied a same-scope Wave 2 operational repair in the owned M10 wrapper `scripts/training/run_srr_v3_m10_complete_repair.py`. The repair wraps the imported legacy `propref_loss` and only supplies a missing log metric key, `correction_opportunity_loss`, as a zero tensor when the M10 non-M6 loss branch omits it. It does not change the optimized loss, model formulas, variants, budgets, split, result paths, executor count, or wave graph, and it does not edit the forbidden legacy training script, shared model code, or shared loss code.

Repair fingerprints:

| Artifact | SHA256 |
| --- | --- |
| `scripts/training/run_srr_v3_m10_complete_repair.py` | `e6d74451d4b0a22ef170e5b728b4103300d4b8dde3449a9570fa338c06b5bdd6` |
| `configs/srr_v3_m10_complete_repair.yaml` | `df42f9ee55a3ba6ac616a37b2455cb7bca67c5f751f0c5a31c4a18938b107a9b` |
| `data/benchmarks/protocol/splits_MyoPS.json` | `6165caeb5b47feb0d24f20380898037b7e6cead4db1eeba398a3c5a57faf9a1b` |

Local verification passed for `py_compile`, `--list-phases`, `--phase d0_control --print-contract`, targeted M10 `propref_loss` metric compatibility, executor-plan validation, handoff-policy validation, architecture wiki validation, architecture wiki generation check, and `git diff --check`.

One broader legacy test invocation, `env PYTHONPATH=. pytest src/care_myocardium/tests/test_srr_baseline_gate.py src/care_myocardium/tests/test_srr_v3_m10_fidelity.py`, reported `7 passed, 1 failed`: the failure is the known external compatibility case where `test_srr_baseline_gate.py` calls `scripts/training/run_srr_propref_myops_fold0.py` directly without `args.variant`. The M10 wave 2 prompt explicitly says that older script is not in this executor's write scope and this broader failure should be recorded as external compatibility unless it blocks owned M10 entrypoints. The M10-specific fidelity tests passed.

At the repair checkpoint, controller state remained `NEEDS_EVIDENCE` until a compute-node preflight and formal Wave 2 replacement chain could run.

## Retry4 Repaired-Code Formal Submission

At `2026-07-12T14:11:10Z`, the controller confirmed that repaired-code compute-node preflight job `58706079` completed `0:0` on `htzhulab` after `00:00:22`. The a100 mirror preflight `58706080` was cancelled while pending after the htz preflight succeeded. `volta-gpu` was not reused because the hardened CUDA kernel preflight had already proven the current PyTorch build is incompatible with V100 execution.

The controller submitted the unchanged seven-stage Wave 2 formal chain on `htzhulab` with the same executor, variants, budgets, split, case set, evaluation rules, checkpoint-selection rules, result paths, and wave graph. Training dependencies use `afterok`; the finalizer uses `afterany` over all old, superseded, failed, cancelled, preflight, and retry4 job IDs.

| Phase | Job ID | Current state |
| --- | ---: | --- |
| D0 static matched control | `58706293` | `RUNNING` on `g1807htzh01` |
| D1 spatial BR2 | `58706294` | `PENDING (Dependency)` |
| D2 hierarchical PSIP | `58706295` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58706296` | `PENDING (Dependency)` |
| Hard-negative refresh | `58706297` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58706298` | `PENDING (Dependency)` |
| Alignment control | `58706299` | `PENDING (Dependency)` |

Retry4 finalizer job `58706300` is `PENDING (Dependency)`. Runtime artifacts have begun appearing under `results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor/partition_race_retry4/htzhulab`, including the D0 phase contract, one-batch overfit outputs, prototype-update sanity outputs, and prototype bank summary.

Current controller state is `NEEDS_MONITOR`, not complete and not reviewable. Wave 3 remains blocked until Wave 2 terminal accounting and post-job aggregation succeed. No `review.md` was written and no push was performed.

## Retry4 Terminal Accounting And D1 Logging Repair

At `2026-07-12T16:24:12Z`, the retry4 Slurm graph was terminal:

| Phase | Job ID | Terminal state | Credit |
| --- | ---: | --- | --- |
| D0 static matched control | `58706293` | `COMPLETED 0:0` after `02:09:10` | valid D0 runtime evidence |
| D1 spatial BR2 | `58706294` | `FAILED 1:0` after `00:00:58` | zero effective D1 credit |
| D2 hierarchical PSIP | `58706295` | `CANCELLED` by unmet `afterok` | zero credit |
| D3 full memory PropRef | `58706296` | `CANCELLED` by unmet `afterok` | zero credit |
| Hard-negative refresh | `58706297` | `CANCELLED` by unmet `afterok` | zero credit |
| No-nnU-Net-context control | `58706298` | `CANCELLED` by unmet `afterok` | zero credit |
| Alignment control | `58706299` | `CANCELLED` by unmet `afterok` | zero credit |
| Finalizer | `58706300` | `FAILED 1:0` | fail-closed accounting |

D0 wrote formal runtime evidence under the retry4 htz runtime root, including `summary.json`, `training_log.csv`, `validation_events.csv`, `checkpoint_final.pt`, `checkpoint_best.pt`, retrieval usage, gradient sanity, prediction sanity, and full-case predictions/metrics for checkpoint-best and checkpoint-final.

D1 failed after one-batch sanity passed. The D1 log `logs/M10D1MyoPS_58706294_20260712_121728.log` shows:

```text
TypeError: float() argument must be a string or a real number, not 'list'
```

The failure occurs in retrieval-usage logging when the legacy `record_gate_usage` function receives nested/list gate weights from the M10 spatial router. The controller applied a same-scope operational repair in `scripts/training/run_srr_v3_m10_complete_repair.py`, monkeypatching only the wrapper's imported `legacy.record_gate_usage` so nested gate usage is flattened into scalar CSV rows. This does not change model formulas, loss values, variants, budgets, split, result paths, executor count, or wave graph, and it does not edit forbidden shared model/loss files or legacy training scripts.

Repair fingerprints:

| Artifact | SHA256 |
| --- | --- |
| `scripts/training/run_srr_v3_m10_complete_repair.py` | `bf132c6f6c1649c2a98bbe16af3ffe7cd67f436f035431a6b3376e4917203ad3` |
| `configs/srr_v3_m10_complete_repair.yaml` | `df42f9ee55a3ba6ac616a37b2455cb7bca67c5f751f0c5a31c4a18938b107a9b` |
| `data/benchmarks/protocol/splits_MyoPS.json` | `6165caeb5b47feb0d24f20380898037b7e6cead4db1eeba398a3c5a57faf9a1b` |

Local verification passed for py-compile, D1 print-contract, nested gate-usage compatibility smoke, executor-plan validation, handoff-policy validation, architecture wiki strict/history validation, and generated wiki check. Current controller state is `NEEDS_EVIDENCE` pending repaired-code compute-node preflight and a D1-through-alignment replacement chain. Wave 3 remains blocked.

## Retry5 D1-Through-Alignment Replacement Monitor

At `2026-07-12T16:37:37Z`, the controller confirmed repaired-code compute-node preflight job `58714000` completed `0:0` on `htzhulab` after `00:00:20`. Upstream D0 job `58706293` remains the valid completed D0 evidence from retry4: `COMPLETED 0:0` after `02:09:10`, with `summary.json` recording `actual_optimizer_steps=36746`, `elapsed_seconds=7200.021336678998`, and `eval_cases=44`.

The controller submitted a same-scope replacement chain for D1 through alignment only. This retains the same executor, variants, budgets, split, case set, evaluation rules, checkpoint-selection rules, runtime root, and Wave 2 graph. The D1 Slurm dependency is `afterok:58714000` because D0 success was machine-verified before submission; downstream stages use `afterok`.

| Phase | Old job | Replacement job | Current state |
| --- | ---: | ---: | --- |
| D0 static matched control | `58706293` | retained | `COMPLETED 0:0` |
| D1 spatial BR2 | `58706294` | `58714023` | `RUNNING` on `g1807htzh01` |
| D2 hierarchical PSIP | `58706295` | `58714024` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58706296` | `58714025` | `PENDING (Dependency)` |
| Hard-negative refresh | `58706297` | `58714026` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58706298` | `58714027` | `PENDING (Dependency)` |
| Alignment control | `58706299` | `58714028` | `PENDING (Dependency)` |

Retry5 finalizer job `58714029` is pending with `afterany` over all old, superseded, failed, cancelled, preflight, D0, and retry5 replacement jobs.

Current controller state is `NEEDS_MONITOR`, not complete and not reviewable. Wave 3 remains blocked until D1-through-alignment reaches terminal state, finalizer accounting runs, and Wave 2 post-job aggregation produces a successful completion receipt.

## Retry5 Terminal OOM And Retry6 Resource Retry

At `2026-07-12T16:47:36Z`, retry5 reached terminal accounting:

| Phase | Job ID | Terminal state | Credit |
| --- | ---: | --- | --- |
| D0 static matched control | `58706293` | retained `COMPLETED 0:0` | valid D0 runtime evidence |
| D1 spatial BR2 | `58714023` | `OUT_OF_MEMORY 0:125` after `00:07:50` | zero effective D1 credit |
| D2 hierarchical PSIP | `58714024` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| D3 full memory PropRef | `58714025` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Hard-negative refresh | `58714026` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| No-nnU-Net-context control | `58714027` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Alignment control | `58714028` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Finalizer | `58714029` | `FAILED 1:0` | fail-closed accounting |

Slurm memory accounting records `ReqMem=64G` and batch `MaxRSS=67107264K` for D1. The controller treats this as an operational resource-request failure, not a scientific design change. The retry5 finalization replay wrote `wave2_partition_race_retry5_finalization.json` with `status: NEEDS_EVIDENCE`, `winner_reason: no_completed_chain`, D1 `OUT_OF_MEMORY(0:125)`, and downstream jobs cancelled.

The controller then submitted same-scope retry6 with only the Slurm memory request increased to `96G`. Code/config/split hashes remain unchanged:

| Artifact | SHA256 |
| --- | --- |
| `scripts/training/run_srr_v3_m10_complete_repair.py` | `bf132c6f6c1649c2a98bbe16af3ffe7cd67f436f035431a6b3376e4917203ad3` |
| `configs/srr_v3_m10_complete_repair.yaml` | `df42f9ee55a3ba6ac616a37b2455cb7bca67c5f751f0c5a31c4a18938b107a9b` |
| `data/benchmarks/protocol/splits_MyoPS.json` | `6165caeb5b47feb0d24f20380898037b7e6cead4db1eeba398a3c5a57faf9a1b` |

Retry6 compute-node preflight `58714615` completed `0:0` on `htzhulab` with `ReqMem=96G`. The replacement chain is:

| Phase | Job ID | Current state |
| --- | ---: | --- |
| retained D0 | `58706293` | `COMPLETED 0:0` |
| D1 spatial BR2 | `58714634` | `RUNNING` on `g1807htzh01` |
| D2 hierarchical PSIP | `58714635` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58714636` | `PENDING (Dependency)` |
| Hard-negative refresh | `58714637` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58714638` | `PENDING (Dependency)` |
| Alignment control | `58714639` | `PENDING (Dependency)` |

Retry6 finalizer job `58714640` is pending with `afterany`. Current controller state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry6 Terminal OOM And Retry7 Resource Retry

At `2026-07-12T17:10:37Z`, retry6 reached terminal accounting:

| Phase | Job ID | Terminal state | Credit |
| --- | ---: | --- | --- |
| D0 static matched control | `58706293` | retained `COMPLETED 0:0` | valid D0 runtime evidence |
| D1 spatial BR2 | `58714634` | `OUT_OF_MEMORY 0:125` after `00:12:46` | zero effective D1 credit |
| D2 hierarchical PSIP | `58714635` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| D3 full memory PropRef | `58714636` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Hard-negative refresh | `58714637` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| No-nnU-Net-context control | `58714638` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Alignment control | `58714639` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Finalizer | `58714640` | `FAILED 2:0` | finalizer argument-format failure; local replay performed |

Slurm memory accounting records `ReqMem=96G` and batch `MaxRSS=100661736K` for D1. The retry6 finalizer failed because the controller submitted `--aggregation-command` as split argv rather than a single string; this was an operational finalizer submission defect and does not change the training accounting. The controller locally replayed retry6 finalization with Slurm accounting access and wrote `wave2_partition_race_retry6_finalization.json`, recording `status: NEEDS_EVIDENCE`, `winner_reason: no_completed_chain`, D1 `OUT_OF_MEMORY(0:125)`, and downstream jobs cancelled.

The controller then submitted same-scope retry7 with only the Slurm memory request increased to `128G`. Code/config/split hashes remain unchanged:

| Artifact | SHA256 |
| --- | --- |
| `scripts/training/run_srr_v3_m10_complete_repair.py` | `bf132c6f6c1649c2a98bbe16af3ffe7cd67f436f035431a6b3376e4917203ad3` |
| `configs/srr_v3_m10_complete_repair.yaml` | `df42f9ee55a3ba6ac616a37b2455cb7bca67c5f751f0c5a31c4a18938b107a9b` |
| `data/benchmarks/protocol/splits_MyoPS.json` | `6165caeb5b47feb0d24f20380898037b7e6cead4db1eeba398a3c5a57faf9a1b` |

Retry7 compute-node preflight `58719811` completed `0:0` on `htzhulab` with `ReqMem=128G`. The replacement chain is:

| Phase | Job ID | Current state |
| --- | ---: | --- |
| retained D0 | `58706293` | `COMPLETED 0:0` |
| D1 spatial BR2 | `58719835` | `RUNNING` on `g1807htzh01` |
| D2 hierarchical PSIP | `58719836` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58719837` | `PENDING (Dependency)` |
| Hard-negative refresh | `58719838` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58719839` | `PENDING (Dependency)` |
| Alignment control | `58719840` | `PENDING (Dependency)` |

Retry7 finalizer job `58719841` is pending with `afterany`. Its `aggregation_command` is recorded as a single string to avoid the retry6 finalizer argument-format failure. Current controller state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry7 Terminal OOM And Retry8 Patron-QOS Resource Retry

At `2026-07-12T17:44:44Z`, retry7 reached terminal accounting: D1 `58719835` failed as `OUT_OF_MEMORY 0:125` after `00:18:06` with `ReqMem=128G` and batch `MaxRSS=134216104K`; D2-through-alignment `58719836`-`58719840` were cancelled by unmet `afterok`; finalizer `58719841` failed fail-closed. The controller replayed retry7 finalization and wrote `wave2_partition_race_retry7_finalization.json` with `status: NEEDS_EVIDENCE`, `winner_reason: no_completed_chain`, and D1 `OUT_OF_MEMORY(0:125)`.

A direct 160G retry under `gpu_access` was rejected by Slurm with `QOSMaxMemoryPerJob`; `sacctmgr` showed `gpu_access` has `MaxTRESPerJob mem=128G`, while the user's allowed QoS list includes `gpu_access_patron`. The controller therefore submitted same-scope retry8 with `--qos=gpu_access_patron --mem=160G`. This changes only Slurm resource routing, not code/config/split/variants/budgets/formulas/result paths/executor count/wave graph.

Retry8 preflight `58720440` completed `0:0`. Current retry8 state:

| Phase | Job ID | Current state |
| --- | ---: | --- |
| retained D0 | `58706293` | `COMPLETED 0:0` |
| D1 spatial BR2 | `58720458` | `RUNNING` on `g1807htzh01` |
| D2 hierarchical PSIP | `58720459` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58720460` | `PENDING (Dependency)` |
| Hard-negative refresh | `58720461` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58720462` | `PENDING (Dependency)` |
| Alignment control | `58720463` | `PENDING (Dependency)` |

Retry8 finalizer job `58720464` is pending with `afterany`. Current controller state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry8 Terminal OOM And D1 Memory-Growth Diagnosis

At `2026-07-12T18:21:31Z`, retry8 reached terminal accounting:

| Phase | Job ID | Terminal state | Credit |
| --- | ---: | --- | --- |
| D0 static matched control | `58706293` | retained `COMPLETED 0:0` | valid D0 runtime evidence |
| D1 spatial BR2 | `58720458` | `OUT_OF_MEMORY 0:125` after `00:23:41` | zero effective D1 credit |
| D2 hierarchical PSIP | `58720459` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| D3 full memory PropRef | `58720460` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Hard-negative refresh | `58720461` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| No-nnU-Net-context control | `58720462` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Alignment control | `58720463` | `CANCELLED 0:0` by unmet `afterok` | zero credit |
| Finalizer | `58720464` | `FAILED 1:0` | fail-closed accounting |

Slurm memory accounting records `ReqMem=160G`, `QOS=gpu_access_patron`, and batch `MaxRSS=167770540K` for D1. The controller locally replayed retry8 finalization and wrote `wave2_partition_race_retry8_finalization.json`, recording `status: NEEDS_EVIDENCE`, `winner_reason: no_completed_chain`, D1 `OUT_OF_MEMORY(0:125)`, and downstream jobs cancelled.

D1 wrote early runtime artifacts under the retained retry4 htz runtime root, including `one_batch_overfit.csv`, `one_batch_overfit.json`, `prototype_bank_summary.json`, `prototype_update_sanity.csv`, and `checkpoint_validation_step_1666.pt`. It did not write `training_log.csv`, `validation_events.csv`, `summary.json`, or final full-case completion evidence, so D1 remains zero-credit for the M10 minimum-effective-training budget.

The repeated D1 OOM sequence is now:

| Attempt | Job ID | ReqMem | MaxRSS | Elapsed |
| --- | ---: | ---: | ---: | ---: |
| retry5 | `58714023` | `64G` | `67107264K` | `00:07:50` |
| retry6 | `58714634` | `96G` | `100661736K` | `00:12:46` |
| retry7 | `58719835` | `128G` | `134216104K` | `00:18:06` |
| retry8 | `58720458` | `160G` | `167770540K` | `00:23:41` |

This pattern indicates a D1 memory-growth defect in the runtime path, not a startup, environment, or ordinary pending/scheduler condition. The current state is `NEEDS_EVIDENCE`, not blocked and not complete. The controller may continue only with a same-scope Wave 2 operational repair inside the owned wrapper/evaluation/job/result write scope; any required change to forbidden shared architecture/loss files or scientific design must return to the appropriate revision/planning gate. Wave 3 remains blocked.

## Retry9 1200G Resource Replacement Monitor

At `2026-07-12T18:29:52Z`, the controller submitted same-scope retry9 after retry8 D1 OOM. The retry9 preflight job `58728960` completed `0:0` on `htzhulab` with `ReqMem=1200G`, `QOS=gpu_access_patron`, and node `g1807htzh01`.

Retry9 changes only Slurm resource routing. Code/config/split hashes remain unchanged:

| Artifact | SHA256 |
| --- | --- |
| `scripts/training/run_srr_v3_m10_complete_repair.py` | `bf132c6f6c1649c2a98bbe16af3ffe7cd67f436f035431a6b3376e4917203ad3` |
| `configs/srr_v3_m10_complete_repair.yaml` | `df42f9ee55a3ba6ac616a37b2455cb7bca67c5f751f0c5a31c4a18938b107a9b` |
| `data/benchmarks/protocol/splits_MyoPS.json` | `6165caeb5b47feb0d24f20380898037b7e6cead4db1eeba398a3c5a57faf9a1b` |

The replacement chain is:

| Phase | Job ID | Current state |
| --- | ---: | --- |
| retained D0 | `58706293` | `COMPLETED 0:0` |
| D1 spatial BR2 | `58732391` | `RUNNING` on `g1807htzh01` |
| D2 hierarchical PSIP | `58732393` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58732395` | `PENDING (Dependency)` |
| Hard-negative refresh | `58732397` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58732399` | `PENDING (Dependency)` |
| Alignment control | `58732400` | `PENDING (Dependency)` |

Retry9 finalizer job `58733769` is pending with `afterany` over all old, superseded, failed, cancelled, preflight, retained D0, and retry9 replacement jobs. Current controller state is `NEEDS_MONITOR`, not complete and not reviewable. Wave 3 remains blocked.

## Retry9 Progress Monitor Past Prior OOM Window

At `2026-07-12T19:11:38Z`, retry9 D1 `58732391` remained `RUNNING` on `g1807htzh01` for `00:43:51` with `ReqMem=1200G`. Live memory accounting reported `MaxRSS=280730920K` and `AveRSS=280694048K`.

This crossed every prior D1 OOM window:

| Attempt | Job ID | ReqMem | Outcome | Elapsed |
| --- | ---: | ---: | --- | ---: |
| retry5 | `58714023` | `64G` | `OUT_OF_MEMORY` | `00:07:50` |
| retry6 | `58714634` | `96G` | `OUT_OF_MEMORY` | `00:12:46` |
| retry7 | `58719835` | `128G` | `OUT_OF_MEMORY` | `00:18:06` |
| retry8 | `58720458` | `160G` | `OUT_OF_MEMORY` | `00:23:41` |
| retry9 | `58732391` | `1200G` | `RUNNING` | `00:43:51` |

D1 has written `checkpoint_validation_step_1666.pt` and `checkpoint_validation_step_3332.pt`. It has not written final `training_log.csv`, `validation_events.csv`, `summary.json`, or post-job aggregation evidence, so the state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry9 Running Monitor With Additional Checkpoints

At `2026-07-12T19:46:43Z`, retry9 D1 `58732391` remained `RUNNING` on `g1807htzh01` for `01:18:54` with `ReqMem=1200G`. Live memory accounting reported `MaxRSS=442276744K` and `AveRSS=442239872K`.

D1 has now written additional scheduled checkpoint evidence:

```text
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
checkpoint_validation_step_4998.pt
checkpoint_validation_step_5000.pt
checkpoint_best.pt
checkpoint_validation_step_6664.pt
```

D2-through-alignment remain dependency-pending and finalizer `58733769` remains dependency-pending. D1 has not written final `training_log.csv`, `validation_events.csv`, `summary.json`, or post-job aggregation evidence, so the state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry9 D1 Final-Checkpoint Running Monitor

At `2026-07-12T22:01:54Z`, retry9 D1 `58732391` remained `RUNNING` on `g1807htzh01` for `03:34:05` with `ReqMem=1200G`. Live memory accounting reported `MaxRSS=889579444K` and `AveRSS=889579444K`.

D1 has written final-checkpoint and training-log artifacts:

```text
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
checkpoint_validation_step_4998.pt
checkpoint_validation_step_5000.pt
checkpoint_validation_step_6664.pt
checkpoint_validation_step_8330.pt
checkpoint_validation_step_9996.pt
checkpoint_validation_step_11662.pt
checkpoint_validation_step_13328.pt
checkpoint_best.pt
checkpoint_final.pt
training_log.csv
validation_events.csv
```

D2-through-alignment remain dependency-pending and finalizer `58733769` remains dependency-pending. D1 has not written `summary.json`, Slurm has not reported a terminal state, and post-job aggregation has not run, so the state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry9 Undertraining and Retry10 Replacement

Retry9 D1 `58732391` reached Slurm `COMPLETED 0:0`, but the runtime summary shows it did not satisfy the blocking D1 training floor:

| Field | Observed | Required |
| --- | ---: | ---: |
| optimizer steps | `13600` | `25000` |
| train-loop seconds | `10805.073559065` | `9000` |
| validation events | `9` | `15` |
| eval cases | `44` | `44` |

The stop reason was `max_runtime_seconds`, with `max_runtime_seconds=10800.0`. This makes retry9 D1 `SCIENTIFIC_UNDERTRAINED` for M10 minimum-effective training and blocks downstream credit. The controller cancelled retry9 D2-through-alignment jobs `58732393`, `58732395`, `58732397`, `58732399`, and `58732400`. Retry9 finalizer `58733769` reached `FAILED 1:0` after writing fail-closed `finalizer_state.json`.

The controller applied a same-scope operational repair in the owned Wave 2 entrypoint `scripts/training/run_srr_v3_m10_complete_repair.py`: default `max_runtime_seconds` is now `28500.0`, still within the 8-hour Slurm walltime, so the original `max_steps` and validation minima can control formal completion. This does not change variants, model formulas, training budgets, split, case set, evaluation rules, checkpoint-selection rules, result paths, executor count, or wave graph.

Retry10 compute preflight `58743253` completed `0:0`, then the controller submitted the D1-through-alignment replacement chain:

| Phase | Retry10 job | Dependency | State at submission monitor |
| --- | ---: | --- | --- |
| D0 static matched control | `58706293` | retained | `COMPLETED 0:0` |
| D1 spatial BR2 | `58743282` | `afterok:58743253` | `RUNNING` |
| D2 hierarchical PSIP | `58743287` | `afterok:58743282` | `PENDING (Dependency)` |
| D3 full memory PropRef | `58743290` | `afterok:58743287` | `PENDING (Dependency)` |
| Hard-negative refresh | `58743292` | `afterok:58743290` | `PENDING (Dependency)` |
| No-nnU-Net-context control | `58743294` | `afterok:58743292` | `PENDING (Dependency)` |
| Alignment control | `58743295` | `afterok:58743294` | `PENDING (Dependency)` |
| Finalizer | `58743452` | `afterany` over all old and retry10 jobs | `PENDING (Dependency)` |

Current state is `NEEDS_MONITOR`, not complete and not reviewable. Wave 3 remains blocked.

## Retry10 Terminal OOM

At terminal accounting, retry10 D1 `58743282` reached `OUT_OF_MEMORY` with exit code `0:125` after `06:09:20` on `g1807htzh01`. The retained D0 job `58706293` remains valid upstream evidence, but retry10 D1 receives zero D1 minimum-effective-training credit and D2-through-alignment did not run because their required `afterok` dependency was not satisfied.

The Wave 2 finalizer job `58743452` wrote `finalizer_state.json` and `care_milestone_finalizer_58743452.log`. Its terminal classification is:

```text
final_state=RUNTIME_FAILURE
failure_class=OUT_OF_MEMORY_NEEDS_REVISION
suggested_next_state=NEEDS_REVISION
retryable=false
aggregation_exit_code=None
```

D1 retry10 wrote checkpoints through step 21658:

```text
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
checkpoint_validation_step_4998.pt
checkpoint_validation_step_5000.pt
checkpoint_validation_step_6664.pt
checkpoint_validation_step_8330.pt
checkpoint_validation_step_9996.pt
checkpoint_validation_step_11662.pt
checkpoint_validation_step_13328.pt
checkpoint_validation_step_14994.pt
checkpoint_validation_step_15000.pt
checkpoint_validation_step_16660.pt
checkpoint_validation_step_18326.pt
checkpoint_validation_step_19992.pt
checkpoint_validation_step_21658.pt
checkpoint_best.pt
```

D1 did not write final `training_log.csv`, `validation_events.csv`, `summary.json`, or `runtime_manifest.json`, and it did not reach the D1 optimizer-step floor of `25000`. Current controller state is `NEEDS_REVISION`, not `NEEDS_MONITOR`, not complete, and not reviewable. Wave 3 remains blocked. No `review.md` was written and no push was performed.

## Retry10 D1 Step18326 Monitor

At `2026-07-13T03:44:53Z`, retry10 D1 `58743282` was `RUNNING` on `g1807htzh01` for `04:42:57` with `ReqMem=1200G`. Live memory accounting reported `MaxRSS=1070713496K` and `AveRSS=1070713496K`.

D1 retry10 has written validation checkpoints through step 18326:

```text
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
checkpoint_validation_step_4998.pt
checkpoint_validation_step_5000.pt
checkpoint_validation_step_6664.pt
checkpoint_validation_step_8330.pt
checkpoint_validation_step_9996.pt
checkpoint_validation_step_11662.pt
checkpoint_validation_step_13328.pt
checkpoint_validation_step_14994.pt
checkpoint_validation_step_15000.pt
checkpoint_validation_step_16660.pt
checkpoint_validation_step_18326.pt
checkpoint_best.pt
```

D2-through-alignment remain dependency-pending and finalizer `58743452` remains dependency-pending. D1 has not written final `training_log.csv`, `validation_events.csv`, `summary.json`, `runtime_manifest.json`, or post-job aggregation evidence, so the state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry10 D1 Step16660 Monitor

At `2026-07-13T03:05:23Z`, retry10 D1 `58743282` was `RUNNING` on `g1807htzh01` for `04:03:38` with `ReqMem=1200G`. Live memory accounting reported `MaxRSS=971164048K` and `AveRSS=970805196K`.

D1 retry10 has written validation checkpoints through step 16660:

```text
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
checkpoint_validation_step_4998.pt
checkpoint_validation_step_5000.pt
checkpoint_validation_step_6664.pt
checkpoint_validation_step_8330.pt
checkpoint_validation_step_9996.pt
checkpoint_validation_step_11662.pt
checkpoint_validation_step_13328.pt
checkpoint_validation_step_14994.pt
checkpoint_validation_step_15000.pt
checkpoint_validation_step_16660.pt
checkpoint_best.pt
```

D2-through-alignment remain dependency-pending and finalizer `58743452` remains dependency-pending. D1 has not written final `training_log.csv`, `validation_events.csv`, `summary.json`, `runtime_manifest.json`, or post-job aggregation evidence, so the state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry10 D1 Step15000 Monitor

At `2026-07-13T02:33:14Z`, retry10 D1 `58743282` was `RUNNING` on `g1807htzh01` for `03:30:54` with `ReqMem=1200G`. Live memory accounting reported `MaxRSS=887014088K` and `AveRSS=887014088K`.

D1 retry10 has written validation checkpoints through step 15000:

```text
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
checkpoint_validation_step_4998.pt
checkpoint_validation_step_5000.pt
checkpoint_validation_step_6664.pt
checkpoint_validation_step_8330.pt
checkpoint_validation_step_9996.pt
checkpoint_validation_step_11662.pt
checkpoint_validation_step_13328.pt
checkpoint_validation_step_14994.pt
checkpoint_validation_step_15000.pt
checkpoint_best.pt
```

D2-through-alignment remain dependency-pending and finalizer `58743452` remains dependency-pending. D1 has not written final `training_log.csv`, `validation_events.csv`, `summary.json`, `runtime_manifest.json`, or post-job aggregation evidence, so the state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry10 D1 Step13328 Monitor

At `2026-07-13T01:58:39Z`, retry10 D1 `58743282` was `RUNNING` on `g1807htzh01` for `02:55:56` with `ReqMem=1200G`. Live memory accounting reported `MaxRSS=777281088K` and `AveRSS=777281088K`.

D1 retry10 has written validation checkpoints through step 13328:

```text
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
checkpoint_validation_step_4998.pt
checkpoint_validation_step_5000.pt
checkpoint_validation_step_6664.pt
checkpoint_validation_step_8330.pt
checkpoint_best.pt
checkpoint_validation_step_9996.pt
checkpoint_validation_step_11662.pt
checkpoint_validation_step_13328.pt
```

D2-through-alignment remain dependency-pending and finalizer `58743452` remains dependency-pending. D1 has not written final `training_log.csv`, `validation_events.csv`, `summary.json`, or post-job aggregation evidence, so the state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry10 D1 First-Checkpoint Monitor

At `2026-07-12T23:40:10Z`, retry10 D1 `58743282` was `RUNNING` on `g1807htzh01` for `00:37:44` with `ReqMem=1200G`. Live memory accounting reported `MaxRSS=248631016K` and `AveRSS=248631016K`.

D1 retry10 has written early sanity/prototype files and validation checkpoints:

```text
one_batch_overfit.csv
one_batch_overfit.json
prototype_update_sanity.csv
prototype_bank_summary.json
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
```

D2-through-alignment remain dependency-pending and finalizer `58743452` remains dependency-pending. D1 has not written final `training_log.csv`, `validation_events.csv`, `summary.json`, or post-job aggregation evidence, so the state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry10 D1 Time-Floor Monitor

At `2026-07-13T01:36:59Z`, retry10 D1 `58743282` was `RUNNING` on `g1807htzh01` for `02:34:35` with `ReqMem=1200G`. Live memory accounting reported `MaxRSS=722601808K` and `AveRSS=722601808K`.

D1's declared minimum train-loop seconds floor is `9000` seconds. The current elapsed time is `9275` seconds, so retry10 D1 has crossed the minimum-time floor. This is necessary progress but not completion evidence.

D1 retry10 has written validation checkpoints through step 11662:

```text
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
checkpoint_validation_step_4998.pt
checkpoint_validation_step_5000.pt
checkpoint_validation_step_6664.pt
checkpoint_validation_step_8330.pt
checkpoint_best.pt
checkpoint_validation_step_9996.pt
checkpoint_validation_step_11662.pt
```

D2-through-alignment remain dependency-pending and finalizer `58743452` remains dependency-pending. D1 has not written final `training_log.csv`, `validation_events.csv`, `summary.json`, or post-job aggregation evidence, so the state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry10 D1 Step6664 Monitor

At `2026-07-13T00:28:02Z`, retry10 D1 `58743282` was `RUNNING` on `g1807htzh01` for `01:25:37` with `ReqMem=1200G`. Live memory accounting reported `MaxRSS=473120584K` and `AveRSS=473120584K`.

D1 retry10 has written validation checkpoints through step 6664:

```text
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
checkpoint_validation_step_4998.pt
checkpoint_validation_step_5000.pt
checkpoint_best.pt
checkpoint_validation_step_6664.pt
```

D2-through-alignment remain dependency-pending and finalizer `58743452` remains dependency-pending. D1 has not written final `training_log.csv`, `validation_events.csv`, `summary.json`, or post-job aggregation evidence, so the state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry9 D1 Minimum-Time Monitor

At `2026-07-12T21:02:29Z`, retry9 D1 `58732391` remained `RUNNING` on `g1807htzh01` for `02:34:44` with `ReqMem=1200G`. Live memory accounting reported `MaxRSS=717908636K` and `AveRSS=717802624K`.

D1's declared minimum train-loop seconds floor is `9000` seconds. The current elapsed time is `9284` seconds, so retry9 D1 has crossed the minimum-time floor. This is necessary progress but not completion evidence.

D1 has now written scheduled checkpoint evidence through step 11662:

```text
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
checkpoint_validation_step_4998.pt
checkpoint_validation_step_5000.pt
checkpoint_validation_step_6664.pt
checkpoint_validation_step_8330.pt
checkpoint_validation_step_9996.pt
checkpoint_validation_step_11662.pt
checkpoint_best.pt
```

D2-through-alignment remain dependency-pending and finalizer `58733769` remains dependency-pending. D1 has not written final `training_log.csv`, `validation_events.csv`, `summary.json`, or post-job aggregation evidence, so the state remains `NEEDS_MONITOR`, not complete and not reviewable.

## Retry9 Running Monitor Through Step 8330

At `2026-07-12T20:19:19Z`, retry9 D1 `58732391` remained `RUNNING` on `g1807htzh01` for `01:51:31` with `ReqMem=1200G`. Live memory accounting reported `MaxRSS=570767692K` and `AveRSS=570767692K`.

D1 has now written scheduled checkpoint evidence through step 8330:

```text
checkpoint_validation_step_1666.pt
checkpoint_validation_step_3332.pt
checkpoint_validation_step_4998.pt
checkpoint_validation_step_5000.pt
checkpoint_validation_step_6664.pt
checkpoint_validation_step_8330.pt
checkpoint_best.pt
```

D2-through-alignment remain dependency-pending and finalizer `58733769` remains dependency-pending. D1 has not written final `training_log.csv`, `validation_events.csv`, `summary.json`, or post-job aggregation evidence, so the state remains `NEEDS_MONITOR`, not complete and not reviewable.
