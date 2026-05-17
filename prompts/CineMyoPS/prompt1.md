# CineMyoPS myocardium_cinemyops 低分诊断 Prompt

你是 CARE-Myocardium 项目的代码与方法诊断助手。请在 `/overflow/htzhu/CARE` 仓库中检查当前 CineMyoPS 适配到 CARE CineMyoPS 数据集后的 `myocardium_cinemyops` / offline myocardium 指标异常问题，并把结论写成中文报告。

## 背景与目标

当前统一评测记录显示，CineMyoPS fold 0 的离线 `Dataset502_CARECineMyoPS` 指标为：

| metric | current fold0 | nnU-Net 参照 |
| --- | ---: | ---: |
| `class_1` myocardium | `0.0000` | `0.6864` |
| `class_2` LV_blood | `0.0000` | `0.9036` |
| `class_3` scar | `0.0000` | `0.2446` |

全 0 基本说明存在系统性 pipeline 问题，优先检查数据准备、frame policy、label remap、export 和评测链路。目标是让 CineMyoPS 正确适配当前 CARE CineMyoPS 数据集，重点服务 leaderboard `myocardium_cinemyops`，但不要在本轮引入新模块或替换模型结构。

## 必须参考的本地资料

- `docs/literature/Ding 等 - 2025 - CineMyoPS Segmenting Myocardial Pathologies from Cine Cardiac MR.pdf`
- `results/experiments/CineMyoPS_iteration_log.md`
- `results/metrics/unified/CineMyoPS/fold_0/evaluation_summary.json`
- `results/metrics/unified/nnUNet502/aggregate.md`
- `code/CineMyoPS/task026_utils.py`
- `code/CineMyoPS/prepare_task026_cine_4d.py`
- `code/CineMyoPS/export_protocol_val_predictions.sh`
- `code/CineMyoPS/sanity_check_task026.py`
- `code/CineMyoPS/verify_ed_at_t0.py`
- `jobs/CineMyoPS/*.sh`
- `scripts/evaluation/run_unified_eval_model.sh`
- `scripts/evaluation/evaluate_predictions.py`
- 相关日志：`logs/CineMyoPS*`, Slurm job `50094791` 及后续 job

## 诊断任务

1. 先确认当前结果是否完整：
   - 哪些 folds 已完成，哪些缺失；
   - 当前全 0 是否来自 fold0 的真实预测，还是旧缓存/空预测/label remap 错误；
   - 训练 job 是否完整跑完，export 是否成功，eval 是否评测了正确 pred dir。

2. 检查数据准备和 frame policy：
   - 确认 `t=0` 是否作为 ED frame，并检查 `verify_ed_at_t0.csv` 或生成逻辑；
   - `Task026_Cine_4D` 是否确实写入 ED-first + sampled frames；
   - 训练、推理、export 使用的 Task 名称、fold、num frames 是否一致；
   - 是否仍有 legacy Task025 / middle frame 输出被混用；
   - case id 是否与 `splits_CineMyoPS.json` 的 val cases 一致。

3. 检查标签语义与 remap：
   - CARE raw/compact 到 Cine compact 的映射是否为 `0=background`, `1=myocardium`, `2=LV_blood`, `3=scar`；
   - `task026_utils.py` 中 `COMPACT_LABEL_MAP = {0:0, 1:1, 2:2, 5:3}` 是否与 `Dataset502_CARECineMyoPS/labelsTr` 一致；
   - export 输出是否包含 `1/2/3`，还是只有 `0` 或错误 raw ids；
   - 预测和 GT 的 spacing/origin/direction 是否因 resample 后仍能对齐。

4. 检查训练/export 失败模式：
   - 训练 loss 是否下降，validation 是否生成非空 mask；
   - export script 是否找到 fold0 checkpoint；
   - `results/predictions/CineMyoPS/fold_0/*.nii.gz` 是否存在 13 个 val cases；
   - 抽样统计每个预测的 unique labels、非零体素数和图像尺寸；
   - 如果所有预测为 0，定位是模型输出、阈值/argmax、checkpoint 路径、还是 export 后处理造成。

5. 给出修复优先级：
   - 第一优先级是恢复非空、语义正确、空间对齐的 predictions；
   - 第二优先级是 ED-first frame policy 和 Task026 训练/推理一致性；
   - 第三优先级才是训练时长、fold 数、ensemble 和后处理；
   - 暂时不要建议引入新的 motion module、foundation model 或外部数据。

## 可运行命令建议

```bash
cd /overflow/htzhu/CARE

# 查看当前 CineMyoPS 指标
cat results/metrics/unified/CineMyoPS/fold_0/evaluation_summary.json

# 检查 Task026 数据
./env_CARE/bin/python code/CineMyoPS/sanity_check_task026.py
./env_CARE/bin/python code/CineMyoPS/verify_ed_at_t0.py

# 重新 export/eval fold0
FOLD=0 bash code/CineMyoPS/export_protocol_val_predictions.sh
bash scripts/evaluation/run_unified_eval_model.sh CineMyoPS --folds 0

# 检查日志
sacct -j 50094791
tail -n 160 logs/CineMyoPS*.log
```

## 输出要求

请将中文报告写到：

`docs/notes/CineMyoPS_myocardium_cinemyops_diagnosis.md`

报告结构：

1. `结论摘要`：说明全 0 最可能来自哪个环节。
2. `当前结果完整性`：fold/checkpoint/job/export/eval 状态表。
3. `Task026 数据链路核查`：frame policy、case split、label map、geometry。
4. `预测文件体检`：每个 val case 的 unique labels、非零体素数、尺寸，至少列出异常样例。
5. `最小修复方案`：限定在当前 CineMyoPS 数据适配、训练/export/eval 修复。
6. `下一步命令`：给出可复制命令。
7. `文献对照`：简短说明 Ding 2025 的 CineMyoPS 设计与当前 CARE wrapper 的偏差，尤其 ED frame、temporal frames、输出标签语义。

报告必须使用中文，路径、模型名、metric 名称保留英文。结论要明确区分“已证实”“高概率”“待验证”。
