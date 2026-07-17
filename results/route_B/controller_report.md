# Route B Controller Adequacy Recovery Report

controller_run_status: FORMAL_ADEQUACY_RACE_SUBMITTED_NEEDS_MONITOR
operational_completion_status: ROUTE_B_NEEDS_MONITOR
experiment_adequacy_decision: NEEDS_MONITOR
git_commit_decision: LOCAL_MONITOR_PACKET_COMMIT_REQUIRED
git_push_decision: SKIP_PUSH
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW

## Summary

The controller is correcting the previous premature handoff. The earlier `500` step result was terminal but undertrained; it should not have been treated as ready for reviewer. This run uses `25000` steps so the training loop can meet the `1800` second adequacy threshold.

## Race Jobs

| job_id | partition | state | command |
| --- | --- | --- | --- |
| `59364846` | `htzhulab` | PENDING | `sbatch --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh` |
| `59364845` | `a100-gpu` | PENDING | `sbatch --partition=a100-gpu --gres=gpu:nvidia_a100-pcie-40gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh` |
| `59364847` | `volta-gpu` | PENDING | `sbatch --partition=volta-gpu --gres=gpu:tesla_v100-sxm2-16gb:1 --qos=gpu_access --export=ALL,ROUTE_B_STEPS=25000,ROUTE_B_RACE_LOCK_NAME=bounded_train_eval_25000_adequacy_winner.lock jobs/route_B/run_bounded_train_eval.sh` |

Watcher: `logs/route_B/controller_goal_monitor_adequacy_25000.log`.
