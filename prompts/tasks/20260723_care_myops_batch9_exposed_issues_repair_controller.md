---
task_key: 20260723_care_myops_batch9_exposed_issues_repair
task_kind: scientific_milestone
task_type: batch9_exposed_issues_repair
status: READY_FOR_CONTROLLER
controller_mode: coordinator_acceptance_owner
milestone_number: null
milestone_id: null
risk_level: high
route_change: false
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260723_care_myops_batch9_exposed_issues_repair_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: none
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
route_promotion_gate: planner_only
scientific_completion_gate: planner_only
blocked_after_completion: Batch10,nnunet_anchor,baseline_fallback,old_SRR,BR2_lite,SIP,prototype,memory,proposal,refiner,Cine,fold_expansion,validation_upload,hosted_claim,route_promotion
---

## Execution Contract

本任务不是接回 nnU-Net，也不是新 Batch。保留 `CAREMMReliableDistillResEnc` / CARE-MMRD 前向结构不变；标准 nnU-Net 只保留为比较指标，禁止加载其 logits、checkpoint、预测或作为 fallback。唯一目标是修复 Batch 9 已暴露的训练、解码和验收缺陷，再公平重跑。

开始前同步最新 `main`，读取 `CURRENT.md`、Planner 决定、repair config、executor plan、原 Batch 9 代码与终态证据，以及 Slurm/Mapper skill。Controller 必须监督到所有作业终态、聚合、validator、wiki/CURRENT 和本地轻量 commit 完成。

## Controller Prompt

你是本任务的 coordinator 和最终操作验收人。只允许显式修复以下问题：

1. 修复 `masked_mean`：case mask 必须展开到 loss tensor，BCE、consistency、feature distillation 按真实有效体素数归一化；记录未加权 loss、加权贡献和梯度范数。
2. 修复训练调度：direct 使用 `lr=0.01` 的 polynomial decay；warm-start teacher/control/distill 使用 `lr=0.001` 的 polynomial decay，禁止恒定高学习率 continuation。
3. 修复 sampler：按 scar 0.35、可靠 edema 0.35、anatomy 0.20、background 0.10 显式采样，禁止固定 `edema -> scar -> anatomy` 优先级；输出真实采样 manifest。
4. 修复 no-T2 推理：训练监督仍为零，并在 inference/evaluation argmax 前 hard mask class 4，no-T2 预测 edema 体素必须精确为零。
5. 修复验证与 checkpoint：每 25 epoch 对固定 44 例评价并保存 checkpoint；拒绝阳性空预测和 no-T2 edema 非零；按 config 的词典序规则选择并 reload checkpoint，禁止只看 epoch500。
6. 修复 validator/finalizer：known-bad 必须真实注入错误；每个 seed 独立判定，任何 seed 的 scar 或 edema 失败不得被跨 seed 平均掩盖；terminal 字段必须来自真实 Slurm accounting、aggregation 和 validator，禁止硬编码 PASS。

完成真实单元测试和 fixed-case overfit 后，按 executor plan 重跑两个 direct seed，各 500 epoch / 125000 steps。只有两个 seed 均无 GT-positive 空预测、no-T2 edema 为零，且 scar、edema 都比原 Batch 9 同 seed 改善，才继续 teacher/control/distill。Continuation 必须从 repaired direct selected checkpoint warm-start，并保持 matched manifest。

不得改变模型 forward，不得引入 nnU-Net anchor/fallback、旧 SRR、BR2/SIP、prototype/memory、proposal/refiner、外部数据/权重、Cine、扩 fold 或上传。发现普通实现、训练、评价或 packet 缺陷时，在本任务内退回 Executor 修复；不得只记录问题后退出。

终态只返回 Planner，并明确列出每个 seed、每个病种的 direct 与 control/distill 结果、空预测、HD95、remote FP、no-T2 安全和 failed gate。Controller 不得授权下一 Batch、提交或科学终止。

## Executor Worker Contract

Executor 只执行上述修复、测试、Slurm、评价和证据写入，不能自行宣布任务完成。所有 diff、测试、运行和结果必须返回 Controller 验收。

## Mapper Contract

Mapper 只核对修复后真实代码、loss/dataflow、runtime 和 wiki/CURRENT 是否一致。架构未改变，不重画模型图；不得把 validator PASS 写成科学成功。
