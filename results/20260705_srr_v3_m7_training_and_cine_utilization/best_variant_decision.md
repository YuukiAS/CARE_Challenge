# Best Variant Decision

status: `METRIC_TABLE_DECISION_EXECUTED_UNAUDITED`
route_promotion_decision: `NO_PROMOTION`

The executor does not promote a route. This file only applies the M7 metric-table rules to identify whether any row is worth reviewer attention.

| variant | checkpoint | decode | scar Dice delta | edema Dice delta | scar HD95 delta | edema HD95 delta | remote FP delta | decision |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| m7_scar_precision_edema_safe | checkpoint_final | pathology_aware | 0.006052879325744249 | 0.0 | -0.03748207362611389 | 0.0 | 0.041666666666666664 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_scar_precision_edema_safe | checkpoint_best | pathology_aware | 0.004824428206111696 | 0.0 | 0.10255812104356583 | 0.0 | 0.08333333333333333 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_full_srr_context_arbitration | checkpoint_final | pathology_aware | 0.004617755235648668 | 0.0 | -0.08099789436597497 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_conservative_component_arbitration | checkpoint_best | pathology_aware | 0.0007171918491678438 | 0.0 | -0.004463390701448485 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_full_srr_context_arbitration | checkpoint_best | pathology_aware | 0.00014070810814225768 | 0.0 | 0.08157774807352565 | 0.0 | 0.041666666666666664 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_conservative_component_arbitration | checkpoint_final | pathology_aware | 0.00013849858589320974 | 0.0 | 0.07838311738320762 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_full_srr_context_arbitration | checkpoint_final | argmax | 5.88991581358204e-05 | 0.0 | -0.00045684373735799255 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_scar_precision_edema_safe | checkpoint_final | argmax | 5.437605902387094e-05 | 0.0 | 0.0 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_scar_precision_edema_safe | checkpoint_best | argmax | 4.137061883682329e-06 | 0.0 | 0.0 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_full_srr_context_arbitration | checkpoint_best | argmax | -9.364925350636525e-06 | 0.0 | 0.0 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_conservative_component_arbitration | checkpoint_final | argmax | -1.025301096394445e-05 | 0.0 | 0.0 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |
| m7_conservative_component_arbitration | checkpoint_best | argmax | -1.5103343102271238e-05 | 0.0 | 0.0 | 0.0 | 0.0 | NO_PROMOTION_SCIENTIFIC_UNRESOLVED |

top_metric_row: `m7_scar_precision_edema_safe__checkpoint_final__pathology_aware`
top_metric_decision: `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`

A reviewer still must check per-case failures, no-T2 safety, label/export caveats, and Cine secondary evidence before any next milestone.
