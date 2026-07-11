---
task_key: 20260711_srr_v3_m10_complete_mechanism_repair
task_kind: scientific_milestone
task_type: controller
controller_mode: true
milestone_number: 10
milestone_id: M10
status: PLANNING_REVIEW_RUNNING
risk_level: high
route_change: true
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 3
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: independent_thread
reviewer: separate_readonly
review_required: true
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: independent runtime reviewer plus later GPT planner; M10 cannot promote itself
experiment_adequacy_gate: reconciliation in progress; no execution authorization
route_negative_gate: M10 cannot declare scientific stop
scientific_completion_gate: reconciliation in progress; no execution authorization
diagnostic_publication_gate: local lightweight reviewed packet only
diagnostic_publication_scope: [md, csv, json]
blocked_after_diagnostic_publication: [validation_packaging, validation_upload, hosted_metric_claim, fold_expansion, route_promotion, scientific_stop, M11_execution]
planning_review_required: true
planning_reviewer: separate_gpt_thread
planning_review_path: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_planning_review.md
planning_review_token: ""
planning_reviewed_commit: ""
---

# M10 planning reconciliation in progress

The prior planning review is invalid because it reviewed the obsolete planner baseline
`e26895b99dc142ff64ea6e6f291600c6b67af98c` rather than the latest planner draft
`828735482396d6d727d2294e88c89868e3118ad3` from `agent/m10-planner-draft`.

This intermediate state intentionally blocks Codex integration and M10 execution while the critic performs a three-way reconciliation among:

1. default-branch common baseline `925a00169649a523947e475204e68228cb8816f6`;
2. latest Planner draft `828735482396d6d727d2294e88c89868e3118ad3`;
3. the superseded Critic-reviewed contract formerly at `435abf35a4b1b85d75e58f83bcb58faa0b89efe1`.

No former critic token or reviewed commit is valid in this state.

## Execution Contract

```yaml
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 3
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: independent_thread
reviewer: separate_readonly
```

## Controller Prompt

Blocked while `status: PLANNING_REVIEW_RUNNING`. Do not execute M10, submit jobs, create runtime result packets, merge shared prompts, or start a controller.

## Executor Worker Contract

Blocked while planning reconciliation is incomplete.

## Mapper Contract

Blocked while planning reconciliation is incomplete.

## Reviewer Prompt

Blocked until the final reconciled staging, executor plan, stable contract hash, and new independent planning review are committed and metadata-bound.
