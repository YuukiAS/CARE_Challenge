# Label Export QC

controlled_state: EXECUTED_UNAUDITED

## Compact Label Contract

- evaluator label space: compact Dataset501 labels.
- compact labels: `0=background`, `1=myocardium`, `2=LV_blood`, `3=RV_blood`, `4=myops_edema`, `5=myops_scar`.
- raw-to-compact mapping source: `code/nnUNet/nnunet_label_utils.py`.
- compact-to-raw validation packaging: not executed.
- hosted validation/export evidence: evidence not found; upload/package generation is forbidden here.

## Fold0 Prediction Label Sets

| variant | prediction_count | compact_label_values |
| --- | ---: | --- |
| `baseline_nnunet501_fold0` | 44 | `0,1,2,3,4,5` |
| `oof_scar_component_score` | 44 | `0,1,2,3,4,5` |

## QC Decision

- invalid compact labels outside `0..5`: none detected.
- challenge-facing caveat: compact fold0 metrics are not hosted validation evidence.
