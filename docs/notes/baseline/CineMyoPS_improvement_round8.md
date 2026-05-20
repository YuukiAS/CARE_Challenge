# CineMyoPS improvement round8: hosted metric and HD repair

Date: 2026-05-19

## Scope

- Followed `prompts/CineMyoPS/prompt8_official_metric_hd_repair.md`.
- No training and no automatic upload.
- Goal: explain why the round7 `pathology_direct` hybrid validation submission had poor hosted CineMyoPS Dice/HD, then test export-only HD repair candidates on protocol fold0.

Latest refreshed leaderboard for `myocardium_cinemyops`:

| rank | user | time | Dice | HD |
| ---: | --- | --- | ---: | ---: |
| 1 | NCC1H | 20260515 16:16:58 | 0.2594 | 38.1004 |
| 6 | OrganAgent | 20260519 00:06:58 | 0.1748 | 75.2130 |

Interpretation: hosted `myocardium_cinemyops` does not behave like the previous local `class_1` myocardium proxy. Given the required CineMyoPS raw pathology label `2221`, the hosted score is more consistent with pathology/scar evaluation plus HD sensitivity.

## Code Changes

- Added `scripts/evaluation/cinemyops_round8_hd_repair.py`.
  - Audits validation submission raw-label CineMyoPS predictions.
  - Reports per-case `2221` volume, connected component count, largest component fraction, and scar-to-anatomy bbox distance.
  - Builds export-only compact-label repair variants for protocol fold0.
- Updated `scripts/submission/prepare_care_myocardium_validation.py`.
  - Added `--cine-postprocess-mode`.
  - Records explicit CineMyoPS postprocess mode in the manifest, including when `--cine-pred-dir` is provided.

Checks:

```bash
./env_CARE/bin/python -m py_compile scripts/submission/prepare_care_myocardium_validation.py scripts/evaluation/cinemyops_round8_hd_repair.py
```

## Validation Zip QA

Original round7 package audited:

```text
results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921/CARE-Myocardium-OrganAgent.zip
```

Outputs:

- `results/diagnostics/CineMyoPS_round8_validation_zip_qc.csv`
- `results/diagnostics/CineMyoPS_round8_validation_zip_qc.md`

Summary:

| item | value |
| --- | ---: |
| validation cases | 15 |
| total raw `2221` voxels | 58952 |
| cases with extra scar components or bbox-distance outliers | 14 |
| cases with scar bbox outside anatomy bbox | 0 |

The dominant issue is not scar far outside the submitted myocardium/LV bbox. Instead, 14/15 cases contain multiple disconnected `2221` components inside the broad anatomy bbox. This pattern is exactly the kind of small outlier behavior described in `docs/notes/baseline/Dice_HD.md`: little volume impact, but large HD sensitivity.

## Protocol Fold0 HD Audit

Output:

```text
results/metrics/unified/CineMyoPS_R8_hd_audit/fold_0/
```

Summary file:

```text
results/metrics/unified/CineMyoPS_R8_hd_audit/fold_0/summary.md
```

| variant | class_1 Dice | class_3 Dice | class_1 HD | class_3 HD | class_1 HD95 | class_3 HD95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| nnunet502_fold0 | 0.6864 | 0.2446 | 9.7380 | 39.0330 | 4.2299 | 29.9377 |
| pathology_direct | 0.6933 | 0.4378 | 14.5342 | 40.4694 | 6.0698 | 26.6533 |
| class1_primary_overlay | 0.6934 | 0.4374 | 14.4526 | 40.1611 | 6.0058 | 26.5847 |
| cardiac_only | 0.7611 | 0.0000 | 9.8425 | NA | 3.4140 | NA |
| pathology_largest_component | 0.6933 | 0.4441 | 14.5342 | 27.7648 | 6.0698 | 18.7983 |
| pathology_myocardium_roi | 0.6933 | 0.4378 | 14.5342 | 40.4694 | 6.0698 | 26.6533 |
| pathology_volume_guard | 0.6933 | 0.4388 | 14.5342 | 37.7505 | 6.0698 | 26.4855 |
| pathology_roi_lcc_volume_guard | 0.6933 | 0.4388 | 14.5342 | 37.7505 | 6.0698 | 26.4855 |

Best export-only repair: `pathology_largest_component`.

- It does not reduce `class_1`.
- It improves `class_3` Dice from `0.4378` to `0.4441`.
- It improves `class_3` HD from `40.4694` to `27.7648`.
- It improves `class_3` HD95 from `26.6533` to `18.7983`.

`pathology_myocardium_roi` had effectively no effect, confirming that the most damaging local outliers are disconnected scar islands inside the anatomy bbox rather than scar drifting far outside the cardiac region.

## Candidate Package

Because protocol fold0 evidence showed HD/HD95 improvement without Dice collapse, a new validation candidate was prepared from explicit predictions.

Candidate compact prediction dir:

```text
results/predictions/CineMyoPS_R8_validation_hd_repair/pathology_largest_component/fold_0
```

Upload-ready package:

```text
results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_lcc_hd_repair_20260519_083839/CARE-Myocardium-OrganAgent.zip
```

Manifest:

```text
results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_lcc_hd_repair_20260519_083839/manifest.json
```

Manifest evidence:

```json
{
  "combo": {"myops_model": "nnUNet", "cine_model": "CineMyoPS"},
  "cine": {
    "source": "explicit",
    "pred_dir": "results/predictions/CineMyoPS_R8_validation_hd_repair/pathology_largest_component/fold_0",
    "postprocess_mode": "pathology_largest_component"
  },
  "pathology_label_fallback": {"raw_label": 2221, "cases": []}
}
```

Zip QA:

| branch | files | cases | aggregate raw labels |
| --- | ---: | ---: | --- |
| MyoPS | 15 | 15 | `{0: 4016921, 200: 41199, 500: 56541, 600: 56526, 1220: 20525, 2221: 13281}` |
| CineMyoPS | 15 | 15 | `{0: 14975281, 200: 115603, 500: 217577, 2221: 49263}` |

Candidate validation QA:

- `results/diagnostics/CineMyoPS_round8_validation_lcc_candidate_zip_qc.csv`
- `results/diagnostics/CineMyoPS_round8_validation_lcc_candidate_zip_qc.md`

After largest-component repair:

| item | value |
| --- | ---: |
| validation cases | 15 |
| total raw `2221` voxels | 49263 |
| cases with extra scar components or bbox-distance outliers | 0 |

## nnU-Net Baseline Package

An updated nnU-Net-only 5-fold baseline package was also prepared from existing validation predictions, without rerunning inference:

```text
results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+nnUNet_CineMyoPS_5fold_baseline_round8_20260519_084057/CARE-Myocardium-OrganAgent.zip
```

Manifest:

```text
results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+nnUNet_CineMyoPS_5fold_baseline_round8_20260519_084057/manifest.json
```

Caveat: the nnU-Net Cine branch required one-voxel `2221` formatting fallback in `Case1009`, `Case1011`, and `Case1014`, so it is a baseline package but not an ideal pathology prediction.

## Conclusion

Round8 found a concrete HD failure mode: `pathology_direct` produces many disconnected scar components in validation predictions. The problem is not primarily large anatomy-bbox drift. The `pathology_largest_component` export-only repair is the current best validation candidate because it removes those disconnected scar islands and substantially improves protocol `class_3` HD/HD95 without Dice collapse.

No package was uploaded automatically.

If hosted Dice remains low after this candidate, stop small CineMyoPS postprocessing and move round9 toward a new `src/` motion/strain route, using MTI-MyoScarSeg-style motion-texture fusion or StrainNet-style cine strain features rather than further local class_1 proxy tuning.
