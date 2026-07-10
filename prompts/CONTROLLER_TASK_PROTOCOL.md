# Controller Task Protocol

Controller tasks are governed by `prompts/AGENT_FLOW_V2_PROTOCOL.md`. A
controller is a Codex continuity supervisor for one GPT-authored task, not a
strategic planner and not a reviewer.

## Required Frontmatter

Controller-supervised tasks must include:

```yaml
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
mapper_slots: 1
mapper_required: true | false
architecture_impact: "none" | "component" | "system"
wiki_update_required: true | false
diagram_update_required: true | false
slurm_runtime_continuity_required: true | false
continuity_backend: "none" | "slurm_dependency" | "tmux_watcher"
review_mode: "independent_thread" | "short_goal"
reviewer: "separate_readonly"
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
```

`allow_git_commit` and `auto_git_commit` authorize only a local lightweight
final-packet commit for the current task. They do not authorize route promotion,
validation packaging/upload, hosted metric claims, fold expansion, next
milestone execution, or pushing.

## Lifecycle

Controller-supervised long Slurm, overnight, multi-job, or high-resume-risk
tasks must follow this order:

```text
1. controller bootstrap
2. executor implementation
3. implementation snapshot
4. mapper draft
5. durable continuity
6. FINALIZER_A terminal accounting, runtime-output check, and aggregation
7. mapper final
8. FINALIZER_B validators, wiki/history checks, and the single local commit
9. controller report confirming the committed packet
10. controller stops
11. separate reviewer independently runs
12. reviewer separately commits review.md
13. user manually pushes
```

At each phase, the controller re-grounds from disk/live state. It must not rely
on stale chat summaries or executor self-assessment.

## Required Receipts

Controller-supervised result packets must produce or validate:

```text
results/<task_key>/controller_context.json
results/<task_key>/controller_ledger.csv
results/<task_key>/controller_bootstrap_snapshot.md
results/<task_key>/implementation_snapshot.md
results/<task_key>/finalizer_state.json
results/<task_key>/mapper_report_draft.md
results/<task_key>/mapper_report_final.md
results/<task_key>/architecture_delta_final.md
results/<task_key>/controller_report.md
```

`controller_context.json` must include task prompt path and sha256,
`AGENTS.md` sha256, Slurm skill sha256 when Slurm is involved, git head,
required job IDs, required runtime paths, continuity backend evidence, and files
read.

`controller_ledger.csv` is append-only and records timestamp, phase, git head,
task hash, job states, decision, and next action.

`finalizer_state.json` is the terminal accounting receipt. It must record job
states and exit codes, runtime/log/output paths, aggregation command and exit
code, validator commands and exit codes, mapper-final status, lock path, git
head before finalization, optional local commit after finalization, and final
state.

`executor_plan_path` is required when `executor_count > 1`,
`executor_slots > 1`, or `parallel_execution_allowed: true`. It must validate
with `scripts/ops/validate_executor_plan.py`. The controller launches executors
only by declared wave, records launch and merge ledgers, and remains the only
merge owner.

## Durable Continuity

If `slurm_runtime_continuity_required: true`, `continuity_backend` must be
`slurm_dependency` or `tmux_watcher`.

For `slurm_dependency`, use `scripts/ops/submit_care_dependency_finalizer.py` to
submit `jobs/src/care_milestone_finalizer.sh` with
`--dependency=afterany:<jobids>`. The submission receipt must include finalizer
job ID, command, log path, lock path, and result directory.

For `tmux_watcher`, a namespace-local watcher must record session name, PID,
command, log path, lock path, and result directory. Merely writing
`continuity_backend: tmux_watcher` is not evidence.

`PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, and `AWAITING_SACCT` are
monitor states. They map to `NEEDS_MONITOR`, not `NEEDS_EVIDENCE` and not
`BLOCKED`. A scheduler block requires the Slurm routing skill's pending
threshold evidence.

## Controller Report

`controller_report.md` is written before independent review. It must not claim
reviewer approval, audited-go, final route promotion, or final scientific stop.

Before review, the report ending must use:

```text
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
```

Required ending fields:

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

## Subagent Fallback

If automatic subagent launch is unavailable, the controller writes prompt files
such as:

```text
results/<task_key>/subagents/executor_prompt.md
results/<task_key>/subagents/mapper_prompt.md
results/<task_key>/subagents/reviewer_prompt.md
```

The controller then records `NEEDS_SUBAGENT_LAUNCH` or
`NEEDS_HUMAN_APPROVAL`. It must not pretend executor, mapper, or reviewer
separation happened.

## Forbidden Controller Behavior

The controller must not:

- launch an internal auditor;
- write `review.md`;
- collect reviewer review before committing the packet;
- write audited-go;
- decide final route promotion or final scientific stop;
- push;
- increase executor or mapper slots beyond the GPT-authored task graph;
- convert pending/running Slurm states to blocked before the Slurm skill
  threshold.
