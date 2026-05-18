# CARE-Myocardium Submission Packaging

Use `prepare_care_myocardium_validation.py` as the single validation submission entrypoint.

The official upload zip is written without a timestamp in the filename:

```text
CARE-Myocardium-OrganAgent.zip
```

Each run is separated by a timestamped parent folder:

```text
results/submissions/care_myocardium_validation/
├── workspaces/<model_combo>_<timestamp>/
└── upload_ready/<model_combo>_<timestamp>/
    ├── CARE-Myocardium-OrganAgent.zip
    ├── manifest.json
    └── submission_tree/
```

Evaluation semantics:

- The zip contains both `MyoPS/` and `CineMyoPS/`.
- Uploading one zip is one validation submission attempt. The hosted platform returns all three task metrics from that same upload: `myops_scar`, `myops_edema`, and `myocardium_cinemyops`.
- A package may still mix model sources across branches, for example nnU-Net on MyoPS and CineMyoPS `pathology_direct` on CineMyoPS. In that case, the returned MyoPS metrics evaluate the nnU-Net branch and the returned CineMyoPS metric evaluates the CineMyoPS branch.
- Interpret returned scores per metric, but do not plan or describe this as three separate submissions.

Pre-upload QA requirements:

- The zip must contain exactly the official CARE-Myocardium branch layout: `MyoPS/Anonymous Center/Case****/Case****_pred.nii.gz` and `CineMyoPS/Anonymous Center/Case****/Case****_pred.nii.gz`.
- For validation, each branch should contain `Case1001` through `Case1015`.
- MyoPS predictions must use CARE raw labels only: `0`, `200`, `500`, `600`, `1220`, `2221`.
- CineMyoPS predictions must use CARE raw labels only: `0`, `200`, `500`, `2221`.
- Every MyoPS case must contain at least one pathology label from `{1220, 2221}`. This avoids validator failures such as a case containing only `[0, 200, 500]`.
- Every CineMyoPS case must contain `2221`.
- `manifest.json` should be checked for `pathology_label_fallback.cases`; an empty list is preferred, and any non-empty list must be interpreted as a formatting fallback rather than a real model prediction.

`prepare_care_myocardium_validation.py` now enforces these checks before writing a successful manifest. A package that is missing pathology labels in a case should fail during preparation rather than only after website upload.

Current checked package:

```text
results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921/CARE-Myocardium-OrganAgent.zip
```

Label QA for this package passed on 2026-05-18:

| branch | files | cases | aggregate raw labels | missing pathology cases |
| --- | ---: | ---: | --- | --- |
| MyoPS | 15 | 15 | `{0: 4016921, 200: 41199, 500: 56541, 600: 56526, 1220: 20525, 2221: 13281}` | `[]` |
| CineMyoPS | 15 | 15 | `{0: 14965592, 200: 115603, 500: 217577, 2221: 58952}` | `[]` |

Common commands:

```bash
# nnU-Net for both MyoPS and CineMyoPS, 5-fold ensemble
./env_CARE/bin/python scripts/submission/prepare_care_myocardium_validation.py \
  --submission-model nnUNet \
  --folds 0 1 2 3 4 \
  --checkpoint checkpoint_best.pth

# MyoPS-Net for MyoPS, nnU-Net for CineMyoPS
./env_CARE/bin/python scripts/submission/prepare_care_myocardium_validation.py \
  --submission-model MyoPS-Net

# nnU-Net for MyoPS, CineMyoPS for CineMyoPS
./env_CARE/bin/python scripts/submission/prepare_care_myocardium_validation.py \
  --submission-model CineMyoPS

# Explicit mixed-source package: one upload, three returned metrics
./env_CARE/bin/python scripts/submission/prepare_care_myocardium_validation.py \
  --myops-model MyoPS-Net \
  --cine-model CineMyoPS
```

`U-MyoPS` currently requires explicit validation predictions:

```bash
./env_CARE/bin/python scripts/submission/prepare_care_myocardium_validation.py \
  --submission-model U-MyoPS \
  --myops-pred-dir /path/to/U-MyoPS/validation_predictions \
  --cine-model nnUNet
```

The current repository has U-MyoPS protocol fold export but not a complete validation raw Stage1-to-Stage2 inference pipeline.
