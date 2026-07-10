# Handoff State Machine

Use these states in new CARE task frontmatter, controller reports, finalizer
receipts, and reviews. See `prompts/AGENT_FLOW_V2_PROTOCOL.md` for the canonical
agent-flow v2 lifecycle.

## Execution States

- `READY`: GPT planner has written the task.
- `EXECUTION_PLANNED`: controller or executor has grounded the task and written
  an execution plan.
- `EXECUTOR_RUNNING`: executor worker is active.
- `MAPPER_DRAFT_RUNNING`: mapper draft pass is active.
- `FINALIZER_RUNNING`: deterministic finalizer is collecting terminal job
  accounting, aggregation, validators, and tracked evidence.
- `MAPPER_FINAL_RUNNING`: mapper final pass is reconciling current code,
  runtime evidence, wiki, component table, and diagrams.
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
- Scheduler block requires the Slurm routing skill's pending threshold.
- Controller local commit does not authorize push, validation upload, hosted
  metric claims, route promotion, scientific stop, or next milestone.
