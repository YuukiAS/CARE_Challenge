# Batch6 Commands Run

All commands were run from `/users/a/e/aereinh/CARE` with `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python` where applicable.

| Command | Exit code | Evidence |
| --- | ---: | --- |
| `git fetch --all --prune` | 0 | origin/main `b2f123aa6fe4e84f6801cd15dc6c5f59ffb00080` |
| `tmux ls` | 0 | `care_srr_batch6_executor` existed; pane was stale/interrupted |
| `./envs/env_CARE/bin/python -m py_compile src/care_myocardium/losses/srr_losses.py scripts/training/run_srr_batch6_fixed_overfit.py scripts/training/run_srr_propref_myops_fold0.py scripts/evaluation/audit_srr_batch5_loss_authority.py tests/srr_production/test_myops_batch6_objective_alignment.py` | 0 | Python compile passed before final fixed-overfit retry |
| `./envs/env_CARE/bin/python -m pytest tests/srr_production/test_myops_batch6_objective_alignment.py` | 0 | 10 passed, 3 warnings |
| `./envs/env_CARE/bin/python scripts/evaluation/audit_srr_batch5_loss_authority.py --config configs/srr_production/myops_batch6.yaml --result-root results/20260721_srr_batch6_final_objective_alignment --batch6-mode` | 0 | `loss_authority_audit.json`, optimizer_steps 0, parameter hash unchanged |
| `sbatch jobs/srr_production/run_myops_batch6_fixed_overfit_htzhulab.sh` | 0 | final passing job `59743323` |
| `sacct -j 59743323 --format=JobIDRaw,JobName,Partition,State,ExitCode,Elapsed,NodeList --parsable2` | 0 | COMPLETED, `0:0`, `00:00:27`, `g1807htzh01` |
| `./envs/env_CARE/bin/python scripts/training/run_srr_batch6_formal.py --config configs/srr_production/myops_batch6.yaml --stage 300 --attempt-label batch6_formal300_preflight_local --print-contract` | 0 | formal300 contract printed: 176 train, 44 val, eval 100/200/300 |
| `sbatch jobs/srr_production/run_myops_batch6_formal300_htzhulab.sh` | 0 | failed startup job `59743935`, then completed job `59744053` after same-scope JSON loss-weight parser fix |
| `sacct -j 59743935,59744053 --format=JobIDRaw,JobName,Partition,State,ExitCode,Elapsed,NodeList --parsable2` | 0 | `59743935 FAILED 1:0`; `59744053 COMPLETED 0:0` |
| `./envs/env_CARE/bin/python scripts/evaluation/aggregate_srr_batch6_formal.py --config configs/srr_production/myops_batch6.yaml --result-root results/20260721_srr_batch6_final_objective_alignment --stage 300 --attempt-label batch6_formal300_htzhulab_59744053 --job-id 59744053 --job-state COMPLETED --exit-code 0:0 --elapsed 00:09:06 --node g1807htzh01` | 0 | wrote `training_adequacy.json`, `checkpoint_selection.csv`, `subgroup_metrics.csv`, `help_harm.csv` |
| `sbatch jobs/srr_production/run_myops_batch6_final_interventions_htzhulab.sh` | 0 | failed startup job `59744540`, then completed job `59744941` after same-scope full_gate_zero control fix |
| `sacct -j 59744540,59744941 --format=JobIDRaw,JobName,Partition,State,ExitCode,Elapsed,NodeList --parsable2` | 0 | `59744540 FAILED 1:0`; `59744941 COMPLETED 0:0` |
| `./envs/env_CARE/bin/python scripts/evaluation/aggregate_srr_batch6_final_interventions.py --config configs/srr_production/myops_batch6.yaml --result-root results/20260721_srr_batch6_final_objective_alignment --job-id 59744941 --job-state COMPLETED --exit-code 0:0 --elapsed 00:10:48 --node g1807htzh01` | 0 | wrote `final_mechanism_interventions.csv` |

Pending final verification commands are recorded in `MANIFEST.md` and will be rerun after packet/wiki/validator repair.

## Final Controller Verification Commands

| Command | Exit code | Evidence |
| --- | ---: | --- |
| `./envs/env_CARE/bin/python scripts/srr_production/audit_formal_entrypoints.py --strict` | 0 | no formal entrypoints; status `BLOCKED_PENDING_PLANNER_AFTER_BATCH6_STOP_AT_300` |
| `./envs/env_CARE/bin/python scripts/evaluation/validate_srr_batch6_packet.py --result-root results/20260721_srr_batch6_final_objective_alignment` | 0 | `BATCH6_PACKET_VALIDATION_PASS`, 28 Slurm attempts, formal900 skipped |
| `./envs/env_CARE/bin/python -m pytest -q tests/srr_production/test_myops_batch6_objective_alignment.py tests/srr_production/test_myops_batch5_diagnostics.py tests/srr_production/test_myops_batch4_contract.py` | 0 | 30 passed, 3 warnings |
| `./envs/env_CARE/bin/python scripts/architecture/validate_care_architecture_wiki.py --strict` | 0 | care architecture wiki validation passed |
| `./envs/env_CARE/bin/python scripts/architecture/generate_care_architecture_wiki.py --check` | 0 | care architecture wiki diagrams ok |
| `git diff --check` | 0 | no whitespace errors |
