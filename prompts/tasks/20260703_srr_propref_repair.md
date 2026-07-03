---
task_key: "20260703_srr_propref_repair"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "Codex controller session via prompts/tasks/20260703_srr_recovery_goal.md"
executor: "separate Codex executor session/subagent"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "proposal_refinement / SRR evidence engine / experiment adequacy repair"
target_metric: "myops_scar, myops_edema"
same_split_baseline: "same-split nnU-Net fold0 reference plus 20260703_srr_failure_audit; evidence not found if unavailable"
required_subgroups: ["all-case", "scar-positive", "edema GT-positive", "T2-present/complete", "no-T2 empty-GT stability", "CenterB", "CenterC", "LGE-only"]
required_secondary_metrics: ["Dice", "HD", "HD95", "component_count", "remote_FP", "small_FP", "volume_ratio", "proposal_recall", "proposal_precision", "foreground_rate", "loss_decrease", "optimizer_steps"]
required_evidence: ["result.md", "review.md", "MANIFEST.md", "experiment_adequacy_report.md", "one_batch_overfit", "checkpoint_policy", "prediction_sanity", "proposal_pr_sweep", "metric_csv", "run_log", "same_split_baseline", "cache_isolation", "label_export_QC"]
forbidden_substitutes: ["max_steps=120 formal stop", "best_step=1 checkpoint exported as formal conclusion", "formal STOP without one-batch overfit", "formal STOP without foreground/decode sanity", "dictionary-only/tuning-only route", "validation upload or fold expansion"]
minimum_effective_training: {min_optimizer_steps: 1500, min_train_loop_seconds: 1800, require_one_batch_overfit: true, require_prediction_sanity: true, require_loss_decrease: true, require_post_warmup_validation: true, allow_stop_without_training: false}
experiment_adequacy_gate: "Formal route conclusions require min optimizer steps/time, overfit sanity, post-warmup validation, non-step1 checkpoint comparison, foreground/decode sanity, proposal PR sanity, and clean provenance."
route_negative_gate: "STOP_NO_PROPREF_SIGNAL is allowed only if adequacy passes and metrics remain poor after pipeline bugs are excluded."
promotion_gate: "Promotion requires same-split improvement over nnU-Net or critical secondary metrics with no unacceptable regression, plus auditor approval."
failure_escalation_policy: "Repair pipeline bugs and rerun adequate variants. If adequacy cannot be achieved due resources, write NEEDS_EVIDENCE or SCIENTIFIC_UNDERTRAINED; do not write STOP_NO_PROPREF_SIGNAL."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: SRR-ProposeRefine Repair And Adequate Retry

## Goal

Repair the SRR-ProposeRefine implementation and runner exposed by the diagnostic packet, then rerun a scientifically adequate fold0 experiment. This continues the previous SRR-ProposeRefine hypothesis; it does not authorize a new research route.

The prior diagnostic packet is not an adequate negative result if it used `max_steps=120`, selected `checkpoint_best` at `best_step=1`, had no post-warmup validation, or exported predictions from an early checkpoint. In that case, use `SCIENTIFIC_UNDERTRAINED`, `STOP_PIPELINE_BUG`, `NEEDS_EVIDENCE`, or `NEEDS_REVISION`, not `STOP_NO_PROPREF_SIGNAL`.

## Required prerequisites

Read `prompts/EXPERIMENT_ADEQUACY_GATE.md`, `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`, `prompts/CONTROLLER_TASK_PROTOCOL.md`, and `results/20260703_srr_failure_audit/review.md` if present. If the failure audit is missing, write `NEEDS_EVIDENCE` unless the controller provides equivalent reviewed evidence.

## Required repairs

1. Checkpoint policy: do not export only step-1 `checkpoint_best` for a formal conclusion. Force validation after warmup, after proposal learning, after refinement, and near the end. Export and compare final checkpoint when later validation is absent.
2. Training adequacy: record `actual_optimizer_steps`, `train_loop_seconds`, process wall time, validation events, stage step counts, first/last loss, and loss decrease in `summary.json`.
3. Overfit sanity: implement and run one-batch or one-case overfit before formal retry. If it fails, stop with a pipeline/adequacy status.
4. Decode sanity: compare full-volume argmax with a pathology-aware binary decode/conflict resolver. Report foreground rate, class volumes, empty rate, compact labels, and no-T2 stability.
5. Proposal calibration: add threshold/PR sweep for scar and edema proposals; include lesion-wise recall and outside-myocardium FP ratio.
6. Prototype/memory sanity: verify proposal prototype parameters receive gradients and update. If possible, warm-start proposal prototypes from train lesion features and reviewed FP component features.
7. Provenance: ensure logs or a reliable transcript record command, job id, array id, config, checkpoint, predictions, and metrics.

## Formal retry plan

After repairs and sanity checks, run the three existing variants unless adequacy fails first:

- `srr_propref_shared_dual_dict`
- `srr_propref_scar_precision`
- `srr_propref_no_proto_cascade`

Outputs should be isolated under `results/20260703_srr_propref_repair/variants/<variant>/` unless the controller explicitly accepts another root. Preferred partition is `htzhulab`; each job must stay within 8 hours. If capacity is limited, run one adequate primary variant first and mark remaining variants `NEEDS_EVIDENCE` rather than faking completion.

## Required outputs

Write `result.md`, `MANIFEST.md`, `experiment_adequacy_report.md`, `one_batch_overfit.md`, `checkpoint_policy.md`, `prediction_sanity.md`, `proposal_pr_sweep.csv`, `metrics_summary.md`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `roi_coverage.csv`, `label_export_qc.md`, `failure_interpretation.md`, and `command_transcript.md` under `results/20260703_srr_propref_repair/`. Include updated reviewed code/scripts if needed.

`result.md` must include `experiment_adequacy_decision`, `route_promotion_decision`, `route_negative_decision`, and `scientific_resolution_status`, even though this is an execution subtask.

## Decision rules

Allowed route decisions are `AUDIT_FOR_PROMOTION`, `DIAGNOSTIC_ONLY`, `SCIENTIFIC_UNDERTRAINED`, `STOP_PIPELINE_BUG`, `NEEDS_EVIDENCE`, `NEEDS_REVISION`, and `STOP_NO_PROPREF_SIGNAL`. The last one is allowed only after experiment adequacy passes.

普通 executor 必须停在 `EXECUTED_UNAUDITED` and await review.
