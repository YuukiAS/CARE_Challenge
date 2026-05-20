# CineMyoPS improvement round7: pathology_direct validation packaging

Date: 2026-05-18

## Scope

- Followed prompt7: no new training, no automatic upload.
- Goal: make the official validation packaging path use and record the round6 paper-aligned `pathology_direct` CineMyoPS strategy.
- MyoPS side: conservative nnU-Net fold0 validation prediction.
- CineMyoPS side: `Task026_Cine_4D`, `CARECineMyoPSTrainerBNCalib`, fold0, `model_final_checkpoint`, `CINE_NUM_FRAMES=4`, `CINE_COMBINE_MODE=pathology_direct`.

## Code and Script Changes

- `scripts/submission/prepare_care_myocardium_validation.py`
  - Added `--cine-combine-mode`, defaulting to `CINE_COMBINE_MODE` or `current`.
  - Passes `CINE_COMBINE_MODE` and `CINE_NUM_FRAMES` into CineMyoPS inference subprocess environment.
  - Records `combine_mode` in the CineMyoPS manifest metadata.
  - Prints the CineMyoPS combine mode/frame count for future log auditability.
- `jobs/submission/prepare_care_myocardium_validation_cinemyops_pathology_direct.sh`
  - New 8-hour `htzhulab` validation packaging wrapper.
  - Uses `--myops-model nnUNet --cine-model CineMyoPS --folds 0`.
  - Uses `--cine-combine-mode pathology_direct`.

Checks:

```bash
./env_CARE/bin/python -m py_compile scripts/submission/prepare_care_myocardium_validation.py
bash -n jobs/submission/prepare_care_myocardium_validation_cinemyops_pathology_direct.sh
```

## Packaging Run

Command:

```bash
sbatch jobs/submission/prepare_care_myocardium_validation_cinemyops_pathology_direct.sh
```

- Job: `51368429`
- Log: `logs/CAREValCinePD_51368429_20260518_030921.log`
- Workspace: `results/submissions/care_myocardium_validation/workspaces/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921`
- Upload dir: `results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921`
- Stop reason: completed; upload-ready zip and manifest written.

Upload-ready files:

- `results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921/CARE-Myocardium-OrganAgent.zip`
- `results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921/manifest.json`

## Manifest Evidence

Manifest CineMyoPS metadata:

```json
{
  "source": "CineMyoPS",
  "requested_folds": ["0"],
  "used_folds": ["0"],
  "task": "Task026_Cine_4D",
  "trainer": "CARECineMyoPSTrainerBNCalib",
  "dim": "2d",
  "checkpoint": "model_final_checkpoint",
  "num_frames": 4,
  "combine_mode": "pathology_direct"
}
```

The package uses fold0 only because only fold0 exists for `CARECineMyoPSTrainerBNCalib`; no hard-label vote across unavailable folds was attempted.

## Package QA

Zip layout:

- `zip_check.files`: `30`
- roots: `CineMyoPS/`, `MyoPS/`
- MyoPS prediction files: `15`
- CineMyoPS prediction files: `15`

Pathology fallback:

- `pathology_label_fallback.cases`: `[]`
- No MyoPS or CineMyoPS validation case required the one-voxel `2221` fallback.

Submission-tree label counts after compact-to-raw conversion:

| branch | cases | labels |
| --- | ---: | --- |
| MyoPS | 15 | `{0: 4016921, 200: 41199, 500: 56541, 600: 56526, 1220: 20525, 2221: 13281}` |
| CineMyoPS | 15 | `{0: 14965592, 200: 115603, 500: 217577, 2221: 58952}` |

These CineMyoPS validation predictions are not all background and contain the expected raw myocardium/LV/scar labels.

## Conclusion

The validation package truly uses the paper-aligned `pathology_direct` CineMyoPS strategy and is upload-ready. It was not uploaded automatically. If the hosted `myocardium_cinemyops` metric disagrees with the local class_1 proxy, inspect official metric semantics before any further training.
