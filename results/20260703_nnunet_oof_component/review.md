# Review 20260703 nnU-Net OOF Component

audit_decision: AUDITED_DIAGNOSTIC_PUBLISH
role: read-only auditor
audited_task: `prompts/tasks/20260703_nnunet_oof_component.md`
audited_result: `results/20260703_nnunet_oof_component/result.md`
audited_manifest: `results/20260703_nnunet_oof_component/MANIFEST.md`

## Audit Summary

The executor produced the requested OOF component-scoring package and the central leakage claim is supported. Existing Dataset501 folds 1-4 validation outputs cover the 176 fold0-training cases with no overlap against the 44 fold0 validation cases, and `scripts/evaluation/run_nnunet_oof_component_20260703.py` selects threshold `1.30` from train-side OOF payloads before loading fold0 validation payloads for evaluation.

The current evidence supports diagnostic publication, not route promotion. OOF threshold selection improved train-side component, remote-FP, and small-FP means with negligible Dice loss, but fold0 evaluation shows scar component/remote/small-FP improvements at the cost of worse all-case scar HD and HD95. Edema metrics are unchanged. Therefore `experiment_adequacy_decision: PASS`, `route_promotion_decision: NO_PROMOTION`, `route_negative_decision: STOP_NOT_SUPPORTED`, and `scientific_resolution_status: SCIENTIFIC_UNRESOLVED` are supported for this bounded diagnostic task.

## Required Reads

- Repo/protocol: `AGENTS.md`, `prompts/AGENT_RULES.md`, `prompts/HANDOFF_STATE_MACHINE.md`, `prompts/EXPERIMENT_ADEQUACY_GATE.md`, `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`, `prompts/CONTROLLER_TASK_PROTOCOL.md`, `prompts/CARE_OVERLAY_GATES.md`.
- Skill/gate: `.agents/skills/agent-task-executor/SKILL.md`, `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`, `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`.
- Current task/package: `prompts/tasks/20260703_nnunet_oof_component.md`, `results/20260703_nnunet_oof_component/*`, `scripts/evaluation/run_nnunet_oof_component_20260703.py`.
- Prerequisite evidence: `results/20260703_myops_fp_control/result.md`, `results/20260703_myops_fp_control/review.md`, `results/20260703_myops_fp_control/baseline_vs_variant_metrics.csv`, `results/20260703_myops_audit/review.md`, `scripts/evaluation/run_myops_fp_control_20260703.py`.

## Claim Ledger

| claim | status | audit finding |
| --- | --- | --- |
| `claim.oof_protocol` | SUPPORTED | Split inspection found fold1-4 validation cases cover all 176 fold0-train cases exactly once, with zero fold0-val overlap. The runner builds OOF cases only from folds `1..4` whose validation case IDs are in `splits[0]["train"]`. |
| `claim.no_fold0_gt_leakage` | SUPPORTED | The runner calls `select_threshold(oof_payloads)` before `load_payloads(eval_cases)`. Threshold selection uses OOF payload GT from fold0-training cases only. Fold0 validation GT is loaded after threshold freeze for evaluation. |
| threshold `1.30` selected from OOF evidence | SUPPORTED | `oof_threshold_grid.csv` contains 13 thresholds over 176 OOF cases; `1.30` has the highest objective (`0.562440`) and passes the Dice guardrail. |
| decision/evaluation feature separation | SUPPORTED | `component_feature_table.csv` has `decision_*` columns for score/action inputs and `evaluation_*` columns for GT annotations; no unprefixed GT/FP/distance columns were found in the current component feature table. |
| frozen fold0 actions | SUPPORTED | `component_action_table.csv` has 1025 rows: 819 train-side OOF component actions and 206 fold0-eval component actions, all with selected threshold `1.3`; fold0 actions are generated after threshold selection. |
| same-split baseline comparison | SUPPORTED | `metrics_summary.md`, `subgroup_metrics.csv`, and `component_hd_by_case.csv` compare `oof_scar_component_score` against unchanged `baseline_nnunet501_fold0` on the same 44 fold0 cases and compact label mapping. |
| fold0 metric claim | SUPPORTED_WITH_CAVEAT | Scar all-case component count improves `4.681818 -> 3.681818`, remote FP `0.363636 -> 0.272727`, small FP `2.545455 -> 1.659091`, and Dice changes only `-0.000053`; however HD worsens `25.970646 -> 26.086109` and HD95 worsens `13.600533 -> 13.991715`. This blocks promotion. |
| edema/no-T2 stability | SUPPORTED | Edema all-case, GT-positive, T2-present, CenterB/CenterC, LGE-only, and no-T2 empty-GT rows are unchanged from baseline. The scorer touches scar components only. |
| label/export QC | SUPPORTED | `label_export_qc.md` reports compact labels `0..5` for 44 baseline and 44 scorer predictions and explicitly states hosted validation/export evidence is not present. |
| command/provenance | SUPPORTED | `command_transcript.md` records command, exit status `0`, elapsed seconds, Python path, cwd, and no network/upload/fold expansion. |
| `claim.next_state` | SUPPORTED | Executor stopped at `EXECUTED_UNAUDITED` and did not write `review.md` or claim audited completion. |

## Evidence Coverage

Required artifacts are present: `result.md`, `MANIFEST.md`, `train_oof_protocol.md`, `component_feature_table.csv`, `component_action_table.csv`, `oof_training_summary.md`, `metrics_summary.md`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `label_export_qc.md`, `failure_interpretation.md`, and `command_transcript.md`. The package also includes `oof_threshold_grid.csv`, which is useful and directly supports threshold provenance.

Fold0 scorer predictions are present as 44 NIfTI files under `results/20260703_nnunet_oof_component/variants/oof_scar_component_score/predictions/fold_0/checkpoint_best/`. These are compact-label local evaluation artifacts only, not hosted validation or raw-label submission evidence.

OOF HD/HD95 were not part of the threshold grid; they are recorded as `NA` in `oof_training_summary.md`. This is not a blocker for the task-specific OOF threshold adequacy gate, but it is one reason the result should remain diagnostic-only.

## Gate Decisions

| gate | auditor decision | rationale |
| --- | --- | --- |
| `experiment_adequacy_decision` | PASS | The task-specific adequacy gate required OOF threshold selection without fold0 validation GT plus split provenance, features, actions, and baseline comparison. Those are present. This PASS is bounded to the postprocess/threshold protocol, not a broad model-training adequacy claim. |
| `route_promotion_decision` | NO_PROMOTION | Fold0 scar remote/small/component FP improvements are offset by worse all-case and GT-positive scar HD/HD95; hosted validation and raw-label export evidence are absent. |
| `route_negative_decision` | STOP_NOT_SUPPORTED | The run is not a failed route with adequate negative evidence; it produced useful diagnostic FP-control signal but no promotion. |
| `scientific_resolution_status` | SCIENTIFIC_UNRESOLVED | The scientific route is neither promoted nor stopped. Further direction requires GPT planner/controller judgment and a new authorized task. |

## Diagnostic Publication Decision

diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET

Reviewed diagnostic publication is supported for the minimal packet: `scripts/evaluation/run_nnunet_oof_component_20260703.py`, `results/20260703_nnunet_oof_component/result.md`, `MANIFEST.md`, `train_oof_protocol.md`, `oof_training_summary.md`, `oof_threshold_grid.csv`, `metrics_summary.md`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `component_feature_table.csv`, `component_action_table.csv`, `label_export_qc.md`, `failure_interpretation.md`, `command_transcript.md`, and this `review.md`.

Do not publish checkpoints, prediction NIfTI outputs, heavy logs, upload packages, hosted validation packages, full result trees, credentials, or environment dumps.

## Blocked Actions

- Validation packaging/upload remains blocked.
- Fold expansion remains blocked.
- Hosted metric claims remain blocked.
- Raw-label submission/export improvement claims remain blocked.
- Label/evaluator/fold split changes remain blocked.
- Next-stage training or learned-refinement execution remains blocked unless a new GPT-authored task explicitly authorizes it.
- Git commit/push are not authorized by the audited execution task (`allow_git_commit: false`, `allow_git_push: false`).

## Learned Anchor Refine Prerequisite

Reviewed prerequisite evidence exists for GPT planner consideration only: `results/20260703_myops_fp_control/review.md` accepted the earlier `scar_precision_component_score` as bounded fold0 FP/component evidence, and this audit confirms the follow-on OOF threshold provenance without fold0 GT leakage. That is sufficient prerequisite evidence for a planner to write a future learned-anchor/refinement task.

It is not sufficient to start learned anchor refine training, fold expansion, validation packaging, upload, or challenge-facing route promotion from this audit alone.

## Final Decision

audit_decision: AUDITED_DIAGNOSTIC_PUBLISH
experiment_adequacy_decision: PASS
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNRESOLVED
diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET
