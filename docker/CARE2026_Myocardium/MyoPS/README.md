# CARE2026 MyoPS Pure nnU-Net Production Source

This source context implements the revised final MyoPS workstation Docker build.
The production graph is Dataset501 CAREMyoPS nnU-Net v2 only:

- dataset: `Dataset501_CAREMyoPS`
- trainer: `nnUNetTrainer_500epochs`
- configuration: `3d_fullres`
- folds: `0 1 2 3 4`
- checkpoint: `checkpoint_best.pth`
- TTA: nnU-Net default TTA

Inputs are discovered under `/input` in sorted case order. Each case must provide
all three modalities in the same directory:

- `<CaseID>_LGE.nii.gz` -> channel `0000`
- `<CaseID>_T2.nii.gz` -> channel `0001`
- `<CaseID>_C0.nii.gz` -> channel `0002`

Missing modalities are a hard failure. No zero-fill, case selector, thresholding,
postprocessing, scar overlay, or priority overwrite is performed.

Raw nnU-Net labels are mapped directly to the official labels:

| Raw | Official |
| --- | --- |
| 0 | 0 |
| 1 | 200 |
| 2 | 500 |
| 3 | 600 |
| 4 | 1220 |
| 5 | 2221 |

Outputs are written atomically to `/output/myops/<CaseID>_pred.nii.gz`.
