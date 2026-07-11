# Agent Rules

This repository uses the `prompts/` handoff protocol. The protocol is a
lightweight file bridge between a GPT strategic planner and Codex execution
sessions.

## Default Entry

Codex default task entry:

```text
prompts/tasks/<task_key>.md
```

`task_key` uses `<id>_<short_slug>` with a 1-3 word slug. New tasks do not add a
`_task` suffix because they already live in `prompts/tasks/`.

Long-lived rules:

```text
prompts/AGENT_RULES.md
prompts/CHATGPT_RULES.md
prompts/HANDOFF_ROLES.md
prompts/HANDOFF_STATE_MACHINE.md
prompts/CONTROLLER_TASK_PROTOCOL.md
prompts/EXPERIMENT_ADEQUACY_GATE.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/MECHANISM_GATE_TEMPLATE.md
```

Task/result/review mapping:

```text
prompts/tasks/<task_key>.md
results/<task_key>/result.md
results/<task_key>/review.md
results/<task_key>/controller_report.md   # controller tasks
results/<task_key>/MANIFEST.md
```

If `results/<task_key>/` is created, update
`results/<task_key>/MANIFEST.md`.

`docs/notes/` and `docs/wiki/` are reference stores, not default execution
entries. Read them only when the task explicitly references them.

## Roles

Active agent-flow roles are defined in
`prompts/schemas/agent_flow_policy.yaml`:

- `planner`: first GPT thread that writes the milestone draft.
- `critic`: separate GPT planning-review thread; it reviews and revises the
  plan only, does not execute code, submit jobs, or write runtime `review.md`.
- `controller`: top-level Codex continuity owner for controller-supervised
  tasks.
- `executor`: authorized implementation and job worker.
- `mapper`: read-only code/evidence/architecture mapper.
- `finalizer`: deterministic script or phase for accounting, aggregation,
  validation, and local packet commit.
- `validator`: first-party fail-closed validation.
- `reviewer`: independent read-only runtime reviewer after packet commit.

Do not let one session silently switch roles. If the current session is an
executor/controller, it must stop after the task packet and reviewer handoff are
ready; it must not write `review.md`. Historical `auditor`,
`execution_controller`, and strategic-controller fields are legacy aliases only.

## Language Policy

Keep protocol keys, YAML fields, file paths, controlled state enums, command
names, code identifiers, and API names in English. Human-readable prose in
results, reviews, controller reports, notes, and explanations should follow the
user's language or the target repository's project rules.

If the target project prefers Chinese, write human-readable report prose
primarily in Chinese while keeping protocol fields and controlled values in
English. Project-level language rules win unless they would break
machine-readable protocol fields.

## Permission Boundary

Codex must obey task frontmatter:

- `allow_code_change`
- `allow_shell_command`
- `allow_network`
- `allow_external_upload`
- `requires_human_approval`
- `task_type`
- `controller_mode`
- `review_required`
- `promotion_gate`
- `route_promotion_gate`
- `diagnostic_publication_gate`
- `diagnostic_publication_scope`
- `blocked_after_diagnostic_publication`
- `experiment_adequacy_gate`
- `route_negative_gate`
- `scientific_completion_gate`
- `operational_completion_status`
- `scientific_resolution_status`
- `controller_run_status`
- `failure_escalation_policy`
- `allowed_next_states`
- `auto_git_commit`
- `auto_git_push`
- `allow_git_commit`
- `allow_git_push`

Unauthorized actions are forbidden by default. In particular, do not network,
upload, delete data, run expensive tasks, alter deployment/security/migration
configuration, or push externally unless the task authorizes the action and the
state machine allows it.

## Execution Task Rules

For `task_type: execution`:

- Execute only the authorized task scope.
- Write `results/<task_key>/result.md`.
- Record files read, files changed, commands, exit statuses, tests, artifacts,
  diff summary, failures, incomplete items, approval needs, and auditable claims.
- Use claim lines such as `claim.<name>: <description>`.
- Treat `self_assessed_status` as executor self-assessment only.
- Do not open the next task, invent a new direction, bypass review, or claim
  final audited completion.

## Milestone Task Rules

For `task_type: milestone`, read `prompts/MILESTONE_REVIEW_PROTOCOL.md` before
acting. A Codex executor/controller session may execute exactly one milestone.
It must write the milestone's required outputs, `completion_check.md`,
`review_request.md`, and `MANIFEST.md` under the exact `results/<task_key>/`
directory, then stop.

Milestone result directories matching `results/20??????_*_m[0-9]_*/` are a
repository-visible handoff packet by default. Track the top-level task-required
`.md`, `.csv`, and `.json` files when they are small, reviewable, and free of
secrets or raw data. Do not track nested runtime artifacts, checkpoints,
predictions, NIfTI files, logs, uploads, transcripts, environment dumps, or
heavy/sensitive tables.

A milestone executor/controller session must not write `review.md`, must not
write or claim a `*_AUDITED_GO` state, must not approve itself, and must not
start the next milestone. The next milestone is blocked until a separate
read-only `reviewer` writes `results/<task_key>/review.md` with the exact
controlled token defined by the milestone.

If a milestone prerequisite review is missing or lacks the required audited-go
token, stop before scientific work with the milestone's blocked/needs-evidence
state. Do not generate replacement review evidence inside the executor session.

## Controller Task Rules

For `task_type: controller` or `controller_mode: true`:

- Read the GPT-authored controller task and stay inside it.
- For new tasks, use agent-flow role names from
  `prompts/schemas/agent_flow_policy.yaml`: `planner`, `critic`,
  `controller`, `executor`, `mapper`, `finalizer`, `validator`, and
  `reviewer`. Historical aliases must not become active subagents.
- If `execution_mode: controller_supervised`, obey the GPT-authored
  `executor_slots` and `mapper_slots`. Do not add more subagents unless the
  task explicitly grants isolated slots.
- If the task is overnight, long Slurm, multi-job, or high-resume-risk, it must
  have `slurm_runtime_continuity_required: true` and a durable
  `continuity_backend` of `slurm_dependency` or `tmux_watcher`.
- At `BOOTSTRAP`, `PRE_SUBMISSION`, `MONITOR_RESUME`, `FINALIZE_A`,
  `MAPPER_FINAL`, and `FINALIZE_B`, re-read disk/live state and write fresh
  controller receipts rather than relying on old context.
- If the controller task is part of a milestone chain, the two-step milestone
  gate in `prompts/MILESTONE_REVIEW_PROTOCOL.md` overrides same-session
  controller review: the controller may coordinate the executor step but must
  stop after `completion_check.md` and `review_request.md`; a separate
  read-only reviewer must write `review.md`.
- For high-risk CARE controller work, enforce `prompts/HANDOFF_GATE_POLICY.md`
  before final audit or completion decisions: exact ordered task graph, exact
  result directories and required filenames, strict validator exit behavior,
  completion-check readiness before final audit, controller report terminal
  fields, training adequacy classification, and the current-bad-packet
  regression when applicable.
- Build an execution plan.
- Create or launch separate executor and mapper sessions when supported, and
  prepare a separate reviewer handoff for after the final packet is committed.
- If automatic subagent launch is unavailable, write prompt files such as:

```text
results/<task_key>/subagents/executor_prompt.md
results/<task_key>/subagents/mapper_prompt.md
results/<task_key>/subagents/reviewer_prompt.md
```

  Then mark state `NEEDS_SUBAGENT_LAUNCH` or `NEEDS_HUMAN_APPROVAL`.
- Collect executor result, mapper reports when required, finalizer state, and
  validator results. Prepare the independent reviewer handoff after local packet
  commit; do not require reviewer output before controller commit.
- Apply only operational packet gates before commit. Route promotion,
  route-negative stops, and scientific resolution remain `NOT_REVIEWED` or
  `AWAITING_REVIEW` until the independent reviewer and later planner decision.
- Separate `controller_run_status` and `operational_completion_status` from
  `scientific_resolution_status`. Completing subagent launch, executor results,
  validators, and `controller_report.md` is operational completion only; it
  does not prove the scientific route is promoted or stopped.
- For model/training routes, apply `experiment_adequacy_gate` before accepting
  route promotion or route-negative conclusions.
- Write `results/<task_key>/controller_report.md`.
- If a new direction is needed, write `NEEDS_GPT_PLANNER` and stop.

The execution controller must not turn a failed route into a new high-level
direction. That is the GPT planner's role.

## Runtime Review Rules

Reviewers must be read-only:

- Do not fix code.
- Do not generate missing artifacts.
- Do not rerun execution commands unless a new execution task explicitly
  authorizes it.
- Review claims against file, command, test, artifact, manifest, and diff
  evidence.
- For training/model routes, review whether the artifacts are adequate for the
  conclusion, not only whether they exist. Check actual training budget,
  `train_loop_seconds`, `actual_steps`, `optimizer_steps`, validation events,
  loss decrease, one-batch or tiny-overfit sanity, foreground/prediction sanity,
  proposal metrics when applicable, train/val/cache isolation, same-split
  baseline comparability, and label/export/decode paths.
- If formal training has only a smoke-scale budget, missing logs, missing
  prediction sanity, missing same-split baseline, decode/cache/label mismatch,
  or an unexplained all-zero proposal/prediction collapse, the reviewer must mark
  the route as `PARTIAL`, `UNSUPPORTED`, `SCIENTIFIC_UNDERTRAINED`,
  `SCIENTIFIC_NEEDS_EVIDENCE`, `SCIENTIFIC_NEEDS_REVISION`, or
  `SCIENTIFIC_PIPELINE_BUG`; it must not support `STOP_NO_SIGNAL` or another
  route-negative conclusion.
- Use controlled decisions from `HANDOFF_STATE_MACHINE.md`.

## Git Sync Policy

Default task fields:

- `auto_git_commit: false` for plain executors; controller tasks may set true
  only when schema and task scope authorize a local packet commit.
- `auto_git_push: false`

`allow_git_commit` and `allow_git_push` are outer permission switches. If they
are false or absent, a CARE controller must not commit or push even when
`auto_git_commit` is true. New CARE tasks must default `allow_git_push: false`
and `auto_git_push: false`; the user pushes manually.

For controller tasks, local commit may be triggered only after deterministic
validators pass, no human approval gate is triggered, and the task authorizes
the git action. Push is never automatic; the user pushes manually unless a
future task explicitly overrides this repository default.

- `route_promotion_gate`: reviewer/planner-gated route promotion state, not a
  controller pre-review commit condition.
- `diagnostic_publication_gate`: no route is promoted, but lightweight
  schema-allowed diagnostic code/reports/evidence packets may be committed for
  GPT planner review.

If the trigger is diagnostic publication only, the commit message and
`controller_report.md` must say `diagnostic publication only; no route promotion`.
If neither gate is satisfied, the controller must not commit and must not push and must
record the reason in `controller_report.md`.

Plain executors should not commit/push medium/high risk changes that still need
audit unless the task explicitly authorizes that path.

## Failure Handling

If the task cannot be completed safely:

- Stop expanding scope.
- Record completed work, blocker, missing permission or evidence, and required
  next state.
- Do not write route-negative scientific conclusions such as `STOP_NO_SIGNAL`,
  `STOP_NO_PROPREF_SIGNAL`, `STOP_NO_CLEAN_ANCHOR_SIGNAL`, or
  `STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL` unless `experiment_adequacy_gate` and
  `route_negative_gate` both pass and the reviewer explicitly supports the
  route-negative conclusion.
- If the training/experiment is undertrained, missing critical evidence, or
  affected by a pipeline bug, use `NEEDS_REVISION`, `NEEDS_EVIDENCE`,
  `STOP_PIPELINE_BUG`, `SCIENTIFIC_UNDERTRAINED`,
  `SCIENTIFIC_UNRESOLVED`, or controller-level `NEEDS_GPT_PLANNER` with a clear
  note that the scientific route remains unresolved.
- Use `NEEDS_GPT_PLANNER` when a new direction or strategic judgment is needed.
- Do not bypass `STOP`, `NEEDS_EVIDENCE`, `NEEDS_REVISION`,
  `NEEDS_HUMAN_APPROVAL`, or `NEEDS_GPT_PLANNER`.

## CARE-Specific Execution Overlay

For CARE tasks, keep the role boundary strict. GPT is the `planner`; a separate
GPT `critic` handles planning review when the schema requires it. A Codex executor only executes the authorized task, writes
`result.md`, updates `MANIFEST.md`, and indexes artifacts. Executor
self-assessment is not final completion. For milestone tasks, the Codex executor
also writes `completion_check.md` and `review_request.md`, then stops. It must
not write `review.md` or start the next milestone.

A Codex controller may start or generate executor/mapper subtasks only inside a GPT-authored CARE controller task. It must not switch to a new scientific route, bypass the reviewer, or push. Local commit requires `allow_git_commit: true`, `auto_git_commit: true`, schema-valid packet files, and passing validators.

If the current session is the executor, do not also act as reviewer. If the task is a review, stay read-only: do not fix code, produce missing artifacts, launch training, or rerun experiments unless a separate execution task explicitly authorizes that work.

High-risk CARE tasks require read-only review/audit before fold expansion, validation packaging, upload, or next-stage training. `STOP_*`, `REVISE_*`, `selected_variant: none`, and `*_WAITING_*` block automatic fold expansion, packaging, upload, and continuation unless the user explicitly overrides the block.

Do not claim `TRUE_DONE` when required CARE evidence is missing. Missing checkpoint, prediction, metric file, run log, same-split baseline, cache isolation, label/export QC, or hosted-metric caveat must be reported as missing evidence rather than inferred completion.

For CARE model/training routes, do not claim scientific stop from inadequate
experiments. `controller_run_status: COMPLETE` means the controller completed
the authorized workflow; it does not imply
`scientific_resolution_status: SCIENTIFIC_STOP_SUPPORTED`.
