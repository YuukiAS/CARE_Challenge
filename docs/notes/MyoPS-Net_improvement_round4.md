# MyoPS-Net improvement round4

日期：2026-05-17

## 目标

本轮只测试一个主要假设：round3 的 overall edema 主要被 T2-missing cases 的 class_4 false positives 拖垮，因此先做 T2-aware inference routing / output gating 的 export-only 消融，不启动新训练。

## 输入

| item | value |
| --- | --- |
| Checkpoint | `results/checkpoints/MyoPS-Net/fold_0_maskgated_round3/checkpoints/best.pth` |
| Source prediction | `results/predictions/MyoPS-Net_maskgated_round3/fold_0` |
| Source metadata | `data/benchmarks/MyoPS-Net/fold_0_maskgated_round3/modalities_present.json` |
| Fold | 0 only |
| Training | none |

Round3 reference:

| metric | round3 mask-gated |
| --- | ---: |
| `myops_edema` / class_4 | 0.1293 |
| `myops_scar` / class_5 | 0.4965 |
| foreground_mean | 0.3129 |

T2-present round3 group: edema 0.3555, scar 0.6171.

## 代码改动

| 文件 | 改动 |
| --- | --- |
| `code/MyoPS-Net/export_val_predictions.py` | 可选写出 C0 cardiac branch 的 myocardium support mask，用于非 GT pathology support 消融 |
| `code/MyoPS-Net/apply_round4_postprocess.py` | 新增 round4 export-only 后处理入口，支持 T2-missing edema suppression、prediction-derived myocardium support、small component filter、combined rules，并记录 changed voxels |

说明：当前交互节点没有 GPU，C0 branch support 全量导出在 CPU 上过慢；本轮 `myocardium_limited_pathology` 实际使用 `apply_round4_postprocess.py` 的 prediction-derived fallback，即 class_4/class_5 预测 union 的 3D 最大连通支持区，不使用 GT。

## 变体与输出目录

| variant | rule | predictions | metrics |
| --- | --- | --- | --- |
| `t2_missing_suppress_edema` | T2 absent: class_4 -> 0 | `results/predictions/MyoPS-Net_round4_t2_missing_suppress_edema/fold_0` | `results/metrics/unified/MyoPS-Net_round4_t2_missing_suppress_edema/fold_0` |
| `myocardium_limited_pathology` | remove class_4/class_5 outside prediction-derived support | `results/predictions/MyoPS-Net_round4_myocardium_limited_pathology/fold_0` | `results/metrics/unified/MyoPS-Net_round4_myocardium_limited_pathology/fold_0` |
| `small_component_filter` | remove class_4/class_5 3D components `<20` voxels | `results/predictions/MyoPS-Net_round4_small_component_filter/fold_0` | `results/metrics/unified/MyoPS-Net_round4_small_component_filter/fold_0` |
| `combined_safe` | T2 suppression + prediction-derived support | `results/predictions/MyoPS-Net_round4_combined_safe/fold_0` | `results/metrics/unified/MyoPS-Net_round4_combined_safe/fold_0` |

## Overall fold0 metrics

| variant | myops_edema class_4 | myops_scar class_5 | foreground_mean | official T2-present cases affected |
| --- | ---: | ---: | ---: | --- |
| round3 reference | 0.1293 | 0.4965 | 0.3129 | no postprocess |
| `t2_missing_suppress_edema` | 0.3555 | 0.4965 | 0.4490 | no |
| `myocardium_limited_pathology` | 0.1358 | 0.4986 | 0.3172 | yes |
| `small_component_filter` | 0.1293 | 0.4963 | 0.3128 | yes |
| `combined_safe` | 0.3733 | 0.5048 | 0.4589 | yes |

## Source-group metrics

### t2_missing_suppress_edema

| group | n | edema | scar | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| C0+LGE | 4 | NA | 0.4072 | 0.4072 |
| C0+LGE+T2 | 16 | 0.3555 | 0.6171 | 0.4863 |
| LGE | 24 | NA | 0.4311 | 0.4311 |

### myocardium_limited_pathology

| group | n | edema | scar | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| C0+LGE | 4 | 0.0000 | 0.4087 | 0.2043 |
| C0+LGE+T2 | 16 | 0.3733 | 0.6258 | 0.4996 |
| LGE | 24 | 0.0000 | 0.4288 | 0.2144 |

### small_component_filter

| group | n | edema | scar | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| C0+LGE | 4 | 0.0000 | 0.4099 | 0.2050 |
| C0+LGE+T2 | 16 | 0.3555 | 0.6180 | 0.4867 |
| LGE | 24 | 0.0000 | 0.4295 | 0.2148 |

### combined_safe

| group | n | edema | scar | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| C0+LGE | 4 | NA | 0.4068 | 0.4068 |
| C0+LGE+T2 | 16 | 0.3733 | 0.6258 | 0.4996 |
| LGE | 24 | NA | 0.4404 | 0.4404 |

## Changed voxels

| variant | group | changed voxels | class_4 removed | class_5 removed | class_4 before -> after | class_5 before -> after |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `t2_missing_suppress_edema` | C0+LGE | 447237 | 447237 | 0 | 447237 -> 0 | 7773 -> 7773 |
| `t2_missing_suppress_edema` | C0+LGE+T2 | 0 | 0 | 0 | 27320 -> 27320 | 40917 -> 40917 |
| `t2_missing_suppress_edema` | LGE | 8136171 | 8136171 | 0 | 8136171 -> 0 | 68641 -> 68641 |
| `myocardium_limited_pathology` | C0+LGE | 4396 | 4294 | 102 | 447237 -> 442943 | 7773 -> 7671 |
| `myocardium_limited_pathology` | C0+LGE+T2 | 6505 | 4154 | 2351 | 27320 -> 23166 | 40917 -> 38566 |
| `myocardium_limited_pathology` | LGE | 17621 | 17325 | 296 | 8136171 -> 8118846 | 68641 -> 68345 |
| `small_component_filter` | C0+LGE | 1884 | 1725 | 159 | 447237 -> 445512 | 7773 -> 7614 |
| `small_component_filter` | C0+LGE+T2 | 779 | 566 | 213 | 27320 -> 26754 | 40917 -> 40704 |
| `small_component_filter` | LGE | 10769 | 9987 | 782 | 8136171 -> 8126184 | 68641 -> 67859 |
| `combined_safe` | C0+LGE | 447529 | 447237 | 292 | 447237 -> 0 | 7773 -> 7481 |
| `combined_safe` | C0+LGE+T2 | 6505 | 4154 | 2351 | 27320 -> 23166 | 40917 -> 38566 |
| `combined_safe` | LGE | 8142523 | 8136171 | 6352 | 8136171 -> 0 | 68641 -> 62289 |

## 判定

- `t2_missing_suppress_edema` alone proves the round4 hypothesis: non-T2 edema false positives were the main overall-edema failure. It improves overall edema from 0.1293 to 0.3555 and preserves scar at 0.4965 without affecting official T2-present validation cases.
- `myocardium_limited_pathology` improves T2-present edema/scar, but because it changes T2-present cases, it should be considered a validation-specific ablation rather than a universally safe official-submission default.
- `small_component_filter` is not useful at threshold 20; it barely changes edema and slightly lowers overall scar.
- `combined_safe` is the strongest local fold0 result: edema 0.3733, scar 0.5048, foreground_mean 0.4589. It satisfies useful routing and strong-routing edema criteria, but scar remains below the nnU-Net 5-fold reference 0.5592 and edema remains below 0.4197.

## Recommendation

Do not run folds 1-4 yet. Keep `t2_missing_suppress_edema` as the safe routing default for mixed-modality local folds and official validation compatibility. For one more fold0-only round, train a T2-present edema expert or add explicit T2-present edema routing while preserving LGE scar supervision; export with `combined_safe` only if official-validation-specific rationale accepts changing T2-present predictions.

HD/HD95 was not computed in this budgeted round; the Dice and changed-voxel results were sufficient to decide the next step.
