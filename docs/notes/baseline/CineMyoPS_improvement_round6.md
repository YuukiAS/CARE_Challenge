# CineMyoPS improvement round6: fixed-inference class_1 repair

Date: 2026-05-18

## Scope

- Followed prompt6: no new training, fold0 only, no official validation submission.
- Main hypothesis: after round5 fixed the sliding-window inference axis, class_1 may be recoverable by choosing a better compact combine/export strategy.
- Queue rule: checked `htzhulab`, `a100-gpu`, and `volta-gpu`; `htzhulab` had no pending backlog and the school GPU partitions had substantial pending queues, so the short export-only job stayed on `htzhulab`.

## Code and Script Changes

- Added `jobs/CineMyoPS/sbatch_round6_fixed_inference_modes.sh`.
  - Runs four fixed-inference export/eval modes with isolated `CineMyoPS_R6_*` output tags.
  - Uses fold0, `Task026_Cine_4D`, `CARECineMyoPSTrainerBNCalib`, `model_final_checkpoint`, BN recalibration, and `CINE_INFERENCE_TRAIN_MODE=0`.
- Added `scripts/evaluation/build_cinemyops_class1_overlay.py`.
  - Builds a class_1-primary overlay candidate from `cardiac_only` anatomy and pathology-branch scar predictions.

Checks:

```bash
bash -n jobs/CineMyoPS/sbatch_round6_fixed_inference_modes.sh
./env_CARE/bin/python -m py_compile scripts/evaluation/build_cinemyops_class1_overlay.py
```

## Fixed-Inference Combine Ablation

Command:

```bash
sbatch jobs/CineMyoPS/sbatch_round6_fixed_inference_modes.sh
```

- Job: `51367766`
- Log: `logs/CineMyoPS_r6_modes_51367766_20260518_024719.log`
- Stop reason: all four export/eval modes completed.

| variant | class_1 myocardium | class_2 LV | class_3 scar | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| nnU-Net Dataset502 5-fold reference | 0.6808 | 0.8874 | 0.2586 | - |
| nnU-Net Dataset502 fold0 reference | 0.6864 | - | 0.2446 | - |
| round5 fixed inference `current` | 0.6067 | 0.9305 | 0.3942 | 0.6438 |
| round6 `current` | 0.6076 | 0.9304 | 0.3946 | 0.6442 |
| round6 `cardiac_only` | 0.7611 | 0.9316 | 0.0000 | 0.5642 |
| round6 `myocardium_gated_scar` | 0.0000 | 0.9316 | 0.0000 | 0.3105 |
| round6 `pathology_direct` | 0.6933 | 0.9316 | 0.4378 | 0.6876 |
| round6 `class1_primary_overlay` | 0.6934 | 0.9316 | 0.4374 | 0.6875 |

## Interpretation

- `cardiac_only` proves the anatomy head is strong enough for the local class_1 proxy (`0.7611`), but it drops scar entirely and is not a paper-faithful final method.
- `pathology_direct` is the best paper-aligned candidate in this round. It keeps the pathology branch active and exceeds both nnU-Net class_1 references:
  - above nnU-Net 5-fold mean by `+0.0125`;
  - above nnU-Net fold0 by `+0.0069`;
  - scar sanity is also higher than nnU-Net (`0.4378` vs 5-fold `0.2586`).
- `class1_primary_overlay` gives nearly the same result as `pathology_direct`; it is a useful export diagnostic, but it does not materially improve beyond the direct combine strategy.
- `myocardium_gated_scar` is invalid for this checkpoint because it collapses class_1 and class_3, leaving only LV foreground.

## Per-Case Class_1 Comparison

| case | current | cardiac_only | pathology_direct | class1_overlay |
| --- | ---: | ---: | ---: | ---: |
| Case1005 | 0.6797 | 0.8018 | 0.7503 | 0.7505 |
| Case1010 | 0.6355 | 0.7772 | 0.7230 | 0.7229 |
| Case1019 | 0.5869 | 0.8527 | 0.6849 | 0.6849 |
| Case1021 | 0.5877 | 0.7944 | 0.7513 | 0.7513 |
| Case1023 | 0.6311 | 0.8333 | 0.7559 | 0.7559 |
| Case1026 | 0.5950 | 0.5572 | 0.6086 | 0.6086 |
| Case1029 | 0.6624 | 0.7897 | 0.7629 | 0.7632 |
| Case1037 | 0.6172 | 0.7905 | 0.6667 | 0.6665 |
| Case2004 | 0.6551 | 0.7196 | 0.7549 | 0.7556 |
| Case2009 | 0.4071 | 0.7962 | 0.5490 | 0.5491 |
| Case2010 | 0.6084 | 0.7373 | 0.6975 | 0.6977 |
| Case2017 | 0.5899 | 0.7396 | 0.6321 | 0.6319 |
| Case2021 | 0.6430 | 0.7051 | 0.6760 | 0.6759 |

Worst remaining class_1 case under the best paper-aligned mode is `Case2009` (`0.5490`). The failure is not general all-background collapse; it is case-specific anatomy/pathology interaction.

## Artifacts

- `results/metrics/unified/CineMyoPS_R6_current/fold_0/evaluation_summary.json`
- `results/metrics/unified/CineMyoPS_R6_cardiac_only/fold_0/evaluation_summary.json`
- `results/metrics/unified/CineMyoPS_R6_myo_gated_scar/fold_0/evaluation_summary.json`
- `results/metrics/unified/CineMyoPS_R6_pathology_direct/fold_0/evaluation_summary.json`
- `results/metrics/unified/CineMyoPS_R6_class1_primary_overlay/fold_0/evaluation_summary.json`
- `results/predictions/CineMyoPS_R6_class1_primary_overlay/fold_0/manifest.json`

## Recommendation

Use `CINE_COMBINE_MODE=pathology_direct` as the new fold0 CineMyoPS fixed-inference baseline. It is the closest and strongest strategy after round6 and satisfies the prompt's strong-result criterion. Do not start anatomy-focused training just to repair class_1 yet; the immediate next step should be cache-isolated validation of this combine mode, then decide whether to expand beyond fold0 or calibrate thresholds only if the hosted metric disagrees with the local proxy.
