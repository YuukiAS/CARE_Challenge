自然判断：执行顺序遵守 asset -> implementation checks -> fixed-overfit；fixed 未过，因此 formal300 和 1200 未启动。

Key commands:
- `git pull --ff-only origin main`
- `./envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/tasks/20260721_srr_batch7_upstream_candidate_quality_executor_plan.yaml`
- `sbatch jobs/srr_production/run_myops_batch7_asset_htzhulab.sh`
- `sbatch jobs/srr_production/run_myops_batch7_implementation_checks_htzhulab.sh`
- `sbatch jobs/srr_production/run_myops_batch7_fixed_overfit_htzhulab.sh`
- `./envs/env_CARE/bin/python scripts/evaluation/validate_srr_batch7_packet.py`
- `./envs/env_CARE/bin/python -m pytest -q tests/srr_production/test_myops_batch7_upstream_candidate.py tests/srr_production/test_myops_batch6_objective_alignment.py`
- `./envs/env_CARE/bin/python -m py_compile scripts/srr_production/build_srr_batch7_prototype_memory.py scripts/evaluation/run_srr_batch7_implementation_checks.py scripts/training/run_srr_batch7_fixed_overfit.py scripts/training/run_srr_batch7_formal.py scripts/evaluation/aggregate_srr_batch7_formal.py scripts/evaluation/aggregate_srr_batch7_interventions.py scripts/evaluation/validate_srr_batch7_packet.py scripts/srr_production/infer_myops.py scripts/training/run_srr_propref_myops_fold0.py`
- `git diff --check`

Terminal gate state:
- Asset rebuild PASS: `59767801`.
- Implementation checks PASS: `59768200`.
- Latest fixed-overfit FAIL: `59775353`.
- formal300 not submitted because fixed-overfit failed.
- formal1200 not submitted.
