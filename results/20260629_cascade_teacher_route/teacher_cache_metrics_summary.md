# Cascade Teacher Cache Metrics Summary

Status: OOF-5 teacher cache baseline only; no cascade refiner metrics in this file.

## Teacher Cache Coverage

- Fold0 train teacher predictions: `176/176` from OOF folds 1-4.
- Fold0 validation teacher predictions: `44/44` from fold0 validation.
- Teacher probabilities are present for all indexed rows.
- ROI/crop warning: `26` GT-positive class rows have teacher-derived ROI coverage `<0.95`, mostly scar.

## Core Pathology Teacher Baseline

| split | class | gt-positive cases | Dice mean | Dice min | ROI coverage mean | ROI coverage min | low ROI rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | myops_edema | 64 | 0.4399 | 0.0000 | 0.9983 | 0.9479 | 1 |
| train | myops_scar | 169 | 0.5786 | 0.0000 | 0.9727 | 0.2172 | 17 |
| val | myops_edema | 16 | 0.3944 | 0.1629 | 0.9996 | 0.9961 | 0 |
| val | myops_scar | 43 | 0.5732 | 0.0000 | 0.9748 | 0.3141 | 5 |
| all | myops_edema | 80 | 0.4308 | 0.0000 | 0.9986 | 0.9479 | 1 |
| all | myops_scar | 212 | 0.5775 | 0.0000 | 0.9731 | 0.2172 | 22 |

## Interpretation

- This cache is strong enough to launch a teacher/refiner route without generating new train-side fold0 predictions.
- A cascade model must be compared against these teacher rows and the nnU-Net fold0 reference, not against weak SRR alone.
- Scar ROI misses show why the cascade path should use probabilities/anatomy support and full-volume restore rather than teacher-mask-only crops.
