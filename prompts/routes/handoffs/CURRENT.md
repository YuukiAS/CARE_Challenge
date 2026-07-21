# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。任何新的规划、实现、训练、推理、评价或状态判断都必须先读取本文件。

## 当前状态

```text
state_id: srr_mainline_batch7_mechanism_closure_repair_terminal_20260721
round_id: post_round04_main_only
state_updated_date: 2026-07-21
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
route_worktree_development_authorized: false
single_active_scientific_line: SRR_MyoPS_from_historical_Route_B_lineage
batch4_operational_status: VERIFIED_COMPLETE
batch4_scientific_status: TRAINED_BUT_NEAR_BASELINE
batch5_operational_status: CONTROLLER_VERIFIED_COMPLETE
batch5_scientific_status: DIAGNOSTIC_PACKET_REQUIRED_REPAIR
batch6_operational_status: CONTROLLER_VERIFIED_COMPLETE_STOP_AT_300
batch6_scientific_status: FINAL_OBJECTIVE_REPAIRED_BUT_BELOW_USABLE_SIGNAL
batch7_operational_status: FORMAL300_COMPLETED_STOP_GATE
batch7_scientific_status: MECHANISM_REPAIR_CONNECTED_BUT_PROPOSAL_CHAIN_INADEQUATE
batch7_repair_status: VERIFIED_COMPLETE_STOPPED_AT_PROPOSAL_GATE
next_required_action: PLANNER_DECIDE_POST_PROPOSAL_CHAIN_INADEQUATE
planning_review_required: false
review_required: false
controller_is_coordinator: true
batch8_authorized: false
fold_expansion_authorized: false
cine_training_authorized: false
backbone_replacement_authorized: false
validation_upload_authorized: false
hosted_metric_claim_authorized: false
route_promotion_authorized: false
final_scientific_decision_authorized: false
```

## 当前开发边界

只允许在：

```text
/users/a/e/aereinh/CARE
main
```

开发。不得写入：

```text
/overflow/htzhu/CARE
/users/a/e/aereinh/CARE_worktrees/route_A
/users/a/e/aereinh/CARE_worktrees/route_B
/users/a/e/aereinh/CARE_worktrees/route_C
```

Route A/B/C 仅保留历史证据和 lineage，不是 active development branches。

## 当前默认 Agent Flow

```text
Planner
-> Controller/Coordinator
   -> one Executor
   -> Mapper draft/final
   -> deterministic Finalizer/Validator
   -> Controller verification and same-scope repair loop
   -> local lightweight commit
-> Planner
```

Controller 是 coordinator 和 acceptance owner。Executor 不能自行宣布任务完成。Controller 必须检查真实 diff、模型运行、独立 prediction roots、hash、测试、semantic memory、Slurm、aggregation、CURRENT/wiki/fingerprint，并在同范围内要求 Executor 修复。

## SRR 图与路线目标

Planner 已视觉读取 ChatGPT Project 材料中的：

```text
SRR-v2
SRR-v2.5
SRR-v3
visual_read_status: COMPLETE
```

当前仍保留的路线目标：

```text
[LGE,T2,C0] + availability
-> modality-specific multi-scale encoding
-> availability-aware shared/private/interaction retrieval
-> real prototype and semantic negative memory
-> anatomy-guided anchor-free discovery + anchor-confirmation proposals
-> pathology-specific scar/edema soft-ROI refinement
-> source selection
-> directly supervised bounded nnU-Net correction
```

nnU-Net 只能作为 baseline、anchor、context、error signal 和 safety source，不能替代 SRR。

## 已确认结果

### Batch 6

```text
selected checkpoint SHA256: 729c81e49bf846339ed2f39ef0f2656319befd2b9cfe73268d7cf501e6b40fbd
formal300: COMPLETED
edema positive Dice delta: +0.0027247487
scar positive Dice delta: +0.0006739682
mean positive Dice delta: +0.0016993584
formal900: skipped after gate fail
```

Batch 6 修通 final pathology supervision 和 production gate，但收益不足。

### Batch 7 formal300

```text
terminal commit: 4c79554de785030ed59081ce3ae233711efc062a
selected checkpoint SHA256: d34ad65890cbb6a12aac3fc35bcab71709d680bff5a3aae2d93e010db1cc0e0d
job: 59789651 COMPLETED 0:0
optimizer steps: 300
full-volume eval: 100,200,300
edema positive Dice delta: +0.0054302188
scar positive Dice delta: -0.0048258512
mean positive Dice delta: +0.0003021838
help/harm: 23/35
formal1200: skipped after gate fail
no-T2 edema exact zero: true
```

这证明当前联合模型未达到继续门，但不能作为完整 SRR 设计的有效否定，因为机制证据没有闭环。

## Batch 7 机制证据失效原因

以下原 Batch7 文件不得用于机制结论：

```text
results/20260721_srr_batch7_upstream_candidate_quality/final_mechanism_interventions.csv
results/20260721_srr_batch7_upstream_candidate_quality/proposal_refiner_metrics.csv
results/20260721_srr_batch7_upstream_candidate_quality/source_arbiter_metrics.csv
```

原因：

1. 所有 intervention mode 被写入同一组 formal300 指标；
2. identity 相对 anchor 不为零；
3. proposal-only 和 scar refiner-only 正式指标为空；
4. source arbiter 只有 softmax 单元测试，没有 44 例效果；
5. validator 没有拒绝 placeholder、复制指标和复用预测；
6. named semantic negative memory 没有逐类替换真实 bank；
7. discovery retrieval 仍间接读取 nnU-Net context；
8. CURRENT 和 root wiki 没有在 terminal packet 后正确收尾。

原 Batch7 的 `controller_verification_decision: VERIFIED_COMPLETE` 只保留为 formal300 操作流程完成，不代表 mechanism closure 完成。

## 当前唯一任务

```text
BATCH7_MECHANISM_CLOSURE_REPAIR_TERMINAL_PACKET_REVIEW
```

权威文件顺序：

```text
1. results/srr_production/code_maturity/batch7_planner_audit_and_mechanism_closure_decision.md
2. docs/plans/laneB_round04_active_srr_batch7_mechanism_closure_repair_execution.md
3. configs/srr_production/myops_batch7_repair.yaml
4. prompts/tasks/20260721_srr_batch7_mechanism_closure_repair_controller.md
5. prompts/tasks/20260721_srr_batch7_mechanism_closure_repair_executor_plan.yaml
6. results/20260721_srr_batch7_upstream_candidate_quality/
7. results/20260721_srr_batch6_final_objective_alignment/
```

## Batch7 repair 执行结果

```text
B7R-00 COMPLETE
B7R-01 COMPLETE
B7R-02 COMPLETE
B7R-03 COMPLETE
B7R-04 COMPLETE_STOPPED_AT_PROPOSAL_GATE
B7R-05 NOT_RUN_PROPOSAL_GATE_FAILED
B7R-06 NOT_RUN_PROPOSAL_GATE_FAILED
B7R-07 COMPLETE_TERMINAL_PACKET_WRITTEN
```

Proposal gate evidence:

```text
job: 59828884 FAILED 2:0 as encoded continuation-gate stop
optimizer steps: 600
selected checkpoint SHA256: a2412889d55a0e3eee0ca2d57a77f34db0f10f0a069193cc906785f49fae97f1
mean positive Dice delta: +0.0012229660
scar positive Dice delta: -0.0019961366
edema positive Dice delta: +0.0044420686
help/harm: 25/27
remote-FP relative worsening max: 0.0530525167
```

## 关键执行门

在任何新训练前必须满足：

```text
each intervention has its own 44-case prediction root and manifest
identity and gate-closed changed voxels = 0 for every case
identity softmax max abs delta <= 1e-6
no placeholder or copied metrics
old Batch7 copied table rejected by known-bad test
named semantic memory real by category or valid-mask disabled
discovery logits invariant to anchor confirmation context <=1e-6
confirmation logits change under zeroed anchor context >1e-5
```

Proposal-only 阶段继续门：

```text
mean positive Dice delta >= +0.003
scar Dice delta >= -0.001
edema Dice delta >= +0.003
help >= harm
HD95 and remote-FP worsening <=5%
no-T2 edema exact zero
```

Proposal 阶段已经失败，downstream refiner、source arbiter 和 production gate 训练均未运行。

Scar/edema refiner 必须分别优于本病种 proposal 至少 `+0.001` 才允许进入正式 source；失败 refiner 必须 hard-disable，不能继续平均。

最终 production gate 候选门：

```text
mean positive Dice delta >= +0.005
each pathology Dice delta >= 0
help >= harm
HD95 and remote-FP worsening <=5%
no-T2 edema exact zero
```

## 已授权

```text
truthful independent intervention infrastructure
semantic validator and known-bad repair
real category semantic memory with valid masks
anchor-free discovery routing repair
same-checkpoint 44-case intervention replay
proposal-only 600-step training
conditional pathology-specific refiner stages
conditional source-arbiter and production-gate stages
mapper/wiki/fingerprint repair
local lightweight result commit
```

## 未授权

```text
Batch8
monolithic Batch7 1200-step continuation
backbone replacement
encoder/base retrieval redesign
fold expansion
Cine
external data or weights
validation packaging/upload
hosted metric claim
route promotion
M11
final scientific stop
```

## 完成语义

Controller 已在真实干预、semantic memory、anchor-free discovery、proposal-stage terminal accounting、post-completion aggregation、strict validator、known-bad、mapper final、CURRENT/wiki/fingerprint 和本地轻量 commit 完成后写入：

```text
controller_verification_decision: VERIFIED_COMPLETE
```

这只表示当前修复合同完成。下一步仍由 Planner/用户决定。
