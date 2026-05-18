# MyoPS-Net round6 prompt: all-case hybrid export and edema calibration decision

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续 MyoPS-Net。本轮不要先训练；先闭合 round5 full-modality expert 在 all-case fold0 上的表现，并验证 hybrid routing 是否值得作为 validation submission candidate。

本轮只验证一个主要假设：

> round5 full-modality expert 在完整 C0+LGE+T2 子集上 scar 已超过 nnU-Net，但它只评估了 16 个完整模态病例。若将 complete cases 路由到 round5，并将缺 T2 cases 路由到 round4 `combined_safe`，可能得到一个更强的 all-case MyoPS-Net fold0 结果；若 edema 仍低于 nnU-Net，则下一轮应转向 T2-present edema expert/calibration，而不是继续长训。

## 必须先读

- `docs/notes/MyoPS-Net_improvement_round5.md`
- `results/experiments/MyoPS-Net_iteration_log.md`
- `prompts/MyoPS-Net/prompt5_fullmod_expert_routing.md`
- `jobs/MyoPS-Net/README.md`
- `prompts/Baseline_report.md`
- `results/metrics/nnUNet.md`

## 当前事实

nnU-Net MyoPS reference:

| metric | nnU-Net |
| --- | ---: |
| `myops_edema` / class_4 | 0.4197 |
| `myops_scar` / class_5 | 0.5592 |

MyoPS-Net current results:

| variant | scope | n | myops_edema | myops_scar |
| --- | --- | ---: | ---: | ---: |
| round4 `combined_safe` | all val cases | 44 | 0.3733 | 0.5048 |
| round5 fullmod expert | complete C0+LGE+T2 cases | 16 | 0.3746 | 0.6163 |

Important prepared files:

- `code/MyoPS-Net/build_round6_hybrid.py`
- `jobs/MyoPS-Net/sbatch_round6_hybrid_export.sh`

## Round6 目标

1. Export round5 full-modality checkpoint on the all-val staging root.
2. Evaluate fullmod-on-allval directly to determine whether it collapses on missing-modality cases.
3. Build hybrid predictions:
   - C0+LGE+T2 complete cases -> round5 fullmod expert;
   - T2-missing cases -> round4 `combined_safe` fallback.
4. Evaluate hybrid all-cases and modality subgroups.
5. Decide whether the next step is:
   - validation submission candidate;
   - T2-present edema calibration/expert;
   - or abandoning MyoPS-Net in favor of nnU-Net/U-MyoPS hybrid.

## 必须运行

Use the existing short export-only Slurm script:

```bash
cd /overflow/htzhu/CARE
sbatch jobs/MyoPS-Net/sbatch_round6_hybrid_export.sh
```

Expected outputs:

- `results/metrics/unified/MyoPS-Net_round6_fullmod_on_allval/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_round6_fullmod_on_allval/fold_0/modality_group_metrics.md`
- `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0/modality_group_metrics.md`
- `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0/routing_summary.json`

If the script fails because a checkpoint or fallback prediction is missing, diagnose the path and fix the script/env. Do not start training as a workaround.

## 允许的后续小修

If hybrid routing works but edema remains below nnU-Net, you may prepare but not necessarily run one short calibration/export-only ablation:

- T2-present edema threshold sweep;
- myocardium-support-limited edema mask;
- per-class connected-component filter targeted only at edema;
- no changes to missing-T2 cases unless explicitly justified.

Any calibration must write config-specific dirs such as:

- `results/predictions/MyoPS-Net_round6_edema_calib_<name>/fold_0`
- `results/metrics/unified/MyoPS-Net_round6_edema_calib_<name>/fold_0`

## 结果判定

- If hybrid all-case `myops_scar > 0.5592` and `myops_edema >= 0.4197`: MyoPS-Net can challenge nnU-Net locally; prepare validation submission instructions.
- If scar improves but edema remains < 0.4197: next round should target T2-present edema expert/calibration only.
- If fullmod-on-allval is poor on missing-modality cases but hybrid is good: keep routing, do not use fullmod alone for validation.
- If hybrid does not improve round4: do not expand folds; keep nnU-Net as primary MyoPS baseline.

## 禁止事项

- 不要继续 1000/2000 epoch 或超过 8 小时训练。
- 不要扩展 folds 1-4，除非 fold0 hybrid 同时接近/超过 nnU-Net scar 和 edema。
- 不要把 16-case fullmod result 当作 all-case result。
- 不要复用 stale prediction dirs；每个 variant 必须有独立 prediction/metric path。
- 不要改变 CARE compact label semantics：edema class_4, scar class_5。

## 交付物

- 追加：`results/experiments/MyoPS-Net_iteration_log.md`
- 新报告：`docs/notes/MyoPS-Net_improvement_round6.md`
- 若修改脚本：更新 `jobs/MyoPS-Net/README.md`
- round6 metric JSON / modality group report / routing summary

最终报告必须明确回答：round5 fullmod expert 是否能通过 hybrid routing 变成 all-case 改进；MyoPS-Net 下一轮是否应该做 edema calibration，还是停止投入。
