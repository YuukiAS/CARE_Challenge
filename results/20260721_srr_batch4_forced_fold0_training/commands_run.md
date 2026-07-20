# Batch4 Commands Run

This file records current lightweight controller evidence only. Submitted, pending, or running jobs are not completion evidence.

## Git

- `git fetch origin main`
- `git rev-parse HEAD` -> `89474f7de8c38db1448e47ca7fe94d6620932b31` before local Batch4 commits
- `git commit -m "Prepare SRR Batch4 fold0 training contract"` -> `4451450`
- `git commit -m "Guard Batch4 jobs against unsupported GPUs"` -> `2d1f74d`
- `git commit -m "Record SRR Batch4 preflight dispatch"` -> `4c99875`
- `git commit -m "Add SRR Batch4 monitor packet"` -> `d385242`
- `git commit -m "Fix Batch4 prototype vector extraction"` -> `53fc6e6`
- current HEAD before terminal preflight receipt update: `1d3d1d5dbf66fc6a5e76251d709304e1a2574db2`

## Validation

- `./envs/env_CARE/bin/python -m pytest tests/srr_production/test_myops_batch4_contract.py tests/srr_production/test_myops_batch2_preflight.py tests/srr_production/test_myops_batch2_inference_evaluation.py` -> `15 passed, 3 warnings`
- `./envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/tasks/20260721_srr_batch4_forced_fold0_training_executor_plan.yaml` -> `executor plan validation passed`
- `bash -n jobs/srr_production/run_myops_batch4_preflight_volta.sh jobs/srr_production/run_myops_batch4_preflight_a100.sh jobs/srr_production/run_myops_batch4_preflight_htzhulab.sh jobs/srr_production/run_myops_batch4_fold0_htzhulab.sh jobs/srr_production/run_myops_batch4_fold0_a100.sh jobs/srr_production/run_myops_batch4_fold0_volta.sh jobs/srr_production/run_myops_batch4_fold0_common.sh` -> pass
- `git diff --check` -> pass

## Preflight

- `./envs/env_CARE/bin/python scripts/ops/run_care_training_preflight.py ... --receipt-path results/20260721_srr_batch4_forced_fold0_training/preflight_environment_receipt.json` -> exit 0
- `sbatch --test-only jobs/srr_production/run_myops_batch4_preflight_htzhulab.sh` -> estimated `2026-07-21T12:29:18`
- `sbatch --test-only jobs/srr_production/run_myops_batch4_preflight_a100.sh` -> estimated `2026-08-06T03:13:37`
- `sbatch --test-only jobs/srr_production/run_myops_batch4_preflight_volta.sh` -> estimated `2026-07-20T14:14:35`
- `sbatch jobs/srr_production/run_myops_batch4_preflight_volta.sh` -> submitted `59672536`
- `scancel 59672536` -> cancelled after runtime log showed current torch build does not support V100 compute capability 7.0
- `sbatch --partition=htzhulab --gres=gpu:nvidia_a100-sxm4-80gb:1 --qos=gpu_access --export=ALL,LOGICAL_RUN_ID=srr_batch4_m10d3_full4scale_fold0_seed20260721_preflight_htzhulab_retry1 jobs/srr_production/run_myops_batch4_preflight_htzhulab.sh` -> submitted `59672892`
- `sacct -j 59672892 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList -P` -> `59672892 FAILED 1:0 00:03:58 g180702`
- `./envs/env_CARE/bin/python -m pytest tests/srr_production/test_myops_batch4_contract.py` -> `10 passed, 3 warnings`
- `git commit -m "Fix Batch4 prototype vector extraction"` -> `53fc6e6`
- `sbatch --partition=htzhulab --gres=gpu:nvidia_a100-sxm4-80gb:1 --qos=gpu_access --export=ALL,LOGICAL_RUN_ID=srr_batch4_m10d3_full4scale_fold0_seed20260721_preflight_htzhulab_retry2 jobs/srr_production/run_myops_batch4_preflight_htzhulab.sh` -> submitted `59673675`

## Current Slurm State

- `squeue -j 59673675` at `2026-07-20T18:08:33Z` -> `PENDING (Resources)`
- `sacct -j 59672536,59672892 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList -P` -> `59672536 CANCELLED`, `59672892 FAILED`
- `sacct -j 59672536,59672892,59673675 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList -P` at `2026-07-20T18:27:28Z` -> `59672536 CANCELLED by 397557 0:0 00:00:56 g0311`; `59672892 FAILED 1:0 00:03:58 g180702`; `59673675 COMPLETED 0:0 00:01:41 g180702`
- Read `59673675` runtime summary/overfit/prototype receipts under `results/20260721_srr_batch4_forced_fold0_training/runtime/attempts/srr_batch4_m10d3_full4scale_fold0_seed20260721_preflight_htzhulab_retry2_htzhulab_preflight_59673675/variants/...` -> terminal preflight-only PASS, train176, val44, 60 overfit steps, formal_started=false, optimizer_steps=0
- Reconciled `one_batch_overfit.json` inline `prototype_bank_selected_case_count=EVIDENCE_NOT_FOUND` from same-attempt `prototype_bank_summary.json` -> `selected_case_ids=176`, `source_case_ids=176`, `status=REAL_CASEWISE_PROTOTYPE_MEMORY_READY`, repeat-last fallback false

## Non-Completion Statement

No command in this file proves Batch4 completion. The current preflight state is `PREFLIGHT_PASS_FORMAL_TRAINING_NOT_STARTED`: job `59673675` completed a preflight-only run, but formal 1800-step training, 44-case evaluation, selected checkpoint reload, mapper final, reviewer handoff, validation upload, hosted metric claim, and push have not occurred.

## Formal Training Dispatch

- Pre-submit `--print-contract` at `a984992ba3689bac0b5c7590b7049816fcd4c931` -> `CONTRACT_VALID`, model `m10_d3_hierarchical_memory_propref`, `full_4scale`, `base_channels=32`, train `176`, validation `44`, eval steps `[600, 1200, 1800]`, max steps `1800`, min train loop seconds `1800`.
- `bash -n jobs/srr_production/run_myops_batch4_fold0_common.sh jobs/srr_production/run_myops_batch4_fold0_htzhulab.sh jobs/srr_production/run_myops_batch4_fold0_a100.sh jobs/srr_production/run_myops_batch4_fold0_volta.sh` -> pass.
- `squeue -p htzhulab` and `sinfo -o ...` inspected before submission; primary `htzhulab` remained default.
- `sbatch --export=ALL,LOGICAL_RUN_ID=srr_batch4_m10d3_full4scale_fold0_seed20260721 jobs/srr_production/run_myops_batch4_fold0_htzhulab.sh` -> submitted `59674902`.
- `squeue -j 59674902` at `2026-07-20T18:32:55Z` -> `RUNNING` on `g1807htzh01`; no A100 mirror submitted because primary started immediately.
- Startup log `logs/srr_batch4/SRRB4MyoPS_htzhulab_59674902_20260720_143201.log` confirms `env_CARE` Python, torch `2.11.0+cu130`, GPU `NVIDIA H100 NVL`, capability `sm_90`, logical run `srr_batch4_m10d3_full4scale_fold0_seed20260721`, isolated attempt root, and winner lock.

Running formal training is not completion. Terminal aggregation, validators, mapper final, final packet commit, and independent reviewer handoff remain required.

## Formal Startup Failure And Repair

- `sacct -j 59674902 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList -P` -> `59674902 FAILED 1:0 00:01:22 g1807htzh01`.
- Log `logs/srr_batch4/SRRB4MyoPS_htzhulab_59674902_20260720_143201.log` traceback: `TypeError: float() argument must be a string or a real number, not list` in `record_gate_usage`.
- Runtime attempt produced frozen prototype asset/manifest and one-batch overfit files, but no terminal formal training summary and no 1800-step credit.
- Same-scope repair: `scripts/training/run_srr_propref_myops_fold0.py` now records nested/list-valued gate means as scalar means locally for the propref runner.
- Regression: `./envs/env_CARE/bin/python -m pytest tests/srr_production/test_myops_batch4_contract.py` -> `11 passed, 3 warnings`.

This failure is zero formal training credit. Retry requires archiving the stale failed winner lock and rechecking exact command/scripts/config/hash at the repair commit.

## Formal Retry Dispatch

- Archived stale failed winner lock to `results/20260721_srr_batch4_forced_fold0_training/runtime/locks/srr_batch4_m10d3_full4scale_fold0_seed20260721.winner.failed_59674902_20260720T183637Z/owner.json`.
- Retry pre-submit `--print-contract` at `36d1ef9241a5b5a1606770a5c12e84faff43017f` -> `CONTRACT_VALID`, model `m10_d3_hierarchical_memory_propref`, `full_4scale`, `base_channels=32`, train `176`, validation `44`, eval steps `[600, 1200, 1800]`, max steps `1800`, min train loop seconds `1800`.
- `sbatch --export=ALL,LOGICAL_RUN_ID=srr_batch4_m10d3_full4scale_fold0_seed20260721 jobs/srr_production/run_myops_batch4_fold0_htzhulab.sh` -> submitted `59678596`.
- `squeue -j 59678596` at `2026-07-20T18:41:45Z` -> `RUNNING` on `g1807htzh01`; no A100 mirror submitted because htzhulab retry started immediately.
- Startup log `logs/srr_batch4/SRRB4MyoPS_htzhulab_59678596_20260720_143925.log` confirms `env_CARE` Python, torch `2.11.0+cu130`, GPU `NVIDIA H100 NVL`, capability `sm_90`, logical run `srr_batch4_m10d3_full4scale_fold0_seed20260721`, isolated attempt root, and winner lock.

Running formal retry is not completion. Terminal aggregation, validators, mapper final, final packet commit, and independent reviewer handoff remain required.
