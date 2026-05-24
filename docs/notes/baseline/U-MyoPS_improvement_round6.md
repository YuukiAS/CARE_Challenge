# U-MyoPS round6: missing-modality scar calibration

Date: 2026-05-18

## Goal

Round6 tests export-only scar calibration and routing after round5 showed `Task912_CARE_UmyopsLGEOnlyNoPrior_fold0` `model_best` was the strongest U-MyoPS checkpoint but still below nnU-Net on all-case scar.

This round does not train and does not expand to folds 1-4.

## Execution

Command:

```bash
sbatch jobs/U-MyoPS/sbatch_round6_scar_calibration.sh
```

Slurm job:

- job ID: `51367847`
- node: `g1807htzh01.ll.unc.edu`
- log: `logs/U-MyoPS_r6_calibration_51367847_20260518_024923.log`
- status: completed.

New scripts:

- `code/U-MyoPS/apply_round6_scar_calibration.py`
- `jobs/U-MyoPS/sbatch_round6_scar_calibration.sh`

## Inputs

- U-MyoPS best predictions: `results/predictions/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0`
- nnU-Net501 predictions: `results/predictions/nnUNet501/fold_0`
- GT: `data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr`
- split: `data/benchmarks/protocol/splits_MyoPS.json`
- modality metadata: `data/benchmarks/U-MyoPS/gen_ZS_unaligned/data/*/subject_meta.json`

Diagnostics:

- `results/diagnostics/baseline_paper_models/U-MyoPS/round06_scar_vs_nnunet/per_case_umyops_vs_nnunet_scar.csv`
- `results/diagnostics/baseline_paper_models/U-MyoPS/round06_scar_vs_nnunet/per_case_umyops_vs_nnunet_scar.md`
- `results/diagnostics/baseline_paper_models/U-MyoPS/round06_scar_vs_nnunet/manifest.json`

## Per-case comparison

Same fold0 comparison:

| group | n | U-MyoPS scar | nnU-Net scar | U - nnU-Net |
| --- | ---: | ---: | ---: | ---: |
| all | 44 | 0.5307 | 0.5602 | -0.0295 |
| complete | 16 | 0.6463 | 0.6933 | -0.0471 |
| missing-modality | 28 | 0.4646 | 0.4841 | -0.0195 |
| scar-positive | 43 | 0.5430 | 0.5732 | -0.0302 |

Worst U-MyoPS vs nnU-Net scar gaps:

| case | group | gt scar | U pred | nnU-Net pred | U scar | nnU-Net scar | failure hint |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Case3038 | complete | 8515 | 2671 | 7687 | 0.3256 | 0.7583 | under-segmentation |
| Case5005 | missing | 5585 | 1278 | 2641 | 0.3034 | 0.5726 | under-segmentation |
| Case8019 | missing | 437 | 623 | 665 | 0.4585 | 0.6588 | localization/mixed |
| Case3023 | complete | 1935 | 1798 | 2635 | 0.4838 | 0.6613 | localization/mixed |
| Case1021 | missing | 1766 | 1257 | 1452 | 0.4419 | 0.5699 | localization/mixed |

The all-case gap is not only a missing-T2 problem. Missing-modality cases are weaker, but same-fold nnU-Net is also better on complete cases because of several large complete-case failures, especially `Case3038`.

## Variants

Pure U-MyoPS variants:

- `U-MyoPS_round6_scar_component_filter_100`
- `U-MyoPS_round6_scar_component_filter_250`
- `U-MyoPS_round6_missing_volume_cap_1500`

Hybrid diagnostic variants:

- `U-MyoPS_round6_scar_complete_umyops_missing_nnunet`: keep U-MyoPS everywhere, replace class 5 with nnU-Net only on missing-modality cases.
- `U-MyoPS_round6_complete_umyops_missing_nnunet`: replace class 4 and class 5 with nnU-Net on missing-modality cases.

The hybrid variants are not pure U-MyoPS and are not paper-faithful U-MyoPS.

## Results

Reference:

| model | all-case myops_scar |
| --- | ---: |
| nnU-Net501 fold0 | 0.5602 |
| nnU-Net MyoPS 5-fold mean | 0.5592 |
| U-MyoPS round5 best | 0.5307 |

Round6:

| variant | type | all-case edema | all-case scar | scar-positive scar | complete/T2-present scar |
| --- | --- | ---: | ---: | ---: | ---: |
| `scar_component_filter_100` | pure U-MyoPS | 0.6518 | 0.5284 | 0.5406 | 0.6513 |
| `scar_component_filter_250` | pure U-MyoPS | 0.6518 | 0.5352 | 0.5244 | 0.6202 |
| `missing_volume_cap_1500` | pure U-MyoPS | 0.6518 | 0.5309 | 0.5432 | 0.6463 |
| `scar_complete_umyops_missing_nnunet` | hybrid scar | 0.6518 | 0.5431 | 0.5557 | 0.6463 |
| `complete_umyops_missing_nnunet` | hybrid full | 0.6973 | 0.5431 | 0.5557 | 0.6463 |

Edema remains weak on the T2-present/GT-positive subset:

- best round6 T2-present edema among these variants: `0.1675`
- this is not an edema solution.

## Decision

Pure U-MyoPS did not cross nnU-Net. The best pure scar calibration was component filtering at 250 voxels (`0.5352` all-case scar), still below nnU-Net fold0 `0.5602` and the 5-fold reference `0.5592`. It also reduced complete-case scar to `0.6202`, right at the lower acceptable boundary.

Hybrid routing also did not cross nnU-Net. Replacing missing-modality scar with nnU-Net raised all-case scar to `0.5431`, but complete U-MyoPS cases remained weaker than same-fold nnU-Net, so the hybrid did not reach the nnU-Net reference.

Current conclusion:

- U-MyoPS cannot be claimed as a pure scar model that beats nnU-Net.
- The LGE-only/no-prior route remains a CARE diagnostic/scar-specialist adaptation, not paper-faithful U-MyoPS.
- The only defensible continuation is either:
  - keep U-MyoPS as an official-validation-like complete-case scar specialist candidate only when validation routing can be justified; or
  - run a separate paper-faithful Stage1 repair round focused on prior quality, missing-modality-aware gating, and aligned C0/T2 reliability.

For CARE submission packaging today, nnU-Net remains the conservative MyoPS scar default unless a future hybrid uses a non-oracle routing rule that actually improves all-case validation scar.
