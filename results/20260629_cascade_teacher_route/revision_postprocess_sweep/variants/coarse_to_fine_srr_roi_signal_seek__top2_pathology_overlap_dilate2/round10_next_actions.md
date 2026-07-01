# Lane A Round10 Refiner Decision

Decision: `fail_stop_refiner_candidate`
Cascade variant: `coarse_to_fine_srr_roi`
Enforce scar unchanged: `False`

## Baseline vs Refiner By Subset

| subset | n | delta_edema_dice | delta_edema_hd95_improvement | delta_edema_component_count_improvement | delta_edema_remote_fp_improvement | delta_scar_dice | delta_scar_hd95_improvement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_case | 44 | 0.0024 | 0.0112 | 0.1136 | -0.0227 | 0.0035 | -0.4766 |
| t2_present_gt_positive | 16 | 0.0024 | 0.0307 | 0.3125 | -0.0625 | 0.0009 | -0.1258 |
| complete_modality | 16 | 0.0024 | 0.0307 | 0.3125 | -0.0625 | 0.0009 | -0.1258 |
| CenterB | 7 | 0.0065 | -0.0207 | 0.7143 | 0.0000 | 0.0013 | -0.3918 |
| CenterC | 9 | -0.0007 | 0.0707 | 0.0000 | -0.1111 | 0.0006 | 0.0811 |
| no_t2_empty_gt | 28 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0050 | -0.6925 |
| modality:C0+LGE+T2 | 16 | 0.0024 | 0.0307 | 0.3125 | -0.0625 | 0.0009 | -0.1258 |
| modality:C0+LGE | 4 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0094 | 0.1714 |
| modality:LGE-only | 24 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0042 | -0.8051 |

## Reasons

- Case3004: edema_component_worse
- Case3012: edema_component_worse
- Case3023: edema_component_worse
- Case3026: edema_component_worse
- Case3040: edema_remote_fp_worse

No validation zip was created. No upload was performed. No fold1-4 refiner training was run.
