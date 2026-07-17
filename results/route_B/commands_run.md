# Route B Commands Run Continuation

- `python scripts/route_B/run_implementation_gate.py --strict`
- `python scripts/training/route_B/run_bounded_train_eval.py --steps 25000 --myops-eval-cases 10 --cine-eval-cases 5`
- `python scripts/validation/route_B/validate_route_b_implementation.py --strict --write-report results/route_B/validator_implementation_report.json`
- `python scripts/validation/route_B/validate_route_b_packet.py --strict --write-report results/route_B/validator_packet_report.json`
- `pytest -q tests/route_B src/care_myocardium/tests/test_route_b_implementation.py`
- `git diff --check`

No validation upload, push, M11, or review command was run.

## Adequacy Recovery Race

- `bash -n jobs/route_B/run_bounded_train_eval.sh`
- `python -m py_compile scripts/training/route_B/run_bounded_train_eval.py`
- `sbatch --test-only --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh`
- `sbatch --test-only --partition=a100-gpu --gres=gpu:nvidia_a100-pcie-40gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh`
- `sbatch --test-only --partition=volta-gpu --gres=gpu:tesla_v100-sxm2-16gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh`
- `sbatch --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh` -> `59364846` (`htzhulab`)
- `sbatch --partition=a100-gpu --gres=gpu:nvidia_a100-pcie-40gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh` -> `59364845` (`a100-gpu`)
- `sbatch --partition=volta-gpu --gres=gpu:tesla_v100-sxm2-16gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh` -> `59364847` (`volta-gpu`)
- `scancel 59364845 59364847` after `59364846` started running and obtained the lock.
- `sacct -j 59364845,59364846,59364847 --format JobIDRaw,JobName%30,Partition,State,ExitCode,Elapsed,Start,End,NodeList -P` -> winner `59364846` `COMPLETED`, `ExitCode=0:0`, elapsed `00:32:02`; losers cancelled.

## Terminal Aggregation and Validation

- Winner log: `logs/route_B/RouteBTrainEval_59364846_20260716_223551.log`
- Watcher log: `logs/route_B/controller_goal_monitor_adequacy_25000.log`
- Aggregation outputs: `bounded_train_eval_summary.json`, `training_adequacy.csv`, `metrics_summary.csv`, `case_safety_matrix.csv`, `completion_check.md`, `controller_report.md`, `result.md`, `review_request.md`.
- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B/validate_route_b_packet.py --strict --write-report results/route_B/validator_packet_report.json` -> `PASS`
- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B/validate_route_b_implementation.py --strict --write-report results/route_B/validator_implementation_report.json` -> `PASS`
