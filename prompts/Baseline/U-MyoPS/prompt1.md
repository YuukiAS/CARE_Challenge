# U-MyoPS myops_scar 系统性低分诊断 Prompt

你是 CARE-Myocardium 项目的代码与方法诊断助手。请在 `/overflow/htzhu/CARE` 仓库中检查当前 U-MyoPS 适配到 CARE MyoPS 数据集后的 `myops_scar` 异常低分问题，并把结论写成中文报告。

## 背景与目标

当前统一评测记录显示，U-MyoPS fold 0 的离线指标为：

| metric | current fold0 | nnU-Net 参照 |
| --- | ---: | ---: |
| `myops_edema` / `class_4` | `0.5646` | `0.4197` |
| `myops_scar` / `class_5` | `0.0699` | `0.5592` |

这个 scar 分数过低，优先假设是系统性问题，而不是正常模型能力不足。目标是定位 U-MyoPS 在 CARE 数据适配、标签映射、Stage1/Stage2 bridge、checkpoint/export/eval 链路中的错配，并给出最小修复方案。暂时不要引入新模块或新模型结构。

## 必须参考的本地资料

- `docs/literature/Ding 等 - 2023 - Aligning Multi-Sequence CMR Towards Fully Automated Myocardial Pathology Segmentation.pdf`
- `results/experiments/U-MyoPS_iteration_log.md`
- `results/metrics/unified/U-MyoPS/fold_0/evaluation_summary.json`
- 如存在，也检查：
  - `results/metrics/unified/U-MyoPS_model_best/fold_0/evaluation_summary.json`
  - `results/metrics/unified/U-MyoPS_model_final_checkpoint/fold_0/evaluation_summary.json`
- `code/U-MyoPS/prepare_u_myops_from_care.py`
- `code/U-MyoPS/build_stage2_task_from_stage1.py`
- `code/U-MyoPS/export_stage2_val_predictions.py`
- `code/U-MyoPS/run_stage1.sh`
- `code/U-MyoPS/run_stage2.sh`
- `jobs/U-MyoPS/*.sh`
- `scripts/evaluation/run_unified_eval_model.sh`
- `scripts/evaluation/evaluate_predictions.py`
- `results/metrics/nnUNet.md`
- 相关日志：`logs/U-MyoPS*`, Slurm job `50091983`, `50091984` 及后续 job

## 诊断任务

1. 先确认当前结果是否完整：
   - 哪些 folds 已完成，哪些缺失；
   - 当前报告中的 `0.0699` 是 fold0、某个 checkpoint、还是过期缓存；
   - `model_best` 是否被 smoke run 覆盖；
   - continue training job 是否完成，以及是否已重新 export/eval。

2. 检查标签语义与映射是否一致：
   - CARE/nnU-Net compact label 中 `4=edema`, `5=scar`；
   - U-MyoPS Stage2 nnU-Net label 中 `1=edema`, `2=scar`；
   - export 中是否严格执行 `1 -> 4`, `2 -> 5`；
   - `build_stage2_task_from_stage1.py` 中的训练标签语义是否与 export/eval 完全一致；
   - 是否存在 scar/edema 反转、scar 被当作 edema union、或 raw id `1220/2221` 混用问题。

3. 检查 Stage2 输入和 Stage1 prior：
   - Stage2 输入通道顺序、命名和 dataset json 是否与训练/推理一致；
   - `whichsubnet` 是否训练和推理一致，尤其默认 `scar` 是否正确；
   - Stage1 prior 是否与 fold0 val case、空间网格、case id 对齐；
   - 是否有缺失模态被错误置零、或 C0/T2/LGE 顺序不一致导致 scar 分支失效；
   - 对 per-case scar Dice 极低病例抽样检查预测体素数、GT 体素数、label unique values。

4. 检查 export/evaluation 链路：
   - `validation_raw` 与 fallback GPU inference 输出是否来自同一 checkpoint；
   - `pred_dir_has_all_val_cases` 是否可能复用旧缓存；
   - `evaluation_summary.json` 中是否有大量 empty-GT case 影响 edema 但不影响 scar；
   - 统一评测是否应对 U-MyoPS pathology 指标使用 `--skip-dice-if-gt-empty`，并说明是否影响当前 scar 结论。

5. 给出修复优先级：
   - 第一优先级必须是 pipeline/映射/checkpoint/cache 修复；
   - 第二优先级才是继续训练、loss weight、batch size、epochs；
   - 不要建议引入新 backbone、额外模块或外部数据。

## 可运行命令建议

可根据需要运行以下命令，但要先检查是否会覆盖重要输出：

```bash
cd /overflow/htzhu/CARE

# 查看当前 U-MyoPS 指标
cat results/metrics/unified/U-MyoPS/fold_0/evaluation_summary.json

# 重新导出指定 checkpoint 并评测 fold0
UMYOPS_EXPORT_CHECKPOINT=model_final_checkpoint bash scripts/evaluation/run_unified_eval_model.sh U-MyoPS --folds 0
UMYOPS_EXPORT_CHECKPOINT=model_best UMYOPS_EXPORT_FORCE_FALLBACK=1 bash scripts/evaluation/run_unified_eval_model.sh U-MyoPS --folds 0

# 检查 job 状态与日志
sacct -j 50091983,50091984
tail -n 120 logs/U-MyoPS_*.log
```

## 输出要求

请将中文报告写到：

`docs/notes/U-MyoPS_myops_scar_diagnosis.md`

报告结构：

1. `结论摘要`：一句话判断最可能原因。
2. `当前结果完整性`：fold/checkpoint/job 状态表。
3. `标签与数据链路核查`：逐项列出通过/失败/待查证据。
4. `per-case 现象`：scar Dice 极低病例、预测体素数/GT 体素数/unique labels。
5. `最小修复方案`：按 ROI 排序，限定在数据集适配、训练参数、checkpoint/export/eval 修复。
6. `下一步命令`：给出可复制命令。
7. `文献对照`：简短说明 Ding 2023 的 U-MyoPS 设计与当前 CARE wrapper 的偏差。

报告必须使用中文，路径、模型名、metric 名称保留英文。结论要明确区分“已证实”“高概率”“待验证”。
