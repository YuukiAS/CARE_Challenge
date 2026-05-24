# U-MyoPS myops_scar 低分诊断

## 1. 结论摘要

已证实：`results/metrics/unified/U-MyoPS/fold_0` 中的 `myops_scar=0.0699` 是旧默认导出/缓存结果；2026-05-12 继续训练完成后，用 `model_final_checkpoint` 重新 GPU fallback inference + remap + unified eval 后，fold0 `myops_scar` 提升到 **0.2823**、`myops_edema` 提升到 **0.6507**。高概率：当前主要瓶颈不再是 edema/scar 标签反转，而是 U-MyoPS Stage2 对部分中心/病例的 scar 召回与空间对齐不足，仍明显低于 nnU-Net 5-fold scar 参考线 0.5592。

## 2. 当前结果完整性

| 项目 | 状态 | 证据 | 结论 |
| --- | --- | --- | --- |
| fold 覆盖 | 仅 fold0 有 U-MyoPS 统一评测 | `results/metrics/unified/U-MyoPS/fold_0/evaluation_summary.json`；fold1-4 缺失 | 当前仍是 partial，不能作为 5-fold 最终结果 |
| 旧默认结果 | complete, stale | `results/metrics/unified/U-MyoPS/fold_0`: `class_4=0.5646`, `class_5=0.0699` | 这是旧 `U-MyoPS/fold_0` 缓存，不代表继续训练后的 checkpoint |
| Stage2 continue job | completed | `sacct -j 50091984`: `COMPLETED`, 00:46:14；日志到 epoch 49 并保存 checkpoint | 训练链路完成 |
| `model_final_checkpoint` 复评 | completed | `logs/U-MyoPS_ExportEval_50248470_20260512_195830.log`；`results/metrics/unified/U-MyoPS_model_final_checkpoint/fold_0/evaluation_summary.json` | scar 从 0.0699 提升到 0.2823 |
| `model_best` 复评 | running/pending | job `50263841` 已提交；旧 job `50091983` 因 `tmp_root` bug 失败 | 等待新 job 完成后比较 best vs final |
| scar-weighted 微调 | running/pending | job `50264309` 已提交；trainer `nnUNetTrainerPSNV8ScarCE2` | 从 final checkpoint 初始化，测试 scar CE weight=2.0 |
| `model_best` 是否被 smoke 覆盖 | 高风险但当前已被 continue 训练重写 | 当前 `model_best.model` timestamp 为 2026-05-12 14:03 | 旧 smoke 覆盖风险已被 50091984 后续训练缓解 |

## 3. 标签与数据链路核查

| 核查点 | 状态 | 证据 |
| --- | --- | --- |
| CARE compact label | 已证实一致 | offline eval 对 `Dataset501_CAREMyoPS` 使用 `class_4=myops_edema`, `class_5=myops_scar` |
| Stage2 内部 label | 已证实一致 | `Task901_CARE_UmyopsPathology_fold0/dataset.json`: `1=edema`, `2=scar` |
| train label remap | 已证实一致 | `compact_pathology_label`: `(4 or 1220)->1`, `(5 or 2221)->2` |
| export remap | 已证实一致 | `remap_to_care`: `1->4`, `2->5` |
| whichsubnet | 已证实默认 scar | export log: `whichsubnet=scar chk=model_final_checkpoint` |
| checkpoint fallback cache | 已修复 | `export_stage2_val_predictions.py` 已改为 per-checkpoint tmp root：`fold_0_model_final_checkpoint`, `fold_0_model_best` |
| stale prediction cache | 已修复一处 | `scripts/evaluation/run_unified_eval_model.sh` 在显式 `UMYOPS_EXPORT_CHECKPOINT` 时不再直接跳过 U-MyoPS 导出 |

## 4. per-case 现象

`model_final_checkpoint` 的最低 scar Dice 病例显示：预测中确实有 label 5，但若干病例 scar 体素数明显偏少或空间不重叠；这不符合“scar 全被映射成 edema”的单一错误，更像 Stage2 对部分中心/对齐条件失败。

| case | scar Dice | pred label4 | pred label5 | GT label4 | GT label5 | pred unique | GT unique |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Case2002 | 0.0000 | 440 | 138 | 3016 | 998 | `[0,4,5]` | `[0,1,2,3,4,5]` |
| Case2007 | 0.0000 | 100 | 10 | 1462 | 1303 | `[0,4,5]` | `[0,1,2,3,4,5]` |
| Case2020 | 0.0000 | 109 | 15 | 1032 | 561 | `[0,4,5]` | `[0,1,2,3,4,5]` |
| Case2031 | 0.0000 | 205 | 261 | 307 | 864 | `[0,4,5]` | `[0,1,2,3,4,5]` |
| Case3012 | 0.0000 | 913 | 137 | 4092 | 2818 | `[0,4,5]` | `[0,1,2,3,4,5]` |
| Case3044 | 0.0007 | 61 | 111 | 263 | 5781 | `[0,4,5]` | `[0,1,2,3,4,5]` |
| Case8021 | 0.0000 | 0 | 19 | 0 | 60 | `[0,5]` | `[0,5]` |

补充：GT 中 label `1/2/3` 是 Dataset501 解剖 compact label；当前 U-MyoPS export 只输出 pathology `4/5`，统一评测只统计 `4,5`，因此这些解剖 label 不影响当前 leaderboard 两项。

## 5. 最小修复方案

1. 已完成：修复 checkpoint-specific fallback export，避免 `model_best` 路径触发 `tmp_root` 未定义；避免显式 checkpoint 评测时静默复用旧 `U-MyoPS/fold_0` 预测缓存。
2. 立即执行：等待 job `50263841` 完成，读取 `results/metrics/unified/U-MyoPS_model_best/fold_0/evaluation_summary.json`，选择 `model_best` 或 `model_final_checkpoint` 作为后续 fold0 参考。
3. 高 ROI：继续只调 Stage2，不引入新 backbone。优先检查 `nnUNetTrainerPSNV8` 是否支持 scar/edema class weight 或 `--adjust_weights`；如果支持，scar 权重优先于继续盲目加 epochs。
4. 高 ROI：抽查低分中心病例的 Stage1 prior 和 aligned C0/T2/LGE，尤其 Case20xx/30xx。若 prior 与 LGE/GT 心肌区域错位，优先重跑或修正 Stage1，而不是继续 Stage2。
5. 中 ROI：fold0 只说明趋势。若 `model_best` 未明显超过 final，启动 fold1-4 Stage2，用相同 export/eval 口径补齐 5-fold。
6. 暂不建议：新模型、新外部数据、复杂后处理。当前 scar 缺口首先要从 Stage2 监督权重、Stage1 prior 对齐、checkpoint 选择和 cache hygiene 修。

## 6. 下一步命令

```bash
cd /overflow/htzhu/CARE

# 查看 model_best export/eval job
squeue -j 50263841 -o '%.18i %.30j %.2t %.10M %.20R'
sacct -j 50263841 --format=JobID,JobName%30,State,ExitCode,Elapsed,Start,End
tail -n 120 logs/U-MyoPS_ExportEval_50263841_*.log

# job 完成后读取 model_best 指标
cat results/metrics/unified/U-MyoPS_model_best/fold_0/evaluation_summary.json

# 查看 scar-weighted Stage2 微调
squeue -j 50264309 -o '%.18i %.30j %.2t %.10M %.20R'
sacct -j 50264309 --format=JobID,JobName%30,State,ExitCode,Elapsed,Start,End

# scar-weighted trainer 完成后导出评测
UMYOPS_STAGE2_TRAINER=nnUNetTrainerPSNV8ScarCE2 UMYOPS_EXPORT_CHECKPOINT=model_final_checkpoint \
  sbatch jobs/U-MyoPS/sbatch_export_eval_fold0.sh

# 显式 checkpoint 重新导出时，不再复用 stale U-MyoPS/fold_0 cache
UMYOPS_EXPORT_CHECKPOINT=model_final_checkpoint UMYOPS_EXPORT_FORCE_FALLBACK=1 \
  bash scripts/evaluation/run_unified_eval_model.sh U-MyoPS --folds 0
```

## 7. 文献对照

Ding 2023 的 U-MyoPS 设计动机是处理未配准 MS-CMR：先用配准/融合把多序列特征聚到 common space，再用心肌解剖先验突出 pathology 所在区域。CARE wrapper 的主要偏差是：训练集中大量病例缺 C0/T2，Stage1/Stage2 需要用零填充或跳过缺失模态；同时当前 Stage2 只输出 pathology compact labels 并接入 CARE `class_4/class_5` 评测。`model_final_checkpoint` 的结果说明标签桥接基本可用，但部分中心的 scar 仍可能受 Stage1 prior 质量和缺模态训练分布影响。
