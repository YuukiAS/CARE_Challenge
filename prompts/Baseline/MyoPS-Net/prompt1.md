# MyoPS-Net myops_scar / myops_edema 低于 nnU-Net 诊断 Prompt

你是 CARE-Myocardium 项目的代码与方法诊断助手。请在 `/overflow/htzhu/CARE` 仓库中检查当前 MyoPS-Net 适配到 CARE MyoPS 数据集后，`myops_scar` 和 `myops_edema` 仍低于 nnU-Net 的原因，并把结论写成中文报告。

## 背景与目标

当前统一评测记录显示，MyoPS-Net fold 0 的离线指标为：

| metric | current fold0 | nnU-Net 参照 |
| --- | ---: | ---: |
| `myops_edema` / `class_4` | `0.1973` | `0.4197` |
| `myops_scar` / `class_5` | `0.4614` | `0.5592` |

MyoPS-Net 两个 leaderboard metric 都低于 nnU-Net，尤其 edema 差距较大。目标是定位 CARE 数据适配、缺模态处理、标签口径、loss/采样、训练/export/eval 链路中的可修复问题，并给出不引入新模块的最小改进计划。

## 必须参考的本地资料

- `docs/literature/Qiu 等 - 2023 - MyoPS-Net Myocardial pathology segmentation with flexible combination of multi-sequence CMR images.pdf`
- `results/experiments/MyoPS-Net_iteration_log.md`
- `results/metrics/unified/MyoPS-Net/fold_0/evaluation_summary.json`
- `results/metrics/unified/nnUNet501/aggregate.md`
- `results/metrics/nnUNet.md`
- `code/MyoPS-Net/prepare_myops_net_layout.py`
- `code/MyoPS-Net/export_val_predictions.py`
- `code/MyoPS-Net/run_train.sh`
- `jobs/MyoPS-Net/*.sh`
- `third_party/MyoPS-Net/README.md`
- `scripts/evaluation/run_unified_eval_model.sh`
- `scripts/evaluation/evaluate_predictions.py`
- 相关日志：`logs/MyoPS-Net*`, Slurm job `50089462` 及后续 job

## 诊断任务

1. 先确认当前结果是否完整：
   - 哪些 folds 已完成，哪些缺失；
   - 当前 fold0 指标是否来自完整 200 epoch 训练，还是历史/partial 输出；
   - `50089462` 及后续 job 是否完成 export/eval；
   - 是否存在旧预测缓存导致 aggregate 未更新。

2. 检查 CARE 到 MyoPS-Net 的数据适配：
   - 输入模态 C0/LGE/T2 是否正确 resample 到 LGE grid；
   - T1m/T2starm placeholder 是否被 challenge3 variant 忽略，而不是作为零图污染训练；
   - `train.txt` / `validation.txt` 是否使用 protocol split，且 case/slice 数正确；
   - 缺模态病例的处理是否符合当前 CARE 数据分布，尤其 LGE-only case；
   - 训练和 export 使用的 `MYOPS_NET_VARIANT=challenge3` 是否一致。

3. 检查标签语义与监督口径：
   - CARE compact ids 与 raw ids 是否转换正确：`4 -> 1220 edema`, `5 -> 2221 scar`；
   - upstream `LabelTransform` 是否把 edema/scar 读成预期类别；
   - challenge3 variant 是否严格预测 `edema` 与 `scar`，没有使用 `edema ∪ scar` 或 class 互换；
   - export 是否正确把 upstream 输出 remap 回 CARE compact `4/5`；
   - 统一评测对 MyoPS-Net 使用 `--skip-dice-if-gt-empty` 的影响是否合理。

4. 检查训练设置是否让 pathology 类被压制：
   - `MYOPS_NET_LOSS_WEIGHT_SCAR=2.5`, `MYOPS_NET_LOSS_WEIGHT_EDEMA=2.0` 是否生效；
   - batch size、slice sampling、positive-slice 比例是否导致 edema 学不到；
   - 训练日志中 scar/edema loss 或 val Dice 是否有早停/过拟合/坍缩迹象；
   - per-case 指标是否显示某些中心或缺模态组整体失败。

5. 给出修复优先级：
   - 第一优先级是数据适配、标签映射、variant 一致性、缓存/export 修复；
   - 第二优先级是 loss weight、positive sampling、训练时长、fold 完整性；
   - 第三优先级是后处理和 5-fold ensemble；
   - 暂时不要建议引入新 backbone、新分支或外部数据。

## 可运行命令建议

```bash
cd /overflow/htzhu/CARE

# 查看当前 MyoPS-Net 指标
cat results/metrics/unified/MyoPS-Net/fold_0/evaluation_summary.json

# 重新 export/eval fold0，注意不要误用旧 variant
MYOPS_NET_VARIANT=challenge3 bash scripts/evaluation/run_unified_eval_model.sh MyoPS-Net --folds 0

# 检查 job 状态与日志
sacct -j 50089462
tail -n 160 logs/MyoPS-Net*.log
```

## 输出要求

请将中文报告写到：

`docs/notes/MyoPS-Net_myops_metrics_diagnosis.md`

报告结构：

1. `结论摘要`：一句话判断两项指标低于 nnU-Net 的主要原因。
2. `当前结果完整性`：fold/checkpoint/job/export/eval 状态表。
3. `数据适配核查`：模态、缺模态、slice list、split、variant。
4. `标签与监督口径核查`：raw/compact/remap、edema/scar 语义。
5. `per-case / center / modality group 现象`：区分 LGE-only、LGE+C0、LGE+C0+T2 的表现。
6. `最小修复方案`：按 ROI 排序，限定在当前 MyoPS-Net 适配与训练配置内。
7. `下一步命令`：给出可复制命令。
8. `文献对照`：简短说明 Qiu 2023 的 MyoPS-Net 设定与当前 CARE wrapper 的偏差，特别是 flexible multi-sequence 与 CARE 缺模态。

报告必须使用中文，路径、模型名、metric 名称保留英文。结论要明确区分“已证实”“高概率”“待验证”。
