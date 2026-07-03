# Failure Interpretation

route_decision: `TEMPORAL_PROXY_SIGNAL_DIAGNOSTIC`
experiment_adequacy_decision: `PARTIAL`
route_promotion_decision: `NO_PROMOTION`
route_negative_decision: `STOP_NOT_SUPPORTED`
scientific_resolution_status: `SCIENTIFIC_UNRESOLVED`

Interpretation:

- Reference-control myocardium Dice: `0.5626`; LV Dice: `0.7709`.
- Optical-flow/feature-warp delta: myocardium `0.0406`, LV `0.0454`.
- Motion-descriptor temporal-refiner delta: myocardium `-0.0002`, LV `-0.0001`.
- Translation-only evidence from prior Cine registration was not used as a final hardmode conclusion; this run attempted a harder dense optical-flow/feature-warp proxy plus a descriptor temporal refiner.
- Dense optical flow is reported as a proxy with warp sanity, not a validated diffeomorphic registration method.
- Descriptor aggregation is reported as descriptor evidence, not completed registration.
- Hosted challenge metric, raw-label validation export, and upload-package evidence are `evidence not found` by task constraint.
- If audited, any continuation should be treated as a new planner/controller decision because this package is local proxy evidence only.
