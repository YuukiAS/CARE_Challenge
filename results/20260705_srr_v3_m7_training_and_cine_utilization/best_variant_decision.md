# Best Variant Decision

status: `M7_CONTINUED_METRIC_TABLE_DECISION_EXECUTED_UNAUDITED`
route_promotion_decision: `NO_PROMOTION`

M7 continued uses only `split_role=formal_val` and `eligible_for_best_variant_decision=true` rows from `same_split_help_harm.csv` for this table. No diagnostic train hardcase rows are mixed into formal ranking.

| variant | checkpoint | decode | formal cases | scar Dice delta | edema Dice delta | remote FP delta | decision |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| m7_full_srr_context_arbitration | checkpoint_final | pathology_aware | 8 | 0.0012990051121230181 | -8.052764782574828e-05 | -0.0625 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_scar_precision_edema_safe | checkpoint_best | pathology_aware | 8 | 0.0009438738890054574 | 0.0010844496947527774 | 0.1875 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_full_srr_context_arbitration | checkpoint_best | pathology_aware | 8 | 0.0004661627077832721 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_full_srr_context_arbitration | checkpoint_final | argmax | 8 | 2.1489826655313182e-05 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_scar_precision_edema_safe | checkpoint_best | argmax | 8 | -3.7268422414700464e-06 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_scar_precision_edema_safe | checkpoint_final | argmax | 8 | -3.7268422414700464e-06 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_conservative_component_arbitration | checkpoint_best | pathology_aware | 8 | -8.15128395862362e-05 | 5.2158676828603645e-05 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_conservative_component_arbitration | checkpoint_final | pathology_aware | 8 | -0.0003002201168735563 | -2.3496527956121116e-05 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_scar_precision_edema_safe | checkpoint_final | pathology_aware | 8 | -0.0028249474346803034 | 3.19636177733007e-05 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_conservative_component_arbitration | checkpoint_best | argmax | 8 | 0.0 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_conservative_component_arbitration | checkpoint_final | argmax | 8 | 0.0 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_full_srr_context_arbitration | checkpoint_best | argmax | 8 | 0.0 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
