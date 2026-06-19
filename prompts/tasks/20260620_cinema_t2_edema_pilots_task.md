---
task_id: "20260620_cinema_t2_edema_pilots"
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

# Task 20260620: CARE CineMA adapter pilot + T2-present edema expert pilot

## 目标

在不继续围绕旧 validation zip、LCC、MedNeXt 或旧 third_party wrapper 打转的前提下，执行两个数据机制驱动的改进动作：第一，建立并运行 CineMA 到 CARE CineMyoPS 的 anatomy adapter/pilot；第二，建立并运行 MyoPS T2-present edema expert/routing 的较大规模 pilot。每个训练或推理 job 的 walltime 不得超过 8 小时。

## 背景

开始前必须读取并遵守：

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- 本任务文件 `prompts/tasks/20260620_cinema_t2_edema_pilots_task.md`

还应读取这些背景材料，但不要把它们当作自动执行入口：

- `docs/notes/data_difficulty_and_resource_search_20260619.md`，若路径不存在，则搜索同名或相近的 `data_difficulty_and_resource_search_*.md`
- `baseline_report.md`
- `CARE-README.md`
- `env_nnunet.sh`
- 已有 `results/experiments/*_iteration_log.md`，若存在

上一轮结论需要先复核，而不是盲目照抄。当前待验证判断是：MyoPS train 具有强缺模态结构，约 80/220 为 `C0+LGE+T2` complete cases，24/220 为 `C0+LGE`，116/220 为 `LGE only`；edema 与 T2 presence 强绑定；validation/held-out 是 complete 三模态；CineMyoPS raw data 是 4D cine，而旧 Dataset502/pipeline 过度单帧化；旧 `LCC`、`MedNeXt`、MyoPS-Net zero-filled mapping channel、U-MyoPS Stage1->Stage2 bridge、CineMyoPS single-frame compact wrapper 暂时不应作为主线。

本轮不是只跑 3 到 5 个 case 的玩具 smoke test。计算资源可以积极使用，但必须受 8 小时单 job 限制约束。优先使用 `htzhulab`；只有按 `AGENTS.md` 检查队列后确认等待相对本轮预算明显过长，才使用 `a100-gpu` 或 `volta-gpu` fallback。Slurm 脚本必须按 `AGENTS.md` 的 header 和 timestamped log 风格写入日志。

## 允许动作

本任务显式授权以下动作：

- 读取与 CARE Myocardium、CineMyoPS、MyoPS、leaderboard task、数据结构、已有结果、环境和 Slurm job 相关的文件。
- 联网访问和下载本任务明确需要的外部公开资源，尤其是 `https://github.com/mathpluscode/CineMA` 及其公开 HuggingFace 权重；如果需要其他 cine SAX myocardium/LV 权重，只允许作为 CineMA 阻塞时的 fallback 查询。
- 在隔离目录新增外部 adapter、diagnostic 脚本、job script、README、csv/json/markdown 诊断结果。优先目录包括 `scripts/external_adapters/`、`scripts/diagnostics/`、`jobs/experiments/`、`results/diagnostics/`、`results/cinema_adapter/`、`results/experiments/`、`docs/notes/`；若仓库已有更合适规范，以仓库规范为准。
- 使用 GPU 运行推理、diagnostic 或较短训练/pilot。每个单 job 的 `--time` 或等价 walltime 上限为 8 小时。不要用超长训练替代设计判断。
- 在完成后写 `prompts/tasks/20260620_cinema_t2_edema_pilots_result.md`。

## 禁止动作

- 不要上传 validation，不要调用官方 submission，不要生成或覆盖 upload-ready zip。
- 不要删除数据、模型、旧结果、旧日志或已有 submission package。
- 不要修改主训练入口或旧 baseline 路径，除非只是新增独立文件且不会影响默认行为。
- 不要继续把 LCC calibration、MedNeXt、旧 validation zip forensic、MyoPS-Net zero-filled mapping channel、U-MyoPS bridge 修复、CineMyoPS single-frame compact wrapper 作为本轮主线。
- 不要把 `docs/notes/` 或 `docs/wiki/` 中未被本任务显式引用的内容当作新的执行任务。
- 不要把 hosted leaderboard 或 validation 分数当作本轮目标；本轮只做本地 pilot、adapter 和数据机制验证。

## 执行步骤

### 1. 规则与背景复核

先读取 `AGENTS.md` 和 `prompts/AGENT_RULES.md`，在最终 result 中复述与本轮相关的规则，至少包括：task/result 文件位置、frontmatter 权限、证据要求、GPU 分区优先级、8 小时单 job 限制、日志风格、禁止未授权上传/删除/昂贵命令。

然后读取上一轮数据困难报告，复核 MyoPS 模态组合、edema/T2 绑定、CineMyoPS 4D raw data 与旧单帧 pipeline mismatch。若报告文件不存在或数字与当前仓库统计冲突，以当前仓库只读统计为准，并在 result 中记录差异。

### 2. CineMA -> CARE CineMyoPS adapter/pilot

目标是判断 CineMA 或成熟 cine SAX anatomy 预训练资源是否能在 CARE CineMyoPS raw 4D cine 上稳定输出 myocardium/LV mask，并正确映射回 CARE 原始 NIfTI geometry。

请执行以下工作：

1. 获取或检查 CineMA 资源：确认代码、license、依赖、checkpoint/权重来源、inference example、输入 shape、输出 label 编码、是否支持 SAX myocardium/LV segmentation。若 GitHub 或 HuggingFace 下载失败，记录精确命令、错误信息和 fallback，不要伪造成功。
2. 检查 CARE CineMyoPS raw train/val 数据结构：case 数、frame 数、shape、spacing、affine/direction、label values、label 是否与单一参考 frame 或 4D 全帧相关。
3. 设计 frame 策略：如果 CineMA 只能接受单 timeframe SAX，不要只默认 middle frame。至少比较或说明 ED/middle/representative frame 的选择依据；若可行，对多个 frame 做 temporal subset 推理并聚合 anatomy mask。
4. 尽可能在 8 小时以内覆盖较大样本。如果 CineMA inference 很快，处理全部 64 个 CineMyoPS train cases，并尽量也处理 15 个 validation cases用于未提交诊断；如果全量不现实，至少处理不少于 20 个 train cases，且覆盖不同 shape、slice 数、spacing 和 frame 数。
5. 对有 GT 的 train cases，计算 class_1 myocardium Dice、HD95 或 HD；如果 CARE label 中 LV 可用，也计算 LV Dice 作为 sanity。记录每个 case 的非空情况、label values、voxel count、连通域数量、shape/spacing/affine round-trip 是否正确。
6. 如已有 Dataset502 nnU-Net class_1 prediction/metric 可读，可做本地对比；若不可读，不要阻塞 CineMA pilot，记录缺口。

输出应放在隔离目录，例如 `results/cinema_adapter/<timestamp>/` 或仓库已有实验目录。新增脚本和 job script 必须路径清晰，不能污染默认训练入口。

### 3. MyoPS T2-present edema expert/routing pilot

目标是判断 `myops_edema` 是否应从统一 zero-filled missing-channel 训练转向 T2-present complete-case expert/routing。

请执行以下工作：

1. 重建或读取 MyoPS metadata，列出 complete `C0+LGE+T2`、`C0+LGE`、`LGE only` case id、center、shape/spacing、label presence、edema/scar voxel fraction。
2. 以 complete cases 为核心，建立 T2-present edema expert/routing 的 pilot。edema 的正负监督只能来自 T2-present complete cases；no-T2 cases 不应被当成强 edema-negative 样本。
3. 若现有 nnU-Net、MONAI 或仓库 pipeline 能在 8 小时内构造并运行 complete-case edema fold0 或 official split pilot，请准备并启动一个有统计意义的 pilot，而不是只跑几个 case。优先使用全部 80 个 complete cases 中的训练部分，保留合理 holdout 或已有 fold。可以选择 2D 或轻量 3D 配置，但必须解释选择原因。
4. 若短训不现实，则完成覆盖全部 80 个 complete cases 的较充分 feature/routing baseline，例如 T2 robust-z + myocardium/pathology union prior + component filter，并报告 Dice/HD/precision/recall 或可解释 proxy。
5. 报告三类结果：数据机制结果、模型或规则结果、决策结果。数据机制结果包括 T2 lesion-vs-myocardium contrast、edema voxel fraction、component statistics、myocardium/pathology union prior coverage、按 center/modality group 的统计。模型或规则结果包括训练配置、输入通道、label mapping、fold/split、运行时间、GPU、loss、best checkpoint、local Dice/HD/HD95，或 feature baseline 的对应 proxy。决策结果包括是否值得把 T2-present expert 作为下一步主线、是否需要 missingness mask/modality dropout/late fusion/HeMIS/ModDrop-style 设计、是否仍需查 CAA-Seg/AWSnet。

输出应放在隔离目录，例如 `results/experiments/t2_present_edema_<timestamp>/`、`results/diagnostics/t2_present_edema_<timestamp>/` 或仓库已有实验目录。新增 job script 必须单 job 不超过 8 小时，并记录 job id 和日志路径。

## 预期产出

必须写入：

- `prompts/tasks/20260620_cinema_t2_edema_pilots_result.md`

建议写入或新增：

- CineMA adapter/diagnostic 脚本，路径自定但必须隔离。
- MyoPS T2-present edema diagnostic 或 pilot 脚本，路径自定但必须隔离。
- Slurm job script，若启动 GPU job。
- `docs/notes/cinema_and_t2_edema_pilot_20260620.md` 或同等命名报告。
- 对应 `results/diagnostics/`、`results/cinema_adapter/`、`results/experiments/` 下的 csv/json/markdown/log 输出。

最终 result 至少包含：

- 读取的规则和背景文件。
- 修改或新增的文件列表。
- 运行的命令、job id、日志路径、退出状态。
- CineMA 是否成功获取代码和权重，adapter 是否跑通，跑了多少 train/val cases，主要 Dice/HD/sanity 结果，输出路径。
- T2-present edema pilot 是否完成训练或较大规模诊断，覆盖了多少 complete cases，主要 local 结果，输出路径。
- 两个方向中哪个更值得继续投入。
- 是否仍需要继续找新的 paper/repo，还是可以进入较正式训练。
- 如果继续训练，建议的下一张 8 小时以内 task 是什么。
- git diff 摘要。

## 停止条件

- 缺少 `AGENTS.md` 或 `prompts/AGENT_RULES.md`，且无法确认权限边界。
- 需要外部上传、official validation submission、删除数据或修改高风险配置。
- 单个 job 预计超过 8 小时且无法拆分或降级。
- CineMA 下载、权重、依赖或 license 阻塞，且没有安全 fallback；此时写 result 请求下一张任务，而不是继续扩大范围。
- MyoPS complete-case metadata 或 label mapping 无法确认；此时停止训练，只写诊断和需要人工确认的问题。
- 命令失败且继续执行会扩大风险。

## 人工决策点

- 是否允许 official validation upload。本任务不授权。
- 是否允许超过 8 小时的训练。本任务不授权。
- 是否接受把 CineMA adapter 或 T2-present edema expert 纳入主训练 pipeline。本任务只允许隔离 pilot。
- 若需要非公开权重、账号、token 或外部数据，必须请求人工批准。
- 若两个方向都产生正向本地结果，下一步应由新的 task 决定是否扩展到更正式训练或 submission packaging。
