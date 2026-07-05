# Task Graph Gate Report

## Gate

The validator compares:

- ordered required subtasks from `prompts/tasks/20260704_srr_v25_full_completion_goal.md`;
- executor subtask rows in `results/20260704_srr_v25_full_completion_goal/controller_report.md`;
- actual top-level directories under `results/`.

## Regression Findings

Strict/default validation reports:

- `REQUIRED_RESULT_DIR_MISSING`: `results/20260704_cine_temporal_dictionary_integration`
- `REQUIRED_RESULT_DIR_MISSING`: `results/20260704_srr_v25_completion_check`
- `CONTROLLER_REPORT_SUBTASK_MISSING`: `20260704_cine_temporal_dictionary_integration`
- `CONTROLLER_REPORT_SUBTASK_MISSING`: `20260704_srr_v25_completion_check`
- `TASK_GRAPH_RESULT_DIR_MISSING`: `20260704_cine_temporal_dictionary_integration`
- `TASK_GRAPH_RESULT_DIR_MISSING`: `20260704_srr_v25_completion_check`

## Decision

task_graph_gate: `FAILS_KNOWN_BAD_PACKET_AS_REQUIRED`

The current SRR-v2.5 packet cannot be treated as operationally complete under the repaired gate.
