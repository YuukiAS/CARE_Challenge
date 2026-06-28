---
task_key: "20260628_cine_register"
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

# Task 20260628 Cine Register

## 目标

按照 Result5 对 CineMyoPS 的判断，停止只看单帧或未配准 keyframe context 的路线，系统比较若干 reference-frame registration / warping 模块。目标是在 59 个 geometry-safe CineMyoPS cases 上，确定一种能把 non-reference frames、CineMA anatomy prior 或 motion-like descriptors 安全传播到 reference frame 的方法，为后续 Cine temporal pathology 或 myocardium refinement 提供基础。CineMyoPS 是次线，但必须同步推进。

## 背景

必须读取 `AGENTS.md`、`prompts/AGENT_RULES.md`、`prompts/tasks/20260628_cine_register.md`、Result5、`results/20260626_cine_temporal/result.md`、`results/20260626_cine_temporal/failure_interpretation.md`、`results/20260625_cine_geometry/decision.md`、`results/20260625_cine_geometry/safe_cases.csv`、`results/20260625_cine_geometry/mismatch_cases.csv`、`results/20260620_cinema_adapter_pilot/result.md`、Cine raw 4D data、CineMA adapter outputs、Dataset502/Task026 evaluator 和 current geometry scripts。

当前事实是，reference control 在 safe subset 上有 myocardium Dice 约 0.5626、LV Dice 约 0.7709；keyframe context retrieval 没有超过 reference control；anatomy consistency temporal 更差。Result5 判断，这不是时序无用，而是 non-reference frames 没有通过 motion registration 或 warping 对齐到 reference frame。下一步必须比较配准模块。

## 允许动作

允许联网查找、clone 或 pip install 配准资源，但必须限制在本任务需要的 registration/warping 工具。允许尝试 SimpleITK/ANTsPy/NiftyReg/VoxelMorph/现有 optical-flow 或 cardiac registration 资源中能快速安装和运行的模块。允许写 isolated adapter，不得污染主 pipeline。允许最多三个并行 CPU/GPU jobs，每个不超过八小时。允许使用 external public code，但必须记录 license、install command、commit/version、失败信息和是否可用于 challenge。

## 禁止动作

不要 validation submission、upload package、external upload。不要下载非公开权重、需要账号或许可不清的资源。不要把非reference frame直接与 reference GT 算 Dice 当作时序效果。不要让 5 个 mismatch cases 阻塞 59 个 safe cases。不要覆盖已有 CineMA/nnU-Net/CineMyoPS outputs。不要把 anatomy registration preflight 说成 scar/pathology 成功。

## Registration candidates

至少尝试三类候选中的两类，资源允许则三类都试。

第一类是 classical registration：SimpleITK 或 ANTsPy 的 rigid/affine + BSpline/SyN 类方法。目标是建立稳定、透明、无训练的 reference-frame warping baseline。必须报告 runtime、failure cases、Jacobian/warp sanity、anatomy overlap。

第二类是 learning-based registration：优先 VoxelMorph 或可快速 pip/clone 的轻量学习型 registration。若无合适 cardiac pretrained weight，则允许在 safe subset 内做 unsupervised pairwise training 或 per-case optimization，但单 job 不能超过八小时。必须报告是否真的比 classical registration 更好。

第三类是 motion/optical-flow descriptor：不一定输出 dense warp，可输出 frame-difference、motion magnitude、strain-like descriptor 或 displacement proxy，用于调制 reference decoder。它不能替代 registration，但可作为辅助特征。若使用光流/运动模块，必须说明二维/三维假设和切片处理。

## 执行步骤

先重建 safe 59 cases 与 mismatch 5 cases。对每个 safe case，确定 reference frame，选择若干 non-reference frames，例如 mid/ES-like/representative frames。对每个候选 registration 方法，把 non-reference anatomy prior、texture 或 frame intensity warp 到 reference geometry。评估不能直接用 non-reference pathology GT，而应使用 reference anatomy proxy、CineMA anatomy consistency、LV/MYO overlap、frame-to-reference image similarity、warp smoothness、folding/Jacobian sanity、failure rate 和 runtime。

若某个 registration method 明显失败，记录失败并继续其他候选。若某个方法安装失败，尝试下一个候选，不要停止整个 task。若网络不可用，则基于 SimpleITK 或现有依赖完成 classical baseline，并记录未完成的 external checks。

## 评估

必须报告：safe cases 数、mismatch cases 状态、每种方法的成功率、runtime、warp sanity、myocardium/LV consistency、reference-frame control 对比、是否改善 temporal feature alignment。必须区分 anatomy proxy、motion descriptor 和 pathology prediction。class_3 scar sanity 仍可报告，但不能作为主要失败理由，除非后续引入 scar-specific head。

## 决策门

写 `results/20260628_cine_register/selection.md`，状态只能是 `SELECT_REGISTRATION_MODULE`、`SELECT_CLASSICAL_BASELINE`、`SELECT_MOTION_DESCRIPTOR_ONLY`、`REVISE_REGISTRATION_AND_REPEAT`、`STOP_CINE_REGISTRATION`、`STOP_LICENSE_OR_INSTALL_BLOCKER`。选择 registration module 要求至少在 safe subset 上比 no-warp reference context 有更好的 anatomy consistency 或 motion alignment，且 failure rate、runtime 和 warp sanity 可接受。

## 预期产出

必须写 `results/20260628_cine_register/result.md`、`MANIFEST.md`、`selection.md`、`resource_audit.md`、`safe_cases_used.csv`、`registration_metrics.csv`、`warp_sanity.csv`、`failure_interpretation.md`，并索引所有 install logs、commands、external repo versions、scripts、outputs 和 visual sanity samples。若 clone external repo，应放在隔离目录并记录 license。

## 停止条件

只有 safe subset reference geometry 无法复现、所有 registration candidates 都安装或运行失败且 SimpleITK baseline 不可用、warp/inverse mapping 不安全且无法记录、需要账号/非公开权重/外部上传、或单 job 超过八小时，才停止。

## 人工决策点

是否接受 selected registration module 进入后续 Cine temporal/pathology task。是否允许下载特定 external weight 或使用许可不清资源。本任务不授权 validation submission。
