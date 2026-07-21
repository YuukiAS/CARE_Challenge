# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。任何新的规划、实现、训练、推理、评价或状态判断都必须先读取本文件。

## 当前状态

```text
state_id: srr_mainline_batch6_formal300_gate_fail_stop_20260721
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
batch4_candidate_signal_gate: FAIL
batch5_operational_status: CONTROLLER_VERIFIED_COMPLETE
batch5_planner_audit_status: RUNTIME_COMPLETE_MECHANISM_PACKET_NEEDS_REPAIR
batch6_status: CONTROLLER_VERIFIED_COMPLETE_STOP_AT_300_GATE_FAIL
next_required_action: RETURN_TO_PLANNER
planning_review_required: false
review_required: false
controller_is_coordinator: true
batch6_training_authorized: false
batch6_fixed_overfit_required: true
batch6_formal_300_step_authorized: false
batch6_conditional_900_step_authorized: false_step300_gate_failed
validation_upload_authorized: false
hosted_metric_claim_authorized: false
fold_expansion_authorized: false
cine_training_authorized: false
backbone_replacement_authorized: false
route_promotion_authorized: false
m11_authorized: false
batch7_authorized: false
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
   -> Executor
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

Controller 是 coordinator 和 acceptance owner。Executor 不能自行宣布任务完成。Controller 必须检查真实 diff、测试、Slurm、runtime、aggregation、required outputs、CURRENT/wiki/fingerprint 和 contract-sensitive fields，并在同范围内要求 Executor 修复，直到 `VERIFIED_COMPLETE`、`NEEDS_REPAIR` 或 `OPERATIONALLY_BLOCKED`。

## SRR 图与路线目标

Planner 已视觉读取 ChatGPT Project 材料中的：

```text
SRR-v2
SRR-v2.5
SRR-v3
visual_read_status: COMPLETE
```

Batch 6 必须保留：

```text
[LGE,T2,C0] + availability
-> modality-specific multi-scale encoding
-> shared/private/interaction selective retrieval
-> prototype/memory/negative-space
-> anatomy-guided scar/edema proposal
-> pathology-specific soft ROI refinement
-> directly supervised bounded nnU-Net correction
```

nnU-Net 只能作为 baseline、anchor、context、evidence 和 safety source，不能替代 SRR。

## Batch 4 终态

### 模型与数据

```text
model: SRRProposeRefineMyoPS
variant: m10_d3_hierarchical_memory_propref
encoder_profile: full_4scale
base_channels: 32
final_output_mode: anchor_bounded_srr_correction
fold0 train: 176
fold0 validation: 44
```

### 合法训练

```text
job_id: 59682067
partition: htzhulab
state: COMPLETED
exit_code: 0:0
elapsed: 00:33:26
optimizer_steps: 1800
train_loop_seconds: 1800.0000680589583
full_volume_eval_steps: 600,1200,1800
cases_per_eval: 44
```

### checkpoint 与 prototype

```text
selected_checkpoint: step_1800
selected_checkpoint_sha256: bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6
identity_changed_voxels: 0
identity_softmax_max_abs_delta: 0
prototype_source_case_count: 176
prototype_validation_leakage_cases: 0
prototype_asset_sha256: 8b262f8bb87e0733a48e169c77b028a3833b70cbcd33d2ac2fb4857ba1cbde83
```

### 科学结果

```text
edema Dice: 0.3944358976789887 -> 0.39511554834642215
edema Dice delta: +0.00067965066743345
scar Dice: 0.5601692281262312 -> 0.5615107217364417
scar Dice delta: +0.0013414936102105
scar remote FP: 620.3619700074735 -> 605.6288666886041 mm3
```

结论：训练足额，工程闭环成立，但 `+0.001` 级提升远低于 `+0.01` candidate gate。当前不能扩 fold、上传或声称显著优于 nnU-Net。

## Batch 5 终态与 Planner 复核

Batch 5 使用同一 selected checkpoint、44 cases 和 7 个推理模式完成了诊断运行：

```text
primary_job_id: 59730568
primary_partition: htzhulab
primary_state: COMPLETED
primary_exit_code: 0:0
optimizer_steps: 0
parameter_updates: 0
```

可接受结论：

- 正式 argmax 重排后 step 1800 仍最好；评价语义错误不是低分主因。
- gate 全开相对 full 只给 edema 额外约 `+0.00035`，scar 基本无收益；单纯开 gate 不能解决问题。
- no-anchor 控制明显变差，当前主体性能仍来自 nnU-Net anchor。
- proposal/refiner 存在少量病例级信号，但平均 oracle headroom 只有约 `+0.00256`。
- 最终 `outputs["logits"]` 缺少直接 scar/edema GT loss；旧 correction-opportunity 连接 legacy arbitration；两个正权重 magnitude loss 偏好 correction/residual 接近零。

Planner 代码复核发现 Batch 5 packet 仍需修复：

1. `resolved_weight` 没有从 Batch 4 正式 wrapper、argparse defaults 和 aliases 完整解析。
2. 所谓 proposal-only/refiner-only 的 gate 仍同时读取 proposal/refiner，组件干预不纯。
3. proposal component、remote FP、ROI GT coverage 和 ROI outside ratio 字段实际为空。
4. production gate 得到的是 anchor-preservation gradient，不能据此声称获得 GT-driven repair gradient。
5. strict validator 主要检查文件和字段名，没有 fail closed 检查上述语义和 receipt 自洽。

因此 Batch 5 的操作终态保留为 `CONTROLLER_VERIFIED_COMPLETE`，但科学机制 packet 状态为：

```text
RUNTIME_COMPLETE_MECHANISM_PACKET_NEEDS_REPAIR
```

## 当前 Batch 6

### 唯一目标

```text
FINAL_OBJECTIVE_AND_PRODUCTION_GATE_ALIGNMENT
```

Batch 6 不换 backbone，不重建 dictionary，不扩大训练规模来掩盖问题。它先补齐 Batch 5 证据，再让最终 deployed logits 直接接受 pathology GT loss，并让 production gate 学会：

```text
anchor 错误位置 -> 打开纠正
anchor 正确且高置信位置 -> 保持不动
```

### 当前权威文件顺序

```text
1. docs/plans/laneB_round04_active_srr_batch6_final_objective_alignment_execution.md
2. configs/srr_production/myops_batch6.yaml
3. prompts/tasks/20260721_srr_batch6_final_objective_alignment_controller.md
4. prompts/tasks/20260721_srr_batch6_final_objective_alignment_executor_plan.yaml
5. results/20260721_srr_batch5_post_batch4_diagnostic_repair/
6. docs/plans/laneB_round04_active_srr_batch5_post_batch4_diagnostic_repair.md
7. configs/srr_production/myops_batch5.yaml
8. results/20260721_srr_batch4_forced_fold0_training/
```

### Batch 6 阶段

```text
B6-01: Batch5 effective-weight, pure-intervention and proposal/ROI reconciliation; no training
B6-02: direct final scar/edema loss and 13-channel production gate repair
B6-03: Case2002 + Case1002 fixed-batch 60-step overfit; zero formal credit
B6-04: exact 300-step fold0 calibration; 44-case eval at 100/200/300
B6-05: continue to total 900 steps only if fixed step-300 gate passes
B6-06: selected-checkpoint pure interventions and final mechanism aggregation
B6-07: mapper/wiki/fingerprint and strict validation
B6-08: controller verification, local commit and return to Planner
```

### 300-step continuation gate

只有全部满足才可继续到 900 steps：

```text
mean scar/edema positive-case Dice delta >= +0.003
each pathology Dice delta >= -0.002
help >= harm
HD95 relative worsening <= 5% each pathology
remote-FP relative worsening <= 5% each pathology
no-T2 edema exact zero
finite losses and nonzero final/gate repair gradients
```

### 科学等级

```text
below usable: step-300 continuation gate fails
small usable: final mean Dice delta >= +0.005 and each pathology >= 0
candidate: final mean Dice delta >= +0.010 with safety gates
strong: scar and edema Dice delta each >= +0.030
```

即使 Batch 6 达到 candidate，fold expansion 仍需要 Planner/用户单独授权。

## Batch 6 当前终态

```text
batch6_controller_verification_decision: VERIFIED_COMPLETE
fixed_overfit_status: PASS
fixed_overfit_job_id: 59743323
formal_300_status: COMPLETED
formal_300_job_id: 59744053
formal_900_status: SKIPPED_STEP300_GATE_FAILED
final_interventions_job_id: 59744941
selected_checkpoint_step: 300
selected_checkpoint_sha256: 729c81e49bf846339ed2f39ef0f2656319befd2b9cfe73268d7cf501e6b40fbd
mean_scar_edema_positive_dice_delta: 0.001699358420302757
continuation_gate_required_mean_delta: 0.003
scientific_signal_class: BELOW_USABLE
```

解释：Batch6 修通了 fixed-overfit 所需的方向性纠错 loss 和 gate 梯度，但 300-step formal calibration 的平均正例 Dice 增量没有达到继续到 900 的门槛。因此当前必须停在 300，返回 Planner；不允许自动启动 900、Batch7、fold expansion、Cine、upload 或 hosted claim。

## Batch 6 授权边界

已授权：

```text
Batch5 mechanism evidence reconciliation
loss/gate/code/test/validator repair
source checkpoint gate migration
fixed two-case 60-step overfit
formal 300-step fold0 calibration
conditional extension to total 900 steps after machine-verified step300 gate
same-checkpoint final mechanism interventions
CURRENT/wiki/fingerprint update
local lightweight result commit
```

未授权：

```text
backbone replacement or comparison
encoder/retrieval redesign
prototype/memory rebuild
fold expansion
Cine training
external weights or data
validation packaging/upload
hosted metric claim
route promotion
M11
Batch7 automatic start
final scientific stop
```

## 目标边界

当前距离“大幅好于 nnU-Net”仍很远。已有平均提升约 `+0.001`，candidate gate 是 `+0.01`，strong gate 是 scar 和 edema 各 `+0.03`。Batch 6 的现实任务不是直接达到 strong gate，而是先证明修复后的目标函数能否稳定达到至少 `+0.005` 的可用信号；如果连 300-step gate 都过不了，就应停止继续堆训练，并转向 proposal/refiner 表征本身的重构判断。