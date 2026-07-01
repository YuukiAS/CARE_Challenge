# Failure Interpretation

The previous keyframe-context attempt was evaluated without motion registration. This preflight tests whether a transparent reference-frame warp can improve anatomy-prior consistency before any scar/pathology claim.

Observed interpretation:

- simpleitk_translation.class_1_delta_mean=0.0001
- simpleitk_translation.class_2_delta_mean=0.0000
- simpleitk_translation.success_rate=1.0000
- simpleitk_translation.runtime_seconds_mean=0.82
- classical warp was stable but did not improve anatomy consistency enough.
- The motion descriptor remains useful, but the tested translation warp does not justify selecting a dense registration module yet.
- Non-reference frames were not scored directly against reference GT; all registration deltas use frame0 CineMA anatomy as the reference proxy.
