# U-MyoPS round5 prompt: final-vs-best export and scar-specialist decision

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续 U-MyoPS。本轮不要训练；先比较 LGE-only/no-prior Stage2 的 `model_final_checkpoint` 与 `model_best`，确认是否能把 all-case scar 推过 nnU-Net，或者是否应把 U-MyoPS 固定为 scar specialist candidate。

本轮只验证一个主要假设：

> round4 证明 Stage1 prior / aligned C0/T2 channels 会伤害 scar。LGE-only/no-prior 的 final checkpoint 已接近 nnU-Net all-case scar，并在 complete-modality scar 上超过 nnU-Net；若 `model_best` 或 checkpoint selection 更好，U-MyoPS 可能成为 MyoPS scar branch 的候选。Edema 仍不能按 all-case 空 GT 虚高判断，必须看 T2-present/GT-positive 子集。

## 必须先读

- `docs/notes/U-MyoPS_improvement_round4.md`
- `results/experiments/U-MyoPS_iteration_log.md`
- `prompts/U-MyoPS/prompt4_stage2_prior_ablation.md`
- `jobs/U-MyoPS/README.md`
- `prompts/Baseline_report.md`
- `results/metrics/nnUNet.md`

## 当前事实

nnU-Net MyoPS reference:

| metric | nnU-Net |
| --- | ---: |
| `myops_edema` / class_4 | 0.4197 |
| `myops_scar` / class_5 | 0.5592 |

U-MyoPS round4 task-specific v2 result:

| result | group | n | myops_edema | myops_scar |
| --- | --- | ---: | ---: | ---: |
| LGE-only/no-prior final | all_cases | 44 | 0.6726 | 0.5248 |
| LGE-only/no-prior final | scar_gt_positive_only | 43 | 0.6650 | 0.5370 |
| LGE-only/no-prior final | complete/T2-present | 16 | 0.1622 | 0.6524 |

Interpretation so far:

- Stage1 prior/aligned C0/T2 were harming scar.
- U-MyoPS is a promising scar specialist.
- Edema all-case is inflated by empty-GT cases; T2-present edema remains poor.

Important prepared files:

- `jobs/U-MyoPS/sbatch_round5_export_compare.sh`
- `code/U-MyoPS/export_stage2_val_predictions.py` now includes task name in fallback temp cache root.

## Round5 目标

1. Export/evaluate both `model_final_checkpoint` and `model_best` for `Task912_CARE_UmyopsLGEOnlyNoPrior_fold0`.
2. Confirm prediction/cache isolation by checking task-specific metric dirs and logs.
3. Compare all-cases, scar-positive-only, complete-modality, and T2-present/edema-positive groups.
4. Decide whether U-MyoPS should:
   - become a scar-only candidate branch;
   - be combined with nnU-Net/MyoPS-Net for edema;
   - or stop due to all-case scar below nnU-Net.

## 必须运行

Use the short export-only Slurm script:

```bash
cd /overflow/htzhu/CARE
sbatch jobs/U-MyoPS/sbatch_round5_export_compare.sh
```

Expected outputs:

- `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_final_checkpoint/fold_0/evaluation_summary.json`
- `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_final_checkpoint/fold_0/grouped_diagnostics.md`
- `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0/evaluation_summary.json`
- `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0/grouped_diagnostics.md`

If `model_best` does not exist or maps to an older checkpoint, document exactly why and keep final as the only valid checkpoint. Do not train to create a new best in this round.

## 可选小修

Allowed only if export compare exposes a concrete bug:

- wrong checkpoint path;
- stale temp prediction cache;
- wrong Task name;
- missing trainer/checkpoint tag in metric dir;
- grouped diagnostics missing required T2-present/complete-modality subsets.

Do not change Stage2 training or labels.

## 结果判定

- If `model_best` or fixed final export gives all-case scar > 0.5592: prepare a validation-submission prompt using U-MyoPS as MyoPS scar candidate, but keep edema from nnU-Net/MyoPS-Net.
- If all-case scar remains 0.52-0.55 but complete-modality scar remains > 0.65: U-MyoPS is useful for official validation-like complete cases but not proven all-case better; next step should be hybrid validation packaging only if local routing supports it.
- If scar drops after cache isolation: previous result was contaminated; stop and debug export.
- If edema remains weak on T2-present cases: do not claim U-MyoPS solves `myops_edema`.

## 禁止事项

- 不要启动 Stage2 训练。
- 不要重新启用 Stage1 prior / C0 / T2 channels for scar unless a separate diagnostic proves benefit.
- 不要把 all-case edema 0.67 当成真实 edema 成功。
- 不要扩展 folds 1-4。
- 不要复用旧 `U-MyoPS_round4_*_v2` 目录作为新 round5 输出。

## 交付物

- 追加：`results/experiments/U-MyoPS_iteration_log.md`
- 新报告：`docs/notes/U-MyoPS_improvement_round5.md`
- final-vs-best metric JSON and grouped diagnostics
- 如修改脚本：更新 `jobs/U-MyoPS/README.md`

最终报告必须明确回答：U-MyoPS 当前是否值得作为 scar-specialist branch 继续投入；如果值得，下一轮应如何与 nnU-Net/MyoPS-Net 的 edema branch 组合。
