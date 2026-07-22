# CARE 当前开发状态

本文件是当前 CARE 主线工作的机器真值。新的规划、执行、训练、评价和状态判断必须先读取本文件。

## 当前状态

```text
state_id: srr_mainline_batch7_lightweight_br2_sip_decomposition_ready_20260722
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
batch7_minimal_decomposition_status: READY_FOR_CONTROLLER_AMENDED_TO_LIGHTWEIGHT_BR2_SIP
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

Controller 必须检查真实 diff、resolved loss、SIP公式、representer参数、availability mask、loss-specific gradient、匹配实验、Slurm、aggregation、CURRENT/wiki/fingerprint。普通实现和证据问题必须在当前任务内修复，不得直接退回用户。

## SRR 图与仍保留的目标

Planner 已视觉读取 ChatGPT Project 材料中的 SRR-v2、SRR-v2.5、SRR-v3。

当前保留的论文主线是：

```text
observed-modality-only encoding
-> availability-masked representer dictionary
-> source-pattern-specific sparse retrieval
-> optional BR2 selective integration penalty
-> pathology proposal
-> bounded nnU-Net comparison/safety
```

需要明确区分：

- 当前 M10 16-slot spatial dictionary、prototype maps 和 semantic negative memory 已出现低杠杆负证据，不再作为默认论文核心；
- Representation Retrieval Learning 的高层思想尚未被否定；
- 当前任务检验的是轻量 BR2 representer dictionary 和正式 SIP，而不是继续修旧 dictionary。

## 历史结果

### Batch 6

```text
edema positive Dice delta: +0.0027247487
scar positive Dice delta: +0.0006739682
mean positive Dice delta: +0.0016993584
```

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
mean positive Dice delta: +0.0012229660
scar positive Dice delta: -0.0019961366
edema positive Dice delta: +0.0044420686
help/harm: 25/27
remote-FP relative worsening max: 0.0530525167
```

它真实补齐独立干预、identity零变化、真实category memory、anchor-free discovery code path和strict validator，因此不是全面占位失败。但Planner复核发现proposal stage仍传入空loss JSON，历史混合M10 loss继续参与，不能作为纯proposal或BR2的最终否定。

## 当前 SIP 状态与决定

当前代码仍有：

```text
semantic_retrieval_regularization
pattern_sip_integrativeness_loss
```

它们属于历史启发式正则，不是论文的 source-specific SIP：没有直接定义 $\beta_d^{(s)}$，也没有跨source pattern计算representer integrativeness。

当前决定：

```text
legacy semantic retrieval regularization: formal weight 0
legacy Pattern-SIP: formal weight 0
new BR2 source L1 sparsity: implement and test
new BR2 selective integration penalty: implement and test with SIP-on/off ablation
```

Source只按availability pattern定义：

```text
LGE-only
LGE+C0
LGE+T2+C0
```

Center不得输入router。$|O_d|\le1$ 的representer不得进入SIP。

## 当前唯一任务

```text
BATCH7_FINAL_MINIMAL_BR2_SIP_PATHOLOGY_DECOMPOSITION
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

## 六个匹配实验

```text
scar_minimal
scar_br2_no_sip
scar_br2_sip
edema_minimal
edema_br2_no_sip
edema_br2_sip
```

同病种三组必须从同一checkpoint开始，使用相同seed、病例顺序、patch centers、optimizer、400步预算、评价和decode。两个BR2组还必须共享全部BR2参数初始化，只允许SIP权重不同。

Lightweight BR2只允许：

```text
shared anatomy
LGE private
C0 private
T2 private
LGE-C0 interaction
LGE-T2 interaction
T2-C0 interaction
```

必须hard-mask缺失模态模块，分别输出source coefficients、image residual和final retrieval weights。禁止M10 spatial dictionary、prototype maps、semantic negative memory、refiner、arbiter和gate训练。

## Loss和实现硬门

训练前必须证明：

```text
六组resolved loss完整
空loss JSON被拒绝
legacy semantic/Pattern-SIP精确为零
新SIP数值公式测试通过
每个非零loss单独backward且梯度范围正确
minimal不实例化/消费BR2
BR2 no-SIP/SIP结构和初始化一致
center不进入router
invalid representer在normalization前hard-mask且最终权重为零
重复representer或feature别名被known-bad拒绝
anchor-free discovery覆盖LGE-only scar、T2-present edema、CenterC complete tri-modal
```

## 最终保留门

Minimal保留：positive-case Dice `>=+0.003` 且help/harm、HD95、remote-FP和no-T2安全通过。

BR2保留：相对minimal额外Dice `>=+0.001` 且安全不恶化。

SIP保留：相对no-SIP额外Dice `>=+0.0005`；或Dice下降不超过`0.0005`且HD95/remote-FP改善至少2%，help/harm不恶化。

终态必须写出：

```text
scar_minimal: RETAIN | RETIRE
scar_br2: RETAIN | RETIRE | NOT_APPLICABLE
scar_sip: RETAIN | REMOVE | NOT_APPLICABLE
edema_minimal: RETAIN | RETIRE
edema_br2: RETAIN | RETIRE | NOT_APPLICABLE
edema_sip: RETAIN | REMOVE | NOT_APPLICABLE
```

SIP失败只删除SIP，不自动删除有效BR2。Scar minimal仍为负时停止scar SRR，不得用BR2/refiner/gate继续补救。

## 已授权

```text
explicit proposal loss authority
lightweight availability-masked BR2 representer dictionary
source-pattern learner coefficients
paper-form BR2 SIP and no-SIP ablation
loss-specific gradient verification
expanded anchor-free discovery coverage
six matched 400-step runs
strict validator and known-bad
mapper/wiki/fingerprint update
local lightweight result commit
```

## 未授权

```text
Batch8
current M10 dictionary/prototype/memory continuation
refiner training
source-arbiter training
production-gate training
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

Controller 的 `VERIFIED_COMPLETE` 只表示本次分解合同完成，下一步仍返回 Planner。