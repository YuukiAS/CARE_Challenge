# Lane A Round10 Refiner Decision

Decision: `fail_stop_refiner_candidate`
Cascade variant: `coarse_to_fine_srr_roi`
Enforce scar unchanged: `False`

## Baseline vs Refiner By Subset

| subset | n | delta_edema_dice | delta_edema_hd95_improvement | delta_edema_component_count_improvement | delta_edema_remote_fp_improvement | delta_scar_dice | delta_scar_hd95_improvement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_case | 44 | 0.0026 | -0.0060 | -0.0227 | -0.0455 | 0.0034 | -0.4343 |
| t2_present_gt_positive | 16 | 0.0026 | -0.0164 | -0.0625 | -0.1250 | 0.0009 | -0.1258 |
| complete_modality | 16 | 0.0026 | -0.0164 | -0.0625 | -0.1250 | 0.0009 | -0.1258 |
| CenterB | 7 | 0.0080 | 0.0564 | 0.1429 | 0.0000 | 0.0013 | -0.3918 |
| CenterC | 9 | -0.0017 | -0.0731 | -0.2222 | -0.2222 | 0.0006 | 0.0811 |
| no_t2_empty_gt | 28 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0048 | -0.6241 |
| modality:C0+LGE+T2 | 16 | 0.0026 | -0.0164 | -0.0625 | -0.1250 | 0.0009 | -0.1258 |
| modality:C0+LGE | 4 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0094 | 0.2342 |
| modality:LGE-only | 24 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0040 | -0.7361 |

## Reasons

- Case2008: edema_component_worse
- Case3004: edema_component_worse
- Case3011: edema_remote_fp_worse
- Case3012: edema_component_worse
- Case3023: edema_component_worse
- Case3026: edema_component_worse
- Case3034: edema_dice_up_hd95_worse;edema_component_worse
- Case3040: edema_remote_fp_worse

No validation zip was created. No upload was performed. No fold1-4 refiner training was run.
