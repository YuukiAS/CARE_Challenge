# Result 20260626 Cine Temporal

status: `KEEP_REFERENCE_CONTROL`

## Summary

This task ran an anatomy-first temporal preflight on the 59 strict-safe CineMyoPS cases from `results/20260625_cine_geometry/safe_cases.csv`. The 5 metadata mismatch cases were kept out of evaluation as required.

The temporal variants did not improve the local reference-frame proxies over the frame0 control:

| variant | class_1 myocardium Dice | class_2 LV Dice | note |
| --- | ---: | ---: | --- |
| `reference_control_safe` | 0.5626 | 0.7709 | frame0/reference control |
| `keyframe_context_retrieval` | 0.5623 | 0.7709 | no positive signal vs control |
| `anatomy_consistency_temporal` | 0.4662 | 0.6955 | degraded both proxies |

`class_3_scar_sanity` remains 0 for all variants because the frozen CineMA anatomy source has no scar head; it was not used as the sole failure reason.

## Implementation

- Added `scripts/evaluation/cinemyops_temporal_preflight.py`.
- Reused existing CineMA adapter frame0/mid/representative predictions from `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/`.
- Evaluated C0 `reference_control_safe`, C1 `keyframe_context_retrieval`, and C2 `anatomy_consistency_temporal` in reference geometry.
- Did not score nonreference frames directly against reference GT.
- Did not write prediction NIfTI files or overwrite existing CineMA/nnU-Net/CineMyoPS outputs.

## Evidence

- Metrics summary: `results/20260626_cine_temporal/metrics_summary.md`
- Per-case metrics: `results/20260626_cine_temporal/case_metrics.csv`
- Frame retrieval diagnostics: `results/20260626_cine_temporal/frame_retrieval.csv`
- Decision: `results/20260626_cine_temporal/decision.md`
- Failure interpretation: `results/20260626_cine_temporal/failure_interpretation.md`

## Decision

`KEEP_REFERENCE_CONTROL`

The current temporal retrieval route is not a candidate for fold expansion or hosted submission. The anatomy-first route is still useful as a geometry-safe reference control, but the next Cine decision should be whether to repair keyframe/motion descriptors, repair mismatch cases, or introduce a scar-specific Cine head in a separately authorized task.
