# MyoPS-Net round7 prompt: edema calibration while preserving best scar route

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续 MyoPS-Net。本轮目标仍是让 MyoPS-Net 在 MyoPS scar/edema 上超过 nnU-Net，但 round6 已证明 full-modality expert routing 没有带来 all-case 改进，所以不要继续同一路线长训。

本轮只验证一个主要假设：

> round5 fullmod expert 对 complete cases 的 edema 略有帮助但 scar 不如 round4；round6 hybrid all-case scar/edema 仍低于 nnU-Net。下一步应做 export-only 的 edema calibration/threshold/support ablation，同时保留目前 scar 最好的 route；若这也不能超过 nnU-Net，就应停止 MyoPS-Net fold0 投入或转向全新 edema expert。

定位说明：本轮是 CARE metric 的 last-mile calibration / diagnostic，不是 MyoPS-Net 论文思想本身的替代。MyoPS-Net 的主线仍应是 flexible multi-sequence fusion and missing-modality adaptation；如果 export-only calibration 没有明确收益，下一轮必须回到模型级 T2-aware / modality-mask / dropout adaptation，而不是继续堆后处理。

## 必须先读

- `docs/notes/MyoPS-Net_improvement_round5.md`
- `results/experiments/MyoPS-Net_iteration_log.md`
- `prompts/MyoPS-Net/prompt6_hybrid_export_and_edema_calibration.md`
- `results/metrics/unified/MyoPS-Net_round6_fullmod_on_allval/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0/modality_group_metrics.md`
- `prompts/Baseline_report.md`
- `results/metrics/nnUNet.md`

## 当前事实

Project nnU-Net MyoPS reference:

| metric | nnU-Net 5-fold mean |
| --- | ---: |
| myops_edema / class_4 | 0.4197 |
| myops_scar / class_5 | 0.5592 |

Current MyoPS-Net:

| variant | scope | n | myops_edema | myops_scar |
| --- | --- | ---: | ---: | ---: |
| round4 `combined_safe` | all val cases | 44 | 0.3733 | 0.5048 |
| round5 fullmod expert | complete C0+LGE+T2 cases | 16 | 0.3746 | 0.6163 |
| round6 fullmod-on-allval | all val cases | 44 | 0.1362 | 0.3843 |
| round6 hybrid fullmod+round4 | all val cases | 44 | 0.3746 | 0.5013 |

Round6 modality groups for hybrid:

| group | n | edema | scar |
| --- | ---: | ---: | ---: |
| C0+LGE | 4 | NA | 0.4068 |
| C0+LGE+T2 | 16 | 0.3746 | 0.6163 |
| LGE only | 24 | NA | 0.4404 |

Interpretation:

- Fullmod-on-allval collapses on missing-modality cases.
- Hybrid does not improve over round4 all-case scar; round5 complete-case scar is slightly below round4 complete-case scar.
- Edema remains about `0.045` below nnU-Net reference.

## Round7 目标

1. Preserve the best known scar route, likely round4 `combined_safe` for all-case scar unless a per-group route proves better.
2. Add an export-only edema calibration pipeline for T2-present cases:
   - threshold sweep if softmax/logits can be exported;
   - myocardium-support-limited edema;
   - component-size filtering targeted at class_4 only;
   - optional route: use round5 edema only for complete cases, but keep round4 scar.
3. Evaluate each variant all-cases and modality groups.
4. Decide if MyoPS-Net can realistically exceed nnU-Net; if not, document stop condition clearly.

## 建议实现

If probability maps are not available, first extend `code/MyoPS-Net/export_val_predictions.py` with a `--save-softmax-dir` or similar option. Do not use ad hoc NIfTI label thresholding if logits/probabilities are needed.

Create a short export-only/calibration script, for example:

- `code/MyoPS-Net/apply_round7_edema_calibration.py`
- `jobs/MyoPS-Net/sbatch_round7_edema_calibration.sh`

Candidate variants:

| variant | intended behavior |
| --- | --- |
| `keep_round4_scar_round5_edema_complete` | class_5 from round4, class_4 from round5 only on complete cases |
| `edema_support_limited` | class_4 limited to myocardium/C0 support on T2-present cases |
| `edema_component_filter` | remove small or implausible class_4 components only |
| `edema_threshold_sweep` | sweep class_4 probability threshold on T2-present cases if softmax available |

Write isolated dirs:

- `results/predictions/MyoPS-Net_round7_<variant>/fold_0`
- `results/metrics/unified/MyoPS-Net_round7_<variant>/fold_0`

## 结果判定

- Success: all-case `myops_edema >= 0.4197` and `myops_scar >= 0.5592`.
- Partial success: edema exceeds `0.4197` while scar stays at least round4 level (`>=0.5048`); next round may combine with U-MyoPS/nnU-Net scar.
- If no export-only variant improves edema beyond `0.39`, do not continue MyoPS-Net postprocess; next attempt must be a distinct T2-present edema expert with <=8h fold0 budget.
- If calibration improves local train/protocol but would not apply to official validation complete-modality cases, say so explicitly.
- If export-only calibration fails, explicitly recommend a paper-aligned model round: modality mask/dropout, T2-aware edema head, or robust fusion for CARE missing-modality distribution.

## 禁止事项

- 不要继续 fullmod expert 长训。
- 不要把 16-case result 当作 all-case success。
- 不要牺牲 scar 大幅换 edema；scar must be reported for every variant.
- 不要把 missing-T2 empty-GT edema NA/empty cases当作真实 edema 成功。
- 不要把 threshold/component 后处理包装成 MyoPS-Net paper-faithful improvement；它只能是 CARE calibration.
- 不要扩展 folds 1-4 unless fold0 exceeds or clearly matches nnU-Net on both target classes.

## 交付物

- 新报告：`docs/notes/MyoPS-Net_improvement_round7.md`
- 追加：`results/experiments/MyoPS-Net_iteration_log.md`
- 每个 variant 的 `evaluation_summary.json` 和 `modality_group_metrics.md`
- 如新增脚本：更新 `jobs/MyoPS-Net/README.md`

最终报告必须明确回答：MyoPS-Net 是否还有可能单独超过 nnU-Net；如果不能，下一步应该停止、转向 edema expert，还是与 U-MyoPS/nnU-Net 做组合 submission。
