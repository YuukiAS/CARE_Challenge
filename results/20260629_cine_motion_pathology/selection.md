# Cine Motion Pathology Selection

status: `SELECT_REFERENCE_CONTROL_ONLY`

## Reasons

- `keyframe_context_retrieval` did not improve over `reference_control_safe`: class_1 myocardium delta `-0.0003`, class_2 LV delta approximately `0.0000`.
- `anatomy_consistency_temporal` degraded both local proxies: class_1 myocardium delta `-0.0964`, class_2 LV delta `-0.0753`.
- class_3 scar sanity remained `0.0000` for all variants because the frozen CineMA anatomy source has no scar head.
- This is a local safe-subset proxy result, not hosted `myocardium_cinemyops`.

## Decision

Do not select the current keyframe/context motion route for formal CineMyoPS pathology training. Keep frame0/reference control as the current local Cine baseline until a stronger first-party motion descriptor or aligned pathology head is available.
