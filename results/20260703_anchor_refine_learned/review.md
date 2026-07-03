# Review 20260703 Anchor Refine Learned

audit_decision: AUDITED_DIAGNOSTIC_PUBLISH
claim_audit_decision: SUPPORTED
experiment_adequacy_decision: EVIDENCE_NOT_FOUND
route_promotion_decision: NOT_EVALUABLE
route_negative_decision: NOT_EVALUABLE
scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE
diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET
recommended_next_state: NEEDS_GPT_PLANNER
role: separate read-only auditor
audited_task: `prompts/tasks/20260703_anchor_refine_learned.md`
audited_result: `results/20260703_anchor_refine_learned/result.md`

## Audit Scope

I audited only the task packet under `results/20260703_anchor_refine_learned/`, the GPT-authored task, required handoff/CARE gates, medical-imaging deep-learning gate, and prerequisite reviews named in the user request. I did not edit code, generate missing experiment artifacts, launch training, package validation, upload, expand folds, commit, push, or use network access. I wrote only this `review.md`.

This audit verifies the reviewed packet and prerequisite gate logic. It is not a global forensic process audit of every command that may have run outside the reviewed transcript.

## Claim Ledger

| claim | status | audit finding |
| --- | --- | --- |
| Executor correctly avoided learned training due diagnostic-only prerequisites | SUPPORTED | The task says to use this route only after reviewed prerequisite evidence exists, and allows `NEEDS_EVIDENCE` when prerequisite evidence is missing (`prompts/tasks/20260703_anchor_refine_learned.md:37-41`, `47-51`). The SRR prerequisite review reports undertrained/non-promotable evidence (`results/20260703_srr_propref_repair/review.md:3-9`, `72-84`). The OOF component review explicitly says its evidence is sufficient only for planner consideration and not sufficient to start learned anchor-refine training from that audit alone (`results/20260703_nnunet_oof_component/review.md:73-77`). |
| `claim.prerequisite_gate: NOT_MET` | SUPPORTED | `result.md` cites the same two prerequisite reviews and states the gate failed before training (`result.md:17-22`, `58-60`). This is consistent with the CARE rule that diagnostic publication is not route promotion and does not authorize next-stage training (`prompts/CARE_OVERLAY_GATES.md:39-48`, `49-57`). |
| Required placeholder artifacts are adequate | SUPPORTED | All required task outputs exist as top-level files (`MANIFEST.md:8-21`). Since no learned training was authorized, `training_summary.md`, `one_batch_overfit.md`, `metrics_summary.md`, `label_export_qc.md`, and the header-only CSVs explicitly record missing learned evidence instead of fabricating metrics (`training_summary.md:26-42`; `one_batch_overfit.md:8-21`; `metrics_summary.md:17-29`; `label_export_qc.md:8-25`). |
| `experiment_adequacy_decision: EVIDENCE_NOT_FOUND` | SUPPORTED | The task minimum requires learned training, one-batch overfit, optimizer steps, training time, loss decrease, prediction sanity, checkpoint, metrics, and label/export QC (`prompts/tasks/20260703_anchor_refine_learned.md:21-25`). The reviewed packet reports no learned training, checkpoint, prediction path, metric CSV, run log, or overfit evidence (`training_summary.md:28-42`; `one_batch_overfit.md:12-19`). |
| `route_promotion_decision: NOT_EVALUABLE` | SUPPORTED | No learned fold0 same-split comparison, prediction, metric CSV, or label/export QC exists (`result.md:62-72`; `metrics_summary.md:12-15`, `17-29`). Promotion therefore cannot be evaluated against the unchanged same-split nnU-Net baseline. |
| `route_negative_decision: NOT_EVALUABLE` | SUPPORTED | Route-negative stops require experiment adequacy and auditor support; missing learned evidence cannot support `STOP_NO_LEARNED_ANCHOR_SIGNAL` (`prompts/EXPERIMENT_ADEQUACY_GATE.md:56-73`; `prompts/HANDOFF_STATE_MACHINE.md:69-76`; `prompts/tasks/20260703_anchor_refine_learned.md:49-51`). The executor did not claim a scientific stop. |
| `scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE` | SUPPORTED | The route is neither promoted nor stopped. The state machine includes `SCIENTIFIC_NEEDS_EVIDENCE` for missing scientific evidence (`prompts/HANDOFF_STATE_MACHINE.md:34-36`), and the failure interpretation correctly says this is not a learned route failure (`failure_interpretation.md:6-18`). |
| `self_assessed_status: NEEDS_EVIDENCE` | SUPPORTED | Executor status is explicitly self-assessed, stops at `EXECUTED_UNAUDITED`, and does not claim audited completion (`result.md:3-11`; `prompts/AGENT_RULES.md:106-117`). |
| No network/upload/packaging/fold expansion/training | SUPPORTED_BY_PACKET | The command transcript records `network_used: false`, `external_upload_used: false`, `validation_packaging_used: false`, `fold_expansion_used: false`, `learned_training_run: false`, and no training commands (`command_transcript.md:3-12`, `26-28`). I found no checkpoint, prediction, metric, or subdirectory artifact in the target result packet. |

## Evidence Coverage

Required report artifacts are present: `result.md`, `MANIFEST.md`, `training_summary.md`, `one_batch_overfit.md`, `metrics_summary.md`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `teacher_student_delta.csv`, `label_export_qc.md`, `failure_interpretation.md`, and `command_transcript.md`.

The CSV artifacts are header-only placeholders. That is adequate for this executor outcome because the supported conclusion is missing evidence, not a metric comparison. The packet is careful to mark absent fields as `evidence not found` and does not substitute deterministic postprocessing, preflight checks, or diagnostic OOF thresholding for learned-refiner training.

The packet does not contain learned checkpoints, predictions, logs, formal metric CSVs, or raw-label validation/export evidence. Those absences are the reason the adequacy, promotion, and route-negative gates are not evaluable.

## Audit Decision

The executor's core decision is supported. Given the prerequisite reviews and the task's own gate language, the executor correctly avoided launching learned anchor-refine training and wrote `NEEDS_EVIDENCE` artifacts instead of treating diagnostic-only prerequisite evidence as authorization for next-stage training.

This supports `EVIDENCE_NOT_FOUND`, `NOT_EVALUABLE`, `NOT_EVALUABLE`, `SCIENTIFIC_NEEDS_EVIDENCE`, and `self_assessed_status: NEEDS_EVIDENCE`. It does not support route promotion, validation packaging, upload, fold expansion, hosted metric claims, or a route-negative scientific stop.

## Diagnostic Publication Decision

diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET

Diagnostic publication is supported for the minimal reviewed packet only: `result.md`, `MANIFEST.md`, `training_summary.md`, `one_batch_overfit.md`, `metrics_summary.md`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `teacher_student_delta.csv`, `label_export_qc.md`, `failure_interpretation.md`, `command_transcript.md`, and this `review.md`.

This is diagnostic publication only; no route promotion. Do not publish checkpoints, predictions, NIfTI outputs, upload packages, hosted validation packages, heavy logs, full result trees, credentials, or environment dumps.

## Blocked Actions

- learned anchor-refine training remains blocked under this task outcome
- validation packaging remains blocked
- validation upload remains blocked
- fold expansion remains blocked
- hosted metric claims remain blocked
- raw-label submission/export improvement claims remain blocked
- label/evaluator/fold split changes remain blocked
- route promotion remains blocked
- route-negative scientific stop remains blocked
- git commit/push are not authorized by this execution task (`allow_git_commit: false`, `allow_git_push: false`)

## Controller Launch Decision

The controller should not launch another executor or training job inside this task. The current task has reached a supported `NEEDS_EVIDENCE` outcome. If further work is desired, the controller should report this result and return to the user-supervised GPT planner for a new explicitly authorized evidence-generation task or strategic decision.
