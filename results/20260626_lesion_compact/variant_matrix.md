# Lesion Compact Variant Matrix

| variant | job | mechanism | dictionary mode | elapsed h | budget | primary readout |
| --- | --- | --- | --- | ---: | --- | --- |
| `soft_anatomy_containment` | `56728800` | soft outside-union lesion probability penalty | `cross_modal_interaction_dictionary` | 5.53 | `UNDER_BUDGET_MAX_STEPS` | small Dice gain, but FP/component burden worsened |
| `component_compactness_loss` | `56728801` | 3D probability total-variation compactness proxy | `cross_modal_interaction_dictionary` | 5.65 | `UNDER_BUDGET_MAX_STEPS` | HD95 improved, but Dice and FP burden insufficient |
| `scar_lge_fallback_boost` | `56728802` | scar-positive/LGE-only sampling plus scar weight/router tuning | `cross_modal_interaction_dictionary` | 5.55 | `UNDER_BUDGET_MAX_STEPS` | scar route did not improve; edema degraded |
| `edema_t2_center_balance` | `56728799` | T2-positive and CenterC edema sampling plus edema weight/router tuning | `cross_modal_interaction_dictionary` | 5.35 | `UNDER_BUDGET_MAX_STEPS` | edema collapsed on GT-positive cases |
