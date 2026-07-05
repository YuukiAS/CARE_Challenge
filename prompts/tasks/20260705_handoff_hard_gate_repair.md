---
task_key: "20260705_handoff_hard_gate_repair"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "handoff hard gate repair / controller completion safety"
target_metric: "handoff correctness"
required_evidence:
  - "code_diff"
  - "unit_tests"
  - "strict_validator"
  - "task_graph_gate"
  - "completion_check_gate"
  - "current_bad_packet_regression"
  - "controller_report_schema_gate"
  - "doc_update_summary"
forbidden_substitutes:
  - "missing result directory ignored"
  - "similar filename accepted"
  - "validator exits zero with errors"
  - "final review without completion check"
  - "smoke-scale training treated as full route evidence"
  - "controller report missing terminal status fields"
  - "legacy errors swallowed without explicit allowlist"
promotion_gate: "The repaired gate must fail the known 20260704 SRR-v2.5 incomplete packet and pass new unit/regression tests."
experiment_adequacy_gate: "Not a model-training task. Do not run training. Validate handoff mechanics only."
route_negative_gate: "Not applicable. This task repairs governance and must not draw scientific conclusions about SRR."
scientific_completion_gate: "Operational completion means hard-gate repair is implemented and audited; it does not promote or stop any model route."
allowed_next_states:
  - "EXECUTED_UNAUDITED"
  - "NEEDS_REVISION"
  - "NEEDS_EVIDENCE"
auto_git_commit: false
auto_git_push: false
---

# Task: Handoff Hard-Gate Repair

## Goal

Repair the CARE handoff system so future controller goals cannot skip required subtasks, bypass completion checks, or treat undertrained smoke evidence as full route completion.

This is a governance and validation repair task only. Do not train SRR, do not train Cine, do not package validation, do not upload, and do not choose a new scientific route.

## Required Work

Update `scripts/validation/validate_srr_v25_anti_laziness.py` or add a new validator under `scripts/validation/` so that blocking subtasks referenced by a controller task require exact result directories and exact required output files.

A missing `results/<task_key>/` for a blocking subtask must be an error, not a silent skip.

Required output filenames must match exactly. A similar filename is still a missing required file.

Strict validation must be the default behavior for completion decisions. A validator run with `error_count > 0` must return nonzero unless the command explicitly opts into diagnostic non-strict mode. If legacy findings need to be tolerated, implement an explicit allowlist with reason, expiry, and owner.

Add a task-graph consistency check. The validator must compare the controller task’s ordered subtask list, the controller report’s executor subtask list, and the actual `results/<task_key>/` directories. If a required subtask is missing from the controller report or results tree, report a named blocker.

Add a completion-check-before-final-review gate. If a controller requires `*_completion_check` before `*_final_readonly_audit` or equivalent final review, the final review is blocked unless `results/<completion_check_task>/decision.md` exists and declares `READY_FOR_FINAL_AUDIT` or a task-defined equivalent.

Add an adequacy classifier for smoke-scale training evidence. The validator or report checker must detect when a trainable model route has only tiny probes, very low optimizer steps, missing validation events, missing prediction sanity, limited explicit eval cases, or missing same-split baseline comparison. Such evidence may be diagnostic, but it cannot support route promotion or scientific stop.

Update relevant protocol docs or templates so future GPT planning and execution sessions reference `prompts/GPT_HARD_GATE_PROMPT.md`, `prompts/HANDOFF_GATE_POLICY.md`, and this repair task. Candidate files include `prompts/AGENT_RULES.md`, `prompts/CHATGPT_RULES.md`, `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`, and `prompts/CARE_OVERLAY_GATES.md`. Keep edits minimal and auditable.

## Required Regression

Run the repaired validator against `prompts/tasks/20260704_srr_v25_full_completion_goal.md` and the current `results/` tree.

This command must fail in strict mode and must name at least these blockers:

* missing result directory for `20260704_cine_temporal_dictionary_integration`;
* missing result directory for `20260704_srr_v25_completion_check`;
* final review reached without completion-check readiness;
* 6-step bounded SRR probes classified as diagnostic or undertrained, not adequate full-route training.

If the repaired validator does not fail this known bad packet, the task is not complete.

## Required Tests

Add or update unit tests covering:

* missing result directory is an error;
* required file name mismatch is an error;
* controller task graph and controller report subtask list mismatch is an error;
* final review without completion check is an error;
* validator returns nonzero on errors in strict/default completion mode;
* known 20260704 SRR-v2.5 bad packet fails the regression gate;
* smoke-scale training cannot support route promotion or scientific stop.

## Required Outputs

Write `results/20260705_handoff_hard_gate_repair/` with:

* `result.md`
* `validator_change_summary.md`
* `task_graph_gate_report.md`
* `strict_mode_report.md`
* `completion_check_gate_report.md`
* `current_bad_packet_regression.md`
* `unit_test_report.md`
* `doc_update_summary.md`
* `MANIFEST.md`

## Completion Gate

Do not mark this task as `PASS` unless all unit tests pass, the current bad packet fails strict validation with the named blockers above, and docs/templates now point future planning and execution to the hard-gate policy.

If only part of the repair is implemented, mark `NEEDS_REVISION` and list the remaining blockers.
