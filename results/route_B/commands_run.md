# Route B Commands Run Continuation

- `sacct -j 59317810 --format JobIDRaw,JobName%40,Partition,State,ExitCode,Elapsed,Start,End,NodeList -P`
- `sed -n '1,260p' logs/route_B/RouteBTrainEval_59317810_20260716_133719.log`
- `bash -n jobs/route_B/run_bounded_train_eval.sh`
- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python - <<'PY' ... import torch ... PY`
- `sbatch --test-only --export=ALL,ROUTE_B_STEPS=500 jobs/route_B/run_bounded_train_eval.sh`
- `sbatch --test-only --partition=a100-gpu --gres=gpu:nvidia_a100-pcie-40gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=500 jobs/route_B/run_bounded_train_eval.sh`
- `sbatch --test-only --partition=volta-gpu --gres=gpu:tesla_v100-sxm2-16gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=500 jobs/route_B/run_bounded_train_eval.sh`
- `sbatch --partition=volta-gpu --gres=gpu:tesla_v100-sxm2-16gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=500 jobs/route_B/run_bounded_train_eval.sh`
- `squeue -j 59363006 -o '%i|%j|%P|%T|%M|%R|%b|%C|%m'`
- `scontrol show job 59363006`

Current formal replacement job state: `PENDING` on `volta-gpu` for `Priority`.

Post-completion aggregation has not run. The required future aggregation command is the Slurm wrapper command `python scripts/training/route_B/run_bounded_train_eval.py --steps 500 --myops-eval-cases 10 --cine-eval-cases 5`, which writes the lightweight evidence after the training loop completes.

No validation upload, push, M11, cross-route merge, or review command was run.

Controller goal monitor: `logs/route_B/controller_goal_monitor_59363006.log`.
