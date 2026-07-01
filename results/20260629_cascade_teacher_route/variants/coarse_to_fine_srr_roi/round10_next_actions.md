# Lane A Round10 Refiner Decision

Decision: `fail_stop_refiner_candidate`
Cascade variant: `coarse_to_fine_srr_roi`
Enforce scar unchanged: `False`

## Baseline vs Refiner By Subset

| subset | n | delta_edema_dice | delta_edema_hd95_improvement | delta_edema_component_count_improvement | delta_edema_remote_fp_improvement | delta_scar_dice | delta_scar_hd95_improvement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_case | 44 | 0.0019 | -0.0228 | -0.3409 | -0.0227 | 0.0028 | -0.4037 |
| t2_present_gt_positive | 16 | 0.0019 | -0.0626 | -0.9375 | -0.0625 | 0.0007 | -0.1174 |
| complete_modality | 16 | 0.0019 | -0.0626 | -0.9375 | -0.0625 | 0.0007 | -0.1174 |
| CenterB | 7 | 0.0051 | 0.1092 | -0.1429 | 0.0000 | 0.0001 | -0.3510 |
| CenterC | 9 | -0.0006 | -0.1962 | -1.5556 | -0.1111 | 0.0011 | 0.0644 |
| no_t2_empty_gt | 28 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0040 | -0.5799 |
| modality:C0+LGE+T2 | 16 | 0.0019 | -0.0626 | -0.9375 | -0.0625 | 0.0007 | -0.1174 |
| modality:C0+LGE | 4 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0076 | 0.2076 |
| modality:LGE-only | 24 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0035 | -0.6826 |

## Reasons

- Case2008: edema_component_worse
- Case2017: edema_component_worse
- Case2033: edema_component_worse
- Case3004: edema_component_worse
- Case3012: edema_component_worse
- Case3034: edema_component_worse;edema_remote_fp_worse
- Case3038: edema_component_worse

No validation zip was created. No upload was performed. No fold1-4 refiner training was run.
