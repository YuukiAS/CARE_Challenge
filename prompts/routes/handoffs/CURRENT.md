# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。任何新的规划、实现、训练、推理、评价或状态判断都必须先读取本文件。

## 当前状态

```text
state_id: srr_mainline_batch5_post_batch4_diagnostic_repair_20260721
round_id: post_round04_main_only
state_updated_date: 2026-07-21
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
route_worktree_development_authorized: false
single_active_scientific_line: SRR_MyoPS_from_historical_Route_B_lineage
latest_handoff_flow_commit: 1e74da7527e801726ce6990c9f963119e7cbe9ed
latest_batch4_training_source_commit: 0466260e3f4eb6c50b05a7f5a8b66652b873fe46
latest_batch4_terminal_packet_commit: 82524678e8c4aae5c088b24db8a00643c2603ae9
latest_batch4_explicit_review_commit: 5352d3c7b614adcbe4388a6fcef45c9db662dc38
batch4_operational_status: VERIFIED_COMPLETE
batch4_training_adequacy_status: PASS_EXACT_1800_STEPS_1800_SECONDS_176_44
batch4_scientific_status: BATCH4_TRAINED_NEGATIVE_OR_REPAIR_REQUIRED
batch4_candidate_signal_gate: FAIL
batch5_status: READY_FOR_CONTROLLER
next_required_action: RUN_BATCH5_POST_BATCH4_DIAGNOSTIC_REPAIR
planning_review_required: false
review_required: false
controller_is_coordinator: true
batch5_training_authorized: false
batch5_inference_only_diagnostic_authorized: true
validation_upload_authorized: false
hosted_metric_claim_authorized: false
fold_expansion_authorized: false
cine_training_authorized: false
route_promotion_authorized: false
m11_authorized: false
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

未来任务默认：

```text
Planner
-> Controller/Coordinator
   -> Executor
   -> optional Mapper
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

只有用户或 Planner 在具体任务中显式设置为 true 时，旧 critic/reviewer 流程才启用。

Controller 是 coordinator 和 acceptance owner。Executor 不能自行宣布任务完成。Controller 必须检查真实 diff、测试、Slurm、runtime、aggregation、required outputs 和 contract-sensitive fields，并在同范围内要求 Executor 修复，直到 `VERIFIED_COMPLETE`、`NEEDS_REPAIR` 或 `OPERATIONALLY_BLOCKED`。

## Batch 4 已完成内容

### 正式模型与数据

```text
model: SRRProposeRefineMyoPS
variant: m10_d3_hierarchical_memory_propref
encoder_profile: full_4scale
base_channels: 32
final_output_mode: anchor_bounded_srr_correction
fold0 train: 176
fold0 validation: 44
```

### 合法训练作业

```text
job_id: 59682067
partition: htzhulab
state: COMPLETED
exit_code: 0:0
elapsed: 00:33:26
optimizer_steps: 1800
train_loop_seconds: 1800.0000680589583
unique_train_cases: 176
minimum_case_usage: 1
full_volume_eval_steps: 600,1200,1800
cases_per_eval: 44
```

### checkpoint 与控制

```text
selected_checkpoint: step_1800
selected_checkpoint_sha256: bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6
same_checkpoint_three_modes: complete
identity_changed_voxels: 0
identity_softmax_max_abs_delta: 0
```

### prototype/memory

```text
source_case_count: 176
missing_train_cases: 0
validation_leakage_cases: 0
no_t2_edema_positive_forbidden: true
no_t2_edema_negative_forbidden: true
asset_sha256: 8b262f8bb87e0733a48e169c77b028a3833b70cbcd33d2ac2fb4857ba1cbde83
```

## Batch 4 科学结果

同一 fold0 44 例、同一 nnU-Net anchor：

```text
edema Dice: 0.3944358976789887 -> 0.39511554834642215
edema Dice delta: +0.00067965066743345
scar Dice: 0.5601692281262312 -> 0.5615107217364417
scar Dice delta: +0.0013414936102105
scar remote FP volume: 620.3619700074735 -> 605.6288666886041 mm3
```

结论：

```text
Batch4 engineering closure: achieved
Batch4 significantly better than nnU-Net: no
Batch4 candidate signal threshold +0.01 mean Dice: failed
Batch4 strong signal threshold +0.03 each pathology: failed
```

主要正贡献来自 no-T2/LGE-only scar；T2-present scar 和 CenterC 未改善。当前不能进入 fold expansion、submission candidate 或论文正结果。

## Batch 4 已识别的剩余缺口

1. 历史 checkpoint selection 使用 `pathology_aware` decode，而最终正式结果使用 `anchor_bounded_srr_correction` logits argmax；语义不一致。
2. `correction_gate_diagnostics.csv` 主要记录旧 baseline/arbitration gate，不是正式 `production_correction_gate`。
3. 缺少 proposal/refiner/production-gate 到 final metrics 的病例级机制闭环。
4. frozen prototype manifest 顶层 `feature_hash` 为空，缺少明确 config hash。
5. preflight GPU attempt 没有直接产生 schema-v2 runtime roundtrip receipt；训练后 reload 已证明可用。
6. selected-control Slurm job在 evaluator config 阶段失败，后续评价由本地修复后重跑。
7. root `wiki/README.md` 和 architecture fingerprint 仍停在 M9，需由 Batch 5 mapper 修复。

## 当前 Batch 5

### 目标

```text
POST_BATCH4_EVALUATION_AND_OUTPUT_AUTHORITY_DIAGNOSTIC_REPAIR
```

Batch 5 不训练，不改变 checkpoint 权重，不重建 prototype/memory。它必须：

1. 使用正式 logits argmax 重排 step 600/1200/1800。
2. 分离 positive-GT 与 all-case empty-safe 指标。
3. 对同 checkpoint 做 identity、bounded-full、no-anchor、proposal-only、refiner-only、gate-closed、gate-open-bounded 干预。
4. 直接记录 production gate、raw correction、bounded correction 和病例级 metric delta。
5. 补齐 prototype feature/config/code/split/anchor/asset hashes。
6. 更新 CURRENT、entrypoint authority、wiki 和 fingerprint。
7. 只给出一个 Batch 6 训练修复方向。

### 当前权威文件顺序

```text
1. docs/plans/laneB_round04_active_srr_batch5_post_batch4_diagnostic_repair.md
2. configs/srr_production/myops_batch5.yaml
3. prompts/tasks/20260721_srr_batch5_post_batch4_diagnostic_repair_controller.md
4. prompts/tasks/20260721_srr_batch5_post_batch4_diagnostic_repair_executor_plan.yaml
5. results/srr_production/code_maturity/batch4_planner_audit_and_batch5_decision.md
6. results/20260721_srr_batch4_forced_fold0_training/training_adequacy.json
7. results/20260721_srr_batch4_forced_fold0_training/selected_checkpoint.json
8. results/20260721_srr_batch4_forced_fold0_training/subgroup_metrics.csv
9. results/20260721_srr_batch4_forced_fold0_training/help_harm.csv
10. results/20260721_srr_batch4_forced_fold0_training/slurm_attempts.csv
```

## Batch 5 授权边界

已授权：

```text
code repair within Batch5 write scope
existing-checkpoint diagnostic inference
short inference-only Slurm job
htzhulab -> a100-gpu pending race
CURRENT/entrypoint/wiki/fingerprint repair
local lightweight commit
```

未授权：

```text
optimizer training
new checkpoint training
prototype/memory rebuild
fold expansion
Cine training
validation packaging/upload
hosted metric claim
route promotion
M11
Batch6 automatic start
```

## 目标边界

最终目标仍是显著优于 nnU-Net，而不是 near-identity correction。`+0.001` 级别提升不足。Batch 5 必须先找出一个可验证的主要瓶颈，之后 Planner 才决定是否授权下一次训练。