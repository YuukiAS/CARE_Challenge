# Temporal Dictionary Contract

Status: `PASS`

Temporal execution is gated on a passed, reloaded registration checkpoint and exactly eight evidence slots. Fewer than four valid non-reference frames is a registration failure.

```json
{
  "includes_jacobian": true,
  "includes_residual": true,
  "includes_uncertainty": true,
  "includes_velocity": true,
  "registration_checkpoint_reloaded": true,
  "registration_gate_passed": true,
  "slot_names": [
    "ed_anatomy_anchor",
    "early_systolic_contraction",
    "late_systolic_contraction",
    "early_diastolic_relaxation",
    "late_diastolic_relaxation",
    "motion_magnitude",
    "registered_texture_residual",
    "registration_uncertainty_safety"
  ],
  "valid_non_reference_frames": 4,
  "writes_temporal_output_without_registration": false
}
```
