# Handoff Roles

CARE handoffs use the role model defined by
`prompts/AGENT_FLOW_V2_PROTOCOL.md`. This file is the compact role reference for
active handoff prompts.

## Active Roles

- `planner`: the user-supervised GPT/ChatGPT thread. It chooses the route,
  writes execution contracts, assigns role counts, defines gates, and later decides
  the next high-level task after reading controller results.
- `critic`: the separate GPT/ChatGPT planning-review thread. It reviews and
  revises the planner's milestone draft before Codex execution only when `planning_review_required: true` is explicit. It does not execute code, submit jobs, write runtime
  `review.md`, or become a controller subagent.
- `controller`: the top-level Codex goal for one GPT-authored controller task.
  It supervises phase grounding, executor/mapper/finalizer/validator flow,
  durable Slurm continuity, and local final-packet commit. It verifies and repairs executor work until a terminal controller result exists.
- `executor`: the worker that performs authorized implementation, commands,
  Slurm submissions, aggregations, and evidence writing. It does not self-review
  and does not own overnight continuity.
- `mapper`: the read-only architecture/evidence mapper. It may update `wiki/`
  only when the task authorizes wiki updates. It does not make route-promotion
  or scientific-stop decisions.
- `finalizer`: the deterministic terminal accounting stage or script. It
  collects Slurm state, reruns aggregators/evidence collectors, runs validators,
  coordinates mapper-final evidence, writes finalizer receipts, and performs
  authorized local packet commit. It is not an LLM reviewer.
- `validator`: first-party fail-closed scripts that check task contracts,
  packet receipts, wiki/diagram freshness, Slurm monitor semantics, and
  known-bad fixtures.
- `reviewer`: an optional separate read-only Codex thread or short goal that starts only
  when `review_required: true` is explicit. It writes `review.md`.

## Legacy Compatibility

Historical `auditor`, `execution_controller`, and old strategic-controller
runtime fields are legacy aliases for the independent `reviewer`, `controller`,
and `planner` concepts respectively. New tasks must not create an internal
auditor role, must not ask the controller to collect auditor or reviewer review
before committing the packet, and must not use `auditor_subtasks`.

## Hard Boundaries

- `controller`, `executor`, `mapper`, `finalizer`, and `validator` must not
  write `review.md`.
- `reviewer` must not train, monitor, resume jobs, fix packets, generate wiki
  evidence, or become a controller child.
- `controller` must not decide validation upload, hosted metric claim, fold expansion, next Batch, final route promotion, final scientific stop, or audited-go.
- No role may push. The user pushes manually.
- Controller reports use `controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED` plus machine-checkable evidence fields. Reviewer fields are required only for explicit reviewer tasks.
