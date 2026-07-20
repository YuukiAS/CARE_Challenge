# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。任何新的规划、实现、审查、训练、推理或评价任务，都必须先读取本文件。

## 当前状态

```text
state_id: srr_mainline_batch4_forced_fold0_training_20260721
round_id: post_round04_main_only
date: 2026-07-21
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
single_active_scientific_line: SRR_MyoPS_Cine_from_historical_Route_B
latest_batch3_implementation_commit: 1395ffb29879ab208103bd3acb3c46ad4ab1934f
latest_batch3_record_commit: d251bde18199d2afa9de60b28d02336f88994941
latest_batch4_planning_commit_before_current: 8a5e73c9c0245bd0632faeb3b57723e9f394a9cf
batch3a_review_status: PARTIAL_PASS_REAL_MODEL_IN_LOOP_DIAGNOSTIC_NOT_TRAIN_READY
batch3b_review_status: REAL_4D_IO_DIAGNOSTIC_PROXY_SEGMENTATION_NOT_MODEL_READY
batch4_status: DRAFT_FOR_PLANNING_REVIEW_USER_AUTHORIZED_TRAINING
next_required_action: SEPARATE_GPT_PLANNING_REVIEW_THEN_BATCH4_CONTROLLER
user_training_authorization_received: true
user_slurm_authorization_received: true
user_partition_race_authorization_received: true
controller_authorized_now: 0
formal_training_authorized_now: false_pending_planning_review_and_preflight
slurm_authorized_now: false_pending_planning_review_and_preflight
validation_upload_authorized: false
hosted_metric_claim_authorized: false
```

## 当前开发边界

当前只在 `main` 开发。不得启动 Route A/B/C controller，不得继续 route worktree 开发，不得创建 Round05，不得写入：

```text
/overflow/htzhu/CARE
/users/a/e/aereinh/CARE_worktrees/route_A
/users/a/e/aereinh/CARE_worktrees/route_B
/users/a/e/aereinh/CARE_worktrees/route_C
```

用户已明确授权 Batch 4 进行一次真实 MyoPS fold0 训练，并允许等待过长时使用 `htzhulab`、`a100-gpu`、`volta-gpu` 的同逻辑运行竞速。但本任务属于高风险 Slurm 科学任务，必须先通过独立 GPT 规划审查和同配置预检。规划审查通过前不得提交训练 job。

本轮授权不包括：

```text
Cine training
validation packaging/upload
hosted metric claim
fold expansion
route promotion
M11
final scientific decision
```

## 当前权威文件顺序

按以下顺序读取：

```text
1. docs/plans/laneB_round04_active_srr_batch4_forced_fold0_training_execution.md
2. configs/srr_production/myops_batch4.yaml
3. prompts/tasks/20260721_srr_batch4_forced_fold0_training_controller.md
4. prompts/tasks/20260721_srr_batch4_forced_fold0_training_executor_plan.yaml
5. prompts/tasks/20260721_srr_batch4_forced_fold0_training_planning_review_request.md
6. docs/plans/laneB_round04_active_srr_batch3_myops_inference_closure_and_cine_mainline.md
7. results/srr_production/code_maturity/batch2_critic_audit_and_batch3_decision.md
8. docs/plans/laneB_round04_active_srr_batch2_inference_and_fair_evaluation.md
9. docs/plans/laneB_round04_active_srr_batch1_myops_mainline_repair.md
10. docs/plans/laneB_round04_active_srr_change_review_ledger.md
```

Batch 4 文件覆盖旧文件中与以下内容冲突的表述：

- Batch 3A 已完全达到正式训练前的全部要求；
- 当前诊断模型可以直接作为正式训练模型；
- 训练 runner 的 checkpoint 已与 Batch 3A 推理 schema 兼容；
- identity 模式已经证明模型 logits 与 anchor 精确一致；
- 原型/记忆已经覆盖完整 176 例训练集；
- patch loss 可以作为正式 best checkpoint 选择依据；
- Batch 3B 已经形成可训练 Cine 模型候选；
- 用户仍未授权训练或 Slurm。

## Batch 0–2 结论

### Batch 0

```text
commit: 414427746e51e5d84918e57512619a2d3412326c
status: COMPLETE
```

完成当前实现真相、正式入口收束和旧 B3-B8 去授权。历史 B3-B8 及 wrapper 继续是 `forbidden_formal_entrypoint`。

### Batch 1

```text
commit: ef98e2d3e6808fd616d2732f4d6a645431a7a4ff
reviewed_status: PARTIAL_IMPLEMENTATION_CLOSED_ONLY_AT_SMOKE_LEVEL
```

建立 220 例 OOF anchor、anchor-bounded 输出、记忆接线、梯度和 checkpoint smoke；没有训练和性能结论。

### Batch 2A

```text
commit: b797a55f17b5e4c39a6cb97e8d1e295923f7b546
reviewed_status: PARTIAL_SHARED_COMPONENT_CLOSURE_WITH_REMAINING_GAPS
```

真实解决病例级 provenance、空槽屏蔽、无 T2 全链路检查和 schema v2 smoke。它未建立完整训练集原型资产。

### Batch 2B

```text
commit: b38b1a045236d94045c48f12831a41b190abe691
reviewed_status: NNUNET_BASELINE_AND_IDENTITY_EVALUATOR_COMPLETE_SRR_INFERENCE_MISSING
```

可靠结果是 nnU-Net fold0 44 例重算和统一评价器：

```text
edema Dice: 0.3944358976789887
scar Dice: 0.5601692281262312
```

当时 SRR 推理仍是标签复制，后由 Batch 3A 修复。

## Batch 3A 审查结论

```text
implementation_commit: 1cce038ac6c3cbb91ab2a9bc1033315571d09f71
reported_status: SRR_MODEL_IN_LOOP_UNTRAINED_DIAGNOSTIC
reviewed_status: PARTIAL_PASS_REAL_MODEL_IN_LOOP_DIAGNOSTIC_NOT_TRAIN_READY
```

### 已真实完成

1. 44 个 fold0 验证病例读取真实 Dataset501 `[LGE,T2,C0]` 与 availability，并调用 `SRRProposeRefineMyoPS`。
2. schema v2 零步 checkpoint 被实际加载。
3. raw OOF anchor 与 no-T2 safety context 在模型接口分离。
4. 训练查询排除自身分片；验证/推理读取全部冻结训练分片。
5. 三种模式导出 NIfTI，评价器不再默认把 SRR 目录回退到 identity 目录。
6. geometry 和 no-T2 tensor 检查得到轻量证据。

### 尚未达到训练前全部期望

1. 正式配置仍是 `base_channels=2`、`tiny_3scale`、`srr_propref_shared_dual_dict`，不是 SRR-v3 主线的 M10 D3 full-4scale。
2. identity 虽然调用模型，但推理脚本导出时直接选择 raw anchor labels；changed voxels 为零是部分由导出绕过保证，未证明模型 final logits/softmax 本身精确等于 anchor。
3. zero-step 三模式使用按 final-output mode 绑定的独立 checkpoint；尚未证明同一组训练权重能够公平运行三种控制。
4. zero-step 原型/记忆来自少数病例、单 patch，不是完整 176 例冻结训练资产。
5. 训练 runner 仍写只含 `model_state_dict` 的旧 checkpoint，不能直接由 Batch 3A schema v2 推理入口加载。
6. 当前 best checkpoint 由最多 10 例 patch loss 选择，不是完整 44 例 Dice、HD95、远端假阳性和 help/harm。
7. zero-step anchor-bounded 在 44 例只改变 5 个标签体素：水肿 Dice 从 `0.3944358976789887` 变为 `0.3943897861345629`，瘢痕完全不变。这只证明管线接通。

## Batch 3B 审查结论

```text
implementation_commit: 1395ffb29879ab208103bd3acb3c46ad4ab1934f
reported_status: BATCH3B_REAL_CINE_MAINLINE_DIAGNOSTIC_COMPLETE
reviewed_status: REAL_4D_IO_DIAGNOSTIC_PROXY_SEGMENTATION_NOT_MODEL_READY
```

### 已真实完成

- 三个真实 Dataset502 4D Cine 病例保留时间维；
- frame0 与标签几何对齐并作为参考空间；
- 中间帧通过逐切片二维图像光流 warp 到参考空间；
- 非参考帧能够改变最终输出；
- NIfTI raw-label 导出和本地 Dice/HD95 计算可运行。

### 关键边界

- 解剖预测来自强度百分位阈值和形态学规则，不是训练模型；
- 只使用 frame0 和一个中间帧，不是完整多帧时间建模；
- 配准是 2D optical flow，Jacobian 是代理量；
- CineMA 官方权重未加载；
- 三例心肌 Dice 约为 `0.012`、`0.047`、`0.019`，连通域数量很大；
- 这只能作为 I/O、warp、aggregation 诊断，不能进入本轮训练或 submission 候选。

## Batch 4 决策

Batch 4 只训练 MyoPS。固定顺序：

```text
独立 GPT 规划审查
-> 修复 schema-v2 训练 checkpoint、同 checkpoint 三模式和 identity 导出绕过
-> 用全部 176 例构建冻结原型/记忆资产
-> 60-step one-batch overfit 与同环境预检
-> 强制 1800-step / >=1800-second fold0 Slurm training
-> step 600/1200/1800 各运行完整 44 例评价
-> 固定规则选择 checkpoint 并重新加载
-> 同 checkpoint 运行 identity/anchor-bounded/no-anchor
-> 失败诊断、mapper final、终态 accounting、轻量本地 commit
-> 独立只读 reviewer
```

唯一训练模型：

```text
SRRProposeRefineMyoPS
m10_d3_hierarchical_memory_propref
full_4scale
anchor_bounded_srr_correction
```

本批训练预算不能被 smoke 替代：

```text
optimizer steps >= 1800
train loop seconds >= 1800
full-volume evaluation events = 3
cases per event = 44
unique train cases loaded/sampled = 176
```

分区竞速：先 `htzhulab`；900 秒仍 pending 时加 `a100-gpu`；首次提交后 1800 秒前两者均未开始时，只有在同配置 V100 显存预检通过后才加 `volta-gpu`。所有尝试必须同一逻辑运行、相同哈希、隔离目录、原子 winner lock，并取消 loser。

## 当前立即动作

启动一个独立 GPT 规划审查，读取当前权威文件并写：

```text
prompts/tasks/20260721_srr_batch4_forced_fold0_training_planning_review.md
```

只有该文件包含：

```text
planning_review_decision: AUDITED_GO
planning_review_token: BATCH4_PLANNING_AUDITED_GO
```

并绑定当前有效 main SHA 后，才允许启动 Batch 4 controller。用户训练授权已经收到，规划审查不得把任务改回“只做代码 smoke、不训练”。

## 权威边界

```text
controller_authorized_now: 0
user_training_authorization_received: true
user_slurm_authorization_received: true
formal_training_authorized_now: false_pending_planning_review_and_preflight
slurm_authorized_now: false_pending_planning_review_and_preflight
validation_upload_authorized: false
hosted_metric_claim_authorized: false
route_promotion_authorized: false
m11_authorized: false
final_scientific_decision_authorized: false
```
