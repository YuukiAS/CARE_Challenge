# Handoff Roles

This kit defines a two-layer execution protocol. It is a general repository
protocol, not a domain-specific research policy.

## Layer 1: Strategic Planning

The strategic planning layer is the user-supervised ChatGPT/GPT thread.

Responsibilities:

- Understand the user goal and repository context.
- Search for new directions, compare alternatives, and make research or product
  judgments.
- Decide whether the next handoff is a normal execution task or a controller
  task.
- Write high-quality `prompts/tasks/<task_key>.md` files with scope, evidence
  gates, forbidden substitutes, and failure escalation policy.
- Read audits and controller reports before deciding whether to stop, roll back,
  ask for human approval, or write the next high-level task.

Codex is not the default strategic planner. A Codex session may execute within a
task, but it must not invent a new direction when the GPT-authored task fails.

## Layer 2: Execution Control

The execution-control layer may be a Codex controller session, but only inside a
GPT-authored controller task.

Responsibilities:

- Read the controller task and build an execution plan inside its authorized
  scope.
- Create or launch executor and auditor sessions when the runtime supports it.
- If automatic subagent launch is unavailable, write reusable subagent prompt
  files and stop at `NEEDS_SUBAGENT_LAUNCH` or `NEEDS_HUMAN_APPROVAL`.
- Collect executor results and auditor reviews.
- Decide whether the controller run is operationally complete.
- Decide whether the `experiment_adequacy_gate` is satisfied for any
  training/model route.
- Decide whether the `route_promotion_gate` is satisfied.
- Decide whether the `route_negative_gate` is satisfied before accepting any
  route-negative scientific stop.
- Decide whether the `diagnostic_publication_gate` is satisfied when no route is
  promoted.
- Write `results/<task_key>/controller_report.md`.
- When git is authorized and either audited gate passes, commit the approved
  route-promotion changes or the reviewed diagnostic packet within the task
  scope.
- When git push is authorized and human approval was not triggered, push the
  commit to the remote.
- Output `NEEDS_GPT_PLANNER` and stop if the task needs a new direction or
  exceeds the failure escalation policy.

Diagnostic publication is not route promotion. It exists so reviewed diagnostic
evidence can reach GPT planning without authorizing validation upload, fold
expansion, hosted metric claims, submission packaging, label/evaluator/fold
split changes, or next-stage training.

Operational completion is not scientific completion. A controller can finish the
authorized workflow and publish diagnostics while the route remains
`SCIENTIFIC_UNRESOLVED`, `SCIENTIFIC_UNDERTRAINED`, or
`SCIENTIFIC_PIPELINE_BUG`. A route-negative stop is scientific only when the
experiment adequacy and route-negative gates pass and the auditor supports that
conclusion.

The execution controller is a supervisor for one approved task, not an open-ended
planner.

## Agent-Flow v2 Roles

- `planner`: the ChatGPT/GPT main thread that writes route, task, milestone,
  controller, executor, mapper, and reviewer contracts.
- `controller`: a top-level Codex goal for one GPT-authored controller task. It
  owns long-task continuity, phase grounding, subagent coordination, Slurm
  continuity, finalizer handoff, validator execution, and operational closeout.
- `executor`: a Codex implementation/command subagent, or an independent short
  executor thread for direct tasks. It performs authorized changes, jobs, and
  initial evidence writing.
- `mapper`: a read-only controller subagent for architecture/component/evidence
  mapping. It may update `wiki/` only when authorized by the task and must not
  write review decisions.
- `finalizer`: a deterministic controller-managed stage or script for terminal
  accounting, aggregation, validation, wiki finalization, and commit. It is not
  an LLM reviewer.
- `validator`: a first-party script that checks packet, state-machine,
  wiki/fingerprint, and known-bad fixtures fail closed.
- `reviewer`: a separate read-only Codex thread or short reviewer goal that
  starts after the final packet is committed and writes `review.md`.

Historical `auditor` fields are legacy aliases for `reviewer`. New tasks must
not create a controller-internal `auditor`; use `mapper` for internal read-only
architecture checks and `reviewer` for final independent review.

Executor self-assessment is never the final completion state. A controller
report is also not a replacement for GPT strategic planning or independent
review.
