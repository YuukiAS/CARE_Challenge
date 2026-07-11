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
- `PACKET_COMMITTED_FOR_REVIEW`: controller/executor locally committed the
  lightweight final packet and stopped before review.
- `REVIEWER_RUNNING`: separate read-only reviewer is active.
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

## Scientific States

Controller reports written before independent review must use:

```text
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
```

Reviewer reviews may use milestone-specific audited tokens. Final route
promotion or final scientific stop is a reviewer-plus-GPT-planner decision, not
a controller decision.

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
- `AWAITING_SACCT` in a dependency finalizer must retry within the finalizer
  before returning `AWAITING_SACCT_RETRY_EXHAUSTED`.
- Parallel executor waves require a validated executor plan. Overlapping write
  scopes, shared worktrees, missing dependencies, or merge conflicts map to
  `NEEDS_REVISION_PARALLEL_MERGE_CONFLICT` or `NEEDS_REVISION`.
- Scheduler block requires the Slurm routing skill's pending threshold.
- Controller local commit does not authorize push, validation upload, hosted
  metric claims, route promotion, scientific stop, or next milestone.
