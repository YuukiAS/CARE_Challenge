---
task_key: "20260705_handoff_hard_gate_repair_review"
project: "CARE_Challenge"
status: "READY"
task_type: "audit"
risk_level: "low"
allow_code_change: false
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: false
mechanism_class: "read-only audit of handoff hard gate repair"
target_metric: "handoff correctness"
required_evidence:
  - "result_review"
  - "validator_diff_review"
  - "unit_test_review"
  - "bad_packet_regression_review"
  - "doc_reference_review"
forbidden_substitutes:
  - "fixing code during audit"
  - "generating missing repair artifacts"
  - "approving without checking strict failure"
allowed_next_states:
  - "AUDITED_GO"
  - "NEEDS_REVISION"
  - "NEEDS_EVIDENCE"
auto_git_commit: false
auto_git_push: false
---

# Task: Read-Only Review Of Handoff Hard-Gate Repair

Read `prompts/tasks/20260705_handoff_hard_gate_repair.md` and all artifacts under `results/20260705_handoff_hard_gate_repair/`. This is a read-only audit. Do not edit code, generate missing artifacts, train models, package validation, upload, or plan a new SRR/Cine route.

Verify that the repair satisfies its completion gate:

- unit and regression tests passed;
- default strict validation exits nonzero on errors;
- `--diagnostic-non-strict` is the only zero-exit mode with errors;
- the known bad packet `20260704_srr_v25_full_completion_goal` fails with the required blockers;
- missing required result directories, missing required outputs, missing completion-check readiness, controller report schema gaps, and smoke-scale training evidence are checked;
- protocol docs/templates reference `prompts/HANDOFF_GATE_POLICY.md` and `prompts/GPT_HARD_GATE_PROMPT.md`.

Write `results/20260705_handoff_hard_gate_repair/review.md` with a claim table, evidence summary, decision, remaining blockers if any, and the allowed next state. Use `AUDITED_GO` only if the hard-gate repair is sufficient for future GPT planning. Otherwise use `NEEDS_REVISION` or `NEEDS_EVIDENCE`.