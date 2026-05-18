# MyoPS-Net round4 prompt: T2-aware edema routing and postprocess ablation

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续改进 MyoPS-Net。本轮只验证一个主要假设：

> round3 mask-gated loss 已改善 scar 和 T2-present pathology，但 overall edema 被 T2-missing cases 的 class_4 false positives / scoring 拖垮。下一步应先做 T2-aware inference routing / output gating，而不是继续加 epoch。

## 必须先读

- `docs/notes/MyoPS-Net_improvement_round3.md`
- `results/experiments/MyoPS-Net_iteration_log.md`
- `results/metrics/unified/MyoPS-Net_maskgated_round3/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_maskgated_round3/fold_0/modality_group_metrics.md`
- `logs/MyoPS-Net_51264396_20260517_060037.log`
- `results/metrics/nnUNet.md`

## 当前事实

| metric | baseline fold0 | round2 moddrop | round3 mask-gated | nnU-Net 5-fold |
| --- | ---: | ---: | ---: | ---: |
| `myops_scar` / class_5 | 0.4637 | 0.4584 | **0.4965** | 0.5592 |
| `myops_edema` / class_4 | 0.2794 | 0.1496 | 0.1293 | 0.4197 |

Round3 source-modality groups:

| group | n | edema | scar |
| --- | ---: | ---: | ---: |
| C0+LGE+T2 | 16 | **0.3555** | **0.6171** |
| LGE-only | 24 | 0.0000 | 0.4311 |
| C0+LGE | 4 | 0.0000 | 0.4072 |

Interpretation:

- round3 improved the meaningful T2-present subset and overall scar.
- It failed overall edema because T2-missing groups should not be expected to predict edema reliably.
- Official MyoPS validation cases are all C0+LGE+T2, so T2-present metrics are highly relevant for submission; local fold0 overall is still needed for fair nnU-Net comparison.

## Round4 目标

Do export-only ablations first. Do not start training until you know whether routing/postprocess can recover edema without hurting scar.

## Required export/postprocess variants

Starting from:

- checkpoint: `results/checkpoints/MyoPS-Net/fold_0_maskgated_round3/checkpoints/best.pth`
- predictions: `results/predictions/MyoPS-Net_maskgated_round3/fold_0`

Implement isolated variants:

1. `t2_missing_suppress_edema`
   - If source modality `t2=false`, set predicted class_4 edema voxels to background or non-pathology before evaluation.
   - Do not change C0+LGE+T2 cases.
2. `myocardium_limited_pathology`
   - Remove predicted class_4/class_5 outside a myocardium support. Use only an available prediction-derived support or existing cardiac branch output; do not use GT.
3. `small_component_filter`
   - Per class remove tiny connected components with a configurable voxel threshold.
   - Evaluate Dice and, if available within budget, HD.
4. `combined_safe`
   - Compose the safest non-GT rules above if individual ablations improve target metrics.

Prediction and metric directories must be config-specific:

- `results/predictions/MyoPS-Net_round4_<variant>/fold_0`
- `results/metrics/unified/MyoPS-Net_round4_<variant>/fold_0`

## Required reporting

For each variant, report:

- overall `myops_edema`, `myops_scar`, foreground_mean;
- source groups: LGE-only, C0+LGE, C0+LGE+T2;
- T2-present edema/scar deltas;
- count of changed voxels per class and per source group;
- whether any variant would affect official validation cases, which are all T2-present.

## Optional short training only after export ablation

If export-only routing improves overall edema without harming T2-present metrics, run one fold0 <=8h training variant:

- keep `MYOPS_NET_MASK_GATED_LOSS=1`;
- optionally train edema loss only on T2-present cases;
- keep scar LGE supervision unchanged;
- export with the best routing variant.

Do not run folds 1-4 in this round.

## Success criteria

- useful routing: overall edema improves over 0.1293 and scar remains >=0.49.
- strong routing: edema approaches pre-round2 0.2794 while preserving T2-present scar >=0.61.
- continue toward 5-fold only if scar approaches 0.5592 and edema approaches 0.4197 or official-validation-specific rationale is clearly documented.

## Deliverables

- Code changes.
- New report: `docs/notes/MyoPS-Net_improvement_round4.md`.
- Append `results/experiments/MyoPS-Net_iteration_log.md`.
- New metrics under `results/metrics/unified/MyoPS-Net_round4_<variant>/fold_0`.
- Clear recommendation: run a T2-present edema expert, keep routing only, or stop MyoPS-Net in favor of nnU-Net.
