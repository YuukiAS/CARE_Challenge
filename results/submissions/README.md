# CARE Submission Outputs

Use `scripts/submission/prepare_care_myocardium_validation.py` for CARE-Myocardium validation submissions.

Canonical directory policy:

- `care_myocardium_validation/workspaces/<model_combo>_<timestamp>/`: intermediate inputs and model predictions. These are generated and should not be committed.
- `care_myocardium_validation/upload_ready/<model_combo>_<timestamp>/CARE-Myocardium-OrganAgent.zip`: upload this zip to the website. These zips are generated and should not be committed.
- `care_myocardium_validation/upload_ready/<model_combo>_<timestamp>/manifest.json`: audit metadata, folds/checkpoints, source model combination, and any one-voxel pathology label fallback cases. Keep the latest important manifest contents summarized in docs rather than committing every generated manifest.

The upload zip intentionally has no timestamp in its filename. The timestamp lives on the parent folder so the zip remains compatible with the official `CARE-Myocardium-TeamName.zip` naming convention.

Legacy note:

- `care_myocardium_validation/nnunet_5fold_best/` predates the current `workspaces/` + `upload_ready/` split. Treat it as the archived pure nnU-Net baseline package, not as the naming pattern for new runs.
