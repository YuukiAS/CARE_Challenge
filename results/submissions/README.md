# CARE Submission Outputs

Use `scripts/submission/prepare_care_myocardium_validation.py` for CARE-Myocardium validation submissions.

Directory policy:

- `care_myocardium_validation/workspaces/<model_combo>_<timestamp>/`: intermediate inputs and model predictions.
- `care_myocardium_validation/upload_ready/<model_combo>_<timestamp>/CARE-Myocardium-OrganAgent.zip`: upload this zip to the website.
- `care_myocardium_validation/upload_ready/<model_combo>_<timestamp>/manifest.json`: audit metadata, folds/checkpoints, source model combination, and any one-voxel pathology label fallback cases.

The upload zip intentionally has no timestamp in its filename. The timestamp lives on the parent folder so the zip remains compatible with the official `CARE-Myocardium-TeamName.zip` naming convention.
