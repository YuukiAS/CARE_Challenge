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
- current HEAD: `53fc6e60c1510dfe17aec7a1460883c88e46c705`

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

## Non-Completion Statement

No command in this file proves Batch4 completion. The current terminal state is `NEEDS_MONITOR` because job `59673675` has not started or completed and formal 1800-step training has not been submitted.
