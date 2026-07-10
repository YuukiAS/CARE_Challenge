---
task_key: "YYYYMMDD_short_slug"
project: "CARE_Challenge"
status: "READY"
task_type: "controller"
controller_mode: true
execution_mode: "controller_supervised"
requires_execution_controller: true
planner: "ChatGPT/GPT thread"
controller: "Codex controller session"
executor: "separate Codex executor session/subagent"
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: "prompts/tasks/<task_key>_executor_plan.yaml"
mapper: "separate read-only Codex mapper session/subagent"
mapper_slots: 1
mapper_required: true
architecture_impact: "component"
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: false
continuity_backend: "none"
review_mode: "independent_thread"
reviewer: "separate_readonly"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
required_evidence: ["controller_context", "controller_ledger", "controller_bootstrap_snapshot", "implementation_snapshot", "mapper_report_draft_if_required", "finalizer_state", "mapper_report_final_if_required", "architecture_delta_final_if_required", "validator_report", "controller_report"]
forbidden_substitutes: ["controller inventing a new route", "executor self-review", "controller writing review.md", "reviewer as controller subagent", "missing result directory ignored", "strict validator errors swallowed", "monitor packet treated as completion", "pending Slurm treated as blocked before threshold", "unauthorized fold expansion or upload"]
route_promotion_gate: "Controller cannot decide route promotion; pre-review controller report must write NOT_REVIEWED."
experiment_adequacy_gate: "Controller may classify evidence for reviewer context but cannot make final scientific resolution before review."
route_negative_gate: "Controller cannot decide route-negative scientific stop; pre-review controller report must write NOT_REVIEWED."
scientific_completion_gate: "Final scientific resolution requires independent reviewer token and later GPT planner judgment."
diagnostic_publication_gate: "Only local lightweight packet commit for separate review is allowed; no diagnostic push."
diagnostic_publication_scope: ["controller_report", "controller receipts", "finalizer_state", "mapper reports", "validator reports", "small Markdown/CSV/JSON evidence"]
blocked_after_diagnostic_publication: ["validation_upload", "validation_packaging", "fold_expansion", "hosted_metric_claim", "route_promotion", "scientific_stop", "next_stage_training", "push"]
failure_escalation_policy: "Escalate inside this policy only; new scientific direction requires NEEDS_GPT_PLANNER."
executor_subtasks: ["results/<task_key>/subagents/executor_prompt.md"]
mapper_subtasks: ["results/<task_key>/subagents/mapper_prompt.md"]
reviewer_prompt_path: "results/<task_key>/subagents/reviewer_prompt.md"
controller_report_path: "results/<task_key>/controller_report.md"
allowed_next_states: ["EXECUTION_PLANNED", "EXECUTOR_RUNNING", "MAPPER_DRAFT_RUNNING", "FINALIZER_RUNNING", "MAPPER_FINAL_RUNNING", "VALIDATOR_RUNNING", "PACKET_COMMITTED_FOR_REVIEW", "NEEDS_MONITOR", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_SUBAGENT_LAUNCH", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: true
allow_git_commit: true
auto_git_push: false
allow_git_push: false
allow_diagnostic_push: false
---

# CARE Controller Task: <short title>

## Goal

State the CARE objective, target metric or local proxy, and authorized
mechanism route. The controller may supervise execution only inside this
GPT-authored scope.

## Lifecycle

1. Controller bootstraps from current repo state and writes receipts.
2. Controller launches or writes a separate executor worker contract.
3. Executor performs authorized implementation/evidence work.
4. Controller writes `implementation_snapshot.md`.
5. Mapper draft runs if `mapper_required: true`.
6. Durable continuity runs through `slurm_dependency` or `tmux_watcher` when
   required.
7. `FINALIZER_A` performs terminal accounting, runtime-output checks, and
   aggregation, then writes `finalizer_state.json`.
8. Mapper final reconciles code/evidence/wiki when required.
9. `FINALIZER_B` runs validators, wiki/history checks, `git diff --check`, and
   the single authorized local packet commit.
10. Controller writes `controller_report.md` confirming the committed packet and
    stops.
11. Separate read-only reviewer later writes and commits `review.md`.
12. User manually pushes.

## Durable Continuity Contract

If this task submits Slurm jobs, list required job IDs, runtime output paths,
aggregator command, validator commands, and the chosen backend.

For `slurm_dependency`, submit the finalizer with
`scripts/ops/submit_care_dependency_finalizer.py` and record finalizer job ID,
command, log path, lock path, and result directory.

For `tmux_watcher`, record namespace-local session name, PID, command, log path,
lock path, and result directory.

## Parallel Executor Contract

If `executor_count > 1`, `executor_slots > 1`, or
`parallel_execution_allowed: true`, provide a machine-readable executor plan at
`executor_plan_path` using `prompts/templates/EXECUTOR_PLAN_TEMPLATE.yaml`.
Validate it with `scripts/ops/validate_executor_plan.py`. The controller must
not increase executor count, overlap write scopes, share worktrees, merge out of
order, or ignore merge conflicts.

## Required Receipts

The final packet must include or validate:

```text
controller_context.json
controller_ledger.csv
controller_bootstrap_snapshot.md
implementation_snapshot.md
finalizer_state.json
mapper_report_draft.md
mapper_report_final.md
architecture_delta_final.md
controller_report.md
```

## Subagent Fallback

If Codex cannot automatically launch separate executor/mapper sessions, write
the prompt files under `results/<task_key>/subagents/`, set
`NEEDS_SUBAGENT_LAUNCH` or `NEEDS_HUMAN_APPROVAL`, and stop. Do not pretend
separation happened.

## Git Policy

Local commit is allowed only for the current task's lightweight final packet.
No push is allowed. The commit is not route promotion, validation readiness,
hosted metric claim, scientific stop, fold expansion, or next-stage
authorization.

## Controller Report Required Ending

End `controller_report.md` with:

```text
controller_run_status: COMPLETE | INCOMPLETE | BLOCKED
operational_completion_status: COMPLETE | INCOMPLETE
experiment_adequacy_decision: PASS | FAIL | PARTIAL | EVIDENCE_NOT_FOUND | NOT_REVIEWED
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_PACKET_COMMITTED_FOR_REVIEW | DO_NOT_PUBLISH | NOT_APPLICABLE
git_commit_decision: COMMIT_LOCAL_PACKET | SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
  - path
blocked_actions:
  - validation packaging/upload/fold expansion/hosted metric claim/next-stage training remain blocked
next_required_action: separate reviewer writes review.md
reason_if_not_published: ...
reason_if_no_route_promotion: awaiting independent review
```

## Forbidden

The controller, executor, mapper, finalizer, and validator must not write
`review.md`, launch an internal auditor, grant audited-go, decide final route
promotion, decide final scientific stop, or push.
