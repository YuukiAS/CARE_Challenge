# Result 000 Short Task

status: EXECUTED_UNAUDITED
self_assessed_status: completed

## Execution Summary

Briefly state what was completed, what was not completed, and whether the task
goal appears satisfied from the executor perspective. Start with the practical
meaning in natural prose before listing paths, metrics, commands, or state
tokens.

## Final Output Readability

If this result is summarized for a user, Planner, controller, or reviewer, apply
`prompts/FINAL_OUTPUT_READABILITY_POLICY.md`. First explain the main finding,
why it happened, what should happen next, and what should not be done yet. Put
internal labels and technical evidence after that explanation.

## Files Read

- `path/to/file.md`: purpose and key finding.

## Files Modified

- `path/to/file.py`: change summary.

If no files were modified, write `none`.

## Commands Run

```bash
command
```

- purpose:
- result:
- exit_status:

If no commands were run, write `none`.

## Test Results

- test_or_validation:
- result:
- evidence:

If no tests were run, explain why.

## Experiment Adequacy Evidence

For model/training routes, report:

- one_batch_or_one_case_overfit:
- train_loop_seconds:
- max_steps:
- actual_steps:
- optimizer_steps:
- validation_events:
- loss_decrease:
- prediction_sanity:
  - foreground_rate:
  - compact_label_values:
  - raw_compact_decode_path:
  - per_class_prediction_volume:
  - component_count:
  - empty_rate:
- proposal_refinement_sanity, if applicable:
  - proposal_recall:
  - proposal_precision:
  - lesion_wise_recall:
  - outside_myocardium_fp_ratio:
- logs_provenance:
  - training_log:
  - summary_json:
  - config:
  - checkpoint:
  - prediction_path:
  - metric_csv:
  - transcript_if_stdout_stderr_empty:
- same_split_baseline_comparison:

If the task is not a model/training route, write `not applicable`. If evidence
is missing, write `evidence not found`; do not infer adequacy from Slurm elapsed
time alone.

## Artifact Paths

- `results/000_short_task/MANIFEST.md`: artifact index linking task, result,
  review, and generated files.
- `results/000_short_task/path/to/artifact`: purpose and generation method.

If no additional file artifacts were generated, write `none`.

## Diff Summary

Summarize added, modified, and deleted files. If the target is not a git
repository, say so.

## Claims

Use one auditable claim per line:

- `claim.structure_checked`: The target directory structure was inspected.
- `claim.tests_passed`: The listed validation command exited 0.
- `claim.experiment_adequacy`: The run met the task's minimum effective
  training and sanity requirements.
- `claim.route_negative_supported`: A route-negative stop is supported by
  adequate experiment evidence and same-split baseline comparison.

Do not use domain-specific claim names unless the task defines them.

## Failure Information

Record failed commands, error messages, root cause if known, and incomplete
items. If no failure occurred, write `none`.

## Incomplete Items

- item:
- reason:
- required_next_state:

If none, write `none`.

## Human Approval Needed

List actions that require human approval before continuing. If none, write
`none`.

## Git Commit And Push

- auto_git_commit:
- commit_executed:
- commit_sha:
- auto_git_push:
- push_executed:
- remote:
- route_promotion_gate:
- diagnostic_publication_gate:
- diagnostic_publication_scope:
- diagnostic_publication_only_no_route_promotion:
- reason_if_not_executed:

Executors should not claim final audited promotion or diagnostic publication
unless the task explicitly authorizes them to commit/push without a separate
audit. For medium/high-risk work, publication and promotion decisions belong in
`review.md` or `controller_report.md`.

## Self-Assessed Status

The executor may write one of:

- `completed`
- `partial`
- `blocked`
- `failed`

This is executor self-assessment only. It is not a controller verification
decision and does not replace `controller_report.md`, `completion_check.md`, or
explicit `review.md` when `review_required: true`.

Executors must not self-authorize `SCIENTIFIC_STOP_SUPPORTED` or `STOP_NO_*`.
If experiment adequacy is incomplete, self-assess the scientific state as
`SCIENTIFIC_UNDERTRAINED`, `SCIENTIFIC_NEEDS_EVIDENCE`,
`SCIENTIFIC_NEEDS_REVISION`, or `SCIENTIFIC_UNRESOLVED`.
