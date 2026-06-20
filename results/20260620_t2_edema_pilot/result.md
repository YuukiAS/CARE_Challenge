# Result 20260620 T2 Edema Pilot

status: completed

## 迁移说明

本文件由 legacy 路径 `prompts/tasks/20260620_t2_present_edema_pilot_result.md` 迁移而来。当前 task/result/review 对应关系为：

- task: `prompts/tasks/20260620_t2_edema_pilot.md`
- result: `results/20260620_t2_edema_pilot/result.md`
- review: `results/20260620_t2_edema_pilot/review.md`
- manifest: `results/20260620_t2_edema_pilot/MANIFEST.md`

## 执行摘要

已按 `prompts/tasks/20260620_t2_edema_pilot.md` 执行隔离 pilot。没有联网、没有上传、没有删除数据、没有生成或覆盖 validation upload zip，也没有修改主训练入口或旧 baseline 默认路径。

核心结果：

- 当前仓库统计复核为 MyoPS train 220 例：`C0+LGE+T2` 80、`C0+LGE` 24、`LGE-only` 116。
- MyoPS raw validation 15/15 为 `C0+LGE+T2` complete。
- edema 只出现在 80 个 complete/T2-present train cases；24 个 `C0+LGE` 与 116 个 `LGE-only` 均无 edema label，但 scar 仍大量存在。
- 运行了覆盖全部 80 个 complete cases 的 T2 robust-z + oracle myocardium/scar prior + component filter feature baseline，不是 3-5 case toy smoke。
- 该 feature baseline 在 fold0 complete val 上 Dice 0.2910、precision 0.2982、recall 0.4643、HD 38.6553、HD95 24.0819。
- 结论：T2-present expert/routing 值得作为下一步主线，但简单阈值/规则 baseline 不足以直接进入正式 pipeline 或 submission。

## 与本任务相关的规则复述

- 默认任务入口是 `prompts/tasks/<task_key>.md`，执行报告写到 `results/<task_key>/result.md`，review 写到 `results/<task_key>/review.md`。
- frontmatter 允许 `allow_code_change: true`、`allow_shell_command: true`；禁止联网和外部上传。
- 证据必须来自文件路径、命令、测试结果、输出目录和明确指标。
- 单个 job walltime 不得超过 8 小时；本次没有提交 Slurm/GPU job，实际本地诊断远低于该限制。
- GPU CARE job 默认优先 `htzhulab`，fallback 需先查队列；本次未触发 GPU fallback。
- Slurm job 脚本按仓库日志风格写入 `logs/T2EdemaPilot_<jobid>_<timestamp>.log`。
- 禁止未授权 upload/delete/official validation submission/昂贵长任务；本次遵守。

## 读取文件

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/tasks/20260620_t2_edema_pilot.md`
- `docs/notes/data_difficulty_and_resource_search_20260619.md`
- `README.md`
- `env_nnunet.sh`
- `code/nnUNet/convert_myops_to_nnunet.py`
- `code/nnUNet/nnunet_label_utils.py`
- `data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/dataset.json`
- `data/benchmarks/protocol/splits_MyoPS.json`
- `results/metrics/nnUNet.md`

说明：task 指定的 `CARE-README.md` 当前不存在；已记录缺失，并使用仓库 `README.md` 与相关脚本补足背景。

## 修改文件

- `scripts/experiments/t2_present_edema_pilot.py`
- `jobs/experiments/run_t2_present_edema_pilot.sh`
- `docs/notes/t2_present_edema_pilot_20260620.md`
- `results/20260620_t2_edema_pilot/result.md`

## 生成输出

- `results/experiments/t2_present_edema_20260619_131434/summary.md`
- `results/experiments/t2_present_edema_20260619_131434/manifest.json`
- `results/experiments/t2_present_edema_20260619_131434/myops_case_metadata.csv`
- `results/experiments/t2_present_edema_20260619_131434/myops_group_summary.csv`
- `results/experiments/t2_present_edema_20260619_131434/myops_validation_modality_metadata.csv`
- `results/experiments/t2_present_edema_20260619_131434/feature_baseline_threshold_grid.csv`
- `results/experiments/t2_present_edema_20260619_131434/feature_baseline_case_metrics.csv`
- `results/experiments/t2_present_edema_20260619_131434/feature_baseline_summary.json`
- `results/experiments/t2_present_edema_20260619_131434/feature_baseline_predictions/all_complete/*.nii.gz`
- `results/20260620_t2_edema_pilot/MANIFEST.md`
- `results/20260620_t2_edema_pilot/review.md`

## 运行命令

- `sed -n '1,260p' AGENTS.md`
- `sed -n '1,260p' prompts/AGENT_RULES.md`
- `sed -n '1,260p' prompts/tasks/20260620_t2_edema_pilot.md`
- `sed -n '1,220p' docs/notes/data_difficulty_and_resource_search_20260619.md`
- `sed -n '1,220p' env_nnunet.sh`
- `sed -n '1,260p' code/nnUNet/convert_myops_to_nnunet.py`
- `sed -n '1,220p' code/nnUNet/nnunet_label_utils.py`
- `./envs/env_CARE/bin/python -m py_compile scripts/experiments/t2_present_edema_pilot.py`
- `bash -n jobs/experiments/run_t2_present_edema_pilot.sh`
- `./envs/env_CARE/bin/python scripts/experiments/t2_present_edema_pilot.py`

中间有两次较大默认网格运行因耗时过高被 Ctrl-C 中断，随后将默认 pilot 网格缩小为可复跑的粗网格。最终成功运行的命令退出状态为 0。

## Job id / 日志路径 / 退出状态

- Slurm job id: NA，本次没有提交 Slurm。
- 本地诊断日志：终端输出；未通过 job script tee 到 `logs/`。
- 成功命令退出状态：0。

## 测试结果

- `py_compile` 通过。
- `bash -n jobs/experiments/run_t2_present_edema_pilot.sh` 通过。
- 正式 pilot 运行成功，生成 `results/experiments/t2_present_edema_20260619_131434/`。
- CSV 行数检查：
  - `myops_case_metadata.csv`: 221 行，含 header，覆盖 220 train cases。
  - `myops_validation_modality_metadata.csv`: 16 行，含 header，覆盖 15 raw validation cases。
  - `feature_baseline_case_metrics.csv`: 81 行，含 header，覆盖 80 complete cases。
  - `feature_baseline_threshold_grid.csv`: 5 行，含 header，覆盖 4 个粗网格配置。

## 主要结果

训练/feature baseline 选择：

- 没有启动 GPU training。原因是本任务要求只新增隔离 pilot，不修改主训练入口；当前仓库没有现成 complete-case edema expert 训练入口，`env_CARE` 中也未安装 MONAI。临时构造新的 nnU-Net complete-case Dataset/plan/training 会超出“快速 pilot”边界并引入较大工程面。
- 因此按 task 第 3 步允许的 fallback，执行了覆盖全部 80 个 complete cases 的 feature/routing baseline。

数据机制：

| group | cases | edema-positive | scar-positive | mean edema voxel fraction | T2 edema-vs-myo contrast |
| --- | ---: | ---: | ---: | ---: | ---: |
| `C0+LGE+T2` | 80 | 80 | 79 | 0.0040 | 0.9209 |
| `C0+LGE` | 24 | 0 | 18 | 0.0000 | NA |
| `LGE-only` | 116 | 0 | 115 | 0.0000 | NA |

Feature baseline selected config:

| threshold | prior iterations | min component mm3 | selected on | train Dice | train precision | train recall |
| ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 0.5 | 2 | 50 | fold0 complete train, 64 cases | 0.3223 | 0.3331 | 0.4225 |

Feature baseline metrics:

| split | cases | Dice | precision | recall | HD | HD95 | components |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fold0 complete train | 64 | 0.3223 | 0.3331 | 0.4225 | 36.0893 | 19.7387 | 15.0156 |
| fold0 complete val | 16 | 0.2910 | 0.2982 | 0.4643 | 38.6553 | 24.0819 | 15.3125 |
| all complete | 80 | 0.3160 | 0.3261 | 0.4308 | 36.6025 | 20.6073 | 15.0750 |
| all complete CenterB | 35 | 0.3711 | 0.4480 | 0.3639 | 29.2543 | 14.9910 | 11.9143 |
| all complete CenterC | 45 | 0.2732 | 0.2313 | 0.4829 | 42.3178 | 24.9755 | 17.5333 |

## 决策结果

- 值得把 T2-present expert/routing 作为下一步主线：是。
- 原因：训练标签机制显示 edema supervision 只存在于 complete/T2-present cases，而 validation raw input 是 complete 三模态；继续把 no-T2 cases 当作 dense edema-negative 会引入结构性错配。
- 简单规则 baseline 是否可直接推广：否。fold0 complete val Dice 只有 0.2910，HD95 24.0819，组件数仍高。
- 下一步应考虑：baseline-preserving complete-case T2 edema expert、missingness mask、late fusion、HeMIS/ModDrop-style 设计。
- CAA-Seg/AWSnet：仍可作为 bounded reference/read-only 或小 smoke，但不应替代当前更直接的 complete-case T2 expert路线。

## 失败信息

- `CARE-README.md` 不存在。
- 系统 `python` 缺少 `SimpleITK/numpy/scipy` 等依赖；已使用 `./envs/env_CARE/bin/python`。
- 初版脚本导入 `code.nnUNet` 失败，因为 `code/` 不是 package；已改为与既有转换脚本一致的 `sys.path` 注入 `code/nnUNet`。
- 默认细网格/中等网格耗时偏高；已改成可复跑的粗网格 pilot。该调整不影响全量 80 complete cases 覆盖，但限制了调参精细度。

## git diff 摘要

新增本任务文件：

- `scripts/experiments/t2_present_edema_pilot.py`
- `jobs/experiments/run_t2_present_edema_pilot.sh`
- `docs/notes/t2_present_edema_pilot_20260620.md`
- `results/20260620_t2_edema_pilot/result.md`
- `results/experiments/t2_present_edema_20260619_131434/`

工作树中还存在与本任务无关的 untracked 文件/目录，例如 `results/cinema_adapter/`、`scripts/external_adapters/`、`scripts/diagnostics/cinemyops_raw_structure_audit.py`、`jobs/experiments/run_cinema_adapter_pilot.sh`。本任务未修改这些文件。

## 需要人工批准的事项

- official validation upload：本任务不授权，未执行。
- 超过 8 小时 job：本任务不授权，未执行。
- 将 T2-present expert 纳入主训练 pipeline：本任务只给出 pilot 结论，需要新 task 授权。

## 下一步建议

建议新建一个单独 task：使用现有 nnU-Net501 representation 做 baseline-preserving complete-case edema expert 或 class-4 residual head，训练只使用 T2-present complete cases 的 edema dense supervision；no-T2 cases 仅用于 scar/anatomy 或缺模态 routing 约束，不作为 class-4 hard negative。
