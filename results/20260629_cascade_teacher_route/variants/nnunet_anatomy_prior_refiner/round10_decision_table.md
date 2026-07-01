# Lane A Round10 Refiner Decision

Decision: `fail_stop_refiner_candidate`
Cascade variant: `nnunet_anatomy_prior_refiner`
Enforce scar unchanged: `True`

## Baseline vs Refiner By Subset

| subset | n | delta_edema_dice | delta_edema_hd95_improvement | delta_edema_component_count_improvement | delta_edema_remote_fp_improvement | delta_scar_dice | delta_scar_hd95_improvement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_case | 44 | 0.0014 | -0.0100 | -0.0227 | 0.0227 | 0.0000 | 0.0000 |
| t2_present_gt_positive | 16 | 0.0014 | -0.0276 | -0.0625 | 0.0625 | 0.0000 | 0.0000 |
| complete_modality | 16 | 0.0014 | -0.0276 | -0.0625 | 0.0625 | 0.0000 | 0.0000 |
| CenterB | 7 | 0.0032 | 0.1161 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| CenterC | 9 | 0.0001 | -0.1394 | -0.1111 | 0.1111 | 0.0000 | 0.0000 |
| no_t2_empty_gt | 28 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| modality:C0+LGE+T2 | 16 | 0.0014 | -0.0276 | -0.0625 | 0.0625 | 0.0000 | 0.0000 |
| modality:C0+LGE | 4 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| modality:LGE-only | 24 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## Reasons

- Case2031: edema_component_worse
- Case3011: edema_component_worse
- Case3012: edema_component_worse
- Case3044: edema_component_worse

No validation zip was created. No upload was performed. No fold1-4 refiner training was run.
