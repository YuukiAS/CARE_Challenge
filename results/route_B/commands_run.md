# Route B Commands Run Continuation

- `python scripts/route_B/run_implementation_gate.py --strict`
- `python scripts/training/route_B/run_bounded_train_eval.py --steps 500 --myops-eval-cases 10 --cine-eval-cases 5`
- `python scripts/validation/route_B/validate_route_b_implementation.py --strict --write-report results/route_B/validator_implementation_report.json`
- `python scripts/validation/route_B/validate_route_b_packet.py --strict --write-report results/route_B/validator_packet_report.json`
- `pytest -q tests/route_B src/care_myocardium/tests/test_route_b_implementation.py`
- `git diff --check`

No validation upload, push, M11, or review command was run.
## Three-Way Race Recovery (2026-07-17T02:13:09Z)

- `bash -n jobs/route_B/run_bounded_train_eval.sh`
- `sbatch --test-only --export=ALL,ROUTE_B_STEPS=500 jobs/route_B/run_bounded_train_eval.sh`
- `sbatch --test-only --partition=a100-gpu --gres=gpu:nvidia_a100-pcie-40gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=500 jobs/route_B/run_bounded_train_eval.sh`
- `sbatch --test-only --partition=volta-gpu --gres=gpu:tesla_v100-sxm2-16gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=500 jobs/route_B/run_bounded_train_eval.sh`
- `scancel 59363006`
- `sbatch --export=ALL,ROUTE_B_STEPS=500 jobs/route_B/run_bounded_train_eval.sh` -> `59363146` (`htzhulab`)
- `sbatch --partition=volta-gpu --gres=gpu:tesla_v100-sxm2-16gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=500 jobs/route_B/run_bounded_train_eval.sh` -> `59363147` (`volta-gpu`)
- `sbatch --partition=a100-gpu --gres=gpu:nvidia_a100-pcie-40gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=500 jobs/route_B/run_bounded_train_eval.sh` -> `59363148` (`a100-gpu`)
- `scancel 59363147 59363148` after `59363146` started running
- `sacct -j 59363006,59363146,59363147,59363148 --format JobIDRaw,JobName%30,Partition,State,ExitCode,Elapsed,Start,End,NodeList -P`

Current formal winner job state: `RUNNING` on `htzhulab` as `59363146`. Post-completion aggregation has not run.

## Terminal Aggregation Recovery (2026-07-17T02:16:43Z)

- `sacct -j 59363146 --format JobIDRaw,JobName%30,Partition,State,ExitCode,Elapsed,Start,End,NodeList -P` -> `COMPLETED`, `ExitCode=0:0`, elapsed `00:02:37`.
- Restored post-completion lightweight evidence from `results/route_B/runtime/bounded_train_eval/route_b_undertrained_state.pt` and `logs/route_B/RouteBTrainEval_59363146_20260716_221019.log` without retraining.
- Updated `bounded_train_eval_summary.json`, `training_adequacy.csv`, `metrics_summary.csv`, and `case_safety_matrix.csv`.

Current formal result: `ROUTE_B_SCIENTIFIC_UNDERTRAINED`, ready for read-only reviewer judgment.

## Adequacy Recovery Submission (2026-07-17T02:36:47Z)

- `bash -n jobs/route_B/run_bounded_train_eval.sh`
- `python -m py_compile scripts/training/route_B/run_bounded_train_eval.py`
- `sbatch --test-only --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh`
- `sbatch --test-only --partition=a100-gpu --gres=gpu:nvidia_a100-pcie-40gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh`
- `sbatch --test-only --partition=volta-gpu --gres=gpu:tesla_v100-sxm2-16gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh`
- `sbatch --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh` -> `59364846`
- `sbatch --partition=a100-gpu --gres=gpu:nvidia_a100-pcie-40gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh` -> `59364845`
- `sbatch --partition=volta-gpu --gres=gpu:tesla_v100-sxm2-16gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh` -> `59364847`

## Adequacy Recovery Runtime Update (2026-07-17T02:44:37Z)

- `squeue -j 59364846 -o '%i|%T|%M|%l|%R|%P'` -> `RUNNING` on `htzhulab`.
- `sacct -j 59364845,59364846,59364847 --format JobIDRaw,JobName%30,Partition,State,ExitCode,Elapsed,Start,End,NodeList -P` -> winner `59364846` running; losers `59364845`, `59364847` cancelled.
- RouteB-Continue tmux watcher is active: `logs/route_B/controller_goal_monitor_adequacy_25000.log`.
