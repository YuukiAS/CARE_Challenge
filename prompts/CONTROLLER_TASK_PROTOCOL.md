# Controller Task Protocol

A controller task lets a Codex execution controller coordinate executor and
auditor work for one GPT-approved task. It does not authorize Codex to become
the strategic planner.

## Required Shape

Controller tasks should include:

- `task_type: "controller"`
- `controller_mode: true`
- `planner: "ChatGPT/GPT thread"`
- `strategic_controller: "user-supervised GPT thread"`
- `execution_controller: "Codex controller session"`
- `executor: "Codex executor session"`
- `auditor: "separate Codex auditor session"` or `ChatGPT reviewer`
- `review_required: true`
- `route_promotion_gate`
- `experiment_adequacy_gate`
- `route_negative_gate`
- `scientific_completion_gate`
- `diagnostic_publication_gate`
- `diagnostic_publication_scope`
- `blocked_after_diagnostic_publication`
- `failure_escalation_policy`
- `forbidden_substitutes`
- `required_evidence`
- `allowed_next_states`
- `auto_git_commit: true`
- `auto_git_push: true`
- a controller report path, normally
  `results/<task_key>/controller_report.md`

## Subagent Fallback

Do not assume every Codex runtime can open new sessions automatically.

If automatic launch is supported, the controller records:

- launch command
- session id
- prompt path
- log path
- exit status

If automatic launch is not supported, the controller must write files such as:

```text
results/<task_key>/subagents/executor_prompt.md
results/<task_key>/subagents/auditor_prompt.md
```

The controller then marks the state as `NEEDS_SUBAGENT_LAUNCH` or
`NEEDS_HUMAN_APPROVAL`. It must not pretend executor/auditor separation already
happened.

## Controller Report

Controller tasks must end with:

```text
results/<task_key>/controller_report.md
```

The report must include:

- controller task id
- executor subtask list
- auditor subtask list
- prompt, result, and review path for every subtask
- session, command, and log evidence
- claims summary
- audited decision
- controller run status
- operational completion status
- experiment adequacy decision
- route promotion decision
- route negative decision
- scientific resolution status
- diagnostic publication decision
- git commit decision
- git push decision
- published files
- blocked actions
- next required action
- reason if diagnostic artifacts were not published
- reason if no route promotion occurred
- incomplete items
- whether GPT planner is needed

## Gate Semantics

`route_promotion_gate` answers whether a model/route may become
challenge-facing, expand folds, enter validation packaging/upload, or trigger
next-stage training. It must not be inferred from executor self-assessment.

`experiment_adequacy_gate` answers whether the experiment was sufficient to
support scientific conclusions. For CARE training/segmentation routes, adequacy
requires one-batch or one-case overfit sanity when applicable, minimum effective
training evidence, prediction sanity, proposal/refinement sanity when
applicable, logs/provenance, and same-split baseline comparability. Slurm
elapsed time alone is not adequate evidence.

`route_negative_gate` answers whether a route can be scientifically stopped.
It passes only when:

1. `experiment_adequacy_gate` passes;
2. forbidden substitutes are absent;
3. same-split baseline comparison exists;
4. metric failure is not explainable by undertraining, smoke/preflight,
   decode error, cache contamination, label/export mismatch, missing log, or
   pipeline bug;
5. the auditor explicitly approves the route-negative conclusion.

If `route_negative_gate` fails, controller reports must not write
`STOP_NO_SIGNAL`, `STOP_NO_PROPREF_SIGNAL`, `STOP_NO_CLEAN_ANCHOR_SIGNAL`,
`STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL`, or equivalent scientific stops. Use
`SCIENTIFIC_UNDERTRAINED`, `SCIENTIFIC_PIPELINE_BUG`,
`SCIENTIFIC_NEEDS_EVIDENCE`, `SCIENTIFIC_NEEDS_REVISION`, or
`SCIENTIFIC_UNRESOLVED`.

`scientific_completion_gate` answers whether the route is scientifically
resolved. It can resolve as `SCIENTIFIC_PROMOTED` or
`SCIENTIFIC_STOP_SUPPORTED`. Operational controller completion alone does not
satisfy this gate.

`diagnostic_publication_gate` answers whether reviewed diagnostic artifacts may
be published even when `route_promotion_gate` fails. Diagnostic publication is
for GPT planner review only. It is not model selection, not a challenge-facing
improvement claim, and not validation readiness.

`diagnostic_publication_scope` lists the exact allowed file classes. Default
allowed classes are controller `controller_report.md`, controller
`execution_plan.md`, relevant subtask `result.md` and `review.md`, small
Markdown decision packets, and reviewed first-party scripts needed to reproduce
the diagnostic conclusion. Default forbidden classes include checkpoints,
predictions, NIfTI outputs, heavy logs, secret-bearing command transcripts,
large or privacy-sensitive raw CSV dumps, full result trees, upload packages,
hosted validation packages, external credentials, and `.env`-style files.

`blocked_after_diagnostic_publication` lists actions that remain forbidden after
diagnostic publication. Defaults include validation packaging, validation
upload, fold expansion, hosted metric claims, label/evaluator/fold split
changes, and next-stage training.

When `allow_git_commit: true`, `auto_git_commit: true`, audit passes, and no
human approval is triggered, the controller may commit approved changes if
`route_promotion_gate` is satisfied or may commit reviewed diagnostic artifacts
if `diagnostic_publication_gate` is satisfied. When `allow_git_push: true` and
`auto_git_push: true` under the same conditions, it may push to the remote. If
the trigger is diagnostic publication only, the commit message and controller
report must state `diagnostic publication only; no route promotion`.

If neither gate is satisfied, the controller must not commit or push. Not
committing or not pushing requires an explicit reason in the controller report.

## Controller Report Required Ending

End every controller report with these fields:

```text
controller_run_status: COMPLETE | INCOMPLETE | BLOCKED
operational_completion_status: COMPLETE | INCOMPLETE
experiment_adequacy_decision: PASS | FAIL | PARTIAL | EVIDENCE_NOT_FOUND
route_promotion_decision: PROMOTE | NO_PROMOTION | NOT_EVALUABLE
route_negative_decision: STOP_SUPPORTED | STOP_NOT_SUPPORTED | NOT_EVALUABLE
scientific_resolution_status: SCIENTIFIC_PROMOTED | SCIENTIFIC_STOP_SUPPORTED | SCIENTIFIC_UNRESOLVED | SCIENTIFIC_UNDERTRAINED | SCIENTIFIC_PIPELINE_BUG | SCIENTIFIC_NEEDS_EVIDENCE | SCIENTIFIC_NEEDS_REVISION
diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET | DO_NOT_PUBLISH | NOT_APPLICABLE
git_commit_decision: COMMIT_ROUTE_PROMOTION | COMMIT_DIAGNOSTIC_ONLY | SKIP_COMMIT
git_push_decision: PUSH_ROUTE_PROMOTION | PUSH_DIAGNOSTIC_ONLY | SKIP_PUSH
published_files:
  - path
blocked_actions:
  - validation upload/fold expansion/next-stage training remain blocked
next_required_action: ...
reason_if_not_published: ...
reason_if_no_route_promotion: ...
```

## Examples

Example A: controller executed all subtasks, but the main training route only
ran `actual_steps=120` and `train_loop_seconds=30`.

```text
controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: FAIL
route_promotion_decision: NOT_EVALUABLE
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNDERTRAINED
next_required_action: write revision task with minimum effective training gate
```

Example B: controller executed all subtasks, fully trained variants,
loss/prediction sanity passed, and metrics remain far below baseline.

```text
controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: PASS
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_SUPPORTED
scientific_resolution_status: SCIENTIFIC_STOP_SUPPORTED
next_required_action: return to GPT planner for new direction
```

Example C: controller executed all subtasks and no route promoted, but a
reviewed diagnostic package is useful.

```text
route_promotion_decision: NO_PROMOTION
diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET
scientific_resolution_status: SCIENTIFIC_UNRESOLVED
blocked_actions:
  - validation upload, fold expansion, next-stage training
```
