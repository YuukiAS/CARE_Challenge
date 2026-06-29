---
task_key: "20260629_cine_motion_pathology"
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

# Task 20260629 Cine Motion Pathology

## 目标

`20260628_cine_register` 显示 simple translation registration 稳定但几乎没有 anatomy consistency 增益，selection 是 `SELECT_MOTION_DESCRIPTOR_ONLY`。下一步不要继续把大量时间耗在无收益的 registration baseline 上，也不要回到单帧 wrapper。本任务将 CineMyoPS 次线推进为 motion-descriptor/pathology preflight：在 59 个 geometry-safe cases 上构建 motion-like descriptors、frame-difference/strain-like maps、reference anatomy prior 和 lightweight temporal pathology/anatomy model，判断 motion descriptors 是否能给 myocardium_cinemyops 或 scar sanity 带来正信号。

## 必读材料

必须读取 `AGENTS.md`、`prompts/AGENT_RULES.md`、本任务文件、`results/20260628_cine_register/selection.md`、`results/20260628_cine_register/metrics_summary.md`、`results/20260626_cine_temporal/result.md`、`results/20260626_cine_temporal/failure_interpretation.md`、`results/20260625_cine_geometry/safe_cases.csv`、`results/20260620_cinema_adapter_pilot/result.md`、Result5 或等价文本、Cine raw 4D data、CineMA/CorSeg adapter outputs、Dataset502/Task026 evaluator。

当前事实：reference control 有一定 anatomy 基线；unregistered keyframe context 没有正信号；simple translation registration 几乎不改变 anatomy consistency；因此下一步应把 non-reference frames 转成 motion descriptors 或 weakly aligned context，而不是继续直接堆未配准图像。

## 允许动作

允许联网安装或 clone 轻量 optical-flow/motion descriptor 工具，但必须记录 license、version、install logs 和是否可用于 challenge。允许使用 SimpleITK、OpenCV、scikit-image、torch-based optical flow、VoxelMorph architecture preflight、StrainNet public code/weights若许可清楚。允许最多三个并行 CPU/GPU jobs，每个不超过八小时。允许新增 first-party cine dataset、motion descriptor generator、temporal model、reporting 和 jobs。

## 禁止动作

不要 validation submission、upload package、external upload。不要下载需要账号、许可不清或非公开的权重。不要把 non-reference frame 直接与 reference GT 算 Dice 当作 temporal success。不要让 5 个 mismatch cases 阻塞 59 个 safe cases。不要把 frozen anatomy prior 伪装成 scar model。不要覆盖旧 CineMA/registration outputs。

## Variants

至少运行三条路线中的两条，资源允许则三条都运行。

第一条是 `frame_difference_motion_descriptor`。基于 selected key frames 与 reference frame生成 intensity difference、absolute difference、local gradient difference、cycle summary descriptors，并输入 reference-frame anatomy/pathology refiner。目标是低风险验证 motion-like signal 是否有任何本地 proxy 增益。

第二条是 `optical_flow_descriptor`。使用轻量 2D/3D optical flow 或 displacement proxy，生成 motion magnitude、direction summary、strain-like scalar map。若安装失败，记录并继续第一/第三条。目标是更接近 CineMyoPS/MTI-MyoScarSeg 的 motion cue。

第三条是 `anatomy_motion_teacher_refiner`。使用 CineMA/CorSeg reference anatomy prior + motion descriptor，训练 lightweight temporal refiner，仅在 geometry-safe cases 上评估 myocardium/LV proxy 与 scar sanity。目标是判断 anatomy-motion是否能优于 reference-only control。

## 评估

必须报告 class_1 myocardium、class_2 LV、class_3 scar sanity 的 Dice、HD、HD95、component count、volume ratio、empty rate；报告 motion descriptor statistics、frame selection、reference dominance、per-center performance、safe/mismatch status、runtime、install/resource audit。必须与 reference control 和 previous temporal retrieval 对照。不要把 local proxy 直接称为 hosted `myocardium_cinemyops`。

## 决策门

写 `results/20260629_cine_motion_pathology/selection.md`，状态只能是 `SELECT_MOTION_DESCRIPTOR_ROUTE`、`SELECT_REFERENCE_CONTROL_ONLY`、`REVISE_CINE_MOTION`、`STOP_CINE_NO_SIGNAL`、`STOP_LICENSE_OR_INSTALL_BLOCKER`。选择 motion route 要求至少在 myocardium/LV proxy 或 scar sanity 上有正信号，HD/component 不恶化，并且不是由 label/geometry错误造成。

## 预期产出

必须写 `results/20260629_cine_motion_pathology/result.md`、`MANIFEST.md`、`selection.md`、`resource_audit.md`、`safe_cases_used.csv`、`motion_descriptor_summary.csv`、`metrics_summary.md`、`case_metrics.csv`、`failure_interpretation.md`，并索引 scripts/jobs/logs/predictions/visual sanity samples。

## 停止条件

只有 safe subset reference geometry 无法复现、所有 motion descriptor candidates 都安装或运行失败且无 first-party descriptor fallback、label/evaluator错误、predictions invalid、需要外部上传/非公开权重、或单 job 超过八小时，才停止。
