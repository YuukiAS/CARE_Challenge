# Review: 20260705 Handoff Hard-Gate Repair

task_key: `20260705_handoff_hard_gate_repair_review`
reviewed_task: `prompts/tasks/20260705_handoff_hard_gate_repair.md`
reviewed_result_dir: `results/20260705_handoff_hard_gate_repair/`
decision: `AUDITED_GO`
allowed_next_state: `AUDITED_GO`

## Scope

This was a read-only audit of the handoff hard-gate repair. I did not edit code, generate missing repair artifacts, train models, package validation, upload, or plan a new SRR/Cine route. The only file written by this audit is this `review.md`.

## Claim Table

| Claim | Decision | Evidence |
| --- | --- | --- |
| Required repair artifacts exist under `results/20260705_handoff_hard_gate_repair/`. | `SUPPORTED` | Directory contains `result.md`, `validator_change_summary.md`, `task_graph_gate_report.md`, `strict_mode_report.md`, `completion_check_gate_report.md`, `current_bad_packet_regression.md`, `unit_test_report.md`, `doc_update_summary.md`, and `MANIFEST.md`. |
| Missing required `results/<task_key>/` directories are blockers. | `SUPPORTED` | `check_required_file_names()` emits `REQUIRED_RESULT_DIR_MISSING`; strict regression reports missing dirs for `20260704_cine_temporal_dictionary_integration` and `20260704_srr_v25_completion_check`. |
| Required output filenames must match exactly. | `SUPPORTED` | `check_required_file_names()` emits `REQUIRED_FILE_MISSING`; unit test `test_required_file_name_checker_rejects_similar_replacement` covers similar-name rejection. |
| Controller task graph, controller report subtask list, and result dirs are checked. | `SUPPORTED` | `check_task_graph_consistency()` emits `CONTROLLER_REPORT_SUBTASK_MISSING` and `TASK_GRAPH_RESULT_DIR_MISSING`; unit test covers mismatch. |
| Final audit is blocked without completion-check readiness. | `SUPPORTED` | `check_completion_check_before_final_review()` requires `decision.md` with `READY_FOR_FINAL_AUDIT` or `FINAL_AUDIT_READY`; bad-packet regression reports `COMPLETION_CHECK_READINESS_MISSING`. |
| Controller report terminal schema gaps are checked. | `SUPPORTED` | `check_controller_report_schema()` requires terminal fields including `controller_run_status`, `operational_completion_status`, route decisions, git decisions, published files, blocked actions, and reasons; unit test covers missing field. |
| Smoke-scale bounded SRR evidence cannot support full-route completion, route promotion, or scientific stop. | `SUPPORTED` | `check_training_evidence_adequacy()` emits `SMOKE_SCALE_TRAINING_INADEQUATE`; bad-packet regression reports bounded 6-step / limited eval evidence as inadequate. |
| Strict/default validator exits nonzero when errors exist. | `SUPPORTED` | Re-run strict/default command exited `1` with `error_count: 18`. |
| `--diagnostic-non-strict` is the explicit zero-exit mode with errors. | `SUPPORTED` | Re-run diagnostic command exited `0` with the same `error_count: 18`. |
| Unit and regression tests pass. | `SUPPORTED` | Re-ran `test_srr_v25_anti_laziness_validator`: `Ran 12 tests`, `OK`; re-ran `test_handoff_policy_validator`: `Ran 9 tests`, `OK`; `py_compile` exited `0`. |
| Docs/templates reference the hard-gate policy and GPT hard-gate prompt. | `SUPPORTED` | `rg` confirms references in `prompts/AGENT_RULES.md`, `prompts/CHATGPT_RULES.md`, `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`, and `prompts/CARE_OVERLAY_GATES.md`. |
| Docs/templates directly name the repair task file `20260705_handoff_hard_gate_repair.md`. | `PARTIAL_NON_BLOCKING` | `rg` found no direct task-file-name reference in the checked docs/templates. This is not a blocker for future GPT planning because the docs/templates point to the durable policy and GPT hard-gate prompt, and the reviewed result packet is present. |

## Commands Re-Run

```bash
env PYTHONDONTWRITEBYTECODE=1 ./envs/env_CARE/bin/python -m unittest src.care_myocardium.tests.test_srr_v25_anti_laziness_validator
```

Result: exit `0`, `Ran 12 tests`, `OK`.

```bash
env PYTHONDONTWRITEBYTECODE=1 ./envs/env_CARE/bin/python -m unittest src.care_myocardium.tests.test_handoff_policy_validator
```

Result: exit `0`, `Ran 9 tests`, `OK`.

```bash
env PYTHONDONTWRITEBYTECODE=1 ./envs/env_CARE/bin/python -m py_compile scripts/validation/validate_srr_v25_anti_laziness.py src/care_myocardium/tests/test_srr_v25_anti_laziness_validator.py
```

Result: exit `0`.

```bash
env PYTHONDONTWRITEBYTECODE=1 ./envs/env_CARE/bin/python scripts/validation/validate_srr_v25_anti_laziness.py --repo-root . --controller prompts/tasks/20260704_srr_v25_full_completion_goal.md --results-root results --json
```

Result: exit `1`, `issue_count: 18`, `error_count: 18`, `warning_count: 0`.

```bash
env PYTHONDONTWRITEBYTECODE=1 ./envs/env_CARE/bin/python scripts/validation/validate_srr_v25_anti_laziness.py --repo-root . --controller prompts/tasks/20260704_srr_v25_full_completion_goal.md --results-root results --json --diagnostic-non-strict
```

Result: exit `0`, with the same `issue_count: 18`, `error_count: 18`, `warning_count: 0`.

```bash
git diff --check -- scripts/validation/validate_srr_v25_anti_laziness.py src/care_myocardium/tests/test_srr_v25_anti_laziness_validator.py prompts/AGENT_RULES.md prompts/CHATGPT_RULES.md prompts/templates/CONTROLLER_TASK_TEMPLATE.md prompts/CARE_OVERLAY_GATES.md results/20260705_handoff_hard_gate_repair/result.md results/20260705_handoff_hard_gate_repair/validator_change_summary.md results/20260705_handoff_hard_gate_repair/task_graph_gate_report.md results/20260705_handoff_hard_gate_repair/strict_mode_report.md results/20260705_handoff_hard_gate_repair/completion_check_gate_report.md results/20260705_handoff_hard_gate_repair/current_bad_packet_regression.md results/20260705_handoff_hard_gate_repair/unit_test_report.md results/20260705_handoff_hard_gate_repair/doc_update_summary.md results/20260705_handoff_hard_gate_repair/MANIFEST.md
```

Result: exit `0`.

## Bad-Packet Regression Evidence

The strict/default validator fails `20260704_srr_v25_full_completion_goal` and names the required blockers:

- `REQUIRED_RESULT_DIR_MISSING`: `20260704_cine_temporal_dictionary_integration`
- `REQUIRED_RESULT_DIR_MISSING`: `20260704_srr_v25_completion_check`
- `CONTROLLER_REPORT_SUBTASK_MISSING`: both missing subtasks
- `TASK_GRAPH_RESULT_DIR_MISSING`: both missing result dirs
- `COMPLETION_CHECK_READINESS_MISSING`: `results/20260704_srr_v25_completion_check/decision.md`
- `SMOKE_SCALE_TRAINING_INADEQUATE`: bounded 6-step / limited eval evidence

The run also reports older `CLAIM_WITHOUT_RUNTIME_EVIDENCE` errors. These are not swallowed by default and are therefore consistent with the strict fail-closed behavior.

## Blockers

No blockers for the handoff hard-gate repair.

Non-blocking observation: the updated docs/templates point to `prompts/HANDOFF_GATE_POLICY.md` and `prompts/GPT_HARD_GATE_PROMPT.md`, but do not directly name `prompts/tasks/20260705_handoff_hard_gate_repair.md`. The durable policy/prompt references are sufficient for future GPT planning.

## Decision

decision: `AUDITED_GO`

The hard-gate repair is sufficient for future GPT planning. This audit does not authorize model training, validation packaging, validation upload, fold expansion, challenge-facing route promotion, or a scientific stop for SRR/Cine.
