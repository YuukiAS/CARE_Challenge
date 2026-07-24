---
task_key: 20260724_care_myops_batch10_deadline_rescue
task_kind: scientific_milestone
task_type: deadline_rescue_and_submission_decision
status: READY_FOR_CONTROLLER
controller_mode: coordinator_acceptance_owner
milestone_number: null
milestone_id: null
risk_level: high
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260724_care_myops_batch10_deadline_rescue_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: component
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
review_required: false
review_mode: none
reviewer: none
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
---

## Execution Contract

本任务是 CARE-MMRD 在截止日前的最后一次限时救援，不是新架构搜索。用户已终止原 Batch 9 repair Wave 6 后续运行；不得恢复旧 Wave 6 到 epoch100。先修正 clean-checkout依赖、plans/preprocessing绑定、滑窗推理、正式空间恢复和公平评价，再重评 direct、teacher、control、distill 八个现有 checkpoint。只有正确重评后达到配置中的 near-baseline gate，才允许执行25 epoch matched短续训。

nnU-Net 只允许作为同划分评价基线读取现有 NIfTI prediction和metrics；不得加载其checkpoint、logits或概率进入CARE-MMRD，不得作为anchor、ensemble source或fallback。禁止恢复Batch7、旧SRR、BR2、SIP、prototype、memory、proposal、refiner，禁止新backbone、外部权重、扩fold和Cine训练。

## Controller Prompt

你是本任务的协调者和最终操作验收人。开始前同步最新 `main`，读取 Planner决定、Batch10 config、executor plan、Batch9本地runtime、Slurm与Mapper skill，并冻结用户终止Wave6的job/checkpoint lineage。

严格按 executor plan 的 Wave 0–6 顺序执行。每个 Wave 后检查真实 git diff、import、命令、runtime输出、checkpoint hash、44例case set、metric population、Slurm accounting和required outputs；发现普通实现或证据缺陷时，必须在同一任务内退回同一 Executor 修复并复验，不得只记录问题后退出。不得把 submitted、pending、running、部分checkpoint或epoch25截图写成终态完成。

优先完成无训练救援：

1. clean-checkout import和preprocessing fingerprint；
2. nnU-Net v2等价滑窗、Gaussian、mirror TTA与正式inverse export；
3. 八checkpoint、teacher、baseline的同评价重算；
4.冻结的六种ensemble和calibration/audit后处理。

只有 `near_baseline_gate.json` 通过，才实现同步空间增强、center-first采样和scar/edema病种置信蒸馏，并提交配置固定的四个25 epoch matched jobs。任何seed或病种失败不能被平均掩盖。

Controller必须持续监督所有已提交job到终态，使用`afterok`管理训练依赖、`afterany`完成accounting/finalizer，终态后重新聚合、运行strict validator和known-bad、完成Mapper/wiki/CURRENT一致性并创建一个本地轻量结果commit。不得push runtime结果，不得上传validation或Docker。

最终只允许输出：paper候选通过、仅Docker候选通过、或当前CARE-MMRD停止。必须说明相对同划分nnU-Net的scar/edema Dice、HD95、help/harm、remote FP、空预测、安全性和audit split结果。Controller不得启动Batch11，也不得自行作hosted成绩主张。

## Executor Worker Contract

Executor只执行已冻结的实现、推理、评价、条件式短续训、Docker dry-run和证据写入；不能宣布整个任务完成。每个Wave都返回Controller检查diff、运行和证据，按Controller的同范围修复要求继续工作。

## Mapper Contract

Mapper核对真实代码、checkpoint重建、preprocessing、推理/export、同步增强、采样、蒸馏、Docker入口和终态证据；部署forward不变，因此不重画模型主图。不得把validator PASS写成科学成功。