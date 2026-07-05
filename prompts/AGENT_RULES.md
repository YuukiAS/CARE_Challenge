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

- GPT/ChatGPT is the default `planner` and `strategic_controller`.
- A Codex `execution_controller` may coordinate execution only inside a
  GPT-authored controller task.
- A Codex `executor` performs authorized changes and writes result artifacts.
- An `auditor` is separate from the executor and remains read-only.

Do not let one session silently switch roles. If the current session is the
executor and the task requires an auditor, stop at `EXECUTED_UNAUDITED` after
writing result. If the user explicitly asks the current Codex session to audit,
perform a read-only audit only.

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

## Controller Task Rules

For `task_type: controller` or `controller_mode: true`:

- Read the GPT-authored controller task and stay inside it.
- For high-risk CARE controller work, enforce `prompts/HANDOFF_GATE_POLICY.md`
  before final audit or completion decisions: exact ordered task graph, exact
  result directories and required filenames, strict validator exit behavior,
  completion-check readiness before final audit, controller report terminal
  fields, training adequacy classification, and the current-bad-packet
  regression when applicable.
- Build an execution plan.
- Create or launch separate executor and auditor sessions when supported.
- If automatic subagent launch is unavailable, write prompt files such as:

```text
results/<task_key>/subagents/executor_prompt.md
results/<task_key>/subagents/auditor_prompt.md
```

  Then mark state `NEEDS_SUBAGENT_LAUNCH` or `NEEDS_HUMAN_APPROVAL`.
- Collect executor result and auditor review.
- Apply the task's route promotion gate, diagnostic publication gate, and
  failure escalation policy.
- Separate `controller_run_status` and `operational_completion_status` from
  `scientific_resolution_status`. Completing subagent launch, executor results,
  auditor reviews, and `controller_report.md` is operational completion only; it
  does not prove the scientific route is promoted or stopped.
- For model/training routes, apply `experiment_adequacy_gate` before accepting
  route promotion or route-negative conclusions.
- Write `results/<task_key>/controller_report.md`.
- If a new direction is needed, write `NEEDS_GPT_PLANNER` and stop.

The execution controller must not turn a failed route into a new high-level
direction. That is the GPT planner's role.

## Audit Rules

Auditors must be read-only:

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
  or an unexplained all-zero proposal/prediction collapse, the auditor must mark
  the route as `PARTIAL`, `UNSUPPORTED`, `SCIENTIFIC_UNDERTRAINED`,
  `SCIENTIFIC_NEEDS_EVIDENCE`, `SCIENTIFIC_NEEDS_REVISION`, or
  `SCIENTIFIC_PIPELINE_BUG`; it must not support `STOP_NO_SIGNAL` or another
  route-negative conclusion.
- Use controlled decisions from `HANDOFF_STATE_MACHINE.md`.

## Git Sync Policy

Default task fields:

- `auto_git_commit: true`
- `auto_git_push: true`

`allow_git_commit` and `allow_git_push` are outer permission switches. If they
are false or absent, a CARE controller must not commit or push even when
`auto_git_commit` or `auto_git_push` is true.

For controller tasks, commit/push may be triggered only after audit or re-audit
passes, no human approval gate is triggered, the task authorizes the git action,
and one of these gates is satisfied:

- `route_promotion_gate`: the model/route may be promoted for challenge-facing
  use, fold expansion, validation packaging, upload, or next-stage training, but
  only within the task's explicit authorization.
- `diagnostic_publication_gate`: no route is promoted, but reviewed diagnostic
  code/reports/evidence packets may be published for GPT planner review.

If the trigger is diagnostic publication only, the commit message and
`controller_report.md` must say `diagnostic publication only; no route promotion`.
If neither gate is satisfied, the controller must not commit or push and must
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
  `route_negative_gate` both pass and the auditor explicitly supports the
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

For CARE tasks, keep the role boundary strict. GPT is the strategic planner and strategic controller. A Codex executor only executes the authorized task, writes `result.md`, updates `MANIFEST.md`, and indexes artifacts. Executor self-assessment is not final completion.

A Codex execution controller may start or generate executor/auditor subtasks only inside a GPT-authored CARE controller task. It must not switch to a new scientific route, bypass the auditor, or commit/push unless the task explicitly allows it with `allow_git_commit: true` and `allow_git_push: true`, and either the `route_promotion_gate` or `diagnostic_publication_gate` is satisfied within the authorized scope.

If the current session is the executor, do not also act as auditor. If the task is an audit or review, stay read-only: do not fix code, produce missing artifacts, launch training, or rerun experiments unless a separate execution task explicitly authorizes that work.

High-risk CARE tasks require read-only review/audit before fold expansion, validation packaging, upload, or next-stage training. `STOP_*`, `REVISE_*`, `selected_variant: none`, and `*_WAITING_*` block automatic fold expansion, packaging, upload, and continuation unless the user explicitly overrides the block.

Do not claim `TRUE_DONE` when required CARE evidence is missing. Missing checkpoint, prediction, metric file, run log, same-split baseline, cache isolation, label/export QC, or hosted-metric caveat must be reported as missing evidence rather than inferred completion.

For CARE model/training routes, do not claim scientific stop from inadequate
experiments. `controller_run_status: COMPLETE` means the controller completed
the authorized workflow; it does not imply
`scientific_resolution_status: SCIENTIFIC_STOP_SUPPORTED`.
