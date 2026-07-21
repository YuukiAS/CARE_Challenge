---
task_key: "YYYYMMDD_short_slug"
project: "CARE_Challenge"
status: "READY"
task_kind: "scientific_milestone | maintenance | hotfix | audit"
task_type: "milestone | execution | controller"
controller_mode: false
milestone_number: null
milestone_id: null
risk_level: "low | medium | high"
route_change: false
scientific_decision_scope: "none | mechanism_signal | promotion_candidate | stop_candidate"
execution_mode: direct_executor
requires_execution_controller: false
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: "prompts/tasks/<task_key>_executor_plan.yaml"
mapper_slots: 0
mapper_required: false
architecture_impact: "none | component | system"
wiki_update_required: false
diagram_update_required: false
slurm_runtime_continuity_required: false
continuity_backend: none
review_required: false
review_mode: none
reviewer: none
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
allow_git_commit: false
auto_git_commit: false
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: "No route promotion without Planner/user authorization."
experiment_adequacy_gate: "Task-specific evidence gate."
route_negative_gate: "No scientific stop without adequate evidence and Planner/user authorization."
scientific_completion_gate: "Operational completion is not scientific resolution."
diagnostic_publication_gate: "none unless explicitly authorized"
diagnostic_publication_scope: []
blocked_after_diagnostic_publication: ["validation_upload", "validation_packaging", "fold_expansion", "hosted_metric_claim", "next_stage_training"]
allowed_next_states: ["NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_MONITOR", "NEEDS_GPT_PLANNER", "STOP"]
---

# Task: <short title>

## Execution Contract

Choose one schema:

- Direct executor: `execution_mode: direct_executor`,
  `controller_mode: false`, `requires_execution_controller: false`, exactly one
  executor.
- Controller supervised: `execution_mode: controller_supervised`,
  `task_type: controller`, `controller_mode: true`,
  `requires_execution_controller: true`.

Use `prompts/schemas/milestone_staging.schema.yaml`,
`prompts/schemas/executor_plan.schema.yaml`,
`prompts/schemas/controller_packet.schema.yaml`, and
`prompts/schemas/runtime_review.schema.yaml` as the machine source. Runtime review is optional and applies only when `review_required: true`.

## Goal

State the concrete objective, target metric or local proxy, and what is out of
scope.

## Authorized Scope

List files, scripts, data splits, cached artifacts, and commands the executor
may touch. State explicit forbidden actions.

## Evidence Requirements

List required lightweight Markdown/CSV/JSON evidence. Missing evidence must be
reported as `evidence not found` or `未找到证据`.

## Review Requirement

Default review is disabled. Use `review_required: true`, `review_mode`, and
`reviewer` only when the Planner or user explicitly requires an independent
read-only runtime review. Missing `review.md` must not block a task whose
frontmatter keeps `review_required: false`.

## Final Output Readability

Before the task, result, controller report, or explicit review is sent to a
user or Planner, apply `prompts/FINAL_OUTPUT_READABILITY_POLICY.md`. Start with
a natural Chinese judgment that explains the main problem, why it happened, what
to do now, and what not to do yet. Put internal labels, paths, metrics, commands,
and machine fields after the meaning is clear. Technical details and training
contracts belong at the end.

## Git Policy

Default push is false. Local commit is allowed only when the task explicitly
sets the git fields and the schema/validator permit it. User pushes manually.
