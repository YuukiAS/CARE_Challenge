# Lane A Round10 Refiner Decision

Decision: `fail_stop_refiner_candidate`
Cascade variant: `nnunet_pathology_teacher_srr_refiner`
Enforce scar unchanged: `False`

## Baseline vs Refiner By Subset

| subset | n | delta_edema_dice | delta_edema_hd95_improvement | delta_edema_component_count_improvement | delta_edema_remote_fp_improvement | delta_scar_dice | delta_scar_hd95_improvement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_case | 44 | 0.0010 | -0.0249 | 0.2727 | -0.0227 | 0.0020 | -0.4196 |
| t2_present_gt_positive | 16 | 0.0010 | -0.0686 | 0.7500 | -0.0625 | 0.0005 | -0.0324 |
| complete_modality | 16 | 0.0010 | -0.0686 | 0.7500 | -0.0625 | 0.0005 | -0.0324 |
| CenterB | 7 | 0.0045 | 0.0579 | 0.8571 | 0.0000 | 0.0005 | -0.1157 |
| CenterC | 9 | -0.0018 | -0.1670 | 0.6667 | -0.1111 | 0.0005 | 0.0324 |
| no_t2_empty_gt | 28 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0029 | -0.6578 |
| modality:C0+LGE+T2 | 16 | 0.0010 | -0.0686 | 0.7500 | -0.0625 | 0.0005 | -0.0324 |
| modality:C0+LGE | 4 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0053 | 0.0723 |
| modality:LGE-only | 24 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0025 | -0.7531 |

## Reasons

- Case3012: edema_component_worse
- Case3040: edema_component_worse;edema_remote_fp_worse

No validation zip was created. No upload was performed. No fold1-4 refiner training was run.
