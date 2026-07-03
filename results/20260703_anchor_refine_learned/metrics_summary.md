# Metrics Summary

metrics_status: EVIDENCE_NOT_FOUND
decision: NEEDS_EVIDENCE

No learned anchor-refine predictions or metrics were generated in this executor pass.

## Gate Summary

| gate | decision | rationale |
| --- | --- | --- |
| experiment_adequacy_decision | EVIDENCE_NOT_FOUND | No learned training, overfit sanity, checkpoint, prediction sanity, or learned metric CSV exists. |
| route_promotion_decision | NOT_EVALUABLE | No learned fold0 same-split comparison exists. |
| route_negative_decision | NOT_EVALUABLE | A route-negative stop is forbidden without learned training adequacy and auditor support. |
| scientific_resolution_status | SCIENTIFIC_NEEDS_EVIDENCE | The route is neither promoted nor stopped; prerequisite evidence is missing. |

## Required Metric Evidence

| artifact | status |
| --- | --- |
| same-split nnU-Net baseline for learned comparison | evidence not found |
| learned refiner metric CSV | evidence not found |
| subgroup metrics | evidence not found |
| component/HD by case | evidence not found |
| teacher-student delta | evidence not found |
| prediction sanity | evidence not found |
| label/export QC for learned predictions | evidence not found |

The OOF component package contains diagnostic postprocess metrics, but its review explicitly does not authorize learned-refinement execution or route promotion.
