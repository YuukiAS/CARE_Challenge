---
task_key: "20260620_cinema_adapter_pilot"
project: "CARE-Myocardium"
status: "ready"
executor: "Codex"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: true
allow_external_upload: false
requires_human_approval: false
max_single_job_walltime: "08:00:00"
---

# Task 20260620-A: CineMA -> CARE CineMyoPS adapter pilot

## 目标

建立并运行一个隔离的 CineMA 到 CARE CineMyoPS anatomy adapter/pilot，判断公开 cine SAX myocardium/LV 预训练资源能否在 CARE raw 4D cine 上稳定输出 myocardium/LV mask，并正确映射回 CARE 原始 NIfTI geometry。不要围绕旧 validation zip、LCC、MedNeXt、旧 CineMyoPS single-frame compact wrapper 或 hosted submission 做工作。

## 背景

开始前必须读取并遵守：

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- 本任务文件 `prompts/tasks/20260620_cinema_adapter_pilot.md`

还应读取这些背景材料，但不要把它们当作自动执行入口：

- `docs/notes/data_difficulty_and_resource_search_20260619.md`，若路径不存在，则搜索相近的 `data_difficulty_and_resource_search_*.md`
- `CARE-README.md`
- `env_nnunet.sh`
- 与 CineMyoPS / Dataset502 / CineMA 相关的已有脚本、日志、结果目录

本任务假设待验证的核心结论是：CARE CineMyoPS raw data 是 4D cine，当前旧 pipeline 过度单帧化；`myocardium_cinemyops` 更需要稳定 anatomy prior，而不是继续修旧 LCC 或 scar sanity 后处理。若当前仓库统计与这个判断冲突，以当前仓库统计为准并记录差异。

## 允许动作

- 读取与 CARE CineMyoPS、Dataset502、CineMA、raw NIfTI、label mapping、环境和 Slurm 相关的文件。
- 联网访问和下载 `https://github.com/mathpluscode/CineMA` 及其公开 HuggingFace 权重。若 CineMA 阻塞，允许只查询一个最接近的公开 cine SAX myocardium/LV segmentation fallback，但不要扩大成大规模文献调研。
- 在隔离目录新增外部 adapter、diagnostic 脚本、job script、README、csv/json/markdown 诊断结果。优先目录包括 `scripts/external_adapters/`、`scripts/diagnostics/`、`jobs/experiments/`、`results/cinema_adapter/`、`results/diagnostics/`、`docs/notes/`。
- 使用 GPU 运行 inference 或轻量 postprocess。单个 Slurm job walltime 不得超过 8 小时，优先 `htzhulab`，fallback 必须按 `AGENTS.md` 规则检查队列后使用。
- 完成后写 `results/20260620_cinema_adapter_pilot/result.md`。

## 禁止动作

- 不要上传 validation，不要生成或覆盖 upload-ready zip。
- 不要删除数据、模型、旧结果、旧日志或已有 submission package。
- 不要修改主训练入口或旧 baseline 默认路径；只允许新增隔离 adapter/pilot 文件。
- 不要继续把 LCC calibration、MedNeXt、旧 validation zip forensic、CineMyoPS single-frame compact wrapper 作为主线。
- 不要把 hosted leaderboard 分数当作本任务目标；本任务只做本地 anatomy adapter 和 diagnostic。

## 执行步骤

### 1. 规则与数据复核

读取 `AGENTS.md` 和 `prompts/AGENT_RULES.md`，在 result 中复述与本任务相关的规则，至少包括 task/result 路径、frontmatter 权限、证据要求、GPU 分区优先级、8 小时单 job 限制、日志风格、禁止未授权上传/删除/昂贵命令。

读取上一轮数据困难报告，并用当前仓库只读统计复核 CineMyoPS raw train/val 数据结构：case 数、frame 数、shape、spacing、affine/direction、label values、label 是否与单一参考 frame 或 4D 全帧相关。

### 2. CineMA 资源核验

获取或检查 CineMA 资源，确认：代码路径、license、依赖、checkpoint/权重来源、inference example、输入 shape、输出 label 编码、是否支持 SAX myocardium/LV segmentation。若 GitHub 或 HuggingFace 下载失败，记录精确命令、错误信息、退出状态和可行 fallback，不要伪造成功。

### 3. CARE adapter 设计与运行

设计 frame 和 geometry 策略。如果 CineMA 只能接受单 timeframe SAX，不要只默认 middle frame；至少比较或明确说明 ED、middle、representative frame 的选择依据。若可行，对多个 frame 做 temporal subset 推理并聚合 anatomy mask。

本任务不应只跑 3 到 5 个 case。如果 CineMA inference 很快，处理全部 64 个 CineMyoPS train cases，并尽量处理 15 个 validation cases用于未提交诊断。如果全量不现实，至少处理不少于 20 个 train cases，且覆盖不同 shape、slice 数、spacing 和 frame 数。若需要 Slurm job，写入 `jobs/experiments/` 下的独立脚本，单 job `--time` 不超过 8 小时，并按 `AGENTS.md` 写 timestamped log。

### 4. 本地评估与报告

对有 GT 的 train cases，计算 class_1 myocardium Dice、HD95 或 HD；如果 CARE label 中 LV 可用，也计算 LV Dice 作为 sanity。记录每个 case 的非空情况、label values、voxel count、连通域数量、shape/spacing/affine round-trip 是否正确。若已有 Dataset502 nnU-Net class_1 prediction/metric 可读，可做本地对比；若不可读，不要阻塞 CineMA pilot，记录缺口。

## 预期产出

必须写入：

- `results/20260620_cinema_adapter_pilot/result.md`
- `results/20260620_cinema_adapter_pilot/MANIFEST.md`

建议写入：

- `docs/notes/cinema_adapter_pilot_20260620.md`
- `results/cinema_adapter/<timestamp>/` 下的预测、metrics、manifest、日志或诊断输出；同时在 `results/20260620_cinema_adapter_pilot/MANIFEST.md` 中索引这些路径
- 新增的 adapter 脚本和 Slurm job script，路径需在 result 中列出

最终 result 至少包含：读取文件、修改文件、运行命令、job id、日志路径、退出状态、CineMA 是否成功获取代码和权重、跑了多少 train/val cases、主要 Dice/HD/sanity、输出路径、失败信息、git diff 摘要、下一步建议。

## 停止条件

- 缺少 `AGENTS.md` 或 `prompts/AGENT_RULES.md`，且无法确认权限边界。
- 需要 external upload、official validation submission、删除数据或修改高风险配置。
- 单个 job 预计超过 8 小时且无法拆分或降级。
- CineMA 下载、权重、依赖或 license 阻塞，且没有安全 fallback；此时写 result 请求下一张任务。
- 命令失败且继续执行会扩大风险。

## 人工决策点

- 是否允许 official validation upload。本任务不授权。
- 是否允许超过 8 小时的 job。本任务不授权。
- 是否接受把 CineMA adapter 纳入主训练 pipeline。本任务只允许隔离 pilot。
- 若需要非公开权重、账号、token 或外部数据，必须请求人工批准。
