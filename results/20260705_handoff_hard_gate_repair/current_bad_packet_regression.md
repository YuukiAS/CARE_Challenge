# Current Bad Packet Regression

## Target

Known incomplete packet:

```text
prompts/tasks/20260704_srr_v25_full_completion_goal.md
results/20260704_srr_v25_full_completion_goal/controller_report.md
```

## Strict/Default Result

Command:

```bash
./envs/env_CARE/bin/python scripts/validation/validate_srr_v25_anti_laziness.py --repo-root . --controller prompts/tasks/20260704_srr_v25_full_completion_goal.md --results-root results --json
```

Result:

```text
exit: 1
issue_count: 18
error_count: 18
warning_count: 0
```

## Required Blockers Present

```text
REQUIRED_RESULT_DIR_MISSING: 20260704_cine_temporal_dictionary_integration
REQUIRED_RESULT_DIR_MISSING: 20260704_srr_v25_completion_check
CONTROLLER_REPORT_SUBTASK_MISSING: 20260704_cine_temporal_dictionary_integration
CONTROLLER_REPORT_SUBTASK_MISSING: 20260704_srr_v25_completion_check
TASK_GRAPH_RESULT_DIR_MISSING: 20260704_cine_temporal_dictionary_integration
TASK_GRAPH_RESULT_DIR_MISSING: 20260704_srr_v25_completion_check
COMPLETION_CHECK_READINESS_MISSING: results/20260704_srr_v25_completion_check/decision.md
SMOKE_SCALE_TRAINING_INADEQUATE: bounded 6-step probe / limited eval cases
```

## Additional Legacy Findings

The strict run also reports existing `CLAIM_WITHOUT_RUNTIME_EVIDENCE` findings in older result/review/controller files. These are not swallowed by default and are not allowlisted by this repair.

## Decision

current_bad_packet_regression: `PASS`

The known bad packet fails strict/default validation with the required named blockers.
