# Batch4 Implementation Snapshot

Status: `PREFLIGHT_PASS_FORMAL_TRAINING_NOT_STARTED`

As of: `2026-07-20T18:27:28Z`

Current local commit before this receipt update: `1d3d1d5dbf66fc6a5e76251d709304e1a2574db2`

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
| `59673675` | preflight-only | `htzhulab` | `COMPLETED 0:0` | `sacct` shows elapsed `00:01:41` on `g180702`; runtime summary records preflight-only PASS, 176 train cases, 44 validation cases, 60 overfit steps, formal training false. |

## Boundary

Formal 1800-step training has not started. The `one_batch_overfit.json` inline field `prototype_bank_selected_case_count` is `EVIDENCE_NOT_FOUND`; this receipt accounts it from the same-attempt `prototype_bank_summary.json`, which records `selected_case_ids=176` and `source_case_ids=176`. Step 600/1200/1800 full-volume evaluation, selected checkpoint reload, mapper final, independent review, validation upload, hosted metric claim, and push have not occurred.

## Terminal Preflight Receipt Update

- `sacct -j 59672536,59672892,59673675 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList -P` -> `59672536 CANCELLED by 397557`, `59672892 FAILED 1:0`, `59673675 COMPLETED 0:0 elapsed 00:01:41 g180702`.
- `59673675` runtime summary: `status=PREFLIGHT_PASS_FORMAL_TRAINING_NOT_STARTED`, `train_cases=176`, `val_cases=44`, `preflight_overfit_steps=60`, `formal_training_started=false`, `actual_optimizer_steps=0`.
- `59673675` one-batch overfit: `status=PASS`, first loss `3.4422695636749268`, last loss `1.012618064880371`, relative decrease `0.7058283652256124`.
- Prototype count reconciliation: inline `one_batch_overfit.json` has `prototype_bank_selected_case_count=EVIDENCE_NOT_FOUND`; sibling `prototype_bank_summary.json` from the same attempt records `selected_case_ids=176`, `source_case_ids=176`, `status=REAL_CASEWISE_PROTOTYPE_MEMORY_READY`, and no repeat-last vector fallback.
- This is a terminal preflight receipt only. It is not formal training completion, not a 44-case evaluation, not review-ready, and not a performance claim.

## Formal Training Dispatch

- Job `59674902` submitted to `htzhulab` from commit `a984992ba3689bac0b5c7590b7049816fcd4c931`.
- Initial state: `RUNNING` on `g1807htzh01`; no A100 mirror submitted because the primary started before the pending-race threshold.
- Attempt root: `results/20260721_srr_batch4_forced_fold0_training/runtime/attempts/srr_batch4_m10d3_full4scale_fold0_seed20260721_htzhulab_59674902`.
- Log: `logs/srr_batch4/SRRB4MyoPS_htzhulab_59674902_20260720_143201.log`.
- Winner lock: `results/20260721_srr_batch4_forced_fold0_training/runtime/locks/srr_batch4_m10d3_full4scale_fold0_seed20260721.winner/owner.json`.
- This is a running monitor state, not Batch4 completion.

## Formal Startup Failure And Repair

- Formal attempt `59674902` failed with exit `1:0` after `00:01:22` on `g1807htzh01`.
- Failure reason: `record_gate_usage` received nested/list-valued gate means and attempted `float(value)`.
- Training credit: `0`; formal 1800-step training did not complete and no 44-case evaluation exists.
- Same-scope repair stayed in `scripts/training/run_srr_propref_myops_fold0.py`: nested/list gate means and valid fractions are scalarized by averaging numeric leaves before CSV writing.
- Test: `tests/srr_production/test_myops_batch4_contract.py` now includes nested gate means regression; local run passed `11 passed, 3 warnings`.

## Formal Retry Running

- Job `59678596` submitted to `htzhulab` from repair commit `36d1ef9241a5b5a1606770a5c12e84faff43017f`.
- Initial monitored state after the previous failure window: `RUNNING` for `00:02:14` on `g1807htzh01`; no A100 mirror submitted.
- Attempt root: `results/20260721_srr_batch4_forced_fold0_training/runtime/attempts/srr_batch4_m10d3_full4scale_fold0_seed20260721_htzhulab_59678596`.
- Log: `logs/srr_batch4/SRRB4MyoPS_htzhulab_59678596_20260720_143925.log`.
- Winner lock: `results/20260721_srr_batch4_forced_fold0_training/runtime/locks/srr_batch4_m10d3_full4scale_fold0_seed20260721.winner/owner.json`.
- This is a running monitor state, not Batch4 completion.
