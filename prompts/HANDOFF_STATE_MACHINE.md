# Handoff State Machine

Use these states in new CARE task frontmatter, controller reports, finalizer
receipts, and reviews. See `prompts/AGENT_FLOW_V2_PROTOCOL.md` for the canonical
agent-flow v2 lifecycle.

## Execution States

- `DRAFT_FOR_PLANNING_REVIEW`: planner draft exists but has not passed the
  separate planning critic.
- `PLANNING_REVIEW_RUNNING`: separate GPT critic is reviewing the draft.
- `NEEDS_PLANNING_REVISION`: critic found planning blockers.
- `READY_FOR_CODEX_MERGE`: critic approved the staging contract for Codex
  merge/validation and then execution.
- `BLOCKED_HANDOFF_REVIEW`: planning review cannot complete until the user
  supplies missing context or resolves a handoff contradiction.
- `READY`: GPT planner has written the task.
- `EXECUTION_PLANNED`: controller or executor has grounded the task and written
  an execution plan.
- `EXECUTOR_RUNNING`: executor worker is active.
- `OPERATIONAL_RETRY_RUNNING`: the same executor is retrying the same
  task-local command semantics after an operational defect was repaired.
- `MAPPER_DRAFT_RUNNING`: mapper draft pass is active.
- `FINALIZER_RUNNING`: deterministic finalizer is collecting terminal job
  accounting, aggregation, validators, and tracked evidence.
- `FINALIZER_A_RUNNING`: deterministic accounting/aggregation stage is active.
- `MAPPER_FINAL_RUNNING`: mapper final pass is reconciling current code,
  runtime evidence, wiki, component table, and diagrams.
- `FINALIZER_B_RUNNING`: deterministic validation and single local commit stage
  is active after mapper final.
- `PARALLEL_EXECUTOR_WAVE_RUNNING`: a GPT-authored executor wave is active under
  an executor plan.
- `VALIDATOR_RUNNING`: fail-closed validators are active.
- `VERIFIED_COMPLETE`: controller accepted the executor/finalizer/validator packet as terminal for the current task and committed the lightweight result locally.
- `PACKET_COMMITTED_FOR_REVIEW`: legacy or explicit-review packet locally committed before optional independent review.
- `REVIEWER_RUNNING`: explicit optional separate read-only reviewer is active.
- `REVIEWED`: reviewer wrote `review.md`.

## Outcome States

- `NEEDS_MONITOR`: jobs or watchers are pending/running/awaiting accounting.
- `NEEDS_EVIDENCE`: required evidence is missing after terminal execution.
- `NEEDS_REVISION`: implementation or packet must be revised inside task scope.
- `NEEDS_HUMAN_APPROVAL`: human approval is required.
- `NEEDS_SUBAGENT_LAUNCH`: controller wrote subagent prompts but could not
  launch required separate sessions.
- `NEEDS_GPT_PLANNER`: next action requires strategic GPT/user judgment.
- `STOP`: do not continue this task.

## Block Taxonomy

New controller reports must not use a bare `BLOCKED` without a controlled
reason. Use one of:

- `BLOCKED_PREREQUISITE`: an explicit prerequisite token, file, hash, or
  ancestor gate is missing.
- `BLOCKED_EXTERNAL_RESOURCE`: external data, license, service, or cluster
  resource is unavailable outside the task's control.
- `BLOCKED_PERMISSION`: a required action is outside the current human-approved
  permission boundary.
- `BLOCKED_SCHEDULER_SATURATION`: every submitted routing partition remained
  pending for the Slurm skill's 12 consecutive 2-hour checks.
- `BLOCKED_UNRESOLVED_WORKTREE_CONFLICT`: local git/worktree state prevents
  safe continuation.
- `NEEDS_REVISION_RETURN_TO_PREVIOUS_WAVE`: recovery requires changing frozen
  shared files owned by an earlier executor wave.
- `NEEDS_GPT_PLANNER`: recovery would change scientific design, budget, split,
  task graph, executor count, external resource contract, or route decision.

The following are not blockers by themselves: old jobs failed, the current
packet is `NEEDS_EVIDENCE`, replacement job IDs are needed, an aggregator must
be rerun, a branch is not pushed, ordinary pending is below the scheduler
threshold, or same-scope environment repair completed.

## Operational Recovery Transitions

`NEEDS_EVIDENCE` is a packet/evidence outcome. It does not automatically revoke
the original execution authorization.

When a failed job is caused by an operational defect and the repair stays inside
the same task, executor, command semantics, variant, budget, split, config
meaning, and write scope, the controller may resume the same executor as:

```text
RUNTIME_FAILURE / NEEDS_EVIDENCE
  -> operational defect repaired
  -> OPERATIONAL_RETRY_RUNNING
  -> EXECUTOR_RUNNING / NEEDS_MONITOR
```

The replacement attempt is the same executor's new attempt. It does not increase
`executor_count` and does not require a new planner or human approval. Only a
machine-checkable scope or permission change may move the task to
`NEEDS_GPT_PLANNER` or `NEEDS_HUMAN_APPROVAL`.

## Scientific States

Default controller reports use:

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```

Reviewer reviews may use milestone-specific audited tokens only when `review_required: true` is explicit. Final route promotion, validation upload, hosted metric claim, fold expansion, next Batch, or final scientific stop is a Planner/user decision, not a controller decision.

## Legacy States

- `AUDITOR_RUNNING`: legacy alias for `REVIEWER_RUNNING` in old task files.
- `AUDITED_GO`, `AUDITED_DIAGNOSTIC_PUBLISH`, and
  `AUDITED_SCIENTIFIC_STOP`: reviewer-side legacy/controlled decisions only.
  Controllers must not write them.

## Rules

- `controller`, `executor`, `mapper`, `finalizer`, and `validator` never write
  `review.md`.
- `reviewer` is never an internal controller subagent and never fixes or
  resumes execution.
- `PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, and `AWAITING_SACCT`
  Slurm states map to `NEEDS_MONITOR`.
- Running jobs with missing outputs are still monitor state, not
  `NEEDS_EVIDENCE`.
- Completed jobs with missing runtime outputs or failed aggregation map to
  `NEEDS_EVIDENCE`.
- Failed jobs map to runtime failure evidence, not scheduler block.
- Retryable startup, wrapper, node, preemption, path, lock, or import failures
  map to operational recovery first, not permanent block.
- `AWAITING_SACCT` in a dependency finalizer must retry within the finalizer
  before returning `AWAITING_SACCT_RETRY_EXHAUSTED`.
- Parallel executor waves require a validated executor plan. Overlapping write
  scopes, shared worktrees, missing dependencies, or merge conflicts map to
  `NEEDS_REVISION_PARALLEL_MERGE_CONFLICT` or `NEEDS_REVISION`.
- Scheduler block requires the Slurm routing skill's pending threshold.
- Controller local commit does not authorize push, validation upload, hosted
  metric claims, fold expansion, route promotion, scientific stop, next Batch, or next milestone.
