# Review 20260703 MyoPS Anchor Refine

audit_decision: AUDITED_GO
route_decision_recommendation: STOP_NO_CLEAN_ANCHOR_SIGNAL
promotion_recommendation: no promotion; all three formal variants remain `DIAGNOSTIC_ONLY` fixed deterministic postprocessing evidence, not a learned nnU-Net anchored refiner/cascade.
role: read-only re-auditor
audited_task: `prompts/tasks/20260703_myops_anchor_refine.md`
controller_task: `prompts/tasks/20260703_hardmode_goal.md`
audited_result: `results/20260703_myops_anchor_refine/result.md`
audited_manifest: `results/20260703_myops_anchor_refine/MANIFEST.md`

## Audit Summary

The revised package fixes the prior `NEEDS_REVISION` blocker. I found no current evidence that fold0 validation GT-derived `remote_fp` or `small_fp` fields enter prediction/action selection. In the revised code, formal variant functions receive `case`, `baseline`, `probs`, and `raw` only; GT is read in the driver for metrics and is passed to post-hoc annotation/evaluation functions after predictions are already written. `component_action_table.csv` now separates action inputs under `decision_*` from GT-derived post-hoc annotations under `evaluation_*`.

The evidence package is therefore accepted as a clean diagnostic fold0 package. It does not satisfy the originally requested learned pathology-refiner mechanism, because there was no training run, no learned checkpoint, and no train/OOF coarse cache evidence. The correct mechanism label remains `PARTIAL_MECHANISM_INCOMPLETE`.

The metric signal does not support promotion. Reported deltas are tiny or mixed: component-score is essentially unchanged, ROI has scar remote-FP reduction but HD95/edema regression, and dual-refiner has small Dice/component signals with scar remote-FP and HD95 regressions. This supports `STOP_NO_CLEAN_ANCHOR_SIGNAL` / no promotion rather than Phase 4 continuation.

## Required Reads

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`
- `prompts/tasks/20260703_myops_anchor_refine.md`
- `prompts/tasks/20260703_hardmode_goal.md`
- current package artifacts under `results/20260703_myops_anchor_refine/`
- `src/care_myocardium/postprocess/anchor_refine.py`
- `scripts/evaluation/run_myops_anchor_refine_20260703.py`

## Claim Ledger

| claim | status | audit finding |
| --- | --- | --- |
| required root outputs are present | SUPPORTED | `MANIFEST.md` indexes `result.md`, `variant_matrix.md`, `cache_contract.md`, `training_summary.md`, `metrics_summary.md`, required CSVs, `label_export_qc.md`, `failure_interpretation.md`, `command_transcript.md`, and per-variant artifacts. |
| three formal variants regenerated | SUPPORTED | Found 132 prediction files total, i.e. 44 predictions for each of the three variants, plus 3 configs, 3 logs, and 3 deterministic checkpoint records. |
| same-split nnU-Net fold0 baseline comparison | SUPPORTED | `cache_contract.md`, `metrics_summary.md`, and `teacher_student_delta.csv` compare against `baseline_nnunet501_fold0` from the local fold0 nnU-Net validation cache/checkpoint. |
| validation-GT leakage removed from prediction/action selection | SUPPORTED | Variant functions no longer take GT as an input. `component_filter` selectors use only component size, pathology probability, and anatomy support. GT-derived fields are added by `annotate_component_action_rows` after prediction decisions. |
| `component_action_table.csv` separates decision from evaluation fields | SUPPORTED | Header contains `decision_*` action features and separate `evaluation_*` GT annotations. No `remote_fp`/`small_fp` field without the `evaluation_` prefix is used as a decision feature. |
| all variants are diagnostic-only | SUPPORTED | `variant_matrix.md` marks `nnunet_component_score_refiner`, `myocardium_roi_pathology_refiner`, and `scar_precision_edema_recall_dual_refiner` as `DIAGNOSTIC_ONLY`; no current `AUDIT_FOR_PROMOTION` claim was found outside stale prior-review text replaced by this audit. |
| learned nnU-Net anchored refiner/cascade mechanism completed | UNSUPPORTED | `training_summary.md` reports `no_gpu_training_run`; checkpoint records are `deterministic_parameter_record` with `learned_weights: evidence not found`; train/OOF coarse cache evidence is missing. |
| mechanism evidence label | PARTIAL | The correct label is `PARTIAL_MECHANISM_INCOMPLETE`: fixed deterministic postprocessing with local fold0 metrics, not a trained pathology refiner. |
| metrics support route promotion | UNSUPPORTED | Deltas are too small or mixed, with no clean primary-metric improvement and no learned/OOF evidence. |
| label/export QC | PARTIAL | Compact labels `0..5` are documented with 0 invalid-label rows and 44 predictions per formal variant. Raw-label validation export/package and hosted metrics remain `evidence not found`, correctly caveated. |
| T2/no-T2 edema contract | SUPPORTED | Edema additions are gated by `case.t2_present`; no-T2 empty-GT edema stability remains perfect in reported metrics; no no-T2 dense-negative training was run. |
| no SRR continuation | SUPPORTED | Current script/configs report `uses_srr_or_propref_inputs: false`, and no SRR/PropRef input consumption was found in the revised code path. |
| no alignment dependency | SUPPORTED | Current script/configs report `uses_alignment_inputs: false`, and no alignment output consumption was found. |
| no forbidden operational action | SUPPORTED | No validation zip/package/upload artifact, fold expansion, evaluator/label mapping change, continuation training, commit, or push evidence was found in this package. |

## Variant Findings

| variant | decision | audit finding |
| --- | --- | --- |
| `nnunet_component_score_refiner` | `DIAGNOSTIC_ONLY` | Cleaned of GT-driven action selection, but only negligible scar Dice change and no learned evidence; not promotable. |
| `myocardium_roi_pathology_refiner` | `DIAGNOSTIC_ONLY` | Scar remote-FP signal is offset by scar HD95 and edema Dice/component regressions; not promotable. |
| `scar_precision_edema_recall_dual_refiner` | `DIAGNOSTIC_ONLY` | Small Dice/component improvements are mixed with scar remote-FP and HD95 regressions; not promotable. |

## Forbidden Action Check

No evidence was found for validation packaging/upload, upload-ready zip creation, fold expansion beyond fold0, evaluator or label mapping changes, SRR continuation, alignment dependency, next-stage training, commit, or push. The package remains local fold0 compact-label diagnostic evaluation only.

## Authorization Boundary

This re-audit accepts the revised evidence package and no-promotion decision only. It does not authorize Phase 4, validation packaging, validation upload, fold expansion, next-stage training, route promotion, commit, or push. Any new learned-refiner or train/OOF cache work requires a separate authorized execution/controller decision.
