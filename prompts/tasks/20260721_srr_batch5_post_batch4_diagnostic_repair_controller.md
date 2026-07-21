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
backbone_replacement_allowed: false
next_batch_authorization: planner_only
---

## Execution Contract

本任务只执行 Batch 5。目标是用 Batch 4 的既有 checkpoint 查清：

```text
checkpoint/decode 语义是否正确
proposal 是否有信号
refiner 是否改善 proposal
production gate 是否压制有效修正
当前 loss 是否在结构上鼓励 near-identity
现有组件在 oracle 意义下有多少可兑现上界
```

不得训练，不得修改 checkpoint 权重，不得重建 prototype/memory，不得更换或比较 U-Mamba、MedSAM、MedNeXt、nnU-Net 等骨干，不得扩 fold、启动 Cine、上传 validation、写 hosted claim 或启动 Batch 6。

开始前同步 `main`，确认工作树安全，并读取：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/routes/handoffs/CURRENT.md
docs/plans/laneB_round04_active_srr_batch5_post_batch4_diagnostic_repair.md
docs/plans/laneB_round04_active_srr_batch5_loss_authority_addendum.md
configs/srr_production/myops_batch5.yaml
prompts/tasks/20260721_srr_batch5_post_batch4_diagnostic_repair_executor_plan.yaml
scripts/training/run_srr_propref_myops_fold0.py
src/care_myocardium/losses/srr_losses.py
results/20260721_srr_batch4_forced_fold0_training/
```

仓库固定为：

```text
/users/a/e/aereinh/CARE
main
```

禁止写入 `/overflow/htzhu/CARE` 和 Route A/B/C worktree。

## Controller Prompt

你是 Controller，也是 Coordinator 和 acceptance owner。你必须检查 Executor 的真实 diff、命令、参数 hash、checkpoint/case/decode hash、loss call graph、梯度矩阵、Slurm 终态、聚合和 validator。发现缺口时，在当前 Batch 内退回同一 Executor 修复；不得请求 critic/reviewer。

执行组织边界：若使用 tmux，tmux 只作为 `batch5_executor` 的运行容器或短 watcher 容器。Controller/Coordinator/acceptance owner 必须由非 tmux 的当前 Codex 主线线程执行；tmux session 不得承担 controller verification、reviewer、push 或下一 Batch 授权职责。

固定任务图：

```text
B5-00 bootstrap and immutable Batch4 binding
B5-01 evaluation/decode repair
B5-02 final-loss and production-authority audit
B5-03 production correction interventions
B5-04 44-case same-checkpoint diagnostic inference
B5-05 paired aggregation and oracle headroom
B5-06 prototype provenance and validator repair
B5-07 CURRENT/wiki/fingerprint repair
B5-08 controller verification and unique Batch6 direction
```

不可改变：

```text
fold = 0
validation cases = 44
checkpoint candidates = 600,1200,1800
historical selected checkpoint SHA = bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6
optimizer steps = 0
model/checkpoint/prototype/backbone weights immutable
```

允许 `backward()` 做梯度诊断，但禁止 `optimizer.step()` 和任何参数更新。每个 probe 前后必须证明参数 hash 不变或重新加载同一 checkpoint。

### 必须完成的诊断

1. 用 `anchor_bounded_srr_correction + outputs["logits"].argmax + positive-GT population` 重新排序 step 600/1200/1800；`pathology_aware` 仅作诊断。
2. 在相同 checkpoint、44 cases、anchor、prototype/memory、argmax decode 下运行：

```text
anchor_identity_control
anchor_bounded_full
srr_no_anchor_control
anchor_bounded_proposal_only
anchor_bounded_refiner_only
production_gate_closed
production_gate_open_bounded_control
```

3. 直接记录 `production_correction_gate`、raw/bounded correction、proposal logits、refiner logits、final logits；旧 baseline/arbitration gate 不能冒充 production gate。
4. 从正式 `propref_loss` 解析实际 loss、别名和有效权重，回答：

```text
是否有直接监督 outputs["logits"] 的 scar/edema GT loss
production_correction_gate 是否获得纠错梯度
correction_opportunity 是否仍连接旧 arbitration
bounded-correction penalty 是否偏好 correction -> 0
refiner-effect penalty 是否偏好 residual -> 0
proposal/refiner/dictionary 到最终 gate 的真实梯度路径
```

5. 输出仅用于诊断的 `oracle_headroom.csv`，从 identity/full/proposal-only/refiner-only/gate-open 中记录每个 case/pathology 的 GT-aware best mode、oracle Dice gain、correctable anchor-error voxels 和 avoided harmful-correction voxels。必须标记 `diagnostic_only=true`、`deployable_candidate=false`。

### Required outputs

```text
results/20260721_srr_batch5_post_batch4_diagnostic_repair/implementation_snapshot.md
results/20260721_srr_batch5_post_batch4_diagnostic_repair/evaluation_semantics_audit.md
results/20260721_srr_batch5_post_batch4_diagnostic_repair/loss_authority_audit.md
results/20260721_srr_batch5_post_batch4_diagnostic_repair/loss_parameter_gradient_matrix.csv
results/20260721_srr_batch5_post_batch4_diagnostic_repair/loss_directionality_audit.csv
results/20260721_srr_batch5_post_batch4_diagnostic_repair/checkpoint_reranking.csv
results/20260721_srr_batch5_post_batch4_diagnostic_repair/mode_intervention_metrics.csv
results/20260721_srr_batch5_post_batch4_diagnostic_repair/casewise_mechanism_attribution.csv
results/20260721_srr_batch5_post_batch4_diagnostic_repair/oracle_headroom.csv
results/20260721_srr_batch5_post_batch4_diagnostic_repair/prototype_manifest_audit.json
results/20260721_srr_batch5_post_batch4_diagnostic_repair/batch6_unique_repair_decision.md
results/20260721_srr_batch5_post_batch4_diagnostic_repair/mapper_report_final.md
results/20260721_srr_batch5_post_batch4_diagnostic_repair/controller_report.md
results/20260721_srr_batch5_post_batch4_diagnostic_repair/completion_check.md
results/20260721_srr_batch5_post_batch4_diagnostic_repair/MANIFEST.md
```

### Batch 6 unique decision

只允许一个：

```text
B5_FINAL_OBJECTIVE_ALIGNMENT_BOTTLENECK
B5_OUTPUT_AUTHORITY_BOTTLENECK
B5_PROPOSAL_PRECISION_BOTTLENECK
B5_REFINER_EFFECTIVENESS_BOTTLENECK
B5_EVALUATION_SEMANTICS_ONLY_ISSUE
B5_INSUFFICIENT_MECHANISM_EVIDENCE
```

固定优先级：

1. oracle 平均增益至少 `+0.01`、full 仍接近 identity，且 production gate 缺少直接 final-pathology repair loss或 magnitude penalty 明确偏好零修正：`FINAL_OBJECTIVE_ALIGNMENT`。
2. loss 路径合理，但 gate-open 相对 full 的平均 positive-case Dice 至少 `+0.005`：`OUTPUT_AUTHORITY`。
3. proposal-only 无信号或 remote/component FP 明显恶化：`PROPOSAL_PRECISION`。
4. proposal-only 有信号，但 refiner-only/full 相对 proposal 平均下降至少 `0.002`：`REFINER_EFFECTIVENESS`。
5. 只有 selection/decode 修复改变结论：`EVALUATION_SEMANTICS_ONLY`。
6. 其他：`INSUFFICIENT_MECHANISM_EVIDENCE`。

不得选择 backbone replacement，不得启动 Batch 6。

### Slurm boundary

仅允许 inference/gradient-audit short job：

```text
Python: /users/a/e/aereinh/CARE/envs/env_CARE/bin/python
primary: htzhulab
900s pending: isolated a100-gpu mirror
volta-gpu: forbidden
max runtime: 3600s
optimizer steps: 0
parameter updates: 0
winner lock: required
finalizer: afterany
```

Controller 负责到所有 attempts terminal、聚合和 strict validator 完成。`SUBMITTED/PENDING/RUNNING/NEEDS_MONITOR` 不是完成。

### Controller ending

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
blocked_actions: training,backbone_swap,fold_expansion,Cine,validation_upload,hosted_claim,Batch6
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
batch6_unique_repair_direction:
```

只有全部 required outputs、参数不变、optimizer step 为 0、44 例诊断完整、prototype hashes 完整、CURRENT/wiki 更新且 validator exit 0，才可写 `VERIFIED_COMPLETE`。

## Executor Worker Contract

Executor 只有一个，按 executor plan 顺序实现和运行。不能宣布整个 Batch 完成，不能写 `review.md`，不能 push，不能训练、换骨干或启动下一 Batch。所有新结果写入：

```text
results/20260721_srr_batch5_post_batch4_diagnostic_repair/
```

不得覆盖 Batch 4 历史结果目录。

## Mapper Contract

Mapper 更新 CURRENT、root wiki、COMPONENTS/architecture fingerprint，明确记录 Batch 4 足额但信号不足、Batch 5 final-loss authority、production gate、oracle headroom 状态，以及 backbone replacement 未测试、未授权。Mapper 不训练、不作下一 Batch 授权。

## Reviewer Prompt

`review_required: false`。不得启动独立 reviewer。Controller 完成后返回 Planner。
