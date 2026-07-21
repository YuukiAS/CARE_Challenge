自然判断：执行顺序遵守 asset -> implementation checks -> fixed-overfit -> formal300；formal300 已完成但 continuation gate 未过，因此 1200 未启动。

Key commands:
- `git pull --ff-only origin main`
- `./envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/tasks/20260721_srr_batch7_upstream_candidate_quality_executor_plan.yaml`
- `sbatch jobs/srr_production/run_myops_batch7_asset_htzhulab.sh`
- `sbatch jobs/srr_production/run_myops_batch7_implementation_checks_htzhulab.sh`
- `sbatch jobs/srr_production/run_myops_batch7_fixed_overfit_htzhulab.sh`
- `sbatch jobs/srr_production/run_myops_batch7_formal300_htzhulab.sh`
- `./envs/env_CARE/bin/python scripts/evaluation/aggregate_srr_batch7_formal.py --stage 300 --attempt-label batch7_formal300_htzhulab_59789651 --job-id 59789651 --job-state COMPLETED --exit-code 0:0 --elapsed 00:11:25 --node g1807htzh01`
- `./envs/env_CARE/bin/python scripts/evaluation/aggregate_srr_batch7_interventions.py`
- `./envs/env_CARE/bin/python scripts/evaluation/validate_srr_batch7_packet.py`
- `./envs/env_CARE/bin/python -m pytest -q tests/srr_production/test_myops_batch7_upstream_candidate.py tests/srr_production/test_myops_batch6_objective_alignment.py`
- `./envs/env_CARE/bin/python -m py_compile scripts/srr_production/build_srr_batch7_prototype_memory.py scripts/evaluation/run_srr_batch7_implementation_checks.py scripts/training/run_srr_batch7_fixed_overfit.py scripts/training/run_srr_batch7_formal.py scripts/evaluation/aggregate_srr_batch7_formal.py scripts/evaluation/aggregate_srr_batch7_interventions.py scripts/evaluation/validate_srr_batch7_packet.py scripts/srr_production/infer_myops.py scripts/training/run_srr_propref_myops_fold0.py src/care_myocardium/models/srr_propref.py`
- `git diff --check`

Terminal gate state:
- Asset rebuild PASS: `59767801`.
- Implementation checks latest PASS: `59784603`.
- Fixed-overfit PASS: `59783024`.
- formal300 retry after receipt parser repair: `59789651`, COMPLETED `0:0`, elapsed `00:11:25`, node `g1807htzh01`.
- formal300 continuation gate: FAIL, mean positive Dice delta `0.0003021837774180077 < 0.005`.
- formal1200 not submitted: `SKIPPED_STEP300_GATE_FAILED`.
