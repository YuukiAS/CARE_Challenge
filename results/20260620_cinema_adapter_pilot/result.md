# Result 20260620 Cinema Adapter Pilot

status: completed

## 迁移说明

本文件由 legacy 路径 `prompts/tasks/20260620_cinema_adapter_pilot_result.md` 迁移而来。当前 task/result/review 对应关系为：

- task: `prompts/tasks/20260620_cinema_adapter_pilot.md`
- result: `results/20260620_cinema_adapter_pilot/result.md`
- review: `results/20260620_cinema_adapter_pilot/review.md`
- manifest: `results/20260620_cinema_adapter_pilot/MANIFEST.md`

## 执行摘要

已按 task 建立并运行隔离 CineMA -> CARE CineMyoPS anatomy adapter pilot。没有上传 validation，没有生成或覆盖 upload-ready zip，没有修改主训练入口或旧 baseline 默认路径。

核心结果：

- CineMA GitHub 代码成功获取到 `results/cinema_adapter/external/CineMA`，commit `c10daa1d93f0ea28d8b9ad9206b0f673d25805c1`。
- CineMA license 为 MIT；SAX segmentation 示例确认输入为 1 个 timeframe，输出 `1=RV, 2=myocardium, 3=LV`。
- HuggingFace ACDC SAX seed0 权重成功下载并加载。
- Slurm job `55524633` 在 `htzhulab` / `g1807htzh01` 完成，日志为 `logs/CineMAAdapter_55524633_20260619_131229.log`。
- 全量处理 64 个 train cases 和 15 个 validation cases；共 234 个 selected frames。
- train frame0/ED：myocardium Dice mean/median `0.5723/0.6861`，LV Dice mean/median `0.7779/0.9092`。
- train all selected frames：myocardium Dice mean/median `0.4655/0.4866`，LV Dice mean/median `0.6775/0.7288`。
- validation 无 GT，本任务只记录非空 anatomy predictions，不做 hosted/submission 解释。

## 相关规则复述

- 默认 task 入口为 `prompts/tasks/20260620_cinema_adapter_pilot.md`，执行报告写到 `results/20260620_cinema_adapter_pilot/result.md`，review 写到 `results/20260620_cinema_adapter_pilot/review.md`。
- frontmatter 授权：`allow_code_change: true`、`allow_shell_command: true`、`allow_network: true`、`allow_external_upload: false`、`requires_human_approval: false`、`max_single_job_walltime: 08:00:00`。
- 证据需来自文件路径、命令退出状态、日志、metrics 和明确错误信息。
- GPU job 默认优先 `htzhulab`；单 job walltime 不超过 8 小时；日志使用 timestamped tee 风格。
- 禁止未授权上传、删除数据、长时间/高资源扩大执行、修改高风险配置、继续旧 validation zip/LCC/MedNeXt/旧 single-frame wrapper 主线。

## 读取文件

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/tasks/20260620_cinema_adapter_pilot.md`
- `docs/notes/data_difficulty_and_resource_search_20260619.md`
- `README.md`（task 指定的 `CARE-README.md` 不存在）
- `env_nnunet.sh`
- `code/CineMyoPS/prepare_task025_from_care.py`
- `code/CineMyoPS/prepare_task026_cine_4d.py`
- `data/nnUNet/nnUNet_raw/Dataset502_CARECineMyoPS/dataset.json`
- `results/metrics/unified/CineMyoPS/aggregate.json`
- `results/metrics/unified/CineMyoPS/aggregate.md`
- `results/cinema_adapter/external/CineMA/README.md`
- `results/cinema_adapter/external/CineMA/LICENSE`
- `results/cinema_adapter/external/CineMA/pyproject.toml`
- `results/cinema_adapter/external/CineMA/cinema/examples/inference/segmentation_sax.py`

## 修改文件

新增：

- `scripts/diagnostics/cinemyops_raw_structure_audit.py`
- `scripts/external_adapters/cinema_care_adapter.py`
- `jobs/experiments/run_cinema_adapter_pilot.sh`
- `docs/notes/cinema_adapter_pilot_20260620.md`
- `results/20260620_cinema_adapter_pilot/result.md`

新增结果目录：

- `results/diagnostics/cinemyops_raw_structure_audit_20260620/`
- `results/cinema_adapter/external/CineMA/`
- `results/cinema_adapter/python_deps/`
- `results/cinema_adapter/metadata_check_20260620/`
- `results/cinema_adapter/smoke_cpu_1case_20260620/`
- `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/`
- `results/20260620_cinema_adapter_pilot/MANIFEST.md`
- `results/20260620_cinema_adapter_pilot/review.md`

注意：当前工作树还出现了 `t2_present_edema` 相关未跟踪文件/目录（例如 `docs/notes/t2_present_edema_pilot_20260620.md`、`jobs/experiments/run_t2_present_edema_pilot.sh`、`scripts/experiments/`、`results/experiments/t2_present_edema_20260619_131434/`）。这些不是本 task 创建或修改的对象，本次未处理。

## 运行命令

- `sed -n ... AGENTS.md prompts/AGENT_RULES.md prompts/tasks/20260620_cinema_adapter_pilot.md`
- `rg --files | rg '(...CineMyoPS|Dataset502|CineMA...)'`
- `git clone --depth 1 https://github.com/mathpluscode/CineMA.git results/cinema_adapter/external/CineMA`，退出码 0。
- `./envs/env_CARE/bin/python -m pip install --target results/cinema_adapter/python_deps --no-deps monai==1.5.2`，sandbox DNS 失败后经 escalated 网络权限成功，退出码 0。
- `./envs/env_CARE/bin/python scripts/diagnostics/cinemyops_raw_structure_audit.py --output-dir results/diagnostics/cinemyops_raw_structure_audit_20260620`，退出码 0。
- `PYTHONPATH=results/cinema_adapter/python_deps:results/cinema_adapter/external/CineMA ./envs/env_CARE/bin/python scripts/external_adapters/cinema_care_adapter.py --metadata-only --output-dir results/cinema_adapter/metadata_check_20260620 --max-train-cases 20 --max-val-cases 15`，初次因 Path JSON 序列化 bug 失败；修复后退出码 0。
- `PYTHONPATH=... ./envs/env_CARE/bin/python scripts/external_adapters/cinema_care_adapter.py --output-dir results/cinema_adapter/smoke_cpu_1case_20260620 --max-train-cases 1 --max-val-cases 0 --device cpu --trained-dataset acdc --seed 0`，sandbox HuggingFace DNS 失败；escalated 后权重下载和模型加载成功，但暴露固定输入尺寸错误。
- 修复 adapter 中 `256/320 -> 192x192x16` 固定输入尺寸处理后，CPU smoke 太慢，已中止，改用 GPU job。
- `squeue -p htzhulab -u "$USER"`，sandbox socket 权限失败；escalated 后成功，显示当时无本人 htzhulab job。
- `sinfo -o '%P|%a|%l|%D|%t|%G|%N'`，sandbox socket 权限失败；escalated 后成功。`sinfo` 不列 `htzhulab`，但 `squeue -p htzhulab` 可查询。
- `bash -n jobs/experiments/run_cinema_adapter_pilot.sh`，退出码 0。
- `sbatch jobs/experiments/run_cinema_adapter_pilot.sh`，sandbox socket 权限失败；escalated 后提交成功：`Submitted batch job 55524633`。
- `./envs/env_CARE/bin/python -m py_compile scripts/diagnostics/cinemyops_raw_structure_audit.py scripts/external_adapters/cinema_care_adapter.py`，退出码 0。

## 数据复核结果

输出：`results/diagnostics/cinemyops_raw_structure_audit_20260620/summary.json` 和 `summary.md`。

关键统计：

- CineMyoPS train cases: `64`
- CineMyoPS validation cases: `15`
- train frame counts: `64/64` 为 30 frames
- validation frame counts: `14` cases 为 30 frames，`1` case 为 50 frames
- train direction unique: `64`
- validation direction unique: `6`
- raw train label values case presence: `0:64, 200:64, 500:64, 2221:63`
- train labels match a single 3D cine frame geometry: `64/64`
- Dataset502 raw: `64 imagesTr`, `64 labelsTr`
- Dataset502 description: `CARE CineMyoPS_train (single Cine frame, middle time by default)`

结论：当前仓库统计支持 task 假设：raw CineMyoPS 是 4D cine，Dataset502/旧 pipeline 是单帧化数据，不应继续把旧 single-frame wrapper 当成本 task 主线。

## CineMA 资源核验

- 代码路径：`results/cinema_adapter/external/CineMA`
- commit: `c10daa1d93f0ea28d8b9ad9206b0f673d25805c1`
- GitHub: `https://github.com/mathpluscode/CineMA`
- license: MIT
- 依赖：CineMA 需要 MONAI；本地 `env_CARE` 缺失，已隔离安装 `monai==1.5.2` 到 `results/cinema_adapter/python_deps/`
- inference example: `cinema/examples/inference/segmentation_sax.py`
- input shape: ACDC SAX checkpoint 需要固定 `192x192x16`
- output label encoding: `1=RV`, `2=myocardium`, `3=LV`
- HuggingFace weights: `mathpluscode/CineMA`, `finetuned/segmentation/acdc_sax/acdc_sax_0.safetensors`
- 权重状态：已成功下载到 HuggingFace cache 并加载。

## Adapter 设计

`scripts/external_adapters/cinema_care_adapter.py` 当前策略：

- 对每个 raw 4D Cine case 选择 frame 0、middle frame、representative frame；representative frame 是与 temporal mean 平均绝对差最大的 frame。
- 每个 frame 先转成 CineMA 期望的 `(x, y, z)`，做 min-max intensity scaling。
- 对 CARE 原 frame 做中心 crop/pad 到 `192x192x16`，适配 ACDC SAX checkpoint。
- 模型预测后将 mask 反投回原始 frame geometry，crop/pad 外区域补 0，并用原 frame 的 SimpleITK metadata 写 NIfTI。
- CARE raw label 映射为 compact：`200->1 myocardium`，`500->2 LV`，`2221->3 scar`。
- train 计算 myocardium/LV Dice 和 HD95；validation 只记录非空预测和 label counts。

## 测试结果

Slurm run:

- job id: `55524633`
- log: `logs/CineMAAdapter_55524633_20260619_131229.log`
- output: `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/`
- runtime from adapter: `144.341` seconds
- rows: `234`
- train cases: `64`
- validation cases: `15`
- predictions written: `234`

Train all selected frames:

| metric | mean | median |
| --- | ---: | ---: |
| myocardium Dice | 0.4655 | 0.4866 |
| LV Dice | 0.6775 | 0.7288 |
| myocardium HD95 | 12.1390 | 7.9567 |
| LV HD95 | 12.3675 | 9.1264 |

Train frame 0 only:

| metric | mean | median |
| --- | ---: | ---: |
| myocardium Dice | 0.5723 | 0.6861 |
| LV Dice | 0.7779 | 0.9092 |
| myocardium HD95 | 11.0684 | 6.0000 |
| LV HD95 | 10.7595 | 6.0000 |

Train non-frame-0 selected frames:

| metric | mean | median |
| --- | ---: | ---: |
| myocardium Dice | 0.4108 | 0.4204 |
| LV Dice | 0.6261 | 0.6676 |
| myocardium HD95 | 12.6871 | 8.8991 |
| LV HD95 | 13.1978 | 10.9729 |

Existing Dataset502 comparison:

- `results/metrics/unified/CineMyoPS/aggregate.json` 可读，但只包含 `folds: 1` 的聚合记录。
- 该文件中 `class_1 mean=0.0003976`、`class_2 mean=0.3091`、`class_3 mean=0.00162`、`foreground_mean=0.1037`。
- 因为不是完整 5-fold local baseline summary，只作为弱参照，不写成完整模型性能结论。

## 失败信息与修复

- `CARE-README.md` 不存在；已读取根目录 `README.md` 并在本 result 记录该缺口。
- sandbox 内 pip / HuggingFace / Slurm socket 分别出现 DNS 或 `Operation not permitted`，均按权限规则用 escalated 命令完成必要步骤。
- adapter 初版 metadata dry run 因 `PosixPath` 无法 JSON 序列化失败；已加入 `jsonable()` 修复。
- adapter 初版直接送入 256/320 in-plane frame，CineMA ACDC checkpoint 报 fixed patch grid shape error：`shape '[1, 768, 12, 12, 16]' is invalid`；已改为中心 crop/pad 到 `192x192x16` 再反投回原 geometry。
- CPU smoke 推理太慢；中止后用 8 小时内 `htzhulab` GPU job 完成全量 pilot。

## git diff 摘要

`git diff --stat` 对 tracked files 为空，因为本 task 只新增未跟踪文件/目录。

本 task 新增的主要未跟踪路径：

- `scripts/diagnostics/cinemyops_raw_structure_audit.py`
- `scripts/external_adapters/cinema_care_adapter.py`
- `jobs/experiments/run_cinema_adapter_pilot.sh`
- `docs/notes/cinema_adapter_pilot_20260620.md`
- `results/20260620_cinema_adapter_pilot/result.md`
- `results/diagnostics/cinemyops_raw_structure_audit_20260620/`
- `results/cinema_adapter/`

工作树同时存在非本 task 创建的未跟踪 `t2_present_edema` 相关文件/目录，未纳入本次 diff 结论。

## 需要人工批准的事项

- official validation upload：本 task 未授权，未执行。
- 超过 8 小时 job：未需要，未请求。
- 将 CineMA adapter 纳入主训练 pipeline：本 task 只允许隔离 pilot，未执行。
- 非公开权重、账号、token 或外部数据：未使用。

## 下一步建议

1. 保持隔离 adapter，先把中心 crop/pad 改成 geometry-aware foreground/heart crop，重点修 center_beta 弱例。
2. 在没有证明 CARE label 对应全时相之前，frame 0/ED 应作为第一监督比较目标；不要把 all-frame Dice 当最终 supervised 结论。
3. 用同一 adapter 跑 CineMA `mnms` 和 `mnms2` SAX checkpoints，比 ACDC seed0 更全面地判断 domain robustness。
4. 若 anatomy prior 继续稳定，只把 myocardium/LV mask 作为独立 prior candidate 输出，不直接改主 training pipeline 或 validation packaging。
