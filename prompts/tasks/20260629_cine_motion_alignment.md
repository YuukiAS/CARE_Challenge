---
task_key: "20260629_cine_motion_alignment"
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
max_parallel_gpu_jobs: 3
---

# Task 20260629 Cine Motion Alignment

## 目标

上一轮 Cine registration 只验证了平移级 baseline，结果几乎没有增益。本任务补做真正的 Cine reference-frame motion alignment：在 59 个 geometry-safe cases 上比较 ANTs/SimpleITK 非刚性配准、光流或运动描述符、以及轻量 VoxelMorph-style 无监督方案，判断是否能把非参考帧的 anatomy/texture/motion 信息可靠带回 reference frame。

## 必读材料

读取本任务文件、`AGENTS.md`、`prompts/AGENT_RULES.md`、`results/20260628_cine_register/selection.md`、`results/20260628_cine_register/metrics_summary.md`、`results/20260626_cine_temporal/result.md`、`results/20260625_cine_geometry/safe_cases.csv`、`results/20260620_cinema_adapter_pilot/result.md`、Result5 或等价文本、Cine raw 4D data、CineMA adapter outputs 和 Dataset502/Task026 evaluator。

## 允许动作

允许安装或复用公开的配准/光流工具，但必须记录来源、版本、安装命令和失败日志。允许最多三个并行 CPU/GPU jobs，每个不超过 8 小时。若外部工具不可用，必须至少完成 SimpleITK BSpline/Demons 或 first-party motion descriptor baseline。

## 禁止动作

不要 validation submission、upload package、external upload。不要使用不可审计的外部权重。不要把非参考帧直接和 reference pathology GT 计算 Dice 当作成功。不要让 5 个 mismatch cases 阻塞 59 个 safe cases。不要覆盖旧 CineMA/registration outputs。

## 候选路线

至少完成两类：第一，classical deformable registration，例如 ANTs SyN 或 SimpleITK BSpline/Demons；第二，dense optical-flow 或 motion descriptor，例如 frame difference、motion magnitude、strain-like scalar map；第三，若可行，轻量 VoxelMorph-style unsupervised registration。

## 评估

报告 safe case 数、成功率、运行时间、warp smoothness、folding/Jacobian proxy、frame-to-reference similarity、CineMA myocardium/LV anatomy consistency、motion magnitude distribution 和 failure cases。必须与 no-warp reference context 和 previous translation baseline 对照。

## 决策门

写 `results/20260629_cine_motion_alignment/selection.md`，状态只能是 `SELECT_MOTION_ALIGNMENT`、`SELECT_MOTION_DESCRIPTOR_ONLY`、`SELECT_REFERENCE_ONLY`、`REVISE_ALIGNMENT_AND_REPEAT`、`STOP_ALIGNMENT_BUG`。选择 motion alignment 要求 anatomy consistency 或 motion alignment 相比 translation/no-warp 有明确正信号，且运行时间和失败率可接受。

## 预期产出

必须写 `results/20260629_cine_motion_alignment/result.md`、`MANIFEST.md`、`selection.md`、`resource_audit.md`、`safe_cases_used.csv`、`registration_metrics.csv`、`warp_sanity.csv`、`motion_descriptor_summary.csv`、`failure_interpretation.md`，并索引 scripts、logs、commands、outputs 和 visual sanity samples。

## 停止条件

只有 safe subset reference geometry 无法复现、所有候选都失败且无 first-party fallback、warp/inverse mapping 不安全且无法记录、或单 job 超过 8 小时，才停止。单个候选失败不能停止整个任务。
