# Validator Change Summary

## Updated Entry Point

Updated `scripts/validation/validate_srr_v25_anti_laziness.py`.

## New Hard Gates

- `REQUIRED_RESULT_DIR_MISSING`: a blocking subtask with no exact `results/<task_key>/` directory is an error.
- `REQUIRED_FILE_MISSING`: exact required output filenames are enforced; similar spellings do not satisfy the requirement.
- `CONTROLLER_REPORT_SUBTASK_MISSING`: controller report executor list must include every ordered required subtask.
- `TASK_GRAPH_RESULT_DIR_MISSING`: required subtasks must exist in the actual results tree.
- `COMPLETION_CHECK_READINESS_MISSING` and `COMPLETION_CHECK_NOT_READY`: final review/audit is blocked without completion-check readiness.
- `CONTROLLER_REPORT_FIELD_MISSING`: terminal controller report fields are required.
- `SMOKE_SCALE_TRAINING_INADEQUATE`: bounded/smoke trainable evidence cannot support full-route completion, route promotion, or scientific stop.

## Strict Behavior

Default command behavior now returns nonzero when `error_count > 0`.

`--diagnostic-non-strict` is the explicit diagnostic escape hatch. It preserves the findings but returns zero for non-completion scans.

The legacy `--strict` flag remains accepted for compatibility, but strict behavior no longer depends on passing it.
