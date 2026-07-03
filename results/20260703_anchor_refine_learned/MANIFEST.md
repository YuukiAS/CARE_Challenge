# Manifest 20260703_anchor_refine_learned

task: `prompts/tasks/20260703_anchor_refine_learned.md`
controller_task: `prompts/tasks/20260703_srr_recovery_goal.md`
result: `results/20260703_anchor_refine_learned/result.md`
review: `results/20260703_anchor_refine_learned/review.md` (not written by executor)

## Artifacts

| path | purpose |
| --- | --- |
| `result.md` | Executor self-assessment and decision fields. |
| `training_summary.md` | Records that learned training was not authorized by prerequisite evidence. |
| `one_batch_overfit.md` | Records that one-batch overfit was not run because the prerequisite gate failed. |
| `metrics_summary.md` | Summarizes missing learned metrics and non-evaluable promotion/stop gates. |
| `subgroup_metrics.csv` | Header-only placeholder for subgroup metrics; no learned predictions exist. |
| `component_hd_by_case.csv` | Header-only placeholder for component/HD case metrics; no learned predictions exist. |
| `teacher_student_delta.csv` | Header-only placeholder for teacher/student deltas; no learned checkpoint exists. |
| `label_export_qc.md` | Records missing learned prediction/export evidence and blocked validation packaging/upload. |
| `failure_interpretation.md` | Explains the NEEDS_EVIDENCE decision and blocked actions. |
| `command_transcript.md` | Records commands and non-actions for this executor pass. |

## Prerequisite Reviews Used

- `results/20260703_srr_propref_repair/review.md`
- `results/20260703_nnunet_oof_component/review.md`

## Decision Fields

experiment_adequacy_decision: EVIDENCE_NOT_FOUND

route_promotion_decision: NOT_EVALUABLE

route_negative_decision: NOT_EVALUABLE

scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE

self_assessed_status: NEEDS_EVIDENCE
