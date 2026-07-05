# MANIFEST: 20260704 SRR-v2.5 Local Refinement Ablation

task: `prompts/tasks/20260704_srr_v25_local_refinement_ablation.md`
result: `results/20260704_srr_v25_local_refinement_ablation/result.md`
review: `results/20260704_srr_v25_local_refinement_ablation/review.md` (not created)

## Artifacts

| path | purpose |
| --- | --- |
| `result.md` | Executor summary and gate decision. |
| `roi_contract.md` | Scar/edema local ROI policy and bounded crop contract. |
| `bounds_stats.csv` | One-case runtime crop bounds, volume ratios, and no-T2 block code. |
| `local_loss.md` | ROI/local loss terms and smoke training evidence. |
| `ablation.csv` | Required input ablation matrix; only decode smoke row observed, input ablations not run. |
| `component_metrics.csv` | One-case component/Dice/HD95/remote-FP metrics. |
| `hard_subgroup_effect.md` | Smoke subgroup effect and missing hard-subgroup evidence. |
| `runtime_smoke/` | Raw one-step CPU smoke outputs from the formal runner. |

## Status

`EXECUTED_UNAUDITED`; bounded crop evidence exists, but formal input ablations,
hard subgroup metrics, and read-only audit are missing.
