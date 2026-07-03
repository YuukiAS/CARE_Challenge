# Re-Review 20260703 MyoPS SRR ProposeRefine

audit_decision: AUDITED_GO
route_decision_recommendation: STOP_NO_PROPREF_SIGNAL
role: read-only re-auditor
audited_task: `prompts/tasks/20260703_myops_srr_propose_refine.md`
audited_result: `results/20260703_myops_srr_propose_refine/result.md`
audited_manifest: `results/20260703_myops_srr_propose_refine/MANIFEST.md`
controller_task: `prompts/tasks/20260703_hardmode_goal.md`
evidence_supplement_prompt: `results/20260703_hardmode_goal/subagents/myops_srr_propose_refine_evidence_revision_executor_prompt.md`

## Audit History

- Prior audit decision: `NEEDS_EVIDENCE`.
- Prior missing-evidence items: zero-byte per-variant logs without a final transcript, Slurm job/config ID mismatch for shared/scar variants, and low-LR calibration wording that implied logged evidence not present in `training_log.csv`.
- Current re-audit decision: `AUDITED_GO` for accepting the revised Phase 2B evidence package and its stop recommendation. This is not route promotion and does not authorize fold expansion, validation packaging/upload, next-stage training, commit, or push.

## Re-Audit Summary

The evidence supplement resolves the prior provenance blockers sufficiently for audit. `provenance_reconciliation.md`, `variant_provenance.csv`, `command_transcript.md`, and the updated `result.md` now explicitly caveat the zero-byte tee logs as `evidence not found`, provide a final transcript from `sacct` plus configs/checkpoints/prediction counts/metric paths, reconcile the shell-side `SLURM_JOB_ID` values against canonical array IDs `57617442_0..2`, and correct the low-LR claim to "implemented in code but not logged" for the formal `max_steps=120` runs.

The route conclusion remains supported: all three formal PropRef variants have fold0 checkpoints, 44 compact-label predictions, metric CSVs, and subgroup/component/proposal evidence, but final scar/edema metrics remain far below the same-split nnU-Net references. The correct route recommendation is `STOP_NO_PROPREF_SIGNAL`, not `AUDIT_FOR_PROMOTION`.

## Required Reads

- Repo/protocol: `AGENTS.md`, `prompts/AGENT_RULES.md`, `prompts/CHATGPT_RULES.md`, `prompts/HANDOFF_ROLES.md`, `prompts/HANDOFF_STATE_MACHINE.md`, `prompts/CONTROLLER_TASK_PROTOCOL.md`, `prompts/CARE_OVERLAY_GATES.md`.
- Skill: `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`, `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`.
- Task/gates: `prompts/tasks/20260703_myops_srr_propose_refine.md`, `prompts/tasks/20260703_hardmode_goal.md`, `results/20260703_myops_audit/review.md`, `results/20260703_myops_fp_control/review.md`.
- Evidence prompt: `results/20260703_hardmode_goal/subagents/myops_srr_propose_refine_evidence_revision_executor_prompt.md`.
- Current package: `result.md`, `MANIFEST.md`, prior `review.md`, `architecture_contract.md`, `variant_matrix.md`, `variant_matrix.csv`, `training_schedule.md`, `metrics_summary.md`, `proposal_metrics.csv`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `hardneg_memory.csv`, `roi_coverage.csv`, `label_export_qc.md`, `failure_interpretation.md`, `command_transcript.md`, `slurm_status.csv`, `provenance_reconciliation.md`, `variant_provenance.csv`, per-variant `run_config.env`, summaries, logs, checkpoints, predictions, and metrics.
- Code spot-checks: `src/care_myocardium/models/srr_propref.py`, `scripts/training/run_srr_propref_myops_fold0.py`, `scripts/evaluation/aggregate_srr_propref_20260703.py`, `jobs/src/run_srr_propref_myops_fold0.sh`.

## Claim Ledger

| claim | status | audit finding |
| --- | --- | --- |
| prerequisite gates | SUPPORTED | `results/20260703_myops_audit/review.md` and `results/20260703_myops_fp_control/review.md` both report `AUDITED_GO`. |
| `claim.architecture_contract` | SUPPORTED | `SRRProposeRefineMyoPS` contains SRR evidence features, pathology proposal dictionaries, typed negative prototype memory, and `SoftROIRefinementHead`; final scar/edema logits consume features, evidence logits, proposal logits, and soft ROI masks. |
| proposal/refinement is not old SRR-v2 tuning | SUPPORTED | The audited route is not another temperature/gate/mix-weight ladder; formal variants implement proposal dictionaries or no-prototype control feeding soft ROI refinement. |
| formal variants completed with predictions/checkpoints/configs/metrics | SUPPORTED | Each required variant has `checkpoint_best.pt`, `summary.json`, `run_config.env`, per-variant metric CSVs, and 44 prediction files indexed by `variant_matrix.*` and `variant_provenance.csv`. |
| zero-byte log handling | SUPPORTED | The three configured tee logs are 0 bytes, and the revised package explicitly marks per-variant stdout/stderr as `evidence not found` instead of inferring log content. |
| final provenance transcript | SUPPORTED | `command_transcript.md` records the array launch command, `sacct` command/output/exit status, per-task variant mapping, config parameters, and the evidence basis used when stdout/stderr could not be recovered. |
| Slurm ID reconciliation | SUPPORTED | `provenance_reconciliation.md` and `variant_provenance.csv` explain that `run_config.env` captured shell-side `SLURM_JOB_ID` values `57617443`, `57617444`, and `57617442`, while canonical array-element identities are `57617442_0`, `57617442_1`, and `57617442_2`; `sacct` shows all completed with exit `0:0`. |
| `claim.three_stage_schedule` | SUPPORTED | Current `result.md` and `training_schedule.md` correctly state that `low_lr_calibration` is implemented in code but no formal `training_log.csv` emitted a low-LR row under `max_steps=120`. |
| aggregate script rerun preserves corrected low-LR wording | PARTIAL | Current report artifacts are corrected, but `scripts/evaluation/aggregate_srr_propref_20260703.py` still contains an older generated-result sentence that would claim low-LR calibration is recorded if rerun. This is a reproducibility caveat, not a blocker for accepting the current package. |
| negative prototype memory and safe replay | SUPPORTED | `hardneg_memory.csv` records replay-safe components and states no-T2 myocardium/scar unsafe edema entries remain excluded by the `replay_safe` filter. |
| no-T2 edema contract | SUPPORTED | Training code masks dense edema/proposal losses to T2-present samples; no-T2 edema negative handling is limited to background-safe terms, and the package reports no-T2 empty-GT stability slices. |
| same-split nnU-Net comparison | SUPPORTED | `metrics_summary.md` reports nnU-Net fold0 scar all-case Dice `0.5602` and edema GT-positive Dice `0.3944`, then compares every PropRef variant against those references. |
| proposal metrics support stop signal | SUPPORTED | Scar proposal precision is near zero for all variants, edema proposal precision is near zero, and final edema/scar Dice remains noncompetitive despite proposal evidence. |
| final metrics support `STOP_NO_PROPREF_SIGNAL` | SUPPORTED | Scar all-case Dice is `0.0007`, `0.0011`, and `0.0038`; edema GT-positive Dice is `0.0070`, `0.0069`, and `0.0066`, far below the same-split nnU-Net references. |
| label/export QC | SUPPORTED | `label_export_qc.md` reports 44 compact-label predictions per variant with compact labels `0..5` only and raw-label validation package evidence not found. |
| forbidden upload/package/fold expansion absence | SUPPORTED | The audited artifacts are local fold0 compact-label evaluation outputs. I found no evidence of validation upload, upload-ready packaging, fold expansion, label mapping edit, split edit, evaluator edit, network use, commit, or push in this package. |
| executor self-review absence | SUPPORTED | The executor stopped at `EXECUTED_UNAUDITED`; this file is the separate read-only re-audit. |

## Forbidden Substitute Checks

| forbidden substitute | finding |
| --- | --- |
| dictionary-only variant as final mechanism | Not found. Proposal outputs feed soft ROI refinement heads before final logits. |
| temperature/gate/mix-weight tuning as mechanism | Not found as a new route. |
| full-image dense head as final route | Partially avoided mechanistically: outputs are full-volume logits, but final pathology logits are soft-ROI residual-refined rather than a plain dense head. Metrics show the mechanism failed. |
| compactness-only fix or hard ROI deletion | Not found. The ROI is soft and differentiable. |
| preflight-only completion | Not found. Formal predictions and metrics exist for all three variants. |
| no-T2 myocardium as edema dense negative | Not found in the audited PropRef training code or hard-negative memory table. |
| compact-label proxy as hosted challenge improvement | Not found. Hosted validation and raw-label package evidence remain explicitly absent. |
| validation upload/package/fold expansion | Not found and remains unauthorized. |
| executor self-review | Not found. |

## Remaining Caveats

- Per-variant stdout/stderr remains unrecoverable: `evidence not found`. The replacement provenance transcript is sufficient for this re-audit, but the original logs are still absent.
- Hosted validation metrics and upload-ready raw-label package evidence remain `evidence not found`, as required by task scope.
- `scripts/evaluation/aggregate_srr_propref_20260703.py` should not be rerun as-is to regenerate `result.md` without preserving the corrected low-LR wording; current checked artifacts are corrected.

## Contradicted Or Unsupported Claims

No current package claim is `UNSUPPORTED` or `CONTRADICTED`.

One claim is `PARTIAL`: rerun reproducibility of the corrected low-LR wording in `aggregate_srr_propref_20260703.py`. This does not change the audit decision because current `result.md`, `training_schedule.md`, `provenance_reconciliation.md`, and `command_transcript.md` are corrected and auditable.

## Route Decision

Recommended route decision: `STOP_NO_PROPREF_SIGNAL`.

The Phase 2B evidence package is now audit-clean enough to accept the stop conclusion. Do not promote this route, expand folds, package validation, upload, launch next-stage PropRef training, commit, or push from this result.
