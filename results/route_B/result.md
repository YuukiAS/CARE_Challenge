# Route B Controller Result Continuation

Final controller token: `ROUTE_B_SCIENTIFIC_UNDERTRAINED`

Route B did run to a terminal post-completion packet. The first formal attempt `59317810` failed before training because the wrapper used bare `/usr/bin/python` without `torch`; this has zero training credit. The unlocked Volta replacement `59363006` was cancelled before start. A locked three-way race then submitted `59363146` (`htzhulab`), `59363147` (`volta-gpu`), and `59363148` (`a100-gpu`). `59363146` started first on `htzhulab`, obtained `results/route_B/locks/bounded_train_eval_winner.lock`, and the two pending losers were cancelled.

Winner job `59363146` completed successfully: `COMPLETED`, `ExitCode=0:0`, elapsed `00:02:37`, node `g180702`. Startup provenance confirms the repaired environment: `python_executable=/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`, `torch_version=2.11.0+cu130`, `cuda_available=True`.

The bounded train/eval completed `500` optimizer steps. Loss decreased from `2.432160` to `0.076860` over `43.331` seconds, with `2` validation events. The result remains scientifically undertrained because train-loop seconds did not meet the minimum adequacy threshold. This packet is now ready for read-only reviewer judgment, not route promotion.

## Metrics

| task | metric | value | cases | status |
| --- | --- | --- | --- | --- |
| MyoPS | `myops_scar_compact5_dice` | 0.3333333333333333 | 10 | UNDERTRAINED |
| MyoPS | `myops_edema_compact4_dice` | 0.0 | 10 | UNDERTRAINED |
| CineMyoPS | `class_1_myocardium_proxy_dice` | 0.7623529411764706 | 5 | UNDERTRAINED |
| CineMyoPS | `class_3_scar_sanity_dice` | 0.6 | 5 | UNDERTRAINED |

Tracked evidence: `results/route_B/bounded_train_eval_summary.json`, `results/route_B/training_adequacy.csv`, `results/route_B/metrics_summary.csv`, `results/route_B/case_safety_matrix.csv`, `logs/route_B/RouteBTrainEval_59363146_20260716_221019.log`.
