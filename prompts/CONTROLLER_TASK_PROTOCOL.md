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
review_required: false | true
review_mode: "none" | "independent_thread" | "short_goal"
reviewer: "none" | "separate_readonly"
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
10. controller stops with `VERIFIED_COMPLETE`, `NEEDS_REPAIR`, or `OPERATIONALLY_BLOCKED`
11. planner later reads the result packet and decides the next task
12. optional separate reviewer runs only when `review_required: true`
13. user pushes only when explicitly authorized
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
Prepare waves with `scripts/ops/prepare_care_executor_wave.py`; merge completed
executor branches with `scripts/ops/merge_care_executor_wave.py`. If subagent
launch is unavailable, the controller must write `NEEDS_SUBAGENT_LAUNCH`
instead of pretending the executor started.

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
The watcher must inspect `finalizer_state.json` after each iteration. It
continues on `NEEDS_MONITOR`, `AWAITING_SACCT_RETRY_EXHAUSTED`, and
`INITIALIZING`, stops successfully only on `READY_FOR_MAPPER_FINAL`,
`PACKET_COMMITTED_FOR_REVIEW`, or `READY_FOR_LOCAL_PACKET_COMMIT`, and stops
nonzero on failure/evidence/revision/mapper/validator states.

`PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, and `AWAITING_SACCT` are
monitor states. They map to `NEEDS_MONITOR`, not `NEEDS_EVIDENCE` and not
`BLOCKED`. A scheduler block requires the Slurm routing skill's pending
threshold evidence.
`AWAITING_SACCT` exhaustion is retryable monitor evidence, not success; the
finalizer must record retry fields and the watcher/finalizer backend that will
continue accounting.

## Operational Recovery Decision Table

The controller must classify terminal or failed runtime states before asking
for new authorization:

| Situation | Controller action |
| --- | --- |
| job pending/running/accounting | `NEEDS_MONITOR`, continue continuity |
| startup failure, repair remains inside executor scope | same executor replacement attempt |
| preemption/node failure, same config can resume or replace | same executor resume/replacement attempt |
| terminal success but output missing | rerun collector/aggregator; only then `NEEDS_EVIDENCE` if still missing |
| current executor wrapper/helper must change inside allowed write scope | task-local revision, preflight, then retry |
| frozen shared architecture/loss/config must change | `NEEDS_REVISION_RETURN_TO_PREVIOUS_WAVE` |
| scientific formula, variant, budget, split, graph, executor count, or decision gate changes | `NEEDS_GPT_PLANNER` |
| external permission/data/license cannot be solved | controlled external or permission blocker |

A controller report that asks for explicit human or planner authorization must
cite the exact contract field that requires it. If no field changes and the
repair is same-scope operational recovery, the controller must not invent an
approval gate.

If `next_required_action` asks to obtain explicit authorization, the report must
also include:

```text
authorization_reason:
changed_contract_fields:
out_of_scope_paths_or_actions:
why_operational_retry_is_insufficient:
```

## Controller Report

`controller_report.md` is written before independent review. It must not claim
reviewer approval, audited-go, final route promotion, or final scientific stop.

Required ending fields:

```text
controller_run_status: COMPLETE | INCOMPLETE | BLOCKED
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status: COMPLETE | INCOMPLETE
experiment_adequacy_decision: PASS | FAIL | PARTIAL | EVIDENCE_NOT_FOUND | NOT_REVIEWED
contract_compliance_status: PASS | FAIL
required_outputs_complete: true | false
validators_passed: true | false
all_jobs_terminal: true | false
aggregation_complete: true | false
route_promotion_decision: NOT_AUTHORIZED
route_negative_decision: NOT_AUTHORIZED
scientific_resolution_status: PLANNER_DECISION_REQUIRED
diagnostic_publication_decision: LOCAL_PACKET_COMMITTED | DO_NOT_PUBLISH | NOT_APPLICABLE
git_commit_decision: COMMIT_LOCAL_PACKET | SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
  - path
blocked_actions:
  - validation packaging/upload/fold expansion/hosted metric claim/next-stage training remain blocked
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
reason_if_not_published: ...
reason_if_no_route_promotion: not authorized by this controller task
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
