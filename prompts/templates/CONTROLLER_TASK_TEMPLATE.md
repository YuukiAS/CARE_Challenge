---
task_key: "YYYYMMDD_short_slug"
project: "CARE_Challenge"
status: "READY"
task_type: "controller"
controller_mode: true
execution_mode: "controller_supervised"
requires_execution_controller: true
controller_is_coordinator: true
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
review_required: false
review_mode: "none"
reviewer: "none"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
required_evidence: ["controller_context", "controller_ledger", "controller_bootstrap_snapshot", "implementation_snapshot", "mapper_report_draft_if_required", "finalizer_state", "mapper_report_final_if_required", "architecture_delta_final_if_required", "validator_report", "controller_report", "completion_check"]
forbidden_substitutes: ["controller inventing a new route", "executor self-review", "executor declaring whole-task completion", "controller writing review.md", "reviewer as controller subagent", "missing result directory ignored", "strict validator errors swallowed", "monitor packet treated as completion", "pending Slurm treated as completion", "unauthorized fold expansion or upload", "internal code label used as final scientific judgment"]
route_promotion_gate: "Controller cannot decide route promotion; route promotion remains Planner/user authorization."
experiment_adequacy_gate: "Controller must verify operational and experiment adequacy against the frozen contract before VERIFIED_COMPLETE."
route_negative_gate: "Controller cannot decide route-negative scientific stop; scientific stop remains Planner/user authorization."
scientific_completion_gate: "Operational completion is not final scientific resolution; Planner/user decides the next scientific direction."
diagnostic_publication_gate: "Only local lightweight packet commit is allowed unless explicitly authorized."
diagnostic_publication_scope: ["controller_report", "completion_check", "controller receipts", "finalizer_state", "mapper reports", "validator reports", "small Markdown/CSV/JSON evidence"]
blocked_after_diagnostic_publication: ["validation_upload", "validation_packaging", "fold_expansion", "hosted_metric_claim", "route_promotion", "scientific_stop", "next_stage_training", "push"]
failure_escalation_policy: "Same-scope implementation, environment, Slurm, finalizer, aggregation, or validator failures must be repaired inside the controller loop; new scientific direction requires NEEDS_GPT_PLANNER."
executor_subtasks: ["results/<task_key>/subagents/executor_prompt.md"]
mapper_subtasks: ["results/<task_key>/subagents/mapper_prompt.md"]
reviewer_prompt_path: null
controller_report_path: "results/<task_key>/controller_report.md"
completion_check_path: "results/<task_key>/completion_check.md"
allowed_next_states: ["EXECUTION_PLANNED", "EXECUTOR_RUNNING", "MAPPER_DRAFT_RUNNING", "FINALIZER_RUNNING", "MAPPER_FINAL_RUNNING", "VALIDATOR_RUNNING", "VERIFIED_COMPLETE", "NEEDS_MONITOR", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_REPAIR", "NEEDS_SUBAGENT_LAUNCH", "NEEDS_GPT_PLANNER", "OPERATIONALLY_BLOCKED", "STOP"]
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
3. Executor performs authorized implementation, command, and evidence work.
4. Controller inspects the real git diff, changed files, commands, required
   outputs, frozen contract fields, training budget, data split, and evaluation
   scope after each executor wave.
5. If work is incomplete but still inside the original scope, Controller sends
   the executor back for repair instead of returning to Planner.
6. Mapper draft runs if `mapper_required: true`.
7. Durable continuity runs through `slurm_dependency` or `tmux_watcher` when
   required.
8. The deterministic finalizer performs terminal accounting, runtime-output
   checks, aggregation, and writes `finalizer_state.json`.
9. Mapper final reconciles code/evidence/wiki when required.
10. Controller runs validators, wiki/history checks, and `git diff --check`.
11. Controller writes `controller_report.md` and `completion_check.md` with a
    machine-checkable completion decision.
12. If all completion gates pass and local commit is authorized, Controller
    commits the lightweight packet locally and stops with `VERIFIED_COMPLETE`.
13. User manually pushes. A separate reviewer starts only when
    `review_required: true` is explicitly set.

## Durable Continuity Contract

If this task submits Slurm jobs, list required job IDs, runtime output paths,
aggregator command, validator commands, and the chosen backend.

For `slurm_dependency`, submit the finalizer with
`scripts/ops/submit_care_dependency_finalizer.py` and record finalizer job ID,
command, log path, lock path, and result directory.

For `tmux_watcher`, record namespace-local session name, PID, command, log path,
lock path, and result directory.

Submitted, pending, running, awaiting accounting, short smoke, partial output,
executor summary, or job ID alone is not completion. Slurm-derived completion
requires terminal job accounting, runtime outputs, zero-exit aggregation,
regenerated tracked evidence, and passing validators.

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
mapper_report_draft.md, if required
mapper_report_final.md, if required
architecture_delta_final.md, if required
validator_report.md
controller_report.md
completion_check.md
```

For code implementation tasks, `implementation_snapshot.md` must preserve the
implementation SHA, changed file list, `git diff --stat`, contract-sensitive
diff findings, tests run with exit codes, and known-bad regression results.

## Subagent Fallback

If Codex cannot automatically launch separate executor/mapper sessions, write
the prompt files under `results/<task_key>/subagents/`, set
`NEEDS_SUBAGENT_LAUNCH` or `NEEDS_HUMAN_APPROVAL`, and stop. Do not pretend
separation happened.

## Final Output Readability

Controller-facing and Planner-facing prose must pass
`prompts/FINAL_OUTPUT_READABILITY_POLICY.md`. Start `controller_report.md` with a
natural Chinese judgment explaining what was completed, why the evidence is or
is not adequate, what should happen next, and what remains unauthorized. Put
internal labels, paths, metrics, commands, and machine fields after the meaning
is clear. Do not use repository status tokens or mechanism labels as section
headings unless their scientific meaning has already been explained.

## Git Policy

Local commit is allowed only for the current task's lightweight final packet.
No push is allowed. The commit is not route promotion, validation readiness,
hosted metric claim, scientific stop, fold expansion, or next-stage
authorization.

## Controller Report Required Ending

End `controller_report.md` and mirror the decision in `completion_check.md` with:

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status: COMPLETE | INCOMPLETE | BLOCKED
experiment_adequacy_decision: PASS | FAIL | PARTIAL | EVIDENCE_NOT_FOUND
contract_compliance_status: PASS | FAIL | PARTIAL
required_outputs_complete: true | false
validators_passed: true | false
all_jobs_terminal: true | false | not_applicable
aggregation_complete: true | false | not_applicable
git_commit_decision: COMMIT_LOCAL_PACKET | SKIP_COMMIT
git_push_decision: SKIP_PUSH
route_promotion_decision: NOT_AUTHORIZED
route_negative_decision: NOT_AUTHORIZED
scientific_resolution_status: PLANNER_DECISION_REQUIRED
published_files:
  - path
blocked_actions:
  - validation packaging/upload/fold expansion/hosted metric claim/next-stage training remain blocked
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
reason_if_not_published: ...
reason_if_no_route_promotion: controller not authorized to decide route promotion
```

Only `controller_verification_decision: VERIFIED_COMPLETE` represents current
task completion. If required outputs, validators, terminal job accounting,
aggregation, contract compliance, or authorized local commit policy are
incomplete, the decision must be `NEEDS_REPAIR` or `OPERATIONALLY_BLOCKED`.

## Optional Explicit Review

If and only if the task explicitly sets `review_required: true`, write
`review_request.md` and `subagents/reviewer_prompt.md` for a separate read-only
reviewer. The reviewer remains optional by default and must not be used as a
substitute for controller verification.

## Forbidden

The controller, executor, mapper, finalizer, and validator must not write
`review.md`, launch an internal auditor, grant audited-go, decide final route
promotion, decide final scientific stop, authorize validation packaging/upload,
authorize fold expansion, start the next Batch, or push.
