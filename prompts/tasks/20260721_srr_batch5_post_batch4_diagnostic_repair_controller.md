---
task_key: 20260721_srr_batch5_post_batch4_diagnostic_repair
task_kind: scientific_milestone
task_type: post_training_diagnostic_repair
controller_mode: coordinator_acceptance_owner
milestone_number: null
milestone_id: null
status: READY_FOR_CONTROLLER
risk_level: medium
route_change: false
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260721_srr_batch5_post_batch4_diagnostic_repair_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: component
wiki_update_required: true
diagram_update_required: false
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
validation_upload_allowed: false
hosted_metric_claim_allowed: false
fold_expansion_allowed: false
training_allowed: false
next_batch_authorization: planner_only
---

## Execution Contract

本任务只执行 Batch 5：审计和修复 Batch 4 的 checkpoint selection、decode 语义、production correction gate 证据、prototype provenance 和机器状态。不得训练、不得修改 checkpoint 权重、不得重建 prototype/memory、不得上传 validation、不得启动 Cine、不得启动 Batch 6。

权威输入：

```text
prompts/routes/handoffs/CURRENT.md
docs/plans/laneB_round04_active_srr_batch5_post_batch4_diagnostic_repair.md
configs/srr_production/myops_batch5.yaml
prompts/tasks/20260721_srr_batch5_post_batch4_diagnostic_repair_executor_plan.yaml
results/srr_production/code_maturity/batch4_planner_audit_and_batch5_decision.md
results/20260721_srr_batch4_forced_fold0_training/
```

运行仓库：

```text
/users/a/e/aereinh/CARE
main
```

禁止写入 `/overflow/htzhu/CARE` 和 Route A/B/C worktree。

## Controller Prompt

你是 CARE Batch 5 Controller，也是 Coordinator 和最终执行验收者。你不能只启动 Executor、等待自然语言总结后退出。你必须持续检查实际 git diff、命令、checkpoint/case/decode hashes、Slurm 状态和病例级结果；发现缩水、语义偏移或缺失证据时，必须把当前 wave 退回同一 Executor 原地修复。

开始时：

```bash
cd /users/a/e/aereinh/CARE
git status --short
git fetch --all --prune
git switch main
git pull --ff-only origin main
```

工作树不干净时保全并报告，不得覆盖未知改动。

必须读取：

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
.agents/skills/care-mapper/SKILL.md
.agents/skills/slurm-routing-partition/SKILL.md
wiki/README.md
```

视觉图版本由 Planner 已完成：

```text
diagram_versions_read: SRR-v2, SRR-v2.5, SRR-v3
visual_read_status: COMPLETE_FROM_CHATGPT_PROJECT_MATERIALS
```

恢复出的路线目标是：availability-aware selective retrieval、semantic representation bank、anatomy-guided pathology proposal、scar/edema soft-ROI refinement 和 bounded nnU-Net correction。Batch 5 不得把 SRR 退化为普通后处理。

### 固定任务图

```text
B5-00 bootstrap and immutable Batch4 binding
B5-01 evaluation/decode repair
B5-02 production correction intervention implementation
B5-03 44-case same-checkpoint diagnostic inference
B5-04 paired aggregation and mechanism attribution
B5-05 prototype provenance and semantic validator repair
B5-06 CURRENT/wiki/fingerprint repair
B5-07 controller terminal verification and unique Batch6 direction
```

每个阶段都 blocking。不得用旧 Batch 4 文件、自然语言解释或 validator pass 替代缺失的新 Batch 5 输出。

### 不可更改的科学输入

```text
fold = 0
validation cases = 44
checkpoint candidates = 600, 1200, 1800
historical selected checkpoint SHA = bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6
optimizer steps = 0
model weights immutable
prototype/memory immutable
```

### 评价修复

Checkpoint reranking 的正式输入必须是：

```text
runtime_mode = anchor_bounded_srr_correction
decode = outputs["logits"].argmax
population = positive-GT cases for each pathology
```

`pathology_aware` 只能作为 diagnostic decode，不能授予 checkpoint authority。

必须明确输出 positive-GT 与 all-case empty-safe 两套指标。不得把约 0.78 的 all-case edema Dice 与 0.3944 positive-case baseline 混为一谈。

### 真实机制干预

在不改变 checkpoint 参数的前提下实现并运行：

```text
anchor_identity_control
anchor_bounded_full
srr_no_anchor_control
anchor_bounded_proposal_only
anchor_bounded_refiner_only
production_gate_closed
production_gate_open_bounded_control
```

所有模式必须使用相同 checkpoint SHA、相同 44 cases、相同 raw OOF anchor、相同 prototype/memory 和相同 argmax decode。

必须直接从模型输出记录：

```text
production_correction_gate
bounded_scar_correction
bounded_edema_correction
scar/edema proposal logits
scar/edema refiner logits
final logits
```

不得用旧 `baseline_residual_gate` 或 branch arbitration weight 冒充 production gate。

### Controller 反偷懒检查

每次 Executor 提交结果后，Controller 必须检查：

```text
git diff --stat
git diff --check
changed file list
checkpoint SHA and case-list hashes
no optimizer call/step
all intervention modes present
44 NIfTI outputs per required mode or exact fail-closed evidence
positive-case/all-case metric names
production-gate fields nonempty
historical Batch4 files unchanged
strict validator exit code
```

出现以下情况必须退回修复：

```text
只重排 CSV 不运行真实 intervention
proposal-only/refiner-only 使用不同 checkpoint
pathology-aware 继续作为正式 selection authority
使用 all-case edema Dice 作主结果
只记录 baseline/arbitration gate
feature/config hash 为空
修改 Batch4 historical packet
写 review.md
启动训练
```

### Slurm inference-only

只允许 short inference job：

```text
Python: /users/a/e/aereinh/CARE/envs/env_CARE/bin/python
primary: htzhulab
900s pending: isolated a100-gpu mirror
volta-gpu: forbidden
max runtime: 3600s
optimizer steps: exactly 0
winner lock: required
finalizer: afterany
```

Controller 必须负责到所有 attempts terminal、aggregation 和 validator 完成。`SUBMITTED`、`PENDING`、`RUNNING`、`NEEDS_MONITOR` 不是完成。

### Batch 6 唯一方向

最终文件 `batch6_unique_repair_decision.md` 必须只选一个：

```text
B5_OUTPUT_AUTHORITY_BOTTLENECK
B5_PROPOSAL_PRECISION_BOTTLENECK
B5_REFINER_EFFECTIVENESS_BOTTLENECK
B5_EVALUATION_SEMANTICS_ONLY_ISSUE
B5_INSUFFICIENT_MECHANISM_EVIDENCE
```

不得同时推荐多条训练路线，不得直接启动 Batch 6。

### Controller Ending

`controller_report.md` 必须以以下字段结束：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status:
experiment_adequacy_decision: DIAGNOSTIC_ONLY_NO_TRAINING
contract_compliance_status:
required_outputs_complete:
validators_passed:
all_jobs_terminal:
aggregation_complete:
git_commit_decision:
git_push_decision: NO_PUSH
blocked_actions: training,fold_expansion,Cine,validation_upload,hosted_claim,Batch6
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
batch6_unique_repair_direction:
```

只有全部完成条件满足时才写 `VERIFIED_COMPLETE`。

## Executor Worker Contract

Executor 只有一个，按 executor plan 顺序工作。Executor 负责实现、命令和证据写入，但不能自行宣布整个 Batch 5 完成，不能写 `review.md`，不能 push，不能启动训练或下一 Batch。

Executor 必须将所有新结果写入：

```text
results/20260721_srr_batch5_post_batch4_diagnostic_repair/
```

不得覆盖：

```text
results/20260721_srr_batch4_forced_fold0_training/
```

## Mapper Contract

Mapper 在代码和诊断结束后读取最终实现与结果，更新 CURRENT、root wiki、COMPONENTS/architecture fingerprint，使其反映：

```text
Batch4 operationally complete
Batch4 scientific signal insufficient
Batch5 diagnostic repair active/complete
production correction mechanism evidence status
Cine remains proxy/incomplete
```

Mapper 不训练、不提交 Slurm、不作下一 Batch 授权。

## Reviewer Prompt

`review_required: false`。不得启动独立 reviewer。Controller 完成执行验收后将结果返回 Planner。