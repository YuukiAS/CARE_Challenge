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
executor_plan_path: prompts/tasks/20260723_care_myops_batch9_exposed_issues_repair_executor_plan_v2.yaml
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
route_promotion_gate: planner_only
scientific_completion_gate: planner_only
blocked_after_completion: Batch10,nnunet_anchor,baseline_fallback,standard_nnunet_checkpoint,old_SRR,BR2_lite,SIP,prototype,memory,proposal,refiner,Cine,fold_expansion,validation_upload,hosted_claim,route_promotion
---

## Execution Contract

本任务不是接回 nnU-Net，也不是新 Batch。保留 `CAREMMReliableDistillResEnc` / CARE-MMRD 的部署前向、三模态独立 stem、availability hard mask、anatomy/scar/edema 分头和最终六类输出不变。允许使用 nnU-Net v2 的 Trainer、plans、augmentation 和 deep-supervision 基础设施作为 CARE-MMRD 的训练引擎，但禁止加载标准 nnU-Net checkpoint、logits、预测，禁止 anchor correction 或 baseline fallback。

开始前同步最新 `main`，读取 `CURRENT.md`、Planner 决定、repair config、v2 executor plan、原 Batch 9 代码和终态证据，以及 Slurm/Mapper skill。Controller 必须监督到全部作业终态、聚合、validator、wiki/CURRENT 和本地轻量 commit。

## Controller Prompt

你是本任务的 coordinator 和最终操作验收人。只允许修复以下已暴露问题：

1. 实现 `src/care_myocardium/training/nnUNetTrainerCAREMMReliableDistill.py`；正式优化循环必须由该 Trainer 持有，旧 runner 只能调度、preflight 和收集证据。
2. 使用 `PlansManager` / `ConfigurationManager` 解析 `nnUNetResEncUNetMPlans` 的 patch、kernel、stride、stage channels 和 deep-supervision scales；禁止硬编码 `20x128x128` 或结构 fallback。正式 plans 无法解析时停止，不得偷换模型。
3. 使用 nnU-Net v2 的空间与强度增强并记录 transform hash、augmentation seed 和参数；启用训练期深监督，各尺度使用 nearest-neighbor 下采样的可靠标签 mask，推理仍只使用最高分辨率输出。
4. 修复所有 masked loss 的有效体素归一化；anatomy Dice 排除 background。对 32 个真实 batch 审计各 loss 的 weighted gradient norm 和两两 cosine：若 final-six loss 与 scar/edema loss 的 cosine 小于 `-0.25` 的 batch 比例超过 `0.25`，固定把 final-six loss 权重置零；否则保留。其他冲突或任一项支配超过 10 倍时 preflight 失败。
5. direct 使用 `lr=0.01` polynomial decay；teacher/control/distill 使用 `lr=0.001` polynomial decay。
6. sampler 按 scar 0.35、可靠 edema 0.35、anatomy 0.20、background 0.10 采样，禁止固定类优先级。
7. no-T2 不接收 edema 监督或蒸馏，并在 inference/evaluation argmax 前 hard mask class 4；预测 edema 体素必须精确为零。
8. 每 25 epoch 对固定 44 例评价并保存 checkpoint；按 config 的最低双病种 Dice、平均 Dice、正例 HD95 词典序选择并 reload，禁止只选 epoch500。
9. fixed overfit 的 full、LGE+C0、LGE-only 必须分别使用全新 model、optimizer、scheduler，并使用与 formal direct 相同的 loss、optimizer 和日程；禁止跨 pattern 状态继承。
10. control/distill 必须记录全部 25000 optimizer steps 的 runtime manifest，并输出覆盖 case、patch、augmentation、student mask、LR、teacher checkpoint/input 的 streaming hash；每 seed mismatch 必须为0。
11. teacher 完成后先做蒸馏有效覆盖 gate：feature 非零 batch 比例至少0.95，logit/anatomy各至少0.50，scar/edema GT-positive 体素进入 confidence mask 的比例各至少0.05；不通过不得启动 control/distill。
12. known-bad 必须真实篡改 packet/runtime receipt 并证明 validator 非零退出；逐 seed、逐病种 fail closed，terminal 字段必须由真实 Slurm accounting、aggregation 和 validator 派生，禁止硬编码 PASS。

完成实现、真实单元测试、loss 冲突审计和独立 fixed overfit 后，按 v2 executor plan 重跑两个 direct seed，各 500 epoch / 125000 steps。只有两个 seed 均无 GT-positive 空预测、no-T2 edema 为零、selected checkpoint 已 reload，且 scar、edema 都优于原 Batch 9 同 seed，才允许 teacher；teacher coverage gate 通过后才允许 matched control/distill。

不得改变部署前向，不得引入 nnU-Net 模型权重或 fallback、旧 SRR、BR2/SIP、prototype/memory、proposal/refiner、外部数据/权重、Cine、扩 fold 或上传。普通实现、训练、评价或 packet 缺陷必须在本任务内退回 Executor 修复，不得只记录后退出。

终态只返回 Planner，逐 seed、逐病种报告 direct/control/distill、空预测、HD95、remote FP、no-T2 安全、蒸馏覆盖和 failed gate。Controller 不得授权下一 Batch、提交或科学终止。

## Executor Worker Contract

Executor 只执行上述修复、测试、Slurm、评价和证据写入，不能自行宣布任务完成。所有 diff、测试、运行和结果必须返回 Controller 验收。

## Mapper Contract

Mapper 核对修复后的真实 Trainer、plans、augmentation、deep supervision、loss/dataflow、runtime 和 wiki/CURRENT 是否一致。部署架构未改变，不重画模型图；不得把 validator PASS 写成科学成功。
