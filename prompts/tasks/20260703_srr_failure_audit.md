---
task_key: "20260703_srr_failure_audit"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "Codex controller session via prompts/tasks/20260703_srr_recovery_goal.md"
executor: "separate Codex executor session/subagent"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "audit / experiment adequacy / SRR-ProposeRefine failure diagnosis"
target_metric: "myops_scar, myops_edema"
same_split_baseline: "nnU-Net fold0 reference and 20260703 PropRef diagnostic packet; evidence not found if unavailable"
required_subgroups: ["all-case", "scar-positive", "edema GT-positive", "T2-present/complete", "no-T2 empty-GT stability", "CenterB", "CenterC", "LGE-only"]
required_secondary_metrics: ["train_loop_seconds", "optimizer_steps", "validation_events", "best_step", "loss_decrease", "foreground_rate", "proposal_recall", "proposal_precision", "Dice", "HD95"]
required_evidence: ["result.md", "review.md", "MANIFEST.md", "experiment_adequacy_report.md", "checkpoint_policy_audit.md", "decode_sanity_audit.md", "proposal_failure_audit.md", "required_revision_plan.md"]
forbidden_substitutes: ["accepting STOP_NO_PROPREF_SIGNAL without adequacy", "artifact presence as scientific evidence", "ignoring best_step=1", "ignoring missing post-warmup validation", "ignoring near-zero foreground/prediction sanity"]
experiment_adequacy_gate: "Classify prior PropRef as adequate only if optimizer steps, train time, validation cadence, loss decrease, checkpoint selection, foreground/decode, and proposal PR sanity are sufficient."
route_negative_gate: "A scientific stop is unsupported if failure can be explained by undertraining, checkpoint policy, decode, label/export, cache, or pipeline bug."
promotion_gate: "This audit does not promote routes. It determines whether prior STOP was supported or should become SCIENTIFIC_UNDERTRAINED / NEEDS_REVISION / STOP_PIPELINE_BUG."
failure_escalation_policy: "If adequacy evidence is insufficient, write SCIENTIFIC_UNDERTRAINED and route to 20260703_srr_propref_repair. If code/decode bug is found, write STOP_PIPELINE_BUG and route to repair."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: SRR-ProposeRefine Failure Adequacy Audit

## Goal

Audit the previous `20260703_myops_srr_propose_refine` diagnostic packet and decide whether `STOP_NO_PROPREF_SIGNAL` was scientifically supported. The expected outcome is likely `SCIENTIFIC_UNDERTRAINED` or `NEEDS_REVISION`, because the diagnostic packet reports `best_step=1`, `max_steps=120`, and very short train-loop times. This task must turn that suspicion into an evidence-indexed report.

This task does not train and does not change model behavior except for optional read-only audit helper scripts. It is the gate before any retry.

## Required reads

Read the controller/result/review packet and the code that produced it:

- `results/20260703_hardmode_goal/controller_report.md`
- `results/20260703_hardmode_goal/execution_plan.md`
- `results/20260703_myops_srr_propose_refine/result.md`
- `results/20260703_myops_srr_propose_refine/review.md`
- `results/20260703_myops_srr_propose_refine/metrics_summary.md`
- `results/20260703_myops_srr_propose_refine/proposal_metrics.csv`
- `results/20260703_myops_srr_propose_refine/subgroup_metrics.csv`
- `results/20260703_myops_srr_propose_refine/variant_matrix.csv`
- `results/20260703_myops_srr_propose_refine/variant_provenance.csv`
- `results/20260703_myops_srr_propose_refine/training_schedule.md`
- all available `results/20260703_myops_srr_propose_refine/variants/*/summary.json`
- all available `results/20260703_myops_srr_propose_refine/variants/*/training_log.csv`
- `src/care_myocardium/models/srr_propref.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `scripts/evaluation/aggregate_srr_propref_20260703.py`
- `jobs/src/run_srr_propref_myops_fold0.sh`

## Required audit questions

1. Was the previous run a scientifically adequate formal training run? Inspect `actual_steps`, `max_steps`, `best_step`, `train_loop_seconds`, validation events, and loss trend.
2. Did checkpoint selection export step 1 as `checkpoint_best` because `val_every` exceeded `max_steps`? If yes, mark route-negative conclusion unsupported.
3. Did the training logs include all three stages and low-LR calibration as actual logged training evidence? If not, mark partial.
4. Did proposal metrics fail because proposal maps flooded the volume, collapsed to background, or were evaluated only at a bad fixed threshold? Require PR/threshold sweep evidence for future tasks.
5. Did final full-volume argmax suppress pathology heads? Audit foreground rate, per-class volume, empty rate, compact label values, and pathology-aware decode availability.
6. Did logs/provenance prove training, or only Slurm completion? Distinguish Slurm elapsed from train-loop seconds.
7. Is the previous `STOP_NO_PROPREF_SIGNAL` supported, or should the scientific status be `SCIENTIFIC_UNDERTRAINED`, `SCIENTIFIC_PIPELINE_BUG`, `SCIENTIFIC_NEEDS_REVISION`, or `SCIENTIFIC_UNRESOLVED`?

## Required outputs

Write:

- `results/20260703_srr_failure_audit/result.md`
- `results/20260703_srr_failure_audit/MANIFEST.md`
- `results/20260703_srr_failure_audit/experiment_adequacy_report.md`
- `results/20260703_srr_failure_audit/checkpoint_policy_audit.md`
- `results/20260703_srr_failure_audit/decode_sanity_audit.md`
- `results/20260703_srr_failure_audit/proposal_failure_audit.md`
- `results/20260703_srr_failure_audit/required_revision_plan.md`

If an auditor is launched, write `results/20260703_srr_failure_audit/review.md`.

## Decision rules

- If adequacy evidence fails, do not repeat `STOP_NO_PROPREF_SIGNAL`; write `SCIENTIFIC_UNDERTRAINED` or `NEEDS_REVISION`.
- If code/decode/checkpoint policy is the likely explanation, write `STOP_PIPELINE_BUG` or `SCIENTIFIC_NEEDS_REVISION`.
- Only if the route was trained adequately and failed for model reasons may you support `SCIENTIFIC_STOP_SUPPORTED`.

普通 executor 必须停在 `EXECUTED_UNAUDITED`。
