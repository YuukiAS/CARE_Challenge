---
task_id: "20260620_t2_present_edema_pilot"
project: "CARE-Myocardium"
status: "ready"
executor: "Codex"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
max_single_job_walltime: "08:00:00"
---

# Task 20260620-B: MyoPS T2-present edema expert/routing pilot

## 目标

建立并运行一个较大规模 MyoPS T2-present edema expert/routing pilot，判断 `myops_edema` 是否应从统一 zero-filled missing-channel 训练转向 complete-case T2-aware expert/routing。不要围绕旧 validation zip、LCC、MedNeXt、MyoPS-Net zero-filled mapping channel、U-MyoPS bridge 或 hosted submission 做工作。

## 背景

开始前必须读取并遵守：

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- 本任务文件 `prompts/tasks/20260620_t2_present_edema_pilot_task.md`

还应读取这些背景材料，但不要把它们当作自动执行入口：

- `docs/notes/data_difficulty_and_resource_search_20260619.md`，若路径不存在，则搜索相近的 `data_difficulty_and_resource_search_*.md`
- `CARE-README.md`
- `env_nnunet.sh`
- 与 MyoPS / Dataset501 / edema / nnU-Net / MONAI 相关的已有脚本、日志、结果目录

本任务假设待验证的核心结论是：MyoPS train 具有强缺模态结构，约 80/220 为 `C0+LGE+T2` complete cases，24/220 为 `C0+LGE`，116/220 为 `LGE only`；edema 与 T2 presence 强绑定；validation/held-out 是 complete 三模态。若当前仓库统计与这些数字冲突，以当前仓库统计为准并记录差异。

## 允许动作

- 读取与 CARE MyoPS、Dataset501、raw NIfTI、label mapping、已有 nnU-Net/MONAI pipeline、环境和 Slurm 相关的文件。
- 在隔离目录新增 metadata builder、diagnostic 脚本、training/pilot config、job script、README、csv/json/markdown 结果。优先目录包括 `scripts/diagnostics/`、`scripts/experiments/`、`jobs/experiments/`、`results/diagnostics/`、`results/experiments/`、`docs/notes/`。
- 使用 GPU 运行 complete-case edema fold0、reasonable split pilot、或充分的 feature/routing baseline。单个 Slurm job walltime 不得超过 8 小时，优先 `htzhulab`，fallback 必须按 `AGENTS.md` 规则检查队列后使用。
- 完成后写 `prompts/tasks/20260620_t2_present_edema_pilot_result.md`。

## 禁止动作

- 不要联网；本任务不需要外部资源。
- 不要上传 validation，不要生成或覆盖 upload-ready zip。
- 不要删除数据、模型、旧结果、旧日志或已有 submission package。
- 不要修改主训练入口或旧 baseline 默认路径；只允许新增隔离 pilot 文件或配置。
- 不要继续把 LCC calibration、MedNeXt、旧 validation zip forensic、MyoPS-Net zero-filled mapping channel、U-MyoPS bridge 修复作为主线。
- 不要把 no-T2 cases 当作强 edema-negative 样本训练 T2-present edema expert。
- 不要把 hosted leaderboard 分数当作本任务目标；本任务只做本地 pilot 和数据机制验证。

## 执行步骤

### 1. 规则与数据复核

读取 `AGENTS.md` 和 `prompts/AGENT_RULES.md`，在 result 中复述与本任务相关的规则，至少包括 task/result 路径、frontmatter 权限、证据要求、GPU 分区优先级、8 小时单 job 限制、日志风格、禁止未授权上传/删除/昂贵命令。

读取上一轮数据困难报告，并用当前仓库只读统计复核 MyoPS train/val 数据结构：complete `C0+LGE+T2`、`C0+LGE`、`LGE only` case id、center、shape/spacing、label presence、edema/scar voxel fraction。

### 2. T2-present edema 数据机制诊断

覆盖全部 complete cases，而不是只跑几个示例。计算并报告：T2 lesion-vs-myocardium contrast、edema voxel fraction、component statistics、myocardium/pathology union prior coverage、按 center/modality group 的统计、complete cases 与 no-T2 cases 的 label 机制差异。edema 的正负监督只能来自 T2-present complete cases；no-T2 cases 只能用于 scar、anatomy 或缺模态分析，不得作为强 edema-negative 训练样本。

### 3. Expert/routing pilot

若现有 nnU-Net、MONAI 或仓库 pipeline 能在 8 小时内构造并运行 complete-case edema fold0 或 reasonable split pilot，请准备并启动一个有统计意义的 pilot。优先使用全部 80 个 complete cases 中的训练部分，保留合理 holdout 或已有 fold。可以选择 2D 或轻量 3D 配置，但必须解释选择原因。训练目标是 edema expert/routing feasibility，不是最终 leaderboard。

若短训不现实，则完成覆盖全部 complete cases 的 feature/routing baseline，例如 T2 robust-z + myocardium/pathology union prior + component filter，并报告 Dice/HD/HD95/precision/recall 或可解释 proxy。不要退化为 3-5 case 的 toy smoke。

### 4. 决策报告

报告三类结果。第一类是数据机制结果。第二类是模型或规则结果，包括训练配置、输入通道、label mapping、fold/split、运行时间、GPU、loss、best checkpoint、local Dice/HD/HD95，或 feature baseline 的对应 proxy。第三类是决策结果：是否值得把 T2-present expert 作为下一步主线；是否需要 missingness mask、modality dropout、late fusion、HeMIS/ModDrop-style 设计；是否仍需查 CAA-Seg/AWSnet；是否可以进入更正式训练。

## 预期产出

必须写入：

- `prompts/tasks/20260620_t2_present_edema_pilot_result.md`

建议写入：

- `docs/notes/t2_present_edema_pilot_20260620.md`
- `results/diagnostics/t2_present_edema_<timestamp>/` 或 `results/experiments/t2_present_edema_<timestamp>/` 下的 metadata、metrics、manifest、日志或诊断输出
- 新增 diagnostic/training/pilot 脚本和 Slurm job script，路径需在 result 中列出

最终 result 至少包含：读取文件、修改文件、运行命令、job id、日志路径、退出状态、覆盖了多少 complete cases、是否完成训练或较大规模诊断、主要 local Dice/HD/HD95 或 proxy、输出路径、失败信息、git diff 摘要、下一步建议。

## 停止条件

- 缺少 `AGENTS.md` 或 `prompts/AGENT_RULES.md`，且无法确认权限边界。
- 需要联网、external upload、official validation submission、删除数据或修改高风险配置。
- 单个 job 预计超过 8 小时且无法拆分或降级。
- MyoPS complete-case metadata 或 label mapping 无法确认；此时停止训练，只写诊断和需要人工确认的问题。
- 命令失败且继续执行会扩大风险。

## 人工决策点

- 是否允许 official validation upload。本任务不授权。
- 是否允许超过 8 小时的 job。本任务不授权。
- 是否接受把 T2-present edema expert 纳入主训练 pipeline。本任务只允许隔离 pilot。
- 若 pilot 产生正向本地结果，下一步应由新的 task 决定是否扩展到更正式训练或 submission packaging。
