# U-MyoPS Improvement Round7

Date: 2026-05-18

## Goal

Round7 returned from export-only calibration to a more paper-aligned Stage1-prior route. The tested hypothesis was:

> A CARE-aware LGE + dilated Stage1 prior Stage2 task can keep the U-MyoPS prior-aware idea while avoiding the original full C0/T2/LGE aligned-input failure and the LGE-only/no-prior ablation.

This round was fold0 only, <=8h walltime, and did not use nnU-Net fallback in the final predictions beyond the existing U-MyoPS Stage2 export mechanism.

## Run

Command:

```bash
sbatch jobs/U-MyoPS/sbatch_round7_lge_dilated_prior.sh
```

- Job: `51368430`
- Log: `logs/U-MyoPS_r7_lge_dilated_prior_51368430_20260518_031147.log`
- Stage2 task: `Task914_CARE_UmyopsLGEDilatedPrior_fold0`
- Input variant: `lge_dilated_prior`
- Prior dilation radius XY: `8`
- Trainer: `nnUNetTrainerPSNV8ScarCE2`
- Epoch budget: `80`
- Stop reason: completed 80 epochs; last internal scar/class_2 validation metric `0.6170`

Outputs:

- `results/predictions/U-MyoPS_round7_lge_dilated_prior_model_best/fold_0`
- `results/metrics/unified/U-MyoPS_round7_lge_dilated_prior_model_best/fold_0`
- `results/predictions/U-MyoPS_round7_lge_dilated_prior_model_final_checkpoint/fold_0`
- `results/metrics/unified/U-MyoPS_round7_lge_dilated_prior_model_final_checkpoint/fold_0`

## Results

Reference:

| model | myops_edema | myops_scar |
| --- | ---: | ---: |
| nnU-Net Dataset501 5-fold mean | 0.4197 | 0.5592 |
| nnU-Net Dataset501 fold0 | 0.3944 | 0.5602 |
| U-MyoPS round5 LGE-only/no-prior best | 0.6518 | 0.5307 |
| U-MyoPS round6 best pure scar calibration | 0.6518 | 0.5352 |

Round7:

| checkpoint | all-case edema | all-case scar | scar-positive scar | complete/T2-present scar | missing-modality scar |
| --- | ---: | ---: | ---: | ---: | ---: |
| `model_best` | 0.7039 | 0.5539 | 0.5668 | 0.6571 | 0.4949 |
| `model_final_checkpoint` | 0.7039 | 0.5538 | 0.5667 | 0.6571 | 0.4948 |

Edema remains inflated by empty-GT cases. On edema GT-positive/T2-present cases, round7 edema is only `0.1858`, so U-MyoPS should still not be used as the edema model.

## Interpretation

- The CARE-aware dilated prior helped scar meaningfully: all-case scar improved from round5 `0.5307` and round6 pure best `0.5352` to `0.5539`.
- The result is still just below nnU-Net 5-fold `0.5592` and fold0 `0.5602`, so U-MyoPS has not crossed the baseline yet.
- Complete/T2-present scar is strong (`0.6571`) but still below nnU-Net fold0 complete subset from round6 diagnostics (`0.6933`).
- Missing-modality scar improved to `0.4949`, above prior U-MyoPS missing-modality `0.4646` and slightly above nnU-Net fold0 missing-modality `0.4841`.
- Main remaining failures are low-scar or over/under-segmented cases such as `Case7005`, `Case1045`, `Case1029`, `Case1053`, `Case5005`, `Case3004`, and `Case3038`.

## Decision

Round7 is a partial success and is the best pure U-MyoPS scar result so far, but it is not enough to replace nnU-Net for the MyoPS branch. If U-MyoPS continues, the next round should be a very small prior-reliability/gating or per-case failure analysis round, not fold expansion. For current submission, keep nnU-Net as the MyoPS branch.
