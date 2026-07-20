# Batch4 Implementation Snapshot

Status: `PREFLIGHT_RETRY2_SUBMITTED_AWAITING_TERMINAL_EVIDENCE`

As of: `2026-07-20T18:08:33Z`

Current local commit: `53fc6e60c1510dfe17aec7a1460883c88e46c705`

## Gate

- Planning review file: `prompts/tasks/20260721_srr_batch4_forced_fold0_training_planning_review.md`
- Planning review decision: `AUDITED_GO`
- Planning review token: `BATCH4_PLANNING_AUDITED_GO`
- Reviewed contract commit: `20e3aaf304f1687ba2e50c3885eb4bf88738d889`
- Execution head from origin before local Batch4 commits: `89474f7de8c38db1448e47ca7fe94d6620932b31`

## Implemented

- Training runner saves schema-v2 checkpoints through the shared checkpoint helper.
- Checkpoint architecture identity is mode-independent; runtime output mode is selected at inference/runtime.
- MyoPS identity export uses model logits argmax and records anchor/final softmax delta evidence.
- Batch4 contract fails closed for M10 D3 full-4scale, fold0 176/44 split, 1800 steps, 60-step overfit, and 600/1200/1800 full-volume evaluation events.
- Batch4 overfit preflight fits prototype/memory from the full training split instead of a single sampled case.
- Batch4 overfit pass criterion uses relative loss decrease fraction.
- `--preflight-only` stops after the one-batch preflight and before formal optimizer training.
- Formal training RNG is reset after preflight so preflight optimizer steps do not become formal training credit.
- Slurm job common script checks torch CUDA architecture compatibility before taking the winner lock.

## Verification

- `./envs/env_CARE/bin/python -m pytest tests/srr_production/test_myops_batch4_contract.py tests/srr_production/test_myops_batch2_preflight.py tests/srr_production/test_myops_batch2_inference_evaluation.py` -> `15 passed, 3 warnings`
- `./envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/tasks/20260721_srr_batch4_forced_fold0_training_executor_plan.yaml` -> passed
- `bash -n jobs/srr_production/run_myops_batch4_preflight_volta.sh jobs/srr_production/run_myops_batch4_preflight_a100.sh jobs/srr_production/run_myops_batch4_preflight_htzhulab.sh jobs/srr_production/run_myops_batch4_fold0_htzhulab.sh jobs/srr_production/run_myops_batch4_fold0_a100.sh jobs/srr_production/run_myops_batch4_fold0_volta.sh jobs/srr_production/run_myops_batch4_fold0_common.sh` -> passed
- `git diff --check` -> passed
- Environment/contract receipt: `results/20260721_srr_batch4_forced_fold0_training/preflight_environment_receipt.json`

## Slurm Attempts

| job_id | role | partition | state | evidence |
| --- | --- | --- | --- | --- |
| `59672536` | preflight-only | `volta-gpu` | `CANCELLED` | `logs/srr_batch4/SRRB4Pre_volta_59672536_20260720_134651.log` showed unsupported V100 compute capability for current torch build. |
| `59672892` | preflight-only | `htzhulab` | `FAILED` | `logs/srr_batch4/SRRB4Pre_htzhulab_59672892_20260720_135831.log` showed startup `NameError: vectors_from_mask is not defined`. |
| `59673675` | preflight-only | `htzhulab` | `PENDING (Resources)` | `squeue -j 59673675` at `2026-07-20T18:08:33Z`. |

## Boundary

Formal 1800-step training has not started. Step 600/1200/1800 full-volume evaluation, selected checkpoint reload, mapper final, independent review, validation upload, hosted metric claim, and push have not occurred.
