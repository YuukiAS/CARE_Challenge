# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。新的规划、执行、训练、评价和状态判断必须先读取本文件。

## 当前状态

```text
state_id: srr_mainline_batch7_minimal_pathology_decomposition_ready_20260722
round_id: post_round04_main_only
state_updated_date: 2026-07-22
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED
route_worktree_development_authorized: false
single_active_scientific_line: SRR_MyoPS_from_historical_Route_B_lineage
batch6_scientific_status: FINAL_OBJECTIVE_REPAIRED_BUT_BELOW_USABLE_SIGNAL
batch7_operational_status: FORMAL300_COMPLETE_STOP_GATE
batch7_repair_operational_status: VERIFIED_COMPLETE_STOPPED_AT_PROPOSAL_GATE
batch7_repair_scientific_status: TRUTHFUL_EVIDENCE_BUT_PROPOSAL_STAGE_LOSS_AUTHORITY_IMPURE
batch7_minimal_decomposition_status: READY_FOR_CONTROLLER
next_required_action: RUN_BATCH7_MINIMAL_PATHOLOGY_DECOMPOSITION
planning_review_required: false
review_required: false
controller_is_coordinator: true
batch8_authorized: false
refiner_training_authorized: false
source_arbiter_training_authorized: false
production_gate_training_authorized: false
fold_expansion_authorized: false
cine_training_authorized: false
backbone_replacement_authorized: false
validation_upload_authorized: false
hosted_metric_claim_authorized: false
route_promotion_authorized: false
final_scientific_decision_authorized: false
```

## 开发边界

只允许在：

```text
/users/a/e/aereinh/CARE
main
```

开发。不得写入 `/overflow/htzhu/CARE` 或历史 Route A/B/C worktree。Route A/B/C 只保留 lineage 和历史证据。

## 当前流程

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

Controller 必须检查真实 diff、resolved loss、loss-specific gradient、训练冻结范围、匹配实验、Slurm、aggregation、CURRENT/wiki/fingerprint。普通实现和证据问题必须在当前任务内修复，不得直接退回用户。

## SRR 图与仍保留的目标

Planner 已视觉读取 ChatGPT Project 材料中的 SRR-v2、SRR-v2.5、SRR-v3。

仍保留的高层目标是：

```text
observed-modality-only encoding
-> availability-aware retrieval
-> pathology proposal
-> optional evidence-proven dictionary
-> pathology-specific refinement only after proposal success
-> bounded nnU-Net correction
```

高层思想尚未被当前证据否定，但复杂 dictionary、memory、refiner 和 arbiter 不再默认保留，必须分别证明增量价值。

## 已确认的历史结果

### Batch 6

```text
edema positive Dice delta: +0.0027247487
scar positive Dice delta: +0.0006739682
mean positive Dice delta: +0.0016993584
```

Batch 6 修通 final pathology supervision 和 production gate，但收益不足。

### Batch 7 formal300

```text
terminal commit: 4c79554de785030ed59081ce3ae233711efc062a
edema positive Dice delta: +0.0054302188
scar positive Dice delta: -0.0048258512
mean positive Dice delta: +0.0003021838
help/harm: 23/35
```

原 Batch 7 机制表因复制指标、identity 非零和 placeholder 已被 supersede。

### Batch 7 mechanism closure repair

```text
terminal commit: 0fcc3ff605112a0efeab73f3df2f83249793d321
proposal job: 59828884
optimizer steps: 600
selected checkpoint SHA256: a2412889d55a0e3eee0ca2d57a77f34db0f10f0a069193cc906785f49fae97f1
mean positive Dice delta: +0.0012229660
scar positive Dice delta: -0.0019961366
edema positive Dice delta: +0.0044420686
help/harm: 25/27
remote-FP relative worsening max: 0.0530525167
```

本轮真实补齐了：

```text
independent 44-case interventions
identity and gate-closed exact zero
real category semantic memory with hashes and valid masks
anchor-free discovery implementation check
600-step proposal stage
strict known-bad validator
```

因此它不是原 Batch 7 那种全面占位失败。

## Planner 复核发现的剩余问题

### 1. Proposal stage loss authority 不纯

Stage wrapper 传入空 `--loss-weight-json {}`。M10 variant 因此继续使用历史默认混合 loss：refiner、anchor preservation、correction opportunity、branch arbitration、bounded correction、dictionary regularization、prototype/memory 和 refiner-effect 等仍可能参与；新的 discovery/confirmation direct loss默认却为零。

因此 600 步结果不是“纯 proposal 训练后的充分负结果”。

### 2. Gradient authority 只证明连接

当前检查对 proposal logits 均值 backward，而不是对正式非零 loss逐项 backward。它不能证明训练目标方向正确，也没有证明梯度只进入授权模块。

### 3. Anchor-free discovery 测试覆盖不足

当前只检查验证集前两个 LGE-only 病例，没有覆盖 T2-present edema 和 CenterC完整多模态病例。

### 4. 具体组件已经出现负证据

真实 intervention 显示：

```text
semantic negative memory off 后 edema 更好，scar几乎不变
prototype maps 对 edema贡献约 +0.0007，对 scar无稳定收益
scar proposal/refiner/learned-source/gate-one均为负
no-anchor仍严重崩溃
```

这说明当前 semantic memory 和复杂 dictionary 的杠杆很低，scar 与 edema 共享 proposal/dictionary训练存在明显冲突。

## 当前唯一任务

```text
BATCH7_FINAL_MINIMAL_PATHOLOGY_DECOMPOSITION
```

权威文件顺序：

```text
1. results/srr_production/code_maturity/batch7_repair_planner_audit_and_minimal_decomposition_decision_20260722.md
2. docs/plans/laneB_round04_active_srr_batch7_minimal_pathology_decomposition_execution.md
3. configs/srr_production/myops_batch7_minimal_decomposition.yaml
4. prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_controller.md
5. prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_executor_plan.yaml
6. results/20260721_srr_batch7_mechanism_closure_repair/
```

## 执行阶段

```text
B7D-00 bind latest evidence and source checkpoint
B7D-01 implement explicit loss authority and matched variant gates
B7D-02 train scar_minimal and scar_dictionary, 400 steps each
B7D-03 train edema_minimal and edema_dictionary, 400 steps each
B7D-04 write final RETAIN/RETIRE decisions and update state
```

四个实验必须从相同 checkpoint 开始、使用相同 seed、病例顺序、patch centers、optimizer、步数、评价和 decode。Dictionary pair只允许 prototype maps/spatial dictionary开关不同；semantic negative memory不得进入正式训练。

## 最终保留或删除门

Minimal proposal 保留：

```text
positive-case Dice delta >= +0.003
help >= harm
HD95 relative worsening <=5%
remote-FP relative worsening <=5%
no-T2 edema exact zero
```

Dictionary 只有相对同病种 minimal额外提高 `>=+0.001` 且安全不恶化才保留。

终态必须写出：

```text
scar_minimal: RETAIN | RETIRE
scar_dictionary: RETAIN | RETIRE | NOT_APPLICABLE
edema_minimal: RETAIN | RETIRE
edema_dictionary: RETAIN | RETIRE | NOT_APPLICABLE
```

Minimal失败后不得继续该病种的 dictionary/refiner/arbiter/gate修复。本任务后不允许再用“组件仍需完善”延长同一复杂路线。

## 已授权

```text
explicit proposal-stage loss authority
loss-specific gradient verification
expanded anchor-free discovery coverage
scar minimal/dictionary matched runs
edema minimal/dictionary matched runs
strict validator and known-bad
mapper/wiki/fingerprint update
local lightweight result commit
```

## 未授权

```text
Batch8
refiner training
source-arbiter training
production-gate training
monolithic continuation
backbone replacement
encoder redesign
fold expansion
Cine
external data or weights
validation packaging/upload
hosted metric claim
route promotion
final scientific stop
```

Controller 的 `VERIFIED_COMPLETE` 只表示本次最终分解合同完成，下一步仍返回 Planner。