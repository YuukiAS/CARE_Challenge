# Diagnostic Publication Gate

This migration splits two controller outcomes that were previously conflated.

## Route Promotion Gate

`route_promotion_gate` decides whether a model or route may become
challenge-facing. Passing this gate can authorize route promotion, fold
expansion, validation packaging, validation upload, hosted metric claims, or
next-stage training only when the task explicitly allows those actions.

Legacy `promotion_gate` fields remain compatible and should be interpreted as
route-promotion gates unless a task defines a narrower `route_promotion_gate`.

## Diagnostic Publication Gate

`diagnostic_publication_gate` decides whether a controller run that failed route
promotion may still publish reviewed diagnostic artifacts to the repository.
This prevents negative or failed controller runs from leaving all useful
diagnostic code, minimal reports, and audit evidence in ignored local
`results/` state where the GPT planner cannot review them.

Diagnostic publication is not model promotion. It does not mean the route is
selected, challenge-facing, validation-ready, or an improvement over the current
baseline. It also does not mean the scientific route has been resolved; a
diagnostic-only publication may still report
`scientific_resolution_status: SCIENTIFIC_UNRESOLVED` or
`SCIENTIFIC_UNDERTRAINED`.

## Default Diagnostic Publication Scope

Allowed by default after executor plus auditor/re-auditor review:

- controller `controller_report.md`
- controller `execution_plan.md`
- relevant subtask `result.md`
- relevant subtask `review.md`
- small Markdown decision packets such as `failure_interpretation.md`,
  `architecture_gap_audit.md`, `label_export_qc.md`, `training_schedule.md`, or
  `provenance_reconciliation.md`
- reviewed first-party source code/scripts needed to reproduce the diagnostic
  conclusion

Forbidden by default:

- checkpoints
- predictions
- NIfTI outputs
- heavy logs
- command transcripts containing secrets or environment dumps
- large or privacy-sensitive raw CSV dumps
- full result trees
- upload packages
- hosted validation packages
- external credentials
- `.env`-style files

Ignored result files must be added with explicit `git add -f <path>` paths. Do
not change `.gitignore` to unignore an entire generated result tree.

## Blocked After Diagnostic Publication

These remain blocked after diagnostic publication unless another explicit task
authorizes them through route promotion:

- validation packaging
- validation upload
- fold expansion
- hosted metric claims
- label/evaluator/fold split changes
- next-stage training

Diagnostic-only commits and controller reports must state:

```text
diagnostic publication only; no route promotion
```
