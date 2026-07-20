# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。任何新的规划、实现、审查、训练、推理或评价任务，都必须先读取本文件。

## 当前状态

```text
state_id: srr_mainline_batch2_correction_20260720
round_id: post_round04_main_only
date: 2026-07-20
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
single_active_scientific_line: SRR_MyoPS_Cine_from_historical_Route_B
latest_remote_batch1_commit: ef98e2d3e6808fd616d2732f4d6a645431a7a4ff
batch1_review_status: PARTIAL_IMPLEMENTATION_NEEDS_CLOSURE
next_required_batch: BATCH_2A_BATCH1_CLOSURE_THEN_BATCH2B_INFERENCE_EVALUATION
controller_authorized_now: 0
route_worktree_development_authorized: false
formal_training_authorized_now: false
slurm_authorized_now: false
validation_upload_authorized: false
hosted_metric_claim_authorized: false
```

当前默认只在 `main` 开发。不得启动 Route A/B/C controller，不得继续 route worktree 开发，不得创建 Round05，不得写入：

```text
/overflow/htzhu/CARE
/users/a/e/aereinh/CARE_worktrees/route_A
/users/a/e/aereinh/CARE_worktrees/route_B
/users/a/e/aereinh/CARE_worktrees/route_C
```

Route A、Route B、Route C 只保留为历史证据来源。历史 Route B 已合并进入 `main`，但不再作为活动路线运行。

## 当前工作方式

旧流程已经暂停：

```text
portfolio planner -> route critic -> route controller -> reviewer -> next round
```

当前流程是：

```text
一个 main integrator 写入 main
+ 多个绑定精确 SHA 的只读审计
+ 小批次连续修复
+ 每批更新变更账本
+ 真实训练前冻结代码
```

除非用户后续明确授权，本阶段只允许代码追踪、修复、真实病例单次前向/反向、完整推理与评价正确性验证、checkpoint 恢复测试和单元测试。禁止持续优化、正式 fold0 训练、Slurm、validation package 和上传。

## 当前权威文件顺序

按以下顺序读取：

```text
1. docs/plans/laneB_round04_active_srr_batch2_inference_and_fair_evaluation.md
2. docs/plans/laneB_round04_active_srr_batch1_myops_mainline_repair.md
3. docs/plans/laneB_round04_active_srr_plan_correction_addendum.md
4. docs/plans/laneB_round04_active_srr_code_completion_todo.md
5. docs/plans/laneB_round04_active_srr_mainline_production_execution.md
6. docs/plans/laneB_round04_active_srr_change_review_ledger.md
```

最新 Batch 2 修正计划覆盖旧 TODO、父计划和 Batch 1 ledger 中与下列内容冲突的表述：

- Batch 1 已完全形成生产 runner；
- Batch 2 可以直接比较 SRR 与 nnU-Net 性能；
- Batch 1 的 known-bad 已经是实际错误注入；
- 当前 checkpoint 已经证明完整 resume；
- 当前原型库已经完全排除病例自身泄漏。

## Batch 0 状态

Batch 0 已完成并推送：

```text
commit: 414427746e51e5d84918e57512619a2d3412326c
status: COMPLETE
```

它完成了当前实现真相梳理、formal authority 收束和旧 B3-B8 去授权。旧 Round04 B3-B8 Python 脚本及其 job wrapper 仍是：

```text
forbidden_formal_entrypoint
```

不得重新启用。

## Batch 1 状态

Batch 1 实现提交：

```text
commit: ef98e2d3e6808fd616d2732f4d6a645431a7a4ff
reported_status: BATCH_1_MYOPS_MAINLINE_COMPLETE_FOR_BATCH2
reviewed_status: PARTIAL_IMPLEMENTATION_NEEDS_CLOSURE
```

Batch 1 已确认的真实进展：

1. 五折共 220 例 OOF nnU-Net 缓存存在，并生成逐病例路径、fold、checkpoint 和哈希清单。
2. `SRRProposeRefineMyoPS` 增加显式 `anchor_bounded_srr_correction` 模式。
3. 跨折记忆查询可以改变候选图和最终输出。
4. 有 T2 病例上，水肿分支主要模块存在梯度。
5. 一次性真实病例验证中，关闭修正可恢复传入的 anchor tensor。
6. 没有运行优化器更新、Slurm 或正式训练。

Batch 1 尚未闭环的事实：

1. 原型、记忆和 checkpoint 的完整逻辑主要位于 `validate_myops_mainline.py`，尚未由训练 runner 和完整推理入口共同调用。
2. 训练 runner 仍使用旧的全局原型构建逻辑，没有加载 Batch 1 的四 shard 原型/记忆库。
3. 跨折记忆会排除当前 shard，但全局 `ProposalDictionary` 原型仍可能包含当前查询病例。
4. 验证器以合并后的总向量重复更新不同病例的记忆 provenance，不能证明逐病例来源真实对应。
5. 未使用的零计数记忆槽仍可能进入相似度计算。
6. no-T2 安全只证明最终修正和部分梯度为零，尚未证明候选概率、soft ROI、细化残差、全部损失和全部病种专属梯度为零。
7. `read_anchored_case` 会修改 no-T2 病例的水肿 anchor；当前恒等测试不是对原始 nnU-Net OOF 输出的恒等测试。
8. 12 个 known-bad 目前只是按名字固定返回 `REJECTED`，不是实际错误注入。
9. checkpoint receipt 没有真实恢复新 optimizer、随机数状态和下一次采样，因此不是完整 resume 证据。
10. `configs/srr_production/entrypoints.yaml` 内仍存在与 Batch 1 报告互相矛盾的旧说明。

因此，Batch 1 不得被解释为训练就绪，也不得直接进入性能比较。

## 当前立即任务：Batch 2A

Batch 2A 先完成 Batch 1 收口，不训练、不跑 44 例性能比较。必须让以下路径使用同一套共享实现：

```text
validator
training runner
full-volume inference
```

三者必须共同读取：

```text
raw OOF anchor manifest
four-shard prototype/memory bank
case-exclusion policy
final-output configuration
checkpoint schema
no-T2 safety function
```

Batch 2A 必须解决：

- 全局原型的当前病例泄漏；
- 逐病例 provenance 不真实；
- 未使用记忆槽未屏蔽；
- no-T2 全链路 exact-zero；
- raw nnU-Net anchor 与安全上下文混用；
- known-bad 固定字符串拒绝；
- checkpoint 只检查字段存在；
- runner 与 validator 数据流分叉。

Batch 2A 完成前，不得进入 Batch 2B。

## Batch 2B 目标

Batch 2B 只建立完整体积推理和公平评价权威：

```text
real Dataset501 case
-> raw OOF nnU-Net anchor
-> frozen prototype/memory
-> SRR full-volume inference
-> NIfTI geometry-preserving export
-> unified prediction/GT evaluator
```

评价顺序固定为：

1. 重现 nnU-Net fold0 记录指标；
2. 证明 `anchor_identity_control` 在 44 例上逐体素等于原始 OOF prediction；
3. 用零步 checkpoint 只做管线诊断；
4. 正式 SRR 性能比较必须等待用户单独授权真实 fold0 训练。

当前没有受信任的训练后 production SRR checkpoint。因此 Batch 2 不得把未训练模型与 nnU-Net 的差值解释成科学结果。

## 科学结构不变量

后续修复必须保留：

```text
[LGE,T2,C0] + explicit availability
modality-specific multi-scale encoders
shared/private/interaction retrieval
spatial/pathology-conditioned routing
real train/OOF prototypes and safe negatives
anatomy union/LV/RV
separate scar/edema proposals and soft-ROI refiners
no-T2 edema exact safety
pathology-specific bounded SRR correction
same-case raw OOF nnU-Net anchor as segmentation basis
real NIfTI inference
fair same-split Dice/HD/HD95/component/remote-FP evaluation
real multi-frame Cine + registration + temporal aggregation in later Cine batch
```

nnU-Net 可以作为分割基底、上下文、教师与安全来源，但 SRR 必须真实读取原始模态，并拥有检索、候选区域、局部细化和最终修正。不得退化成只读取 nnU-Net 预测的普通后处理。

## 当前路线状态

```text
Route A: HISTORICAL_DORMANT_NOT_ACTIVE
Route B: HISTORICAL_EVIDENCE_MERGED_TO_MAIN_NOT_ACTIVE_AS_ROUTE
Route C: HISTORICAL_STOP_AND_HOLD_NOT_ACTIVE
SRR mainline: ACTIVE_BATCH2A_BATCH1_CLOSURE_NO_TRAINING
```

## 权限边界

```text
controller_authorized_now: 0
formal_training_authorized_now: false
slurm_authorized_now: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
route_worktree_development_authorized: false
route_branch_deletion_authorized: false
```

任何旧 route handoff、controller token、测试通过数量或 receipt 状态都不能越过上述权限边界。