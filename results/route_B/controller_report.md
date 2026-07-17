# Route B Controller Adequacy Recovery Report

controller_run_status: FORMAL_ADEQUACY_RACE_WINNER_RUNNING_NEEDS_MONITOR
operational_completion_status: ROUTE_B_NEEDS_MONITOR
experiment_adequacy_decision: NEEDS_MONITOR
git_commit_decision: LOCAL_MONITOR_PACKET_COMMIT_REQUIRED
git_push_decision: SKIP_PUSH
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW

## Summary

The controller is correcting the previous premature handoff. The earlier `500` step result was terminal but undertrained; it should not have been treated as ready for reviewer. This run uses `25000` steps so the training loop can meet the `1800` second adequacy threshold.

The `htzhulab` leg `59364846` won the race and is running on `g180702`. Pending A100 and Volta losers were cancelled.

## Race Jobs

| job_id | partition | role | state | note |
| --- | --- | --- | --- | --- |
| `59364846` | `htzhulab` | adequacy_race_winner_running | RUNNING | race winner obtained lock and is still training |
| `59364845` | `a100-gpu` | adequacy_race_loser_cancelled | CANCELLED by 397557 | cancelled after htzhulab winner started |
| `59364847` | `volta-gpu` | adequacy_race_loser_cancelled | CANCELLED by 397557 | cancelled after htzhulab winner started |

Watcher: `logs/route_B/controller_goal_monitor_adequacy_25000.log`.
Training log: `logs/route_B/RouteBTrainEval_59364846_20260716_223551.log`.
