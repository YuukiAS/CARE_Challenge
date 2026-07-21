---
task_key: 20260721_srr_batch7_mechanism_closure_repair
task_kind: scientific_milestone
task_type: mechanism_closure_and_stagewise_component_repair
controller_mode: coordinator_acceptance_owner
milestone_number: null
milestone_id: null
status: READY_FOR_CONTROLLER
risk_level: high
route_change: false
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260721_srr_batch7_mechanism_closure_repair_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
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
experiment_adequacy_gate: truthful_interventions_then_stagewise_proposal_refiner_arbiter_gate
route_negative_gate: planner_only
scientific_completion_gate: planner_only
diagnostic_publication_gate: false
diagnostic_publication_scope: none
blocked_after_diagnostic_publication: validation_upload,hosted_claim,fold_expansion,Cine,route_promotion,M11,Batch8
training_allowed: true
backbone_replacement_allowed: false
fold_expansion_allowed: false
cine_allowed: false
validation_upload_allowed: false
hosted_metric_claim_allowed: false
next_batch_authorization: planner_only
---

## Execution Contract

本任务不是启动 Batch 8，也不是把 Batch 7 的 300 步机械延长。Batch 7 已经真实完成 formal300，但其终态机制证据无效：同一组 formal metrics 被复制给所有 intervention mode，proposal/refiner 指标为空，validator 未拒绝 placeholder；同时 named negative memory 和 anchor-free discovery 没有忠实满足原合同。

本任务必须在 `main`、`/users/a/e/aereinh/CARE` 内完成 Batch 7 同范围修复。Controller 是 coordinator 和验收负责人，必须持续监督 Executor，检查真实 diff、运行命令、预测目录、hash、Slurm、聚合和 validator；同范围问题必须立即退回 Executor 修复，不能只记录问题并提前结束。

### 开始前必须读取

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/README.md
prompts/routes/route_portfolio_planner_prompt.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
results/srr_production/code_maturity/batch7_planner_audit_and_mechanism_closure_decision.md
docs/plans/laneB_round04_active_srr_batch7_mechanism_closure_repair_execution.md
configs/srr_production/myops_batch7_repair.yaml
prompts/tasks/20260721_srr_batch7_mechanism_closure_repair_executor_plan.yaml
results/20260721_srr_batch7_upstream_candidate_quality/
```

### 图示目标

必须保留已由 Planner 视觉读取的 SRR-v2、v2.5、v3 目标：observed-modality-only encoding、availability-aware retrieval、真实 prototype/memory、解剖引导 proposal、scar/edema 分病种 refiner、bounded nnU-Net correction。不得把 nnU-Net 变成隐式最终模型，也不得借修复之名换 backbone。

### 固定边界

```text
source main: 4c79554de785030ed59081ce3ae233711efc062a
Batch7 step300 checkpoint SHA256: d34ad65890cbb6a12aac3fc35bcab71709d680bff5a3aae2d93e010db1cc0e0d
fold0 train/validation: 176/44
runtime: anchor_bounded_srr_correction
decode: outputs["logits"].argmax
primary pathology metrics: positive-GT cases
no-T2 edema: exact zero throughout
```

## Controller Prompt

你必须按 executor plan 的 wave 顺序执行，不能跳过、合并或缩短科学阶段。

### 第一原则：先修证据真实性

在任何新训练前，必须修复 intervention runner 和 validator。每个 mode 必须真实运行同一 checkpoint 的 44 例推理，写入独立 prediction root、manifest、command hash 和逐病例 prediction SHA256。不得从 formal casewise 表复制指标。

以下为硬门：

- `anchor_identity` 与 `production_gate_closed` 每例 changed voxels 必须为 0，softmax 最大差 `<=1e-6`；
- proposal-only、refiner-only、learned source、gate-one、prototype on/off、semantic memory on/off 和 no-anchor 都必须拥有独立 predictions；
- 除 identity/gate-closed 预期等价外，不同 mode 的 44-case prediction hash 集不得全部相同；
- 空值、placeholder、复制来源、复用 prediction root 必须让 validator 非零退出；
- 原 Batch7 错误表必须作为 known-bad fixture 被 validator 拒绝。

如果这些要求未通过，不得训练，不得写 `VERIFIED_COMPLETE`。

### 第二原则：显式解决 dictionary 和 discovery 缺口

必须将 named negative memory 改为真实 category bank：scar 的 normal myocardium、blood pool、outside myocardium、LGE bright non-scar、anchor remote FP；edema 的对应 T2-present categories。每类必须有 tensor、case IDs、count、valid mask 和完整 hash。样本不足时 mask 关闭，禁止 deterministic axis、random、repeat-last 或复制其他类别。

必须将 discovery 改成真正 anchor-free：modal encoders 执行一次，discovery retrieval 使用 `anchor_features=None`，confirmation 才读取 nnU-Net context。置零 confirmation context 时，discovery logits 最大差必须 `<=1e-6`，confirmation 至少一个真实病例变化 `>1e-5`。

### 第三原则：真实干预后再分阶段训练

必须先用修复后的 runner 对 Batch7 step300 checkpoint 完成全 44 例 intervention replay，回答当前 proposal、refiner、arbiter、gate 各自效果。

之后严格按以下顺序：

```text
proposal-only 600 steps
-> scar refiner 300 steps
-> edema refiner 300 steps
-> accepted refiner source arbiter 200 steps
-> production gate 200 steps
```

Proposal 阶段未通过配置中的继续门时，必须停止所有后续训练并返回 Planner，不得继续训练 refiner/gate，也不得自行放宽阈值。

Scar/edema refiner 必须分别与本病种 proposal-only 比较。未通过接受门的 refiner 必须在正式路径 hard-disable，不能交给 arbiter 平均。Source arbiter 只能训练已接受的 pathology source；未接受病种固定使用 proposal-only。

### 第四原则：Controller 必须主动修复

Executor 出现以下问题时，Controller 必须在当前任务范围内立即要求修复并重新运行相关 wave：

- 实现与 config/plan 不一致；
- intervention 共用输出目录或结果相同；
- identity 不为零；
- semantic memory 仍消费 deterministic buffers；
- discovery 仍读取 anchor context；
- freeze/trainable groups 不符合阶段合同；
- Slurm wrapper、Python、hash、split、case、decode 或 aggregation 错误；
- validator 只检查文件存在；
- CURRENT/wiki/fingerprint 未更新。

只有需要改变模型主体、训练预算、数据范围、分支数量、外部资源许可或科学门槛时，才停止并交给用户/Planner。普通代码、测试、运行、聚合和 receipt 问题不得上交用户。

### 第五原则：完成语义

Controller 必须负责所有 Slurm jobs 到 terminal accounting，完成 post-completion aggregation、真实 final interventions、strict validator、known-bad、mapper final、wiki/CURRENT/fingerprint 和本地轻量 commit。

禁止以 submitted、pending、running、monitor、unit-test pass、gradient nonzero、fixed overfit pass 或“formal300 已完成”代替本任务完成。

Controller report 首段必须用自然中文说明：真正修了什么、哪些组件独立有效或无效、为什么可以停、下一步由 Planner 决定什么。结尾必须包含：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status:
experiment_adequacy_decision:
contract_compliance_status:
required_outputs_complete:
validators_passed:
all_jobs_terminal:
aggregation_complete:
git_commit_decision:
git_push_decision:
blocked_actions:
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```

`VERIFIED_COMPLETE` 只代表本修复合同完成，不代表路线成功，也不授权 Batch8、fold expansion、Cine、validation 或 hosted claim。

## Executor Worker Contract

Executor 只能按 executor plan 的当前 wave 工作。必须返回真实 diff、命令、测试、runtime path、job ID 和输出；不能自行宣布整体完成，不能跳过失败阶段，不能用 placeholder 或复制表补 required outputs。

所有源码、配置、测试、轻量证据和 wiki 修改只写入授权路径。checkpoint、NIfTI、raw predictions、大日志和 `.pt` asset 留在 runtime，不得提交 Git。

## Mapper Contract

Mapper 在实现完成后做 draft，在所有运行和最终修复完成后做 final。必须检查 dictionary、semantic memory、anchor-free discovery、proposal、refiner、source arbiter、production gate 到 final logits 的真实链路，以及 wiki/COMPONENTS/architecture fingerprint 是否与最终代码和证据一致。Mapper 不做科学晋级判断。
