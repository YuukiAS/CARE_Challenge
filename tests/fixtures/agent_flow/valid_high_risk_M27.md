---
task_key: 20260711_valid_high_risk_m27
task_kind: scientific_milestone
task_type: controller
controller_mode: true
milestone_number: 27
milestone_id: M27
status: DRAFT_FOR_PLANNING_REVIEW
risk_level: high
route_change: true
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: tests/fixtures/agent_flow/valid_high_risk_M27_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: false
continuity_backend: none
review_mode: independent_thread
reviewer: separate_readonly
review_required: true
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: no route promotion before independent review
experiment_adequacy_gate: not applicable to this protocol fixture
route_negative_gate: reviewer plus planner only
scientific_completion_gate: not applicable to this protocol fixture
diagnostic_publication_gate: local lightweight packet only
diagnostic_publication_scope: [md, csv, json]
blocked_after_diagnostic_publication: [push, upload, route_promotion]
planning_review_required: true
planning_reviewer: separate_gpt_thread
planning_review_path: tests/fixtures/agent_flow/valid_high_risk_M27_planning_review.md
planning_review_token: ""
planning_reviewed_commit: ""
---

# Synthetic M27 Agent-Flow Fixture

## Execution Contract

```yaml
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: tests/fixtures/agent_flow/valid_high_risk_M27_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: false
continuity_backend: none
review_mode: independent_thread
reviewer: separate_readonly
```

history_files_read:

- `wiki/current_state.yaml`
- `wiki/history/COMPARISON.md`
- `wiki/history/<predecessor>/README.md`
- `wiki/history/<predecessor>/COMPONENTS.csv`
- `wiki/history/<predecessor>/components/*.md`

## Controller Prompt

Synthetic controller fixture for protocol validation only.

## Executor Worker Contract

Synthetic executor fixture for protocol validation only.

## Mapper Contract

Synthetic mapper fixture for protocol validation only.

## Reviewer Prompt

Synthetic reviewer fixture for protocol validation only.
