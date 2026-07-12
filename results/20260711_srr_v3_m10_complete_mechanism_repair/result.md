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
