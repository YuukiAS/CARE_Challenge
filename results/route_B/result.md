# Route B Controller Result Continuation

Final controller token: `ROUTE_B_NEEDS_MONITOR`

The first formal Slurm attempt `59317810` reached terminal accounting but failed before training started: `FAILED`, `ExitCode=1:0`, elapsed `00:00:04`. Its log records `ModuleNotFoundError: No module named 'torch'` because the wrapper used bare `/usr/bin/python`. This attempt receives zero optimizer-step and train-loop credit.

The Slurm wrapper has been repaired to use `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python` and to print Python/torch/CUDA provenance at startup. A same-scope replacement job `59363006` was submitted with `ROUTE_B_STEPS=500` on `volta-gpu` because current test-only routing estimates put Volta earlier than htzhulab and A100. The replacement is currently non-terminal, so no post-completion aggregation has run.

This packet is not review-ready. The controller must monitor replacement job `59363006`, then rerun/collect post-completion lightweight evidence after the job reaches a terminal state.

Controller goal monitor: `logs/route_B/controller_goal_monitor_59363006.log`.
