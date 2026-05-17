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

# Explicit hybrid
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
