# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。任何新的规划、实现、训练、推理、评价或状态判断都必须先读取本文件。

## 当前状态

```text
state_id: srr_mainline_batch7_upstream_candidate_quality_ready_20260721
round_id: post_round04_main_only
state_updated_date: 2026-07-21
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
route_worktree_development_authorized: false
single_active_scientific_line: SRR_MyoPS_from_historical_Route_B_lineage
batch4_operational_status: VERIFIED_COMPLETE
batch4_training_adequacy_status: PASS_EXACT_1800_STEPS_1800_SECONDS_176_44
batch4_scientific_status: BATCH4_TRAINED_NEGATIVE_OR_REPAIR_REQUIRED
batch5_operational_status: CONTROLLER_VERIFIED_COMPLETE
batch5_planner_audit_status: RUNTIME_COMPLETE_MECHANISM_PACKET_NEEDS_REPAIR
batch6_operational_status: CONTROLLER_VERIFIED_COMPLETE_STOP_AT_300_GATE_FAIL
batch6_scientific_status: FINAL_OBJECTIVE_REPAIRED_BUT_BELOW_USABLE_SIGNAL
batch7_status: READY_FOR_CONTROLLER
next_required_action: RUN_BATCH7_UPSTREAM_CANDIDATE_QUALITY
planning_review_required: false
review_required: false
controller_is_coordinator: true
batch7_asset_rebuild_authorized: true
batch7_fixed_overfit_authorized: true
batch7_formal_300_authorized: true
batch7_conditional_1200_authorized: true_only_after_step300_gate
validation_upload_authorized: false
hosted_metric_claim_authorized: false
fold_expansion_authorized: false
cine_training_authorized: false
backbone_replacement_authorized: false
encoder_base_retrieval_redesign_authorized: false
route_promotion_authorized: false
m11_authorized: false
batch8_authorized: false
final_scientific_decision_authorized: false
```

## 当前开发边界

当前只在：

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

默认不要求 planning critic，也不要求 independent reviewer：

```yaml
planning_review_required: false
planning_reviewer: none
review_required: false
review_mode: none
reviewer: none
```

Controller 是 coordinator 和 acceptance owner。Executor 不能自行宣布任务完成。Controller 必须检查真实 diff、实现语义、测试、prototype/memory 来源、Slurm、runtime、aggregation、required outputs、CURRENT/wiki/fingerprint 和 contract-sensitive fields，并在同范围内要求 Executor 修复，直到 `VERIFIED_COMPLETE`、`NEEDS_REPAIR` 或 `OPERATIONALLY_BLOCKED`。

面向 Planner/user 的 Controller 报告必须先用自然中文解释结论，再列内部字段、路径和指标。

## SRR 图与路线目标

Planner 已视觉读取 ChatGPT Project 材料中的：

```text
SRR-v2
SRR-v2.5
SRR-v3
visual_read_status: COMPLETE
```

当前路线目标：

```text
[LGE,T2,C0] + availability
-> modality-specific multi-scale encoding
-> shared/private/interaction selective retrieval
-> trained-feature-aligned prototype/memory/negative-space
-> anatomy-guided anchor-independent discovery + anchor-confirmation proposals
-> scar/edema differentiable soft ROI refinement
-> learned proposal/refiner source selection
-> directly supervised bounded nnU-Net correction
```

nnU-Net 只能作为 baseline、anchor、context、error signal 和 safety source，不能替代 SRR。

## Batch 4 终态

```text
model: SRRProposeRefineMyoPS
variant: m10_d3_hierarchical_memory_propref
encoder_profile: full_4scale
base_channels: 32
final_output_mode: anchor_bounded_srr_correction
fold0 train/validation: 176/44
valid job: 59682067 COMPLETED 0:0
optimizer_steps: 1800
selected checkpoint step: 1800
selected checkpoint SHA256: bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6
prototype asset SHA256: 8b262f8bb87e0733a48e169c77b028a3833b70cbcd33d2ac2fb4857ba1cbde83
```

科学结果：

```text
edema Dice delta: +0.00067965066743345
scar Dice delta:  +0.0013414936102105
```

工程闭环成立，但仍接近 nnU-Net。

## Batch 5 终态

Batch 5 完成 existing-checkpoint 诊断，确认：

- 正式 argmax 重排后 step1800 仍最好；
- 单纯 gate-open 不能解决低分；
- no-anchor 明显变差，主体性能仍来自 nnU-Net；
- proposal/refiner 平均 oracle headroom 约 `+0.00256`；
- 最终 logits 当时缺少直接 pathology GT loss；
- Batch 5 packet 的有效权重、纯组件干预和 ROI/validator 语义需要后续修复。

## Batch 6 终态

Batch 6 terminal commit：

```text
f139c54fd6b55b99409fcf546a1a0e117d7aa06b
```

执行证据：

```text
fixed-overfit job: 59743323 PASS
formal300 job: 59744053 COMPLETED
final interventions job: 59744941 COMPLETED
formal900: SKIPPED_STEP300_GATE_FAILED
selected checkpoint step: 300
selected checkpoint SHA256: 729c81e49bf846339ed2f39ef0f2656319befd2b9cfe73268d7cf501e6b40fbd
train/validation: 176/44
optimizer_steps: 300
```

Batch 6 修通了 direct final scar/edema supervision、13-channel production gate 和 GT-driven repair/preserve loss。Fixed overfit 通过，说明方向性 loss 和 gate 梯度真实存在。

300 步结果：

```text
edema positive Dice delta: +0.0027247486728372468
scar positive Dice delta:  +0.0006739681677682672
mean positive Dice delta:  +0.001699358420302757
required continuation gate: +0.003
help/harm: 25/18
no-T2 edema exact zero: true
```

这不是运行失败，而是科学继续门失败。900 步被正确禁止。

同 checkpoint 干预：

```text
full gate=1:
  edema +0.00772109
  scar  +0.00028663
proposal-only gate=1:
  edema +0.00434505
  scar  +0.00261628
refiner-only gate=1:
  edema +0.00495245
  scar  -0.00876189
```

结论：final loss/gate 修复有真实但有限作用；scar refiner 明显有害，proposal/refiner 固定平均不合理，上游候选质量成为主瓶颈。

## 当前 Batch 7

### 唯一目标

```text
UPSTREAM_CANDIDATE_QUALITY_AND_SOURCE_SELECTION_REPAIR
```

Batch 7 不再只调 final gate，也不把 Batch 6 机械延长。它必须：

1. 从 Batch 6 step300 训练后 checkpoint 和全部 176 个训练病例重建 prototype/memory；
2. 用完整 tensor SHA256、四 shard 和 validation-zero-leakage 绑定资产；
3. 用真实语义负样本替换正式路径中的 deterministic/random named negatives；
4. 在 M10 spatial dictionary 前查询 memory，并把 scar/edema 正负 prototype maps 真正传入两轮空间路由；
5. 将 proposal 拆成不读取 nnU-Net pathology context 的 discovery branch 与 anchor-confirmation branch；
6. 将正式 refiner 改为从 proposal logits 起步的可微软 ROI residual，不再用离散 crop 作为正式路径；
7. 用 learned source arbiter 选择 proposal/refiner，删除固定 `0.5/0.5` 平均；
8. 保留 Batch 6 direct final loss、production gate repair/preserve 和 no-T2 safety。

### 当前权威文件顺序

```text
1. results/srr_production/code_maturity/batch6_planner_audit_and_batch7_decision.md
2. docs/plans/laneB_round04_active_srr_batch7_upstream_candidate_quality_execution.md
3. configs/srr_production/myops_batch7.yaml
4. prompts/tasks/20260721_srr_batch7_upstream_candidate_quality_controller.md
5. prompts/tasks/20260721_srr_batch7_upstream_candidate_quality_executor_plan.yaml
6. results/20260721_srr_batch6_final_objective_alignment/
7. configs/srr_production/myops_batch6.yaml
8. results/20260721_srr_batch4_forced_fold0_training/
```

### Batch 7 阶段

```text
B7-00: bind Batch6 terminal evidence and forensic code truth; no training
B7-01: rebuild trained-feature-aligned prototype/memory asset; no training
B7-02: wire prototype maps into spatial dictionary
B7-03: implement dual-source proposal, differentiable refiner and source arbiter
B7-04: real-case interventions, strict tests and checkpoint roundtrip
B7-05: Case2002 + Case1002 fixed 100-step overfit; zero formal credit
B7-06: exact 300-step fold0 upstream calibration; 44-case eval at 100/200/300
B7-07: continue to total 1200 only after machine-verified step300 gate
B7-08: selected-checkpoint interventions, mapper/wiki/fingerprint and controller verification
```

### Batch 7 300 步继续门

只有全部满足才允许继续到 1200：

```text
final mean positive Dice delta >= +0.005
each pathology final Dice delta >= +0.001
proposal-only mean positive Dice delta >= +0.005
scar refiner-only Dice delta >= 0
scar learned-source no more than 0.001 below scar proposal-only
edema learned gate captures >=60% of gate-one gain
help >= harm
HD95 relative worsening <=5% each pathology
remote-FP relative worsening <=5% each pathology
no-T2 edema exact zero
finite losses and nonzero required gradients
```

失败时固定停止在 300，跳过 1200，但仍形成完整机制和终态包。

### Batch 7 科学等级

```text
mean Dice delta < +0.01: still insufficient
+0.01 to < +0.03: useful upstream mechanism signal
+0.03 to < +0.05: substantial but below project target
>= +0.05 mean and each pathology >= +0.03: Batch7 target reached
```

这些等级都不自动授权 fold expansion 或 validation upload。

## Batch 7 授权边界

已授权：

```text
Batch6 code/result forensic binding
trained-checkpoint prototype/memory rebuild
real semantic negative memory
spatial prototype-map wiring
dual-source proposal repair
differentiable soft-ROI refiner repair
learned proposal/refiner source arbiter
loss/test/validator/checkpoint/inference repair
fixed two-case 100-step overfit
formal 300-step fold0 calibration
conditional extension to total 1200 after machine gate
selected-checkpoint mechanism interventions
CURRENT/wiki/fingerprint update
local lightweight result commit
```

未授权：

```text
backbone replacement or comparison
encoder/base retrieval redesign
fold expansion
Cine training
external data or weights
validation packaging/upload
hosted metric claim
route promotion
M11
Batch8 automatic start
final scientific stop
```

## 目标边界

Batch 6 已经说明“过度保守”不是唯一问题。Batch 7 的任务是证明：当 prototype/memory 与当前特征空间一致、spatial dictionary 真正读取 prototype、proposal 能独立发现 baseline 漏检、scar refiner 不再有害且系统能选择 proposal/refiner 后，是否可以把局部 `+0.001` 级变化提高到至少 `+0.01`，并争取接近项目希望的 `+0.05`。若 300 步连上游继续门都过不了，就不能再把失败归因于 gate 或训练时长。