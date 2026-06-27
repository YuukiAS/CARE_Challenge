# Result 20260626 Lesion Compact

status: `REVISE_COMPACTNESS_AND_REPEAT`

## Summary

All four authorized lesion compact variants completed on `htzhulab` with `ExitCode=0:0`. The task did not produce a selectable compact package. L2 `component_compactness_loss` produced the only clean mechanism-level signal by improving HD95 relative to the selected D4 dictionary route, but it still failed the full selection gate because Dice, components, remote FP, no-T2 stability, and budget status were insufficient.

## Completed Jobs

| job | variant | state | elapsed | budget status |
| --- | --- | --- | ---: | --- |
| `56728800` | `soft_anatomy_containment` | `COMPLETED` | 5.53h | `UNDER_BUDGET_MAX_STEPS` |
| `56728801` | `component_compactness_loss` | `COMPLETED` | 5.65h | `UNDER_BUDGET_MAX_STEPS` |
| `56728802` | `scar_lge_fallback_boost` | `COMPLETED` | 5.55h | `UNDER_BUDGET_MAX_STEPS` |
| `56728799` | `edema_t2_center_balance` | `COMPLETED` | 5.35h | `UNDER_BUDGET_MAX_STEPS` |

## Key Evidence

- `results/20260626_lesion_compact/metrics_summary.md` contains the primary comparison table and subgroup/localization diagnostics.
- `results/20260626_lesion_compact/selection.md` records the final decision.
- `results/20260626_lesion_compact/failure_interpretation.md` explains each route failure mode.
- `results/20260626_lesion_compact/dictionary_usage.csv` and `.md` preserve dictionary/gate usage diagnostics.

## Guardrails

No validation upload, external upload, external data, external weights, fold expansion, label mapping change, evaluator change, or split change was performed.

Ignored artifacts include variant checkpoints and prediction NIfTI files under `results/20260626_lesion_compact/variants/*/{checkpoints,predictions}/`.
