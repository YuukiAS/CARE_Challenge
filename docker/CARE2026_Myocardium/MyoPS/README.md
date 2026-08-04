# CARE2026 MyoPS nnU-Net Anatomy With Optional Self-Model Pathology

This source context implements the MyoPS workstation Docker build. By default,
the production graph is Dataset501 CAREMyoPS nnU-Net v2:

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

Missing modalities are a hard failure. No zero-fill or threshold search is
performed.

If `/app/models/self_model/selection.json` exists and has
`{"enabled": true, "kind": "care_ase"}`, the Docker entrypoint loads the listed
CARE-ASE checkpoint(s), uses the same nnU-Net preprocessing and geometry
restoration, and overlays only the selected self-model raw pathology labels:

- raw label `5` for scar when `scar_enabled` is true;
- raw label `4` for pure edema when `edema_enabled` is true.

nnU-Net still supplies anatomy/common geometry and remains the comparison
reference, not a scar/edema submission candidate for the self-model attempt.

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
