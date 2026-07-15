# Registration Math Contract

Status: `PASS`

The follow-up registration contract requires B,T,1,H,W,D input, ED reference, ES by selected-checkpoint LV volume, a [16,32,64,128] stationary-velocity U-Net, seven-step scaling-and-squaring, both transform directions, explicit unit conversion, true Jacobian/inverse-consistency metrics, and the exact LNCC/Dice/smoothness/Jacobian/cycle objective.

```json
{
  "es_selection_rule": "minimum_selected_checkpoint_lv_volume",
  "input_layout": "B,T,1,H,W,D",
  "input_rank": 6,
  "integration_method": "scaling_and_squaring",
  "objective_terms": {
    "grad_v": 0.05,
    "inverse_consistency": 0.1,
    "lncc_9x9x9": 1.0,
    "multiclass_dice": 1.0,
    "negative_jacobian": 0.1
  },
  "predicts_both_directions": true,
  "reference_frame": "ED",
  "scaling_and_squaring_steps": 7,
  "selected_frame_count": 8,
  "unet_channels": [
    16,
    32,
    64,
    128
  ],
  "unit_conversion": "normalized_grid_to_voxel_and_physical_mm",
  "uses_direct_velocity_as_displacement": false,
  "velocity_model": "stationary_velocity_field"
}
```
