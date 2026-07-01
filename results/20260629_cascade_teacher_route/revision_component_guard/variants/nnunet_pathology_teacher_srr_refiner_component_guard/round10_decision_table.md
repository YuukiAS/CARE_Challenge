# Lane A Round10 Refiner Decision

Decision: `watch_stop_no_clear_positive_signal`
Cascade variant: `nnunet_pathology_teacher_srr_refiner`
Enforce scar unchanged: `False`

## Baseline vs Refiner By Subset

| subset | n | delta_edema_dice | delta_edema_hd95_improvement | delta_edema_component_count_improvement | delta_edema_remote_fp_improvement | delta_scar_dice | delta_scar_hd95_improvement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_case | 44 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| t2_present_gt_positive | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| complete_modality | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| CenterB | 7 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| CenterC | 9 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| no_t2_empty_gt | 28 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| modality:C0+LGE+T2 | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| modality:C0+LGE | 4 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| modality:LGE-only | 24 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## Reasons

- no clean positive edema/scar signal for nnunet_pathology_teacher_srr_refiner

No validation zip was created. No upload was performed. No fold1-4 refiner training was run.
