# U-MyoPS round8 prompt: prior reliability gating and final scar baseline gate

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续 U-MyoPS。本轮是 baseline 去留判定的第 8 轮。U-MyoPS round7 已经很接近 nnU-Net，但仍未越线；本轮只允许做小范围、可解释的 prior reliability/gating，不要扩 fold。

## 背景与硬事实

U-MyoPS round7:

| checkpoint | all-case edema | all-case scar | scar-positive scar | complete/T2-present scar | missing-modality scar |
| --- | ---: | ---: | ---: | ---: | ---: |
| `model_best` | 0.7039 | 0.5539 | 0.5668 | 0.6571 | 0.4949 |
| `model_final_checkpoint` | 0.7039 | 0.5538 | 0.5667 | 0.6571 | 0.4948 |

References:

| reference | scar |
| --- | ---: |
| nnU-Net Dataset501 fold0 | 0.5602 |
| nnU-Net Dataset501 5-fold mean | 0.5592 |
| U-MyoPS round5 LGE-only/no-prior best | 0.5307 |
| U-MyoPS round6 pure best | 0.5352 |

官方 hybrid zip 的 MyoPS branch 是 nnU-Net，不是 U-MyoPS，返回 scar Dice `0.5969`, HD `16.2536`。U-MyoPS 若进入 submission，必须先在本地 fold0 明确超过 nnU-Net，并且不能引入更差 HD/outlier 风险。

## 必须先读

- `docs/notes/U-MyoPS_improvement_round7.md`
- `results/experiments/U-MyoPS_iteration_log.md`
- `results/metrics/unified/U-MyoPS_round7_lge_dilated_prior_model_best/fold_0/grouped_diagnostics.md`
- `results/metrics/unified/U-MyoPS_round7_lge_dilated_prior_model_best/fold_0/stage1_prior_qc.csv`
- `docs/notes/Dice_HD.md`
- `prompts/DeepResearch/DeepResearch_prompt.md`
- `prompts/DeepResearch/Result1.pdf`
- `prompts/DeepResearch/Result2.pdf`
- `results/leaderboard/care2026_myocardium_myops_scar_latest.csv`
- `AGENTS.md`

DeepResearch 相关提示：B5/B6 强调 anatomy/pathology routing 和 HD/outlier 控制。U-MyoPS round8 不应新建大模型；只用 prior quality、component/volume、myocardium support 做可解释 gating。

## Round8 主要假设

> round7 离 nnU-Net 只差约 0.0053 Dice。少数 prior/pathology overlap 弱或体积异常 case 拉低 scar。通过基于 Stage1 prior reliability 的 per-case gating、dilation radius selection、component cleanup，可以在不训练或极短训练的情况下跨过 0.5592，同时控制 HD/outlier。

## 任务

1. **低分 case 归因**
   - 读取 round7 `per_case_counts.csv` 与 `stage1_prior_qc.csv`。
   - 对最低 scar cases 分类：
     - GT scar empty 但预测非空；
     - prior_pathology_overlap 极低；
     - pred_scar/gt_scar 体积比过大；
     - under-segmentation；
     - complete vs missing modality。
   - 输出 `results/diagnostics/U-MyoPS_round8_prior_gate/case_failure_taxonomy.{csv,md}`。

2. **export-only reliability gating variants**
   - 不训练优先。基于 round7 `model_best` prediction 生成 variants：
     - `drop_empty_gt_like_false_positive_proxy`: 对 prior overlap 极低且 scar volume 很小/孤立的预测做更严格过滤；不能使用 GT。
     - `prior_reliable_keep_lge_fallback`: prior reliability 低时回退到 round5 LGE-only/no-prior 或保守 volume cap。
     - `component_hd_guard`: 只删除远离 myocardium/prior bbox 的小组件，目标是改善 HD，不明显伤 Dice。
     - `volume_ratio_guard`: 基于 train/protocol prediction distribution 的 per-case scar 体积上限/下限。
   - 每个 variant 写独立 prediction/metric dir。

3. **可选极短训练只允许一个**
   - 如果 export-only 明确显示某个 gating 规则有效但需要模型内化，可做一个 <=4h fold0 fine-tune。
   - 否则不要训练。

4. **Dice + HD 双指标**
   - 评估 class_5 Dice，同时补充 HD/HD95 或 component distance proxy。
   - 不能只追求 Dice；官方 MyoPS scar 已显示 Dice/HD 错位，HD 不能恶化。

## 判定标准

- Strong success: pure U-MyoPS all-case scar > 0.5592，且 HD/outlier proxy 不比 round7 更差。
- Partial success: scar 0.556-0.559 且 HD 明显改善；可考虑 round9 小训练或 validation branch packaging。
- Failure: scar 仍 <=0.5539 或提升来自不可泛化规则；round9 不再继续 U-MyoPS，转入 `src/` 新模型。

## 禁止事项

- 不要使用 GT 规则修改预测。
- 不要使用 nnU-Net fallback 冒充 pure U-MyoPS。
- 不要声称 U-MyoPS 解决 edema；edema all-case 是 empty-GT inflated。
- 不要扩展 folds 1-4，除非本轮 pure U-MyoPS 明确超过 nnU-Net。
- 不要只看 Dice，必须考虑 HD/outlier。

## 交付物

- `docs/notes/U-MyoPS_improvement_round8.md`
- 追加 `results/experiments/U-MyoPS_iteration_log.md`
- `results/diagnostics/U-MyoPS_round8_prior_gate/`
- 每个 variant 的 `evaluation_summary.json`、grouped diagnostics、HD/component diagnostics
- 明确回答：U-MyoPS 是否值得进入 round9；若否，是否停止 baseline 主线并转 `src/` 新模型
