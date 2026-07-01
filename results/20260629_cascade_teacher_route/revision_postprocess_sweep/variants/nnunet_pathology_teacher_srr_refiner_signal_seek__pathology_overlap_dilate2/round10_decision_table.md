# Lane A Round10 Refiner Decision

Decision: `fail_stop_refiner_candidate`
Cascade variant: `nnunet_pathology_teacher_srr_refiner`
Enforce scar unchanged: `False`

## Baseline vs Refiner By Subset

| subset | n | delta_edema_dice | delta_edema_hd95_improvement | delta_edema_component_count_improvement | delta_edema_remote_fp_improvement | delta_scar_dice | delta_scar_hd95_improvement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_case | 44 | 0.0009 | -0.0243 | 0.0682 | -0.0227 | 0.0020 | -0.3776 |
| t2_present_gt_positive | 16 | 0.0009 | -0.0668 | 0.1875 | -0.0625 | 0.0005 | -0.0324 |
| complete_modality | 16 | 0.0009 | -0.0668 | 0.1875 | -0.0625 | 0.0005 | -0.0324 |
| CenterB | 7 | 0.0045 | 0.0619 | 0.2857 | 0.0000 | 0.0005 | -0.1157 |
| CenterC | 9 | -0.0019 | -0.1668 | 0.1111 | -0.1111 | 0.0005 | 0.0324 |
| no_t2_empty_gt | 28 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0029 | -0.5900 |
| modality:C0+LGE+T2 | 16 | 0.0009 | -0.0668 | 0.1875 | -0.0625 | 0.0005 | -0.0324 |
| modality:C0+LGE | 4 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0053 | 0.0723 |
| modality:LGE-only | 24 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0025 | -0.6764 |

## Reasons

- Case2008: edema_component_worse
- Case2017: edema_component_worse
- Case3012: edema_component_worse
- Case3026: edema_component_worse
- Case3040: edema_component_worse;edema_remote_fp_worse

No validation zip was created. No upload was performed. No fold1-4 refiner training was run.
