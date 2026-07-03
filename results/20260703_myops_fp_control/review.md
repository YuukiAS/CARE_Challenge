# Review 20260703 MyoPS FP Control

audit_decision: AUDITED_GO
role: read-only auditor
audited_task: `prompts/tasks/20260703_myops_fp_control.md`
audited_result: `results/20260703_myops_fp_control/result.md`
audited_manifest: `results/20260703_myops_fp_control/MANIFEST.md`
controller_task: `prompts/tasks/20260703_hardmode_goal.md`
prerequisite_audit: `results/20260703_myops_audit/review.md` reports `AUDITED_GO`

## Audit Summary

The executor produced the required FP-control artifact package and evaluated the three required fold0 fixed-rule routes against the same-split nnU-Net fold0 baseline. The package contains compact-label predictions for all 44 fold0 cases under variant-specific prediction directories, subgroup metrics, case-level HD/HD95/component/FP metrics, component action evidence, label/export QC, and a command transcript.

`scar_precision_component_score` deserves `AUDIT_FOR_PROMOTION` under this task's bounded promotion gate. The supported signal is local fold0 postprocessing evidence: scar all-case remote FP improves from `0.363636` to `0.250000`, component count improves from `4.681818` to `4.522727`, small FP improves from `2.545455` to `2.386364`, and mean HD improves from `25.970646` to `25.509096`, while scar Dice is effectively unchanged (`+0.000076`) and edema metrics are unchanged. This is not hosted validation evidence, not a raw-label submission/export improvement, and not authorization for validation packaging, upload, fold expansion, commit, or push.

Important caveat: scar all-case/GT-positive HD95 slightly worsens (`13.600533` to `13.630773`; delta improvement `-0.030239`). I do not treat that as an unacceptable regression for this narrow component/remote-FP promotion because the other pathology is unchanged and the task gate allowed secondary-metric improvement, but the route should remain framed as FP/component-control evidence rather than broad surface-quality improvement.

## Required Reads

- Repo/protocol: `AGENTS.md`, `prompts/AGENT_RULES.md`, `prompts/CHATGPT_RULES.md`, `prompts/HANDOFF_ROLES.md`, `prompts/HANDOFF_STATE_MACHINE.md`, `prompts/CONTROLLER_TASK_PROTOCOL.md`, `prompts/CARE_OVERLAY_GATES.md`.
- Skill: `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`, `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`.
- Task/gates: `prompts/tasks/20260703_myops_fp_control.md`, `results/20260703_myops_audit/review.md`, `results/20260703_myops_audit/next_route_gate.md`.
- Current package: `results/20260703_myops_fp_control/result.md`, `MANIFEST.md`, `postprocess_config.yaml`, `metrics_summary.md`, `subgroup_metrics.csv`, `baseline_vs_variant_metrics.csv`, `component_hd_by_case.csv`, `component_action_table.csv`, `label_export_qc.md`, `failure_interpretation.md`, `command_transcript.md`, `scripts/evaluation/run_myops_fp_control_20260703.py`.

## Claim Ledger

| claim | status | audit finding |
| --- | --- | --- |
| `claim.same_split_baseline` | SUPPORTED | The script uses `results/predictions/nnUNet501/fold_0` as baseline predictions; those entries are symlinks to the fold0 nnU-Net validation outputs. The script also reads fold0 probability caches and checkpoint paths from the corresponding `/overflow/.../fold_0` nnU-Net result tree. |
| `claim.fixed_variants` | SUPPORTED | `fixed_soft_anatomy_support`, `scar_precision_component_score`, and `edema_recall_safe_fp_control` are implemented and each has 44 exported compact-label prediction files under its own `results/20260703_myops_fp_control/variants/<variant>/predictions/fold_0/checkpoint_best/` directory. |
| `scar_precision_component_score` promotion signal | SUPPORTED | Same-split fold0 comparison supports lower scar remote FP, small FP, component count, and mean HD with negligible Dice increase and unchanged edema metrics. HD95 worsens slightly and must be caveated. |
| `fixed_soft_anatomy_support` decision | SUPPORTED | Metrics show tiny edema/secondary changes and scar Dice/HD95 regression; `DIAGNOSTIC_ONLY` is appropriate. |
| `edema_recall_safe_fp_control` decision | SUPPORTED | Metrics are identical to baseline for edema and scar; no-T2 empty-GT stability is preserved, but no improvement is shown. `DIAGNOSTIC_ONLY` is appropriate. |
| `claim.no_t2_contract` | SUPPORTED | `variant_edema_recall_safe` keeps baseline when `case.t2_present` is false; subgroup metrics show no-T2 empty-GT edema Dice `1.0`, empty rate `1.0`, component/remote/small FP `0.0` for baseline and all variants. No no-T2 myocardium-as-edema-negative route was found in the audited script. |
| CenterB/CenterC reporting | SUPPORTED | `subgroup_metrics.csv` and `metrics_summary.md` include CenterB and CenterC rows for both scar and edema. For the promoted scar route, CenterB scar is unchanged and CenterC scar improves on Dice, HD95, components, remote FP, and small FP. |
| component/remote-FP evidence | SUPPORTED | `component_hd_by_case.csv` has case-level component/FP/HD rows; `component_action_table.csv` has component-level keep/suppress/action rows. `baseline_vs_variant_metrics.csv` contains machine-readable deltas. |
| prediction/cache isolation | SUPPORTED | Variant predictions are isolated by variant/fold/checkpoint path. Baseline probability/checkpoint caches are read-only shared nnU-Net fold0 caches, explicitly recorded in `postprocess_config.yaml`; no variant-specific probability cache is expected for these fixed-rule postprocessors. |
| `claim.label_export_qc` | SUPPORTED | `label_export_qc.md` reports compact Dataset501 label values `0..5`, 44 predictions per variant, no invalid compact labels, and explicitly states hosted validation/export evidence is not present. |
| command/run evidence | SUPPORTED | `command_transcript.md` records script path, exit status `0`, elapsed time, Python path, cwd, and no network use. This is a minimal run transcript, but enough for this report-only fixed-rule evaluation. |
| forbidden upload/package/fold expansion absence | SUPPORTED | The script and artifacts are local fold0 evaluation outputs only. No validation upload, upload-ready package, fold expansion, external network action, commit, or push evidence was found. |
| threshold source not validation-tuned | PARTIAL | The thresholds are fixed constants in the committed task script at audit time. I found no independent pre-registration or edit-history evidence proving they were not adjusted after inspecting fold0 validation metrics. This is acceptable only because the result is framed as local fold0 `AUDIT_FOR_PROMOTION`, not challenge improvement. |
| `claim.train_oof_escalation` | SUPPORTED | Given the audited scar component/remote-FP signal, not running train/OOF component scoring is consistent with the task's fixed-rule phase. Follow-on train/OOF work would require a separate task. |
| `claim.next_state` | SUPPORTED | Executor stopped at `EXECUTED_UNAUDITED` and did not write this review or self-audit. |

## Forbidden Substitute Checks

| forbidden substitute | finding |
| --- | --- |
| val-tuned thresholds reported as challenge improvement | Not found. Threshold provenance is only partially supported, but the executor did not report hosted/challenge improvement. |
| hard deletion without full metrics | Not found. `scar_precision_component_score` suppresses components, but full subgroup, case-level, and component-action metrics are present. |
| compact-label-only gain as challenge improvement | Not found. Compact fold0 results are correctly caveated as not hosted validation evidence. |
| preflight-only completion | Not found. The executor generated predictions and metrics, not only preflight checks. |
| no-T2 samples as edema dense negatives | Not found in the audited fixed-rule script or metrics. |
| executor self-review | Not found. The executor stopped before audit. |
| validation upload/package/fold expansion | Not found. These remain unauthorized and absent. |

## Promotion Recommendation

| variant | audit classification | recommendation |
| --- | --- | --- |
| `scar_precision_component_score` | `AUDIT_FOR_PROMOTION` | Promote only as a bounded fold0 fixed-rule FP/component-control candidate for subsequent controller/planner handling. Do not describe as hosted challenge improvement. |
| `fixed_soft_anatomy_support` | `DIAGNOSTIC_ONLY` | Keep as diagnostic evidence only. |
| `edema_recall_safe_fp_control` | `DIAGNOSTIC_ONLY` | Keep as no-T2-safe baseline-preserving diagnostic only. |

## Remaining Caveats

- Hosted CARE validation metrics: `evidence not found`; upload/package generation was forbidden.
- Raw-label export/package QC: `evidence not found`; this task stayed in compact Dataset501 fold0 evaluation.
- Independent proof that thresholds were predeclared before any validation inspection: `evidence not found`.
- The promoted route's gain is small and primarily component/remote-FP oriented; HD95 is not improved on all-case/GT-positive scar.

## Final Decision

audit_decision: AUDITED_GO
promotion_recommendation: `scar_precision_component_score` -> `AUDIT_FOR_PROMOTION`
blocked_actions: validation packaging, validation upload, fold expansion, next-stage training, commit, and push remain unauthorized by this audit.
