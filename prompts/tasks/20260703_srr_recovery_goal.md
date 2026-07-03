---
task_key: "20260703_srr_recovery_goal"
project: "CARE_Challenge"
status: "READY"
task_type: "controller"
controller_mode: true
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "Codex controller session"
executor: "separate Codex executor sessions/subagents"
auditor: "separate read-only Codex auditor sessions or ChatGPT reviewer"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "controller / SRR-ProposeRefine recovery / experiment adequacy"
target_metric: "myops_scar, myops_edema"
same_split_baseline: "same-split nnU-Net fold0 reference plus 20260703 diagnostic packet; evidence not found if unavailable"
required_subgroups: ["all-case", "scar-positive", "edema GT-positive", "T2-present/complete", "no-T2 empty-GT stability", "CenterB", "CenterC", "LGE-only"]
required_secondary_metrics: ["Dice", "HD", "HD95", "component_count", "remote_FP", "small_FP", "volume_ratio", "proposal_recall", "proposal_precision", "foreground_rate", "loss_decrease", "optimizer_steps"]
required_evidence: ["executor_result", "auditor_review", "controller_report", "experiment_adequacy_report", "one_batch_overfit", "prediction_sanity", "checkpoint_policy", "metric_csv", "run_log", "same_split_baseline", "cache_isolation", "label_export_QC"]
forbidden_substitutes: ["STOP_NO_SIGNAL from undertrained run", "using step1 checkpoint as formal evidence when later training has no validation", "smoke/preflight/dryrun as route evidence", "full-volume argmax-only decode without pathology foreground sanity", "no-T2 myocardium as edema negative", "validation GT leakage", "validation upload or package generation"]
route_promotion_gate: "Only after experiment adequacy passes, same-split comparison exists, no leakage is found, and auditor supports promotion."
route_negative_gate: "STOP_NO_* is allowed only after experiment adequacy passes and failure cannot be explained by undertraining, checkpoint selection, decode, label/export, cache, or pipeline bug."
experiment_adequacy_gate: "Must pass one-batch/tiny-overfit, minimum optimizer-step/time evidence, post-warmup validation/checkpoint evidence, foreground/decode sanity, proposal PR sanity, and clean logs/provenance."
scientific_completion_gate: "Controller operational completion is not scientific completion. Scientific status must be promoted, stop-supported, undertrained, pipeline-bug, needs-evidence, needs-revision, or unresolved."
diagnostic_publication_gate: "Even without route promotion, reviewed diagnostic code and small reports may be committed/pushed as diagnostic-only if the controller records published files and blocked actions."
diagnostic_publication_scope: ["controller_report.md", "execution_plan.md", "subtask result.md", "subtask review.md", "small reviewed Markdown decision packets", "reviewed first-party source code/scripts required to reproduce the diagnostic conclusion"]
blocked_after_diagnostic_publication: ["validation packaging", "validation upload", "fold expansion", "hosted metric claims", "label/evaluator/fold split changes", "unauthorized next-stage training"]
executor_subtasks: ["prompts/tasks/20260703_srr_failure_audit.md", "prompts/tasks/20260703_srr_propref_repair.md", "prompts/tasks/20260703_nnunet_oof_component.md", "prompts/tasks/20260703_anchor_refine_learned.md"]
auditor_subtasks: ["results/20260703_srr_recovery_goal/subagents/auditor_prompt.md"]
controller_report_path: "results/20260703_srr_recovery_goal/controller_report.md"
allowed_next_states: ["EXECUTION_PLANNED", "EXECUTOR_RUNNING", "EXECUTED_UNAUDITED", "AUDITOR_RUNNING", "AUDITED_GO", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_SUBAGENT_LAUNCH", "NEEDS_HUMAN_APPROVAL", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: true
auto_git_push: true
allow_git_commit: true
allow_git_push: true
allow_diagnostic_commit: true
allow_diagnostic_push: true
---

# CARE SRR Recovery Goal Controller

## Why this goal exists

The previous hardmode goal ended operationally, but the SRR-ProposeRefine scientific conclusion is not acceptable. The diagnostic packet shows that the formal PropRef variants exported predictions and were audited, but training was not adequate for a scientific negative conclusion: summaries report `best_step=1`, `max_steps=120`, and train-loop seconds of only a few seconds for two variants. Under this recovery goal, such evidence must be classified as `SCIENTIFIC_UNDERTRAINED` or `NEEDS_REVISION`, not as route failure.

This controller does not invent a new research direction. It continues the GPT-approved SRR-ProposeRefine and nnU-Net-anchored refinement routes, but repairs the experiment adequacy, checkpoint/decode, and leakage issues exposed by the three-hour failed run.

## Required reads

The controller and all subtasks must read the handoff protocol, CARE overlay, medical-imaging skill, and the current diagnostic packet:

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/CHATGPT_RULES.md`
- `prompts/HANDOFF_ROLES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`
- `prompts/EXPERIMENT_ADEQUACY_GATE.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `prompts/tasks/20260703_hardmode_goal.md`
- `results/20260703_hardmode_goal/controller_report.md`
- `results/20260703_myops_srr_propose_refine/result.md`
- `results/20260703_myops_srr_propose_refine/review.md`
- `results/20260703_myops_srr_propose_refine/metrics_summary.md`
- `results/20260703_myops_srr_propose_refine/*/summary.json`
- `results/20260703_myops_srr_propose_refine/*/training_log.csv`
- `src/care_myocardium/models/srr_propref.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `scripts/evaluation/aggregate_srr_propref_20260703.py`
- `jobs/src/run_srr_propref_myops_fold0.sh`
- `results/20260703_myops_fp_control/review.md`
- `results/20260703_myops_anchor_refine/review.md`

## Controller workflow

1. Start with `20260703_srr_failure_audit`. It must classify the prior Phase 2B result using the new experiment adequacy standard. It should identify checkpoint, validation cadence, max-step, train-loop, proposal precision/recall, decode, and provenance failures.
2. Launch `20260703_srr_propref_repair` only after the failure audit returns an audited adequacy diagnosis. This task repairs the PropRef runner/model/aggregator and reruns an adequate fold0 test. It must not emit `STOP_NO_PROPREF_SIGNAL` unless experiment adequacy passes.
3. Launch `20260703_nnunet_oof_component` after the failure audit review, and in parallel with PropRef repair only if it does not block the primary SRR repair. Its job is to turn the bounded fixed-rule FP/component signal into train/OOF component-scoring evidence without leakage.
4. Launch `20260703_anchor_refine_learned` only if the OOF component scorer or PropRef repair produces usable inputs. If learned training/cache evidence is missing, this task must write `NEEDS_EVIDENCE`, not deterministic postprocess `STOP`.
5. Each executor writes `results/<task_key>/result.md` and `MANIFEST.md`, then stops at `EXECUTED_UNAUDITED`.
6. Each auditor writes `results/<task_key>/review.md`. Auditors must evaluate both artifact presence and experiment adequacy; artifact presence alone cannot support route-negative conclusions.
7. The controller writes `results/20260703_srr_recovery_goal/controller_report.md` with separate operational and scientific statuses.

## Experiment adequacy requirements

A training route can support promotion or scientific stop only if it passes all applicable checks:

- `one_batch_overfit` or `tiny_case_overfit` passes before formal training.
- actual optimizer steps, train-loop seconds, validation events, and loss decrease are recorded.
- checkpoints are not selected only from step 1 unless the route is explicitly a smoke run.
- at least one post-warmup checkpoint or final checkpoint is exported and compared.
- prediction foreground rate, per-class volume, empty rate, compact labels, and pathology-aware decode are reported.
- proposal metrics include recall, precision, lesion-wise recall, outside-myocardium FP ratio, and PR/threshold sweep, not just a fixed 0.5 threshold.
- no-T2 edema contract, label/export QC, same-split baseline, and cache isolation are reviewed.

If any required adequacy evidence is missing, use `SCIENTIFIC_UNDERTRAINED`, `SCIENTIFIC_PIPELINE_BUG`, `NEEDS_EVIDENCE`, or `NEEDS_REVISION`. Do not write `STOP_NO_SIGNAL`.

## Publication and git policy

This controller may commit/push audited diagnostic-only code and reports even if no route is promoted, provided the diagnostic publication gate passes. A diagnostic commit must explicitly state `diagnostic publication only; no route promotion`. Validation packaging, validation upload, fold expansion, hosted metric claims, and next-stage training remain blocked unless explicitly authorized by a later task.

## Expected final controller statuses

The final controller report must include:

```yaml
controller_run_status: COMPLETE | INCOMPLETE | BLOCKED
operational_completion_status: COMPLETE | INCOMPLETE
experiment_adequacy_decision: PASS | FAIL | PARTIAL | EVIDENCE_NOT_FOUND
route_promotion_decision: PROMOTE | NO_PROMOTION | NOT_EVALUABLE
route_negative_decision: STOP_SUPPORTED | STOP_NOT_SUPPORTED | NOT_EVALUABLE
scientific_resolution_status: SCIENTIFIC_PROMOTED | SCIENTIFIC_STOP_SUPPORTED | SCIENTIFIC_UNRESOLVED | SCIENTIFIC_UNDERTRAINED | SCIENTIFIC_PIPELINE_BUG | SCIENTIFIC_NEEDS_EVIDENCE | SCIENTIFIC_NEEDS_REVISION
diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET | DO_NOT_PUBLISH | NOT_APPLICABLE
git_commit_decision: COMMIT_ROUTE_PROMOTION | COMMIT_DIAGNOSTIC_ONLY | SKIP_COMMIT
git_push_decision: PUSH_ROUTE_PROMOTION | PUSH_DIAGNOSTIC_ONLY | SKIP_PUSH
published_files:
  - path
blocked_actions:
  - validation upload/fold expansion/next-stage training remain blocked
next_required_action: ...
reason_if_not_published: ...
reason_if_no_route_promotion: ...
```
