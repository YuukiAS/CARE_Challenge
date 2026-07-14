# M10 Controller Validator Report

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Run timestamp UTC: `2026-07-11T15:45:38Z`

## Current Validation / Hard-Gate Audit

Run timestamp UTC: `2026-07-14T00:16:15Z`

| Command | Exit | Result |
| --- | ---: | --- |
| `python scripts/validation/hash_canonical_prompt_contract.py --executor-file prompts/shared/EXECUTOR_PROMPTS.md --executor-heading 'M10 executor/controller: SRR-v3 complete mechanism repair' --reviewer-file prompts/shared/REVIEWER_PROMPTS.md --reviewer-heading 'M10 reviewer: SRR-v3 complete mechanism repair'` | 0 | `955f6ab31e523123ba339e5b1732b78b304f099b9ce92bc896dfbb1e5d76653f` |
| compare against `prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_planning_review.md` `canonical_contract_sha256` | 1 | expected `5030af7d74e35a423dd7e782ed0d55dffc1c1e78335c4016bb75920c17da0e64`; mismatch |
| `git diff 35b4f6b..HEAD -- prompts/shared/EXECUTOR_PROMPTS.md` | 0 | drift localized to M10 `Slurm continuity and finalizers`; commit `c53fa06` added preflight, retry, `afterok`/`afterany`, old/replacement job retention, zero-credit startup policy |
| `squeue -j 58848099,58848203,58848205,58848313 -h -o '%i\|%j\|%T\|%M\|%R'` | 0 | no active queued/running Wave3 jobs |
| `sacct -j 58848099,58848203,58848205,58848313 --format=JobID,JobName%18,Partition,State,ExitCode,Elapsed,NodeList -P` | 0 | adapter `COMPLETED`, registration `FAILED 2:0`, temporal `CANCELLED`, finalizer `COMPLETED` |

Interpretation: the current controller packet is not normal M10 completion. The Wave3 runtime evidence is terminal and
fail-closed, and the canonical prompt contract hash no longer matches the planning review. Per the M10 prompt, this is
`M10_BLOCKED_PREREQUISITE`; the controller must not self-update the planning review hash or continue M10 execution.

## Commands

| Command | Exit | Result |
| --- | ---: | --- |
| `python scripts/ops/validate_executor_plan.py prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml` | 0 | `executor plan validation passed` |
| `python scripts/validation/validate_handoff_policy.py --strict-tasks --warnings-as-errors` | 0 | `handoff policy validation passed` |
| `python scripts/architecture/validate_care_architecture_wiki.py --strict --history` | 0 | `care architecture wiki validation passed` |
| `python scripts/architecture/generate_care_architecture_wiki.py --check-all` | 0 | `care architecture wiki diagrams ok` |
| `python scripts/validation/hash_canonical_prompt_contract.py --executor-file prompts/shared/EXECUTOR_PROMPTS.md --executor-heading 'M10 executor/controller: SRR-v3 complete mechanism repair' --reviewer-file prompts/shared/REVIEWER_PROMPTS.md --reviewer-heading 'M10 reviewer: SRR-v3 complete mechanism repair'` | 0 | `5030af7d74e35a423dd7e782ed0d55dffc1c1e78335c4016bb75920c17da0e64` |
| `git diff --check` | 0 | no whitespace errors |
| `python -m py_compile scripts/training/run_srr_v3_m10_complete_repair.py scripts/evaluation/evaluate_srr_v3_m10_full_case.py scripts/evaluation/aggregate_srr_v3_m10_myops.py` | 0 | pass |
| `bash -n jobs/src/run_srr_v3_m10_myops_d0_control.sh jobs/src/run_srr_v3_m10_myops_d1_spatial_br2.sh jobs/src/run_srr_v3_m10_myops_d2_hierarchical_psip.sh jobs/src/run_srr_v3_m10_myops_d3_full_propref.sh jobs/src/run_srr_v3_m10_hard_negative_refresh.sh jobs/src/run_srr_v3_m10_no_context_control.sh jobs/src/run_srr_v3_m10_alignment_control.sh` | 0 | pass |
| `env PYTHONPATH=. pytest src/care_myocardium/tests/test_srr_v3_m10_fidelity.py` | 0 | `5 passed` |
| `squeue -j 58644072,58644073,58644074,58644106,58644107,58644108,58644109 -o '%i\|%j\|%T\|%M\|%D\|%R\|%P'` | 0 | no active jobs returned |
| `sacct -j 58644072,58644073,58644074,58644106,58644107,58644108,58644109 --format=JobIDRaw,JobName,State,ExitCode,Elapsed,Start,End,NodeList -P` | 0 | all seven top-level jobs `FAILED`, exit `1:0` |
| `env PYTHONPATH=. python scripts/evaluation/aggregate_srr_v3_m10_myops.py --all --job-id ... --job-state ... --job-exit-code ... --job-log ...` | 2 | expected fail-closed `STARTUP_FAILED_NEEDS_EVIDENCE` |
| `./envs/env_CARE/bin/python -c 'import sympy, mpmath; ...'` | 0 | `sympy 1.14.0`, `mpmath 1.3.0` after local dependency repair |
| `./envs/env_CARE/bin/python -c 'import torch; ... torch.optim.AdamW(...)'` | 0 | `optimizer_ok` after local dependency repair |

## Gate Checks

| Check | Exit | Interpretation |
| --- | ---: | --- |
| `git cat-file -t 828735482396d6d727d2294e88c89868e3118ad3` | 0 | planner draft commit object exists |
| `git merge-base --is-ancestor 828735482396d6d727d2294e88c89868e3118ad3 HEAD` | 0 | planner draft commit is an ancestor of current HEAD |
| `python scripts/validation/hash_canonical_prompt_contract.py ...` | 0 | canonical post-merge contract hash matches planning review |

## Interpretation

The repository validators pass for the current policy/wiki state and this resumed packet. The M10 executor plan is syntactically valid and serial.

The prior prerequisite blocker is repaired. This validator report is not completion evidence for M10 runtime work; it only authorizes proceeding to serial wave 1.

Wave 1 has since completed and wave 2 submitted seven serial Slurm jobs. Formal accounting now shows all seven jobs failed with exit code `1:0`. Logs show the shared failure cause is missing `mpmath` for `sympy` during PyTorch optimizer initialization.

The active controller state is `NEEDS_MONITOR`; replacement Wave 2 enhanced compute-node preflight job `58683497` is pending. Prior preflight job `58682781` was superseded before formal submission because the current Slurm skill requires CUDA/config/writability/fingerprint checks. This remains not completion evidence and not a review request.

## Latest Validation

After enhanced preflight submission:

| Command | Exit | Result |
| --- | ---: | --- |
| `python scripts/ops/validate_executor_plan.py prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml` | 0 | pass |
| `python scripts/validation/validate_handoff_policy.py --strict-tasks --warnings-as-errors` | 0 | pass |
| `python scripts/architecture/validate_care_architecture_wiki.py --strict --history` | 0 | pass after root `TODO.md` removal from the working tree |
| `python scripts/architecture/generate_care_architecture_wiki.py --check-all` | 0 | pass |
| `bash -n ...wave2_env_preflight.sh ...care_milestone_finalizer.sh` | 0 | pass |
| `git diff --check` | 0 | pass |

The earlier root `TODO.md` validator blocker is cleared in the current working tree. This remains a monitor packet, not completed M10 runtime evidence.

## Replacement Submission Validation

After the authorized three-partition preflight race and replacement submission:

| Command | Exit | Result |
| --- | ---: | --- |
| `python -m json.tool results/20260711_srr_v3_m10_complete_mechanism_repair/finalizer_state.json` | 0 | pass |
| `python scripts/ops/validate_executor_plan.py prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml` | 0 | `executor plan validation passed` |
| `python scripts/validation/validate_handoff_policy.py --strict-tasks --warnings-as-errors` | 0 | `handoff policy validation passed` |
| `python scripts/architecture/validate_care_architecture_wiki.py --strict --history` | 0 | `care architecture wiki validation passed` |
| `python scripts/architecture/generate_care_architecture_wiki.py --check-all` | 0 | `care architecture wiki diagrams ok` |
| `git diff --check` | 0 | pass |
| `bash -n results/.../wave2_env_preflight.sh jobs/src/run_srr_v3_m10_*.sh jobs/src/care_milestone_finalizer.sh` | 0 | pass |
| `squeue -j 58700815,58700821,58700822,58700826,58700827,58700828,58700832,58700842 ...` | 0 | D0 `PENDING (Resources)`, downstream jobs `PENDING (Dependency)`, finalizer `PENDING (Dependency)` |
| `sacct -j 58700815,58700821,58700822,58700826,58700827,58700828,58700832,58700842 ...` | 0 | all replacement/finalizer jobs currently `PENDING`, exit `0:0` |

This remains a monitor packet, not completed M10 runtime evidence.

## Safety Confirmation

No `review.md`, validation packaging, upload, route promotion, hosted metric claim, scientific stop, wave 3, push, or M11 work occurred. Replacement Wave 2 jobs were submitted only after compute-node preflight job `58700751` completed `0:0`; the current state is `NEEDS_MONITOR`.

## Latest Validation Context

After explicit user authorization, Wave 2 formal routing was changed from a pending single-partition replacement chain to a three-partition race with isolated runtime roots and deferred mirror aggregation. `volta-gpu` won after preflight `58701110` completed `0:0`; D0 `58701111` is running; watcher `58701118` cancelled pending `htzhulab`/`a100-gpu` mirrors. Current state remains `NEEDS_MONITOR`.

`volta-gpu` D0 later failed with unsupported V100 CUDA kernel execution. The controller hardened preflight with a CUDA kernel probe and submitted a same-scope `htzhulab`/`a100-gpu` retry race. Current state remains `NEEDS_MONITOR`.
