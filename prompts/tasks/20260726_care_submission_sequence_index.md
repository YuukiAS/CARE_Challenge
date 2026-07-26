---
task_key: 20260726_care_submission_sequence_index
task_kind: planning_index
task_type: main_only_submission_sequence
status: READY_FOR_PLANNER_USE
risk_level: high
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: planning_index_only
requires_execution_controller: false
controller_is_coordinator: false
executor_slots: 0
executor_count: 0
parallel_execution_allowed: false
executor_plan_path: null
mapper_slots: 0
mapper_required: false
architecture_impact: system
wiki_update_required: false
diagram_update_required: false
slurm_runtime_continuity_required: false
continuity_backend: none
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
review_required: false
review_mode: none
reviewer: none
allow_git_commit: false
auto_git_commit: false
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
---

# CARE 2026-07-26 三次提交序列

这组提示词把原始大任务拆成 3 个 main-only controller 任务。拆分原因很简单：第 1 次只回答“强 nnU-Net 基线是否被低估”，第 2 次才生成真正带组件级 SRR 思想的 CARE-SCF v1，第 3 次必须等待第 2 次人工上传后的 scar/edema 分项结果，才能做病种定向 v2 和最终 Docker 一致性。三个阶段不能合并执行，也不能在缺少前置证据时跳到后续阶段。

共同边界：

- active worktree: `/users/a/e/aereinh/CARE`
- active branch: `main`
- remote: `YuukiAS/CARE_Challenge`
- result root: `results/20260726_care_fullinfo_nnunet_and_care_scf/`
- Route A/B/C 只作为历史证据，不恢复 route worktree 开发。
- 不自动上传 validation。
- 不自动上传 Docker。
- 不 `git push`。
- 不修改 `MoSAIC_Paper`。
- 不写论文。
- 不把纯 nnU-Net、纯 MoSAIC、固定类别拼接或历史分数选择包装成 CARE 方法。
- 不恢复完整 BR2、SIP、dense retrieval、proposal-free prototype memory、复杂 trainable gate 或新的大型深度网络训练。

## 三个执行入口

1. 第 1 次：5-fold nnU-Net 强基线，只做校准。
   - controller: `prompts/tasks/20260726_care_nnunet5f_control_controller.md`
   - executor plan: `prompts/tasks/20260726_care_nnunet5f_control_executor_plan.yaml`
   - 产物：只生成 `nnUNet5F-control` upload-ready ZIP 和审计文件，供用户手动上传。

2. 第 2 次：提交真正的 CARE-SCF v1，包含组件级 SRR 思想。
   - controller: `prompts/tasks/20260726_care_scf_v1_controller.md`
   - executor plan: `prompts/tasks/20260726_care_scf_v1_executor_plan.yaml`
   - 产物：实现、OOF 评价、安全门、机制激活审计和 `CARE-SCF-v1` upload-ready ZIP，供用户手动上传。

3. 第 3 次：根据第 2 次 hosted scar/edema 分项结果，提交病种定向 CARE-SCF v2，并让它与最终 Docker 完全一致。
   - controller: `prompts/tasks/20260726_care_scf_v2_docker_alignment_controller.md`
   - executor plan: `prompts/tasks/20260726_care_scf_v2_docker_alignment_executor_plan.yaml`
   - 前置：必须存在第 2 次人工上传后的 hosted 结果记录；否则停止为 `BLOCKED_HOSTED_RESULT_REQUIRED_FOR_V2`。

## 执行顺序硬门

第 1 次完成后只允许用户决定是否手动上传 control 包。第 2 次不得因为第 1 次包已经生成就声称 CARE 方法完成；第 3 次不得在没有第 2 次 hosted scar/edema 结果时做病种定向调参。

第 2 次和第 3 次的 CARE-SCF 候选必须在训练 OOF 或 validation candidate 中真实触发非零组件操作，并且至少在部分病例上与 nnU-Net 和 MoSAIC 两个 anchor 都不同。如果机制没有激活，必须返回 `BLOCKED_MECHANISM_INACTIVE`，不得把 anchor 原样打包成 CARE-SCF。

每个 controller 完全结束、aggregation/validator/commit 状态确认后，才允许写 `results/<task>/notification_brief.json`，并由既有 `controller_notifications/notify_goal_watcher.py` / `care_watchboard:Notify` notifier 向 `1155246312@link.cuhk.edu.hk` 发送一封中文短邮件。不得为单个任务另开 notifier，不得在 submitted、pending、running、monitor 包、`NEEDS_MONITOR` 或未完成 aggregation 阶段通知。
