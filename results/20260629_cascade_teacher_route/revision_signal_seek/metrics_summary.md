# Cascade Signal-Seek Revision Metrics Summary

Status: `STOP_NO_SIGNAL_SEEK_ROUTE`
Selected variant: `none`
Ready variants: `2/2`
Slurm job: `57275246_[0-1]`

| variant | eval decision | delta T2+ edema Dice | delta T2+ edema HD95 | delta edema component count improvement | delta edema remote FP improvement | delta all scar Dice | delta all scar HD95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `nnunet_pathology_teacher_srr_refiner_signal_seek` | `fail_stop_refiner_candidate` | 0.0009 | -0.0665 | -0.0625 | -0.0625 | 0.0020 | -0.3773 |
| `coarse_to_fine_srr_roi_signal_seek` | `fail_stop_refiner_candidate` | 0.0025 | -0.0215 | -0.6875 | -0.3125 | 0.0033 | -0.4362 |

Edema rows use the T2-present GT-positive subset. Scar rows use all cases.

## Interpretation

The signal-seek revision confirms that increasing residual capacity and lowering
thresholds does not rescue the cascade route. It creates slightly larger Dice
deltas than the component-guard revision, but the cost is worse HD95 and
substantially worse component/remote-FP behavior. This is not close to the
nnU-Net reference and should not be selected.
