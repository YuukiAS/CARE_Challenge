# MyoPS-Net improvement round6

日期：2026-05-17

## 目标

本轮不训练，只闭合 round5 full-modality expert 在 all-case fold0 上的表现，并验证 hybrid routing 是否能把 round5 的 complete-case scar 优势转化成更强的 all-case MyoPS-Net 结果。

## 输入

| item | path |
| --- | --- |
| round5 checkpoint | `results/checkpoints/MyoPS-Net/fold_0_fullmod_round5/checkpoints/best.pth` |
| all-val staging root | `data/benchmarks/MyoPS-Net/fold_0_maskgated_round3` |
| fallback predictions | `results/predictions/MyoPS-Net_round4_combined_safe/fold_0` |
| split file | `data/benchmarks/protocol/splits_MyoPS.json`, fold 0 |

## 执行

Required script:

```bash
sbatch jobs/MyoPS-Net/sbatch_round6_hybrid_export.sh
```

Runs:

| job | status | note |
| --- | --- | --- |
| `51354700` | failed | exported fullmod-on-allval, then routed all train+val metadata cases and failed on `Case1001`; root cause was using `modalities_present.json` as the case list |
| `51354774` | completed | fixed routing to protocol fold0 validation cases only |

Code fix:

- `code/MyoPS-Net/build_round6_hybrid.py`: added `--fold-json` / `--fold`; routes only fold validation cases.
- `jobs/MyoPS-Net/sbatch_round6_hybrid_export.sh`: passes split file and fold to the hybrid builder.
- `jobs/MyoPS-Net/README.md`: documents that `modalities_present.json` is metadata, not the validation case list.

## Outputs

| variant | prediction dir | metric dir |
| --- | --- | --- |
| fullmod on all-val | `results/predictions/MyoPS-Net_round6_fullmod_on_allval/fold_0` | `results/metrics/unified/MyoPS-Net_round6_fullmod_on_allval/fold_0` |
| hybrid fullmod + round4 | `results/predictions/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0` | `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0` |

Routing summary: `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0/routing_summary.json`.

## Overall fold0 metrics

| variant | scope | n | myops_edema class_4 | myops_scar class_5 | foreground_mean |
| --- | --- | ---: | ---: | ---: | ---: |
| round4 `combined_safe` | all val cases | 44 | 0.3733 | 0.5048 | 0.4589 |
| round5 fullmod expert | complete C0+LGE+T2 cases only | 16 | 0.3746 | 0.6163 | 0.4954 |
| round6 fullmod on all-val | all val cases | 44 | 0.1362 | 0.3843 | 0.2603 |
| round6 hybrid fullmod + round4 | all val cases | 44 | 0.3746 | 0.5013 | 0.4574 |
| nnU-Net Dataset501 5-fold | reference | 5 folds | 0.4197 | 0.5592 | NA |

## Source-group metrics

### Fullmod on all-val

| modality group | n cases | myops_edema class_4 | myops_scar class_5 | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| C0+LGE | 4 | 0.0000 | 0.4118 | 0.2059 |
| C0+LGE+T2 | 16 | 0.3746 | 0.6163 | 0.4954 |
| LGE | 24 | 0.0000 | 0.2251 | 0.1125 |

### Hybrid fullmod + round4

| modality group | n cases | myops_edema class_4 | myops_scar class_5 | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| C0+LGE | 4 | NA | 0.4068 | 0.4068 |
| C0+LGE+T2 | 16 | 0.3746 | 0.6163 | 0.4954 |
| LGE | 24 | NA | 0.4404 | 0.4404 |

Routing counts:

| route | n |
| --- | ---: |
| fullmod_t2_present | 16 |
| fallback_t2_missing | 28 |

## 判定

- Fullmod expert cannot be used directly on all-val: LGE-only scar drops to 0.2251 and overall scar drops to 0.3843.
- Hybrid routing avoids the missing-modality collapse, but it does not improve the previous all-case round4 result: edema improves only 0.3733 -> 0.3746, while scar decreases 0.5048 -> 0.5013.
- Hybrid does not meet nnU-Net edema 0.4197 or scar 0.5592. It also does not satisfy the prompt6 rule for a local all-case improvement over round4.

## Recommendation

Do not expand to folds 1-4. Keep nnU-Net as the primary MyoPS baseline/submission route. MyoPS-Net fullmod/hybrid is not a stronger all-case fold0 candidate.

If continuing MyoPS-Net at all, the only defensible next small round is T2-present edema calibration or a T2-present edema expert, because scar on complete cases is acceptable but edema remains below nnU-Net. Do not continue generic fullmod training or long training.
