# Route B Controller Adequacy Recovery

Final controller token: `ROUTE_B_NEEDS_MONITOR`

The prior terminal packet `ROUTE_B_SCIENTIFIC_UNDERTRAINED` is not an acceptable handoff endpoint because the 500-step run completed only `43.331` train-loop seconds against the required `1800` seconds. The controller is continuing under a goal.

A sufficient bounded train/eval race was submitted with `ROUTE_B_STEPS=25000`, estimated from the previous runtime to exceed the 1800-second adequacy threshold. The race lock is `results/route_B/locks/bounded_train_eval_25000_adequacy_winner.lock`.

`59364846` on `htzhulab` started first, obtained the lock, and is still running on `g180702`. The A100 and Volta race losers were cancelled after the winner started.

| job_id | partition | role | state | note |
| --- | --- | --- | --- | --- |
| `59364846` | `htzhulab` | adequacy_race_winner_running | RUNNING | race winner obtained lock and is still training |
| `59364845` | `a100-gpu` | adequacy_race_loser_cancelled | CANCELLED by 397557 | cancelled after htzhulab winner started |
| `59364847` | `volta-gpu` | adequacy_race_loser_cancelled | CANCELLED by 397557 | cancelled after htzhulab winner started |

This packet is not review-ready. The controller must wait for terminal accounting, collect post-completion evidence, run validators, and only then publish the final packet.
