# Experiment Adequacy Gate

This migration separates controller operational completion from scientific
route resolution.

## Three Independent Outcomes

- `controller_run_status`: whether the controller completed the authorized
  workflow, including planning, subagent launch or fallback, executor result,
  auditor review, and controller report.
- `diagnostic_publication_decision`: whether reviewed diagnostic artifacts may
  be committed/pushed for GPT planner review.
- `scientific_resolution_status`: whether the scientific route is promoted,
  stopped by adequate negative evidence, or still unresolved.

`controller_run_status: COMPLETE` is not the same as
`scientific_resolution_status: SCIENTIFIC_STOP_SUPPORTED`.

## Scientific States

Use one of:

- `SCIENTIFIC_PROMOTED`
- `SCIENTIFIC_STOP_SUPPORTED`
- `SCIENTIFIC_UNRESOLVED`
- `SCIENTIFIC_UNDERTRAINED`
- `SCIENTIFIC_PIPELINE_BUG`
- `SCIENTIFIC_NEEDS_EVIDENCE`
- `SCIENTIFIC_NEEDS_REVISION`

## Experiment Adequacy Gate

For CARE training/segmentation routes, `experiment_adequacy_gate` requires:

- one-batch or one-case overfit sanity, unless explicitly not applicable;
- `train_loop_seconds`;
- `max_steps`;
- `actual_steps`;
- `optimizer_steps`;
- `validation_events`;
- `loss_decrease`;
- prediction sanity, including foreground rate, compact label values,
  raw/compact decode path, per-class prediction volume, component count, and
  empty rate;
- proposal/refinement sanity for proposal tasks, including proposal recall,
  proposal precision, lesion-wise recall, and outside-myocardium FP ratio;
- logs/provenance, including training logs, `summary.json`, config,
  checkpoint, prediction paths, and metric CSV;
- same-split baseline comparison under the same evaluator, split, and label
  mapping.

Slurm elapsed time alone is not sufficient. If stdout/stderr are zero bytes, an
explicit transcript can substitute only when the report names it as replacement
evidence.

## Route Negative Gate

`route_negative_gate` passes only when:

1. `experiment_adequacy_gate` passes;
2. forbidden substitutes are absent;
3. same-split baseline comparison exists;
4. metric failure is not explained by undertraining, smoke/preflight,
   decode error, cache contamination, label/export mismatch, missing logs, or
   pipeline bug;
5. auditor explicitly approves the route-negative conclusion.

If the gate fails, do not write scientific stops such as `STOP_NO_SIGNAL`,
`STOP_NO_PROPREF_SIGNAL`, `STOP_NO_CLEAN_ANCHOR_SIGNAL`, or
`STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL`. Use `NEEDS_REVISION`,
`NEEDS_EVIDENCE`, `STOP_PIPELINE_BUG`, `SCIENTIFIC_UNDERTRAINED`,
`SCIENTIFIC_UNRESOLVED`, or controller-level `NEEDS_GPT_PLANNER` while stating
that the scientific route is unresolved.

## Examples

Example A: controller executed all subtasks, but the main training route only
ran `actual_steps=120` and `train_loop_seconds=30`.

```text
controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: FAIL
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNDERTRAINED
next_required_action: write revision task with minimum effective training gate
```

Example B: controller executed all subtasks, fully trained variants,
loss/prediction sanity passed, and metrics remain far below baseline.

```text
controller_run_status: COMPLETE
experiment_adequacy_decision: PASS
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
blocked_actions: validation upload, fold expansion, next-stage training
```
