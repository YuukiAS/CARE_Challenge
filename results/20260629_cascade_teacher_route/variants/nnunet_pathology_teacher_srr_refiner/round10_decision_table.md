# Lane A Round10 Refiner Decision

Decision: `fail_stop_refiner_candidate`
Cascade variant: `nnunet_pathology_teacher_srr_refiner`
Enforce scar unchanged: `False`

## Baseline vs Refiner By Subset

| subset | n | delta_edema_dice | delta_edema_hd95_improvement | delta_edema_component_count_improvement | delta_edema_remote_fp_improvement | delta_scar_dice | delta_scar_hd95_improvement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_case | 44 | 0.0006 | 0.0012 | -0.0682 | 0.0227 | 0.0000 | 0.0000 |
| t2_present_gt_positive | 16 | 0.0006 | 0.0033 | -0.1875 | 0.0625 | 0.0000 | 0.0000 |
| complete_modality | 16 | 0.0006 | 0.0033 | -0.1875 | 0.0625 | 0.0000 | 0.0000 |
| CenterB | 7 | 0.0015 | 0.0420 | -0.1429 | 0.0000 | 0.0000 | 0.0000 |
| CenterC | 9 | -0.0000 | -0.0268 | -0.2222 | 0.1111 | 0.0000 | 0.0000 |
| no_t2_empty_gt | 28 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| modality:C0+LGE+T2 | 16 | 0.0006 | 0.0033 | -0.1875 | 0.0625 | 0.0000 | 0.0000 |
| modality:C0+LGE | 4 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| modality:LGE-only | 24 | NA | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## Reasons

- Case2007: edema_component_worse
- Case3011: edema_component_worse
- Case3012: edema_component_worse
- Case3034: edema_component_worse
- Case3044: edema_component_worse

No validation zip was created. No upload was performed. No fold1-4 refiner training was run.
