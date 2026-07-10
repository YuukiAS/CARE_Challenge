# Handoff Roles

CARE handoffs use the role model defined by
`prompts/AGENT_FLOW_V2_PROTOCOL.md`. This file is the compact role reference for
active handoff prompts.

## Active Roles

- `planner`: the user-supervised GPT/ChatGPT thread. It chooses the route,
  writes execution contracts, assigns role counts, defines gates, and decides
  the next high-level task after review.
- `controller`: the top-level Codex goal for one GPT-authored controller task.
  It supervises phase grounding, executor/mapper/finalizer/validator flow,
  durable Slurm continuity, and local final-packet commit. It stops before
  review.
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
- `reviewer`: the separate read-only Codex thread or short goal that starts only
  after the executor/controller final packet is committed. It writes
  `review.md`.

## Legacy Compatibility

Historical `auditor` fields mean the independent read-only `reviewer`. New
tasks must not create a controller-internal auditor, must not ask the controller
to collect auditor review before committing the packet, and must not use
`auditor_subtasks`.

## Hard Boundaries

- `controller`, `executor`, `mapper`, `finalizer`, and `validator` must not
  write `review.md`.
- `reviewer` must not train, monitor, resume jobs, fix packets, generate wiki
  evidence, or become a controller child.
- `controller` must not decide final route promotion, final scientific stop, or
  audited-go.
- No role may push. The user pushes manually.
- Controller reports generated before review use
  `route_promotion_decision: NOT_REVIEWED`,
  `route_negative_decision: NOT_REVIEWED`, and
  `scientific_resolution_status: AWAITING_REVIEW`.
