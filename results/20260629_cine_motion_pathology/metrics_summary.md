# CineMyoPS Temporal Preflight Metrics

## Setup

- safe subset: `results/20260625_cine_geometry/safe_cases.csv`
- source predictions: existing CineMA frame0/mid/representative predictions from `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/`
- C0 `reference_control_safe`: frame0 anatomy prediction only.
- C1 `keyframe_context_retrieval`: frame agreement softmax over frame0/mid/representative predictions, fused at reference geometry.
- C2 `anatomy_consistency_temporal`: majority-style temporal consistency fusion; no nonreference frame is directly scored against GT.

## Metrics

| variant | metric | n | Dice | HD95 | components | empty rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| anatomy_consistency_temporal | class_1_myocardium | 59 | 0.4662 | 12.0677 | 2.7797 | 0.0000 |
| anatomy_consistency_temporal | class_2_lv | 59 | 0.6955 | 11.8560 | 1.0339 | 0.0169 |
| anatomy_consistency_temporal | class_3_scar_sanity | 59 | 0.0000 | NA | 0.0000 | 1.0000 |
| keyframe_context_retrieval | class_1_myocardium | 59 | 0.5623 | 11.3331 | 1.4746 | 0.0000 |
| keyframe_context_retrieval | class_2_lv | 59 | 0.7709 | 11.0393 | 1.0847 | 0.0169 |
| keyframe_context_retrieval | class_3_scar_sanity | 59 | 0.0000 | NA | 0.0000 | 1.0000 |
| reference_control_safe | class_1_myocardium | 59 | 0.5626 | 11.3331 | 1.4746 | 0.0000 |
| reference_control_safe | class_2_lv | 59 | 0.7709 | 11.0440 | 1.0847 | 0.0169 |
| reference_control_safe | class_3_scar_sanity | 59 | 0.0000 | NA | 0.0000 | 1.0000 |

## Temporal Diagnostics

- safe cases evaluated: `59`
- mismatch cases kept out of evaluation: `5`
- mean reference weight in C1: `0.7520`
- mean temporal entropy in C1: `0.6517`
- class_3 remains a negative control because CineMA anatomy predictions have no scar head.
