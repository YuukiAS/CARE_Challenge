# Cascade Postprocess Sweep Metrics Summary

Status: `STOP_NO_POSTPROCESS_ROUTE`
Selected variant: `none`
Ready modes: `8/8`

| source | mode | delta T2+ edema Dice | delta T2+ edema HD95 | delta component count improvement | delta remote FP improvement | delta T2+ scar Dice |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `nnunet_pathology_teacher_srr_refiner_signal_seek` | `pathology_overlap_dilate1` | 0.0010 | -0.0686 | 0.7500 | -0.0625 | 0.0005 |
| `nnunet_pathology_teacher_srr_refiner_signal_seek` | `pathology_overlap_dilate2` | 0.0009 | -0.0668 | 0.1875 | -0.0625 | 0.0005 |
| `nnunet_pathology_teacher_srr_refiner_signal_seek` | `edema_overlap_dilate2_keep_scar` | 0.0009 | -0.0668 | 0.1875 | -0.0625 | 0.0005 |
| `nnunet_pathology_teacher_srr_refiner_signal_seek` | `top2_pathology_overlap_dilate2` | 0.0010 | -0.0178 | 0.3750 | -0.0625 | 0.0004 |
| `coarse_to_fine_srr_roi_signal_seek` | `pathology_overlap_dilate1` | 0.0024 | -0.0504 | 0.5625 | -0.0625 | 0.0009 |
| `coarse_to_fine_srr_roi_signal_seek` | `pathology_overlap_dilate2` | 0.0026 | -0.0164 | -0.0625 | -0.1250 | 0.0009 |
| `coarse_to_fine_srr_roi_signal_seek` | `edema_overlap_dilate2_keep_scar` | 0.0026 | -0.0164 | -0.0625 | -0.1250 | 0.0008 |
| `coarse_to_fine_srr_roi_signal_seek` | `top2_pathology_overlap_dilate2` | 0.0024 | 0.0307 | 0.3125 | -0.0625 | 0.0009 |

All modes are still `fail_stop_refiner_candidate`.

## Interpretation

The sweep partly confirms that component pruning can reduce component burden,
but it does not remove remote-FP regressions and does not create meaningful Dice
or scar gains. The best-looking coarse-to-fine top-2 mode improves HD95 and
component count, but remote FP still worsens and Dice remains a tiny `+0.0024`.
This is not sufficient evidence to select cascade.
