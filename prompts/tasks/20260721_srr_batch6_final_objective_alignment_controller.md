---
task_key: 20260721_srr_batch6_final_objective_alignment
task_kind: scientific_milestone
task_type: final_objective_and_production_gate_repair
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
executor_plan_path: prompts/tasks/20260721_srr_batch6_final_objective_alignment_executor_plan.yaml
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
experiment_adequacy_gate: fixed_overfit_then_300_step_then_conditional_900_step
route_negative_gate: planner_only
scientific_completion_gate: planner_only
diagnostic_publication_gate: false
diagnostic_publication_scope: none
blocked_after_diagnostic_publication: validation_upload,hosted_claim,fold_expansion,Cine,route_promotion,M11,Batch7
training_allowed: true
backbone_replacement_allowed: false
fold_expansion_allowed: false
cine_allowed: false
validation_upload_allowed: false
hosted_metric_claim_allowed: false
next_batch_authorization: planner_only
---

## Execution Contract

本任务只执行 Batch 6。它不是扩大模型规模，而是修复当前训练目标与最终部署输出之间的断裂：proposal/refiner 已经接受 GT 监督，但最终 `outputs["logits"]` 没有直接 pathology 纠错损失，production gate 也没有在 anchor 错误位置打开的明确训练目标。

Batch 6 必须先修复 Batch 5 未闭环的证据，再实现 final pathology loss 和 production gate repair/preserve loss，最后通过 fixed-batch overfit、300-step calibration 和条件式 900-step extension 判断当前 SRR 是否能从 `+0.001` 级 near-identity 推进到至少 `+0.005` 的可用信号。

开始前必须同步 `main`、确认工作树安全，并读取：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
docs/plans/laneB_round04_active_srr_batch6_final_objective_alignment_execution.md
configs/srr_production/myops_batch6.yaml
prompts/tasks/20260721_srr_batch6_final_objective_alignment_executor_plan.yaml
results/20260721_srr_batch5_post_batch4_diagnostic_repair/
scripts/training/run_srr_propref_myops_fold0.py
scripts/srr_production/infer_myops.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/losses/srr_losses.py
```

仓库固定为：

```text
/users/a/e/aereinh/CARE
main
```

禁止写入 `/overflow/htzhu/CARE` 和 Route A/B/C worktree。

### Diagram bootstrap

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3
visual_read_status: COMPLETE
recovered_route_objective: availability-aware multi-scale retrieval -> shared/private/interaction representation -> prototype/memory/negative-space -> anatomy-guided scar/edema proposal -> pathology-specific soft ROI refinement -> directly supervised bounded nnU-Net correction
```

nnU-Net 只能作为 baseline、anchor、context、evidence 和 safety source；不得用 nnU-Net 代替 SRR，也不得在 Batch 6 更换或比较 backbone。

## Controller Prompt

你是 Controller，也是 Coordinator 和 acceptance owner。你必须冻结 Planner 合同和启动 SHA，检查 Executor 的真实 diff、测试、loss 权重解析、checkpoint migration、梯度路径、Slurm 终态、aggregation、required outputs、CURRENT/wiki/fingerprint 和本地轻量 commit。发现同范围缺口时必须退回同一 Executor 修复；不得启动 critic/reviewer，不得把文件存在或 token 当作语义完成。

若使用 tmux，tmux 只作为 `batch6_executor` 或 watcher 容器。Controller verification、科学门判断、commit 和下一 Batch 授权由当前非 tmux Controller 主线承担。

固定任务图：

```text
B6-00 bootstrap and immutable authority binding
B6-01 Batch5 mechanism-evidence reconciliation
B6-02 final pathology objective and production gate implementation
B6-03 fixed two-case 60-step overfit and reload gate
B6-04 formal 300-step fold0 calibration
B6-05 conditional extension to total 900 steps only if the fixed step-300 gate passes
B6-06 selected-checkpoint pure interventions and mechanism aggregation
B6-07 mapper/wiki/fingerprint and strict validation
B6-08 controller verification, local packet commit and return to Planner
```

所有阶段 blocking。B6-01 未完成不得训练；B6-03 未通过不得提交正式训练；B6-04 未通过不得执行 B6-05。

### Immutable authority

```text
fold = 0
train cases = 176
validation cases = 44
edema positive validation cases = 16
scar positive validation cases = 43
source checkpoint step = 1800
source checkpoint SHA = bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6
prototype asset SHA = 8b262f8bb87e0733a48e169c77b028a3833b70cbcd33d2ac2fb4857ba1cbde83
model = SRRProposeRefineMyoPS / m10_d3_hierarchical_memory_propref / full_4scale / base_channels 32
formal output = anchor_bounded_srr_correction
formal decode = outputs["logits"].argmax
primary population = positive-GT pathology cases
```

### B6-01 Batch 5 reconciliation

必须修复并重新验证：

1. 从 Batch 4 正式 wrapper、argparse defaults、variant config、legacy aliases 和 explicit overrides 得到每个 canonical loss 的实际有效权重，`resolved_weight` 不得为空。
2. 使用同 checkpoint 和 44 cases 运行 `proposal_only_gate_one` 与 `refiner_only_gate_one`。前者的 correction/gate 不得读取 refiner，后者不得读取 proposal。
3. 真实计算 proposal precision/recall/lesion recall、component/remote FP、ROI GT coverage/outside ratio，不得写空字段。
4. 修复 Batch 5 validator，使其检查字段内容、干预纯度、parameter hash、exact command 可执行性和终态 receipt 自洽。
5. 该阶段 optimizer steps 必须为 0，所有参数 hash 前后不变。

### B6-02 final objective and gate

严格实现 `configs/srr_production/myops_batch6.yaml` 和 plan 中的公式：

- 使用最终六类 logits 的 one-vs-rest margin直接监督 scar 和 T2-present edema；
- 新增 `loss_final_scar_pathology` 和 `loss_final_edema_t2_present_pathology`；
- production gate 扩为固定 13-channel input；
- checkpoint migration 复制旧 4-channel gate weights/bias，新增通道权重置零；
- 新增 repair/preserve balanced BCE，repair 是 anchor binary prediction 与 GT 不一致，preserve 是 anchor 正确且置信度至少 0.80；
- edema gate supervision 只用于 T2-present；
- canonical weights 完全采用 Batch 6 config；legacy aliases 不得覆盖；
- `loss_correction_opportunity`、`loss_branch_arbitration_consistency`、`loss_bounded_correction`、`loss_refiner_final_label_effect` 权重为 0；
- no-T2 edema 全链 exact zero 必须保持。

必须新增针对以下 known-bad 的测试：

```text
final pathology losses do not consume outputs["logits"]
gate repair loss accidentally consumes legacy segmentation_weight
production gate has no final-pathology repair gradient
no-T2 edema receives gate/final loss supervision
legacy alias overrides canonical Batch6 weights
gate migration changes non-gate checkpoint parameters
proposal-only intervention reads refiner
refiner-only intervention reads proposal
proposal/ROI required fields are blank
validator accepts inconsistent aggregation receipt
```

### B6-03 fixed-batch overfit

使用 Case2002 与 Case1002 固定 pathology patches，60 optimizer steps，只训练 production gate、scar refiner、edema refiner。全部通过条件以 Batch 6 config 为准。Overfit 失败必须在同一 wave 修复，不得用正式长训练绕过。

### B6-04 formal 300-step calibration

从迁移后的 Batch 4 selected checkpoint 开始，运行精确 300 optimizer steps，在 100/200/300 对全部 44 cases 做 full-volume evaluation。训练参数、trainable/frozen groups、loss weights 和评价语义必须与 config 一致。

Step 300 continuation gate：

```text
mean scar/edema positive-case Dice delta >= +0.003
each pathology Dice delta >= -0.002
help >= harm
HD95 relative worsening <= 5% each pathology
remote-FP relative worsening <= 5% each pathology
no-T2 edema exact zero
finite losses and nonzero final/gate repair gradients
```

任一失败时停止在 300 steps，写诚实终态，禁止 B6-05。

### B6-05 conditional 900-step extension

仅在 step-300 gate 全部通过后继续到总计 900 optimizer steps。Step 301 起只额外解冻 scar/edema dictionaries 和 evidence heads；encoder、retrieval 和 prototype/memory 继续冻结。Full-volume eval 固定在 total steps 450/600/900。

训练到训练依赖必须使用 `afterok`。不得把失败的 300-step stage 用 `afterany` 继续训练。

### B6-06 final mechanism evidence

对最终 selected checkpoint 运行：

```text
anchor_identity_control
full_learned_gate
full_gate_one
full_gate_zero
proposal_only_gate_one
refiner_only_gate_one
```

输出 final loss、gate repair/preserve separation、proposal/ROI 指标、case-wise Dice/HD95/help-harm/remote-FP/component 和 CenterB/CenterC、LGE-only/T2-present 子组。不得用 all-case empty-GT 指标冒充 pathology 进展。

### Slurm boundary

```text
Python: /users/a/e/aereinh/CARE/envs/env_CARE/bin/python
primary: htzhulab
pending 900 seconds: isolated a100-gpu mirror
volta-gpu: forbidden
maximum runtime per stage: 14400 seconds
atomic winner lock: required
pending loser cancellation: required
training dependency: afterok
finalizer/accounting: afterany
```

Controller 必须负责到所有 attempts terminal、post-completion aggregation、strict validators 和 local lightweight commit 完成。Submitted/PENDING/RUNNING/NEEDS_MONITOR/AWAITING_SACCT 不是完成。

### Required outputs

```text
results/20260721_srr_batch6_final_objective_alignment/controller_context.json
results/20260721_srr_batch6_final_objective_alignment/controller_ledger.csv
results/20260721_srr_batch6_final_objective_alignment/controller_bootstrap_snapshot.md
results/20260721_srr_batch6_final_objective_alignment/batch5_reconciliation.md
results/20260721_srr_batch6_final_objective_alignment/resolved_loss_weights.csv
results/20260721_srr_batch6_final_objective_alignment/pure_intervention_metrics.csv
results/20260721_srr_batch6_final_objective_alignment/proposal_roi_metrics.csv
results/20260721_srr_batch6_final_objective_alignment/implementation_snapshot.md
results/20260721_srr_batch6_final_objective_alignment/fixed_batch_overfit.json
results/20260721_srr_batch6_final_objective_alignment/loss_gradient_authority.csv
results/20260721_srr_batch6_final_objective_alignment/training_adequacy.json
results/20260721_srr_batch6_final_objective_alignment/checkpoint_selection.csv
results/20260721_srr_batch6_final_objective_alignment/subgroup_metrics.csv
results/20260721_srr_batch6_final_objective_alignment/help_harm.csv
results/20260721_srr_batch6_final_objective_alignment/final_mechanism_interventions.csv
results/20260721_srr_batch6_final_objective_alignment/slurm_attempts.csv
results/20260721_srr_batch6_final_objective_alignment/finalizer_state.json
results/20260721_srr_batch6_final_objective_alignment/mapper_report_draft.md
results/20260721_srr_batch6_final_objective_alignment/architecture_delta_draft.md
results/20260721_srr_batch6_final_objective_alignment/mapper_report_final.md
results/20260721_srr_batch6_final_objective_alignment/architecture_delta_final.md
results/20260721_srr_batch6_final_objective_alignment/controller_report.md
results/20260721_srr_batch6_final_objective_alignment/completion_check.md
results/20260721_srr_batch6_final_objective_alignment/MANIFEST.md
```

### Controller acceptance

Controller 只有在以下条件全部满足时才能写 `VERIFIED_COMPLETE`：

- Batch 5 reconciliation 字段全部真实非空；
- exact effective weights 与 Batch 6 checkpoint contract 一致；
- gate migration 除允许 keys 外 exact-load；
- fixed-batch overfit 通过；
- formal training budget与 conditional continuation rule 未被缩水；
- 所有 job terminal accounting 完整；
- selected checkpoint 已 reload 后评价；
- 44 cases、正式 argmax、positive-GT/all-case 分离；
- no-T2 edema safety exact；
- strict validator 与 known-bad tests exit 0；
- CURRENT/wiki/COMPONENTS/architecture/fingerprint 与最终代码和结果一致；
- lightweight local commit 完成；
- 没有 push、upload、fold expansion、Cine、backbone swap 或 Batch7。

Controller report 结尾必须包含：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status:
experiment_adequacy_decision: STOP_AT_300 | COMPLETED_900 | OVERFIT_OR_IMPLEMENTATION_FAILED
contract_compliance_status:
required_outputs_complete:
validators_passed:
all_jobs_terminal:
aggregation_complete:
git_commit_decision:
git_push_decision: NO_PUSH
scientific_signal_class: BELOW_USABLE | SMALL_USABLE | CANDIDATE | STRONG
blocked_actions: backbone_swap,fold_expansion,Cine,validation_upload,hosted_claim,route_promotion,M11,Batch7
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```

`VERIFIED_COMPLETE` 只证明 Batch 6 合同完成，不自动说明模型成功，也不授权 fold expansion、submission、Cine 或下一 Batch。

## Executor Worker Contract

Executor 只有一个，严格按 executor plan 顺序执行。Executor 负责代码、测试、preflight、job submission、aggregation 和 evidence，但不能宣布整个 Batch 完成，不能写 `review.md`，不能 push，不能改变 Planner 的 loss、gate、预算、split、freeze scope、continuation gate 或评价语义。

所有新 runtime 和结果写入：

```text
results/20260721_srr_batch6_final_objective_alignment/
logs/srr_batch6/
```

不得覆盖 Batch 4/5 历史结果。

## Mapper Contract

Mapper 必须在实现后和终态结果后各执行一次。更新 root wiki、MODEL、COMPONENTS、architecture、current_state、LINEAGE 和三张当前图，明确区分：final loss/gate 已实现、overfit 是否通过、300/900 training 是否足额、当前科学增益等级、仍未授权的 backbone/fold/Cine/upload。Mapper 不作科学晋级决定。

## Reviewer Prompt

`review_required: false`。不得启动独立 reviewer。Controller 完成后直接返回 Planner。