# CARE Agent-Flow v2 Protocol

This is the permanent canonical source for CARE agent-flow v2. It replaces the
retired planning notes `TODO-agents-v2.md` and `TODO-agents.md`, which must not
be used as runtime rule sources.

## Active Roles

Only these role names are active for new CARE handoffs:

- `planner`: the user-supervised GPT/ChatGPT thread that designs the task,
  execution mode, role graph, evidence gates, and reviewer contract.
- `critic`: an optional separate GPT/ChatGPT planning-review thread. It reviews
  the planner's staged contract before Codex execution only when the Planner or
  user explicitly sets `planning_review_required: true`. It does not execute
  code, submit jobs, join the controller runtime, or write runtime `review.md`.
- `controller`: the top-level Codex goal for one GPT-authored controller task.
  The controller is the coordinator and acceptance owner. It owns phase
  re-grounding, executor supervision, git-diff inspection, Slurm continuity,
  same-scope repair loops, finalizer handoff, validators, terminal completion
  checks, and the local result commit.
- `executor`: an implementation/command worker. It performs authorized edits,
  job submission, aggregation, and evidence writing, but it does not self-review
  and does not own overnight continuity.
- `mapper`: a read-only architecture/evidence mapper. It may update `wiki/`
  only when the task authorizes wiki updates. It never writes `review.md`.
- `finalizer`: a deterministic script or controller-managed terminal stage for
  Slurm accounting, aggregation, validation, mapper-final handoff, wiki
  finalization, and local packet commit. It is not an LLM reviewer.
- `validator`: first-party fail-closed scripts that check task, packet,
  controller, wiki, and known-bad fixtures.
- `reviewer`: an optional separate read-only Codex thread or short goal that
  starts only when `review_required: true` is explicit. It writes `review.md`.

Historical `auditor`, `execution_controller`, and old strategic-controller
runtime fields are legacy aliases only. New tasks must not create a
controller-internal auditor subagent.

## Execution Modes

Current default posture is main-only development on `/users/a/e/aereinh/CARE`. Route worktrees and route controllers are not active execution targets unless a new human-approved handoff explicitly reactivates a named route. The role model below still applies to main-line milestones and any future route reactivation.

Short, non-Slurm, low-resume-risk work may use:

```text
planner -> executor -> local result commit -> planner
```

Long Slurm, overnight, multi-job, architecture-affecting, or high-resume-risk
work must use:

```text
planner -> controller/coordinator
                 |-> executor subagent
                 |-> optional mapper draft/final
                 |-> durable Slurm watcher/finalizer
                 |-> validator
                 |-> controller verification and repair loop
                 |-> local result commit
            controller stops with verified terminal result
            -> planner reads results and decides the next task
```

The controller, executor, mapper, finalizer, and validator must not write
`review.md`. The reviewer must not become a controller subagent and is used only
when explicitly required. No role may push unless the user explicitly authorizes
pushing for that task.

## Controller Lifecycle

Controller-supervised tasks follow this exact order:

1. controller bootstrap and frozen Planner contract capture;
2. executor implementation;
3. controller inspects git diff, commands, changed files, and contract-sensitive
   implementation findings;
4. controller checks model/config/data split/case count/training budget/eval
   scale were not reduced;
5. optional mapper draft/final when authorized;
6. durable continuity for Slurm work;
7. `FINALIZER_A`: terminal accounting, runtime-output check, aggregation, and
   `finalizer_state.json` with a terminal or repair state;
8. `FINALIZER_B`: validators, known-bad regressions, wiki/history checks when
   relevant, `git diff --check`, and the single local result commit;
9. controller report and completion check with `controller_verification_decision`;
10. if incomplete, controller returns the same-scope gap to executor/finalizer;
11. controller stops only at `VERIFIED_COMPLETE`, `NEEDS_REPAIR` with no
    authorized same-scope repair left, or `OPERATIONALLY_BLOCKED`;
12. planner later reads the result packet and decides the next task.

`controller_report.md` must not require or invent a reviewer decision. It must
start with a natural Chinese judgment for the Planner/user before listing
machine fields. The default terminal controller decision is machine-checkable:

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status:
experiment_adequacy_decision:
contract_compliance_status:
required_outputs_complete:
validators_passed:
all_jobs_terminal:
aggregation_complete:
git_commit_decision:
git_push_decision:
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```

Only `controller_verification_decision: VERIFIED_COMPLETE` represents current
Batch completion. Final scientific decisions, validation upload, hosted metric
claims, fold expansion, new architecture, external data, route promotion, and
the next Batch require Planner/user authorization.

## Required Execution Contract

Every new CARE milestone or controller task must declare:

```yaml
task_kind: scientific_milestone | maintenance | hotfix | audit
milestone_number: <positive integer or null>
milestone_id: <canonical Mxx or null>
route_change: true | false
scientific_decision_scope: none | mechanism_signal | promotion_candidate | stop_candidate
planning_review_required: true | false
execution_mode: direct_executor | controller_supervised
requires_execution_controller: true | false
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/<task_key>_executor_plan.yaml
mapper_slots: 1
mapper_required: true | false
architecture_impact: none | component | system
wiki_update_required: true | false
diagram_update_required: true | false
slurm_runtime_continuity_required: true | false
continuity_backend: none | slurm_dependency | tmux_watcher
review_required: false | true
review_mode: none | independent_thread | short_goal
reviewer: none | separate_readonly
```

The controller must not increase executor or mapper counts beyond the
GPT-authored task graph.

If `executor_count` is greater than `1` or `executor_slots` is greater than
`1`, the task must provide a machine-readable executor plan. The controller may
only launch executors by wave from that plan, must not exceed `executor_slots`,
and must not change sequential work into parallel work.

Parallel executors are allowed only when the plan proves non-overlapping
`write_scope`, separate worktrees/branches for code-writing executors, isolated
result/runtime/log/lock paths, completed dependencies, and deterministic
controller merge order. MyoPS and Cine are sequential by default unless GPT
explicitly supplies isolation proof.
Use `scripts/ops/prepare_care_executor_wave.py` to prepare each declared wave
and `scripts/ops/merge_care_executor_wave.py` to merge completed executor
branches. Executors must not merge their own branches into the shared branch.

Long Slurm or overnight tasks require a durable finalizer contract. Declaring
`continuity_backend` without a real dependency finalizer job or namespace-local
tmux watcher evidence is invalid.

## Controller Receipts

Controller-supervised result packets must produce or validate:

```text
controller_context.json
controller_ledger.csv
controller_bootstrap_snapshot.md
implementation_snapshot.md
finalizer_state.json
mapper_report_draft.md
mapper_report_final.md
architecture_delta_final.md
```

Receipts must include current task prompt hash, `AGENTS.md` hash, Slurm skill
hash when Slurm is involved, required job IDs, continuity backend evidence,
runtime output paths, aggregation command, validator commands, mapper-final
status, git head before finalization, and local commit after finalization.

## Durable Continuity

Slurm-backed controller tasks should use `slurm_dependency` with
`scripts/ops/submit_care_dependency_finalizer.py`, which submits
`jobs/src/care_milestone_finalizer.sh` with `--dependency=afterany:<jobids>`.

If dependency finalizer submission fails, a namespace-local tmux watcher may be
used only when it records session name, PID, command, log path, lock path, and
result directory.

The tmux watcher must read `results/<task_key>/finalizer_state.json` after each
finalizer run. Finalizer exit code alone is not a completion signal.
`NEEDS_MONITOR`, `AWAITING_SACCT_RETRY_EXHAUSTED`, and `INITIALIZING` continue
polling; `READY_FOR_MAPPER_FINAL`, `PACKET_COMMITTED_FOR_REVIEW`, and
`READY_FOR_LOCAL_PACKET_COMMIT` stop successfully; runtime failure, evidence,
mapper, validator, or revision states stop fail-closed.

`AWAITING_SACCT` retry must be automatic. The default bounded accounting wait is
at least 60 minutes, and `finalizer_state.json` must record `retryable`,
`retry_count`, `retry_backend`, `next_retry_job_id_or_tmux_session`, and
`accounting_wait_seconds`.

Monitor states (`PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`,
`AWAITING_SACCT`) map to `NEEDS_MONITOR`, not `NEEDS_EVIDENCE` and not
`BLOCKED`. Scheduler block requires the Slurm routing skill threshold.

## Operational Failure Recovery

A same-task, same-executor, same-command-semantics replacement attempt after an
operational startup or runtime defect is already authorized by the original
task. It does not require a new planner decision and does not consume another
executor slot.

Operational retry covers environment/package defects, wrapper or import-path
startup defects, transient node or preemption failures, runtime output path
setup, lock setup, and command packaging errors when the repair keeps the same
scientific variant, training budget, split, config semantics, task graph,
executor id, and write scope. The controller must record old and replacement
job lineage, fixed fingerprints, retry reason, and zero training credit for
failed startup attempts.

Implementation revision is allowed only inside the current executor write scope.
If recovery requires changing frozen shared architecture, loss, config, or
other previous-wave files, the controller must return
`NEEDS_REVISION_RETURN_TO_PREVIOUS_WAVE`. If recovery changes formula, variant,
budget, split, task graph, executor count, external resource permission, or
scientific decision gates, the controller must stop with `NEEDS_GPT_PLANNER` or
`NEEDS_HUMAN_APPROVAL` and cite the exact changed contract fields.

Fail-closed completion gates mean do not claim completion without evidence.
They do not mean stop attempting authorized task-local recovery. A controller
must not end a goal merely because the current packet is `NEEDS_EVIDENCE`;
it must first check for a task-local recovery path.

## GPT Milestone Authoring

Future staging prompts use the schemas under `prompts/schemas/`. A short
milestone may be `execution_mode: direct_executor`; a long Slurm, overnight,
multi-job, system-impact, or high-resume-risk milestone uses
`execution_mode: controller_supervised`.

All milestone staging prompts under `prompts/shared/M[0-9]*_*.md` must start on
line 1 with real YAML frontmatter. The human-readable `## Execution Contract`
section is only a mirror and cannot replace frontmatter. Validators must fail
closed if frontmatter and the body contract disagree.

Required frontmatter:

```yaml
---
task_key:
task_kind:
task_type:
controller_mode:
milestone_number:
milestone_id:
status:
risk_level:
route_change:
scientific_decision_scope:
execution_mode:
requires_execution_controller:
executor_slots:
executor_count:
parallel_execution_allowed:
executor_plan_path:
mapper_slots:
mapper_required:
architecture_impact:
wiki_update_required:
diagram_update_required:
slurm_runtime_continuity_required:
continuity_backend:
review_mode:
reviewer:
review_required:
allow_git_commit:
auto_git_commit:
allow_git_push:
auto_git_push:
allow_diagnostic_push:
route_promotion_gate:
experiment_adequacy_gate:
route_negative_gate:
scientific_completion_gate:
diagnostic_publication_gate:
diagnostic_publication_scope:
blocked_after_diagnostic_publication:
planning_review_required:
planning_reviewer:
planning_review_path:
planning_review_token:
planning_reviewed_commit:
---
```

Risk fields such as `task_kind: scientific_milestone`, `risk_level: high`,
`architecture_impact: system`, `slurm_runtime_continuity_required: true`,
`executor_count > 1`, `route_change: true`, and
`scientific_decision_scope != none` classify risk and required evidence, but
they do not automatically require a planning critic. A planning critic is
enabled only when the Planner or user explicitly sets:

```yaml
planning_review_required: true
planning_reviewer: separate_gpt_thread
planning_review_path: prompts/tasks/<task_key>_planning_review.md
planning_review_token: <controlled token>
planning_reviewed_commit: <commit>
```

When this explicit opt-in is present, the legacy planning-review receipt remains
binding: `prompts/tasks/<task_key>_planning_review.md` must validate against
`planning_review.schema.yaml`, its reviewed contract hash must match the
current prompt, and READY candidates without a completed matching planning
review remain blocked. Future tasks without explicit opt-in use
`planning_review_required: false`, `planning_reviewer: none`,
`planning_review_path: null`, `planning_review_token: null`, and
`planning_reviewed_commit: null`.

```text
## Execution Contract
## Controller Prompt
## Executor Worker Contract
## Mapper Contract
## Reviewer Prompt
```

Future short-task staging prompts with `review_required: false` must contain:

```text
## Execution Contract
## Executor Prompt
```

Add `## Reviewer Prompt` only when `review_required: true`.

Long Slurm or overnight prompts without both a Controller Prompt and durable
finalizer contract are invalid.

## Default Sprint Template

```yaml
task_kind: scientific_milestone
risk_level: high
execution_mode: controller_supervised
requires_execution_controller: true
executor_count: 1
controller_is_coordinator: true
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
review_required: false
review_mode: none
reviewer: none
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
```

Default flow:

```text
Planner
-> Controller/Coordinator
-> Executor
-> Controller verification and repair loop
-> deterministic finalizer/validators
-> local commit
-> Planner
```

## Git Boundary

Controller/finalizer local commit only means the current task's lightweight
final packet was committed for separate review. It does not imply route
promotion, validation packaging/upload, hosted metric claim, fold expansion,
scientific stop, or next milestone authorization.

Default controller git policy:

```yaml
auto_git_commit: true
allow_git_commit: true
auto_git_push: false
allow_git_push: false
allow_diagnostic_push: false
```
