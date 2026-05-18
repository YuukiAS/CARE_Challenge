# CARE-Myocardium Validation Submissions

Use `scripts/submission/prepare_care_myocardium_validation.py` as the single entrypoint for new validation packages.

Submission semantics:

- One `CARE-Myocardium-OrganAgent.zip` upload contains both `MyoPS/` and `CineMyoPS/`.
- One upload consumes one validation submission attempt and returns three metrics: `myops_scar`, `myops_edema`, and `myocardium_cinemyops`.
- Mixed-source packages are allowed for internal comparison, but they are still one submission package. Record which model produced each branch before interpreting the three returned metrics.

Current layout:

- `workspaces/<submission_id>/`: generated staging area for converted inputs and raw model predictions.
- `upload_ready/<submission_id>/`: generated final submission folder containing `CARE-Myocardium-OrganAgent.zip`, `manifest.json`, and `submission_tree/`.
- `nnunet_5fold_best/`: legacy archived pure nnU-Net 5-fold baseline. Do not copy this layout for new model combinations.

Submission id convention:

```text
<MyoPSModel>_MyoPS+<CineModel>_CineMyoPS[_short_note]_<YYYYMMDD_HHMMSS>
```

Examples:

- `nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921`
- `nnUNet_reviewtest_20260517_reviewtest`

Pre-upload requirements:

- The zip must follow the official `MyoPS/Anonymous Center/Case****/Case****_pred.nii.gz` and `CineMyoPS/Anonymous Center/Case****/Case****_pred.nii.gz` layout.
- Validation packages should include `Case1001` through `Case1015` in both branches.
- Every MyoPS case must include at least one pathology label from `{1220, 2221}`.
- Every CineMyoPS case must include `2221`.
- Generated zips, prediction trees, and staging workspaces are ignored by git. Record important package status in `scripts/submission/README.md` or experiment notes instead of committing the generated payloads.
