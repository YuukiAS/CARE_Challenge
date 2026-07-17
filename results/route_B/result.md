# Route B Controller Adequacy Recovery

Final controller token: `ROUTE_B_NEEDS_MONITOR`

The prior terminal packet `ROUTE_B_SCIENTIFIC_UNDERTRAINED` is not an acceptable handoff endpoint because the 500-step run completed only `43.331` train-loop seconds against the required `1800` seconds. The controller is continuing under a goal.

A sufficient bounded train/eval race has been submitted with `ROUTE_B_STEPS=25000`, estimated from the previous runtime to exceed the 1800-second adequacy threshold. The race lock is `results/route_B/locks/bounded_train_eval_25000_adequacy_winner.lock`.

Race jobs:

| job_id | partition | state |
| --- | --- | --- |
| `59364846` | `htzhulab` | PENDING |
| `59364845` | `a100-gpu` | PENDING |
| `59364847` | `volta-gpu` | PENDING |

This packet is not review-ready. The controller must wait for a winner, cancel pending losers, collect terminal accounting, and only then publish the final packet.
