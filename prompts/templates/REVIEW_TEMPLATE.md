---
review_key: "YYYYMMDD_short_slug_review"
task_key: "YYYYMMDD_short_slug"
project: "CARE_Challenge"
reviewer: "separate read-only Codex auditor session or ChatGPT reviewer"
role: "auditor"
read_only: true
audited_status: "TRUE_DONE | PARTIAL_MECHANISM_INCOMPLETE | PREFLIGHT_SMOKE_ONLY | NOT_DONE"
promotion_decision: "GO_FOLD_EXPAND | GO_SUBMISSION_PACKAGE | REVISE | STOP | OPEN_NEXT_TASK | NEEDS_GPT_PLANNER"
route_promotion_decision: "PROMOTE_ROUTE | NO_PROMOTION | NEEDS_GPT_PLANNER | STOP"
experiment_adequacy_decision: "PASS | FAIL | PARTIAL | EVIDENCE_NOT_FOUND"
route_negative_decision: "STOP_SUPPORTED | STOP_NOT_SUPPORTED | NOT_EVALUABLE"
scientific_resolution_status: "SCIENTIFIC_PROMOTED | SCIENTIFIC_STOP_SUPPORTED | SCIENTIFIC_UNRESOLVED | SCIENTIFIC_UNDERTRAINED | SCIENTIFIC_PIPELINE_BUG | SCIENTIFIC_NEEDS_EVIDENCE | SCIENTIFIC_NEEDS_REVISION"
diagnostic_publication_decision: "PUBLISH_REVIEWED_DIAGNOSTIC_PACKET | DO_NOT_PUBLISH | NOT_APPLICABLE"
---

# CARE Evidence Audit: <task_key>

## Read-Only Boundary
The auditor must not modify code, create missing artifacts, launch training, rerun experiments, package submissions, or upload. If evidence is missing, report it as missing.

## Inputs Reviewed
- Task file:
- Result file:
- MANIFEST:
- Controller report, if any:
- Selection file, if any:
- `metrics_summary` or metric CSV:
- Key logs:
- Key code paths:
- Checkpoint/prediction/export paths:

## Task Goal
Summarize the claimed CARE target metric, mechanism class, and authorized scope.

## Claimed Completion
List executor/controller claims as `claim.<name>: <description>`.

## Claim Ledger
| Claim | Decision (`SUPPORTED`, `PARTIAL`, `UNSUPPORTED`, `CONTRADICTED`) | Evidence | Notes |
| --- | --- | --- | --- |
| claim.example | UNSUPPORTED | evidence not found | Replace with real claim. |

## Supported Claims
List claims fully supported by files, metrics, logs, and CARE gate evidence.

## Partial Claims
List claims with incomplete or proxy evidence.

## Unsupported Claims
List claims lacking evidence.

## Contradicted Claims
List claims contradicted by task boundaries, metrics, logs, label/export checks, no-T2 semantics, or CARE overlay.

## Missing Evidence
Report missing checkpoint, prediction, metric, log, same-split baseline, subgroup metric, HD95, component count, remote FP, volume ratio, cache isolation, label/export QC, or hosted-metric caveat as `evidence not found` or `未找到证据`.

## Permission Boundary Check
State whether the executor stayed within task authorization. Include any unauthorized code change, shell command, commit, push, upload, fold expansion, package build, or training.

## CARE Gate Check
Check the Bridge Kit handoff state, the medical-imaging skill mechanism gate, and `prompts/CARE_OVERLAY_GATES.md`. Note any conflict or overlap explicitly.

## Experiment Adequacy Check
For model/training routes, audit whether evidence is sufficient for the claimed
scientific conclusion:

- actual training budget: `train_loop_seconds`, `max_steps`, `actual_steps`,
  `optimizer_steps`, and `validation_events`
- loss curve or `loss_decrease`
- one-batch or one-case overfit sanity
- prediction foreground sanity, compact labels, raw/compact decode path,
  per-class prediction volume, component count, and empty rate
- proposal recall/precision, lesion-wise recall, and outside-myocardium FP ratio
  for proposal/refinement tasks
- train/val/cache isolation
- same-split baseline comparability under the same evaluator, split, and label
  mapping
- whether the evidence supports promotion, diagnostic-only publication,
  undertrained/unresolved status, pipeline bug, or supported stop

If formal training has too few optimizer steps, `train_loop_seconds` is
obviously too low, prediction/proposal sanity collapses without explanation, or
key provenance is missing, mark claims as `PARTIAL` or `UNSUPPORTED`. Do not
support `AUDITED_GO`, `STOP_NO_SIGNAL`, or equivalent route-negative
conclusions.

## Audited Status
Use exactly one: `TRUE_DONE`, `PARTIAL_MECHANISM_INCOMPLETE`, `PREFLIGHT_SMOKE_ONLY`, or `NOT_DONE`.

## Promotion Decision
Use exactly one: `GO_FOLD_EXPAND`, `GO_SUBMISSION_PACKAGE`, `REVISE`, `STOP`, `OPEN_NEXT_TASK`, or `NEEDS_GPT_PLANNER`.

## Route Promotion Decision
Use exactly one: `PROMOTE_ROUTE`, `NO_PROMOTION`, `NEEDS_GPT_PLANNER`, or `STOP`. A diagnostic-only result must use `NO_PROMOTION`.

## Experiment Adequacy Decision
Use exactly one: `PASS`, `FAIL`, `PARTIAL`, or `EVIDENCE_NOT_FOUND`. Explain
whether one-batch/tiny-overfit, effective training, loss, prediction/proposal
sanity, provenance, and same-split baseline evidence are sufficient.

## Route Negative Decision
Use exactly one: `STOP_SUPPORTED`, `STOP_NOT_SUPPORTED`, or `NOT_EVALUABLE`.
`STOP_SUPPORTED` requires `experiment_adequacy_decision: PASS` and explicit
evidence that failure is not explained by undertraining, smoke/preflight,
decode/cache/label/log/provenance problems, or a pipeline bug.

## Scientific Resolution Status
Use exactly one: `SCIENTIFIC_PROMOTED`, `SCIENTIFIC_STOP_SUPPORTED`,
`SCIENTIFIC_UNRESOLVED`, `SCIENTIFIC_UNDERTRAINED`,
`SCIENTIFIC_PIPELINE_BUG`, `SCIENTIFIC_NEEDS_EVIDENCE`, or
`SCIENTIFIC_NEEDS_REVISION`.

## Diagnostic Publication Decision
Use exactly one: `PUBLISH_REVIEWED_DIAGNOSTIC_PACKET`, `DO_NOT_PUBLISH`, or `NOT_APPLICABLE`. Publishing a reviewed diagnostic packet does not authorize route promotion, validation packaging/upload, fold expansion, hosted metric claims, label/evaluator/fold split changes, or next-stage training.

## Blocked Promotion Reason
If promotion is blocked, explain the missing evidence, boundary issue, failed gate, or need for GPT strategic planning.

## Next Allowed Action
State the next action allowed under the task and CARE overlay. Without `review.md`, `audit.md`, or `controller_report.md`, high-risk/controller work must not proceed to fold expansion, validation packaging, upload, or next-stage training.
