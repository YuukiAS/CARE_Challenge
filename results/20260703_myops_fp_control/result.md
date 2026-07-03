# Result 20260703 MyoPS FP Control

self_assessed_status: EXECUTED_UNAUDITED
role: executor
review_required: true

## Execution Summary

Executed nnU-Net-anchored fixed-rule/component-scoring postprocessing on fold0 validation cases only. No validation upload, upload-ready package, fold expansion, label mapping edit, fold split edit, evaluator edit, network access, commit, push, or SRR-v2 temperature/gate/mix-weight/threshold tuning was performed.

claim.same_split_baseline: unchanged `baseline_nnunet501_fold0` predictions from `results/predictions/nnUNet501/fold_0` were used as the same-split baseline.
claim.fixed_variants: evaluated `fixed_soft_anatomy_support`, `scar_precision_component_score`, and `edema_recall_safe_fp_control`.
claim.no_t2_contract: `edema_recall_safe_fp_control` preserves baseline predictions for no-T2 cases and does not use no-T2 myocardium as edema dense negatives.
claim.label_export_qc: all exported task predictions use compact labels `0..5`; hosted validation/export evidence remains `evidence not found`.
claim.train_oof_escalation: not executed because at least one fixed-rule route produced audit-worthy same-split signal.
claim.next_state: executor stops at `EXECUTED_UNAUDITED` pending separate read-only audit.

## Variant Decisions

- `fixed_soft_anatomy_support`: `DIAGNOSTIC_ONLY` (positive secondary metric exists but gate is weak or Dice regression requires review)
- `scar_precision_component_score`: `AUDIT_FOR_PROMOTION` (scar secondary FP/surface signal without material Dice regression)
- `edema_recall_safe_fp_control`: `DIAGNOSTIC_ONLY` (edema route preserved baseline/no-T2 stability but produced no same-split improvement)

## Files Read

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/HANDOFF_ROLES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `.agents/skills/agent-task-executor/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`
- `prompts/tasks/20260703_myops_fp_control.md`
- `results/20260629_rescue_goal/final_status.md`
- `results/20260703_myops_audit/result.md`
- `results/20260703_myops_audit/review.md`
- `results/20260703_myops_audit/next_route_gate.md`
- `results/20260703_myops_audit/label_export_qc.md`
- `results/20260703_myops_audit/route_evidence_index.csv`
- `results/20260703_myops_audit/cache_isolation_table.csv`
- `data/benchmarks/protocol/splits_MyoPS.json`
- `results/diagnostics/care_myocardium/laneA_myops/myops_modality_center_case_metrics.csv`
- nnU-Net fold0 predictions and probability caches under `results/predictions/nnUNet501/fold_0` and read-only `/overflow/htzhu/CARE/.../fold_0/validation`

## Files Changed

- `scripts/evaluation/run_myops_fp_control_20260703.py`
- `results/20260703_myops_fp_control/`

## Commands

- `scripts/evaluation/run_myops_fp_control_20260703.py` -> exit 0; elapsed_seconds `52.00`

## Tests / Verification

- Generated prediction directories for all three required variants.
- Generated required task artifacts and compact-label QC.
- Python syntax check for the task script passed before execution.
- No network, upload, package generation, fold expansion, or git commit/push was run.

## Artifacts

- `results/20260703_myops_fp_control/result.md`
- `results/20260703_myops_fp_control/MANIFEST.md`
- `results/20260703_myops_fp_control/postprocess_config.yaml`
- `results/20260703_myops_fp_control/metrics_summary.md`
- `results/20260703_myops_fp_control/subgroup_metrics.csv`
- `results/20260703_myops_fp_control/component_hd_by_case.csv`
- `results/20260703_myops_fp_control/component_action_table.csv`
- `results/20260703_myops_fp_control/label_export_qc.md`
- `results/20260703_myops_fp_control/failure_interpretation.md`

## Failures And Incomplete Items

- `results/20260703_myops_fp_control/review.md` was not written because this session is executor-only.
- Hosted validation metrics and upload-ready raw-label packages are `evidence not found` because they are forbidden by task scope.
- Train/OOF component scoring was not promoted by this executor; see `failure_interpretation.md`.

## Required Next State

EXECUTED_UNAUDITED
