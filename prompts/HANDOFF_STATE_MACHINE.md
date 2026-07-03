# Handoff State Machine

Use these states in task frontmatter, results, reviews, and controller reports
when a controlled state is needed.

## States

- `READY`: GPT planner has written the task and it is ready to execute.
- `EXECUTION_PLANNED`: an execution controller has read the task and written an
  execution plan.
- `EXECUTOR_RUNNING`: an executor session is active.
- `EXECUTED_UNAUDITED`: executor has written result artifacts, but no independent
  audit has accepted the claims.
- `AUDITOR_RUNNING`: a separate auditor is reviewing evidence.
- `AUDITED_GO`: audit supports the claims and the route promotion gate is
  satisfied.
- `AUDITED_DIAGNOSTIC_PUBLISH`: audit supports publishing a reviewed diagnostic
  packet, but no route promotion is approved.
- `AUDITED_SCIENTIFIC_STOP`: audit supports a route-negative conclusion; this
  requires `experiment_adequacy_gate` and `route_negative_gate` to pass.
- `NEEDS_EVIDENCE`: evidence is missing or insufficient.
- `NEEDS_REVISION`: implementation or output must be revised inside the current
  task scope.
- `SCIENTIFIC_PROMOTED`: route is scientifically supported for promotion inside
  the task's authorization.
- `SCIENTIFIC_STOP_SUPPORTED`: route is scientifically stopped by adequate
  negative evidence and auditor approval.
- `SCIENTIFIC_UNRESOLVED`: controller may be operationally complete, but the
  scientific route is neither promoted nor stopped.
- `SCIENTIFIC_UNDERTRAINED`: the run is too short or too weak to support
  promotion or route-negative conclusions.
- `SCIENTIFIC_PIPELINE_BUG`: results are dominated by a pipeline, decode, cache,
  label/export, or optimization bug.
- `SCIENTIFIC_NEEDS_EVIDENCE`: scientific evidence is missing.
- `SCIENTIFIC_NEEDS_REVISION`: scientific route needs a bounded revision before
  promotion or stop can be decided.
- `NEEDS_HUMAN_APPROVAL`: a human approval point was reached.
- `NEEDS_SUBAGENT_LAUNCH`: the controller generated executor/auditor prompts but
  the runtime could not launch separate sessions automatically.
- `ESCALATE_WITHIN_POLICY`: the controller may use an escalation path that the
  task explicitly allowed.
- `NEEDS_GPT_PLANNER`: the next move requires strategic judgment or a new
  direction from the GPT planner.
- `STOP`: do not continue this route.

## Rules

- After an executor writes `result.md`, the state may become
  `EXECUTED_UNAUDITED`, `NEEDS_EVIDENCE`, `NEEDS_REVISION`,
  `NEEDS_HUMAN_APPROVAL`, or `STOP`. The executor must not self-promote to final
  completion.
- Controller operational completion must be reported separately from scientific
  route resolution. `controller_run_status: COMPLETE` and
  `operational_completion_status: COMPLETE` do not imply
  `scientific_resolution_status: SCIENTIFIC_STOP_SUPPORTED` or
  `SCIENTIFIC_PROMOTED`.
- Medium/high risk tasks and controller tasks should not move to release,
  deployment, submission, commit, push, or expensive expansion without an
  independent audit unless the task explicitly says review is not required.
  Commit/push after audit must be triggered by an authorized
  `route_promotion_gate` or `diagnostic_publication_gate`.
- `STOP`, `NEEDS_EVIDENCE`, `NEEDS_REVISION`, `NEEDS_HUMAN_APPROVAL`, and
  `NEEDS_GPT_PLANNER` cannot be bypassed by the executor or execution
  controller.
- `AUDITED_DIAGNOSTIC_PUBLISH` allows only the reviewed files listed in
  `diagnostic_publication_scope` to be committed/pushed. It does not authorize
  fold expansion, validation packaging, validation upload, hosted metric claims,
  label/evaluator/fold split changes, or next-stage training.
- Route-negative states or strings such as `STOP_NO_SIGNAL`,
  `STOP_NO_PROPREF_SIGNAL`, `STOP_NO_CLEAN_ANCHOR_SIGNAL`, and
  `STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL` are invalid scientific conclusions
  unless `experiment_adequacy_decision: PASS`,
  `route_negative_decision: STOP_SUPPORTED`, and auditor support are present.
  Otherwise use `SCIENTIFIC_UNDERTRAINED`, `SCIENTIFIC_UNRESOLVED`,
  `SCIENTIFIC_NEEDS_EVIDENCE`, `SCIENTIFIC_NEEDS_REVISION`, or
  `SCIENTIFIC_PIPELINE_BUG`.
- Only the strategic controller, meaning the user-supervised GPT thread, may
  decide a new research/product direction or write the next high-level task.
- A controller can continue only along `allowed_next_states` and only within the
  task's `failure_escalation_policy`.
