# CineMyoPS Registration Selection

status: `SELECT_MOTION_DESCRIPTOR_ONLY`

## Reasons

- simpleitk_translation.class_1_delta_mean=0.0001
- simpleitk_translation.class_2_delta_mean=0.0000
- simpleitk_translation.success_rate=1.0000
- simpleitk_translation.runtime_seconds_mean=0.61
- classical warp was stable but did not improve anatomy consistency enough.

## Scope

- safe cases evaluated: `59`
- mismatch cases held out: `5`
- Decision uses anatomy consistency against frame0 CineMA anatomy proxy, image similarity, runtime, and warp sanity.
- This is not a scar/pathology success claim.
