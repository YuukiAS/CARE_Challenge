# Controller Report: 20260703 SRR Recovery Goal

controller_task_id: 20260703_srr_recovery_goal
controller_task: `prompts/tasks/20260703_srr_recovery_goal.md`
controller_role: Codex execution controller
status: COMPLETE

## Executive Summary

This controller executed the GPT-authored SRR recovery workflow with separate
executor and read-only auditor subagents. The prior `STOP_NO_PROPREF_SIGNAL`
is not scientifically supported. The old PropRef run and the repaired PropRef
run both fail the experiment adequacy gate; the OOF component scorer has a
leakage-safe diagnostic signal but does not support route promotion because scar
HD/HD95 worsened; learned anchor refine lacks reviewed prerequisite evidence and
therefore was not trained.

The controller outcome is diagnostic publication only; no route promotion, no
scientific stop, and no validation/fold-expansion action is authorized.

## Subtasks

| subtask | executor result | auditor review | audit decision | scientific status |
| --- | --- | --- | --- | --- |
| `20260703_srr_failure_audit` | `results/20260703_srr_failure_audit/result.md` | `results/20260703_srr_failure_audit/review.md` | `AUDITED_DIAGNOSTIC_PUBLISH` | `SCIENTIFIC_UNDERTRAINED` |
| `20260703_srr_propref_repair` | `results/20260703_srr_propref_repair/result.md` | `results/20260703_srr_propref_repair/review.md` | `AUDITED_DIAGNOSTIC_PUBLISH` | `SCIENTIFIC_UNDERTRAINED` |
| `20260703_nnunet_oof_component` | `results/20260703_nnunet_oof_component/result.md` | `results/20260703_nnunet_oof_component/review.md` | `AUDITED_DIAGNOSTIC_PUBLISH` | `SCIENTIFIC_UNRESOLVED` |
| `20260703_anchor_refine_learned` | `results/20260703_anchor_refine_learned/result.md` | `results/20260703_anchor_refine_learned/review.md` | `AUDITED_DIAGNOSTIC_PUBLISH` | `SCIENTIFIC_NEEDS_EVIDENCE` |

## Session Evidence

- failure audit executor: `019f2872-06d0-7c40-a0e6-be47a65d50ef`
- failure audit auditor: `019f2878-27b6-7442-b572-343c6ccb13ec`
- SRR PropRef repair executor: `019f287c-baca-7602-8fd1-f4e4499126d6`
- SRR PropRef repair auditor: `019f288d-1cd4-7122-9746-640a58ebab32`
- nnU-Net OOF component executor: `019f287d-125d-7673-a39e-ece4888a7aa4`
- nnU-Net OOF component auditor: `019f288f-8d6b-7691-a106-475c9dc5ebb8`
- learned anchor refine executor: `019f2894-6928-7920-b833-77855316f735`
- learned anchor refine auditor: `019f2897-92b1-70b0-94cc-ee35d000be88`

The controller execution plan is
`results/20260703_srr_recovery_goal/execution_plan.md`.

## Gate Decisions

### Failure Audit

The failure audit review supports:

- `experiment_adequacy_decision: FAIL`
- `route_negative_decision: STOP_NOT_SUPPORTED`
- `scientific_resolution_status: SCIENTIFIC_UNDERTRAINED`
- `recommended_next_state: NEEDS_REVISION`

The previous `STOP_NO_PROPREF_SIGNAL` is superseded by the current adequacy
gate. The evidence shows `max_steps=120`, `best_step=1`, missing post-warmup
validation, short train-loop seconds, partial proposal/decode sanity, and
insufficient route-negative support.

### SRR PropRef Repair

The repair executor patched the runner and scripts for checkpoint policy,
explicit counters, one-batch overfit, prototype gradient/update sanity,
pathology-aware decode, PR sweep hooks, and task-scoped provenance. The repair
audit supports diagnostic publication of these changes, but formal adequate
fold0 training was not completed. The evidence is an interrupted CPU smoke plus
partial artifacts, not a full adequate training/evaluation run.

Supported decisions:

- `experiment_adequacy_decision: FAIL`
- `route_promotion_decision: NOT_EVALUABLE`
- `route_negative_decision: STOP_NOT_SUPPORTED`
- `scientific_resolution_status: SCIENTIFIC_UNDERTRAINED`

### nnU-Net OOF Component

The OOF component executor used folds 1-4 validation outputs as train-side OOF
evidence for fold0 train cases and froze threshold `1.30` before fold0
evaluation. The audit supports this as leakage-safe for the bounded diagnostic.
However, route promotion is not supported because scar HD/HD95 worsened despite
fewer FP components.

Supported decisions:

- `experiment_adequacy_decision: PASS`
- `route_promotion_decision: NO_PROMOTION`
- `route_negative_decision: STOP_NOT_SUPPORTED`
- `scientific_resolution_status: SCIENTIFIC_UNRESOLVED`

### Learned Anchor Refine

Learned anchor refine was not trained. The executor correctly found that the
reviewed prerequisites are diagnostic-only and do not authorize learned
refinement execution. The audit supports the evidence-missing outcome.

Supported decisions:

- `experiment_adequacy_decision: EVIDENCE_NOT_FOUND`
- `route_promotion_decision: NOT_EVALUABLE`
- `route_negative_decision: NOT_EVALUABLE`
- `scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE`

## Diagnostic Publication

diagnostic publication only; no route promotion

The diagnostic publication gate is satisfied because each executor result has a
separate read-only audit and the reviews support `AUDITED_DIAGNOSTIC_PUBLISH`.
The local diagnostic-only commit was created. The remote push was attempted, but
the execution environment rejected it as public-repository external disclosure.

The publication packet includes only reviewed reports, compact diagnostic
tables, and first-party scripts needed for GPT planner review. It does not
include checkpoints, predictions, NIfTI outputs, heavy logs, command
transcripts, upload packages, validation packages, credentials, or `.env` files.

## Published Files

The intended diagnostic-only commit/push scope is:

- `results/20260703_srr_recovery_goal/controller_report.md`
- `results/20260703_srr_recovery_goal/execution_plan.md`
- `results/20260703_srr_recovery_goal/MANIFEST.md`
- subtask `result.md` and `review.md` files
- reviewed subtask Markdown decision packets
- compact diagnostic metric/provenance CSV/JSON files needed to inspect the
  diagnostic conclusions
- `scripts/training/run_srr_propref_myops_fold0.py`
- `jobs/src/run_srr_propref_myops_fold0.sh`
- `scripts/evaluation/aggregate_srr_propref_repair_20260703.py`
- `scripts/evaluation/run_nnunet_oof_component_20260703.py`

## Blocked Actions

- validation packaging
- validation upload
- upload-ready package generation
- fold expansion
- hosted metric claims
- label/evaluator/fold split changes
- old SRR-v2 tuning routes
- next-stage training without a new GPT-authored task
- route-negative scientific stop based on the current PropRef evidence

## Incomplete Scientific Items

- Adequate PropRef formal fold0 training was not completed.
- PropRef route promotion is not evaluable.
- PropRef route-negative stop is not supported.
- OOF component scorer is diagnostic only because HD/HD95 worsened.
- Learned anchor refine needs evidence and was not trained.

## Required Next Action

Return to the GPT strategic planner. A next task can either authorize an
adequate SRR PropRef training run using the repaired runner and minimum
effective training gate, or choose a different strategy. This controller must
not invent the next scientific direction.

## Required Ending

controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: PARTIAL
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE
diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET
git_commit_decision: COMMIT_DIAGNOSTIC_ONLY
git_push_decision: SKIP_PUSH
published_files:
  - results/20260703_srr_recovery_goal/controller_report.md
  - results/20260703_srr_recovery_goal/execution_plan.md
  - results/20260703_srr_recovery_goal/MANIFEST.md
  - reviewed subtask result/review/report artifacts listed in the diagnostic-only commit
  - reviewed first-party SRR/OOF diagnostic scripts listed in the diagnostic-only commit
blocked_actions:
  - validation upload/fold expansion/next-stage training remain blocked
next_required_action: return to GPT planner for a new evidence-generation task or strategic decision
reason_if_not_published: local diagnostic commit created, but remote push was rejected by the execution environment as public-repository external disclosure
reason_if_no_route_promotion: SRR repair is undertrained, OOF scorer worsened scar HD/HD95, and learned anchor refine lacks prerequisite evidence
