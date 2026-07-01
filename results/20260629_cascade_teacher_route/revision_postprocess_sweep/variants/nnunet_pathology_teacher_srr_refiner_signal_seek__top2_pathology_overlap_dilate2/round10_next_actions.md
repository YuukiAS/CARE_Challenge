# Lane A Round10 Refiner Decision

Decision: `fail_stop_refiner_candidate`
Cascade variant: `nnunet_pathology_teacher_srr_refiner`
Enforce scar unchanged: `False`

## Baseline vs Refiner By Subset

| subset | n | delta_edema_dice | delta_edema_hd95_improvement | delta_edema_component_count_improvement | delta_edema_remote_fp_improvement | delta_scar_dice | delta_scar_hd95_improvement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_case | 44 | 0.0010 | -0.0065 | 0.1364 | -0.0227 | 0.0020 | -0.4001 |
| t2_present_gt_positive | 16 | 0.0010 | -0.0178 | 0.3750 | -0.0625 | 0.0004 | -0.0328 |
| complete_modality | 16 | 0.0010 | -0.0178 | 0.3750 | -0.0625 | 0.0004 | -0.0328 |
| CenterB | 7 | 0.0042 | 0.0509 | 0.8571 | 0.0000 | 0.0003 | -0.1166 |
| CenterC | 9 | -0.0014 | -0.0713 | 0.0000 | -0.1111 | 0.0005 | 0.0324 |
| no_t2_empty_gt | 28 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0030 | -0.6262 |
| modality:C0+LGE+T2 | 16 | 0.0010 | -0.0178 | 0.3750 | -0.0625 | 0.0004 | -0.0328 |
| modality:C0+LGE | 4 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0051 | 0.0632 |
| modality:LGE-only | 24 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0026 | -0.7161 |

## Reasons

- Case3012: edema_component_worse
- Case3023: edema_component_worse
- Case3040: edema_component_worse;edema_remote_fp_worse

No validation zip was created. No upload was performed. No fold1-4 refiner training was run.
