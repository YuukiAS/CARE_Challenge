---
task_key: "20260703_mainline_resume_goal"
project: "CARE_Challenge"
status: "READY"
task_type: "controller"
controller_mode: true
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
controller: "Codex controller session"
executor: "separate Codex executor sessions/subagents"
reviewer: "separate_readonly"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "controller / MyoPS primary formal training / Cine secondary resume"
target_metric: "myops_scar, myops_edema, myocardium_cinemyops diagnostic proxy"
same_split_baseline: "nnU-Net fold0 reference, SRR recovery diagnostics, and Cine diagnostic packet; evidence not found if unavailable"
required_evidence: ["executor_result", "reviewer_review", "controller_report", "experiment_adequacy_report", "job_status", "same_split_baseline", "cache_isolation", "label_export_QC"]
forbidden_substitutes: ["formal completion without MyoPS Slurm launch or adequate artifacts", "pending jobs marked complete", "CPU smoke as formal training", "Cine blocking MyoPS GPU", "route-negative stop without adequacy", "validation upload or fold expansion"]
route_promotion_gate: "MyoPS or Cine promotion requires adequacy and independent audit; Cine remains diagnostic unless hosted evidence exists."
route_negative_gate: "No STOP_NO_* conclusion unless experiment adequacy passes and reviewer supports route-negative decision."
experiment_adequacy_gate: "MyoPS formal training requires minimum effective training evidence; Cine diagnostic requires non-reference frame evidence."
scientific_completion_gate: "Controller operational completion is not scientific completion. Pending jobs must be reported as incomplete/needs-monitor."
diagnostic_publication_gate: "Reviewed diagnostic-only code and reports may be committed/pushed if no route is promoted and publication scope is respected."
diagnostic_publication_scope: ["controller_report.md", "execution_plan.md", "subtask result.md", "subtask review.md", "small reviewed Markdown decision packets", "reviewed first-party scripts"]
blocked_after_diagnostic_publication: ["validation packaging", "validation upload", "fold expansion", "hosted metric claims", "label/evaluator/fold split changes", "unauthorized next-stage training"]
executor_subtasks: ["prompts/tasks/20260703_srr_formal_training.md", "prompts/tasks/20260703_cine_temporal_resume.md"]
reviewer_prompt_path: "results/20260703_mainline_resume_goal/subagents/reviewer_prompt.md"
controller_report_path: "results/20260703_mainline_resume_goal/controller_report.md"
allowed_next_states: ["EXECUTION_PLANNED", "EXECUTOR_RUNNING", "EXECUTED_UNAUDITED", "REVIEWER_RUNNING", "AUDITED_GO", "NEEDS_MONITOR", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_SUBAGENT_LAUNCH", "NEEDS_HUMAN_APPROVAL", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: true
auto_git_push: true
allow_git_commit: true
allow_git_push: true
allow_diagnostic_commit: true
allow_diagnostic_push: true
---

# MyoPS + Cine Mainline Resume Goal

## Purpose

Resume the mainline carefully. MyoPS remains primary. The immediate unresolved item is adequate SRR-ProposeRefine formal fold0 training with the repaired runner. Cine may resume only as a secondary diagnostic route while MyoPS jobs are pending/running or after MyoPS formal artifacts exist.

This goal must not repeat the prior failure pattern: no short CPU smoke run, no step-1 checkpoint conclusion, no pending jobs marked complete, and no route-negative stop without experiment adequacy.

## Required reads

Controller and subtasks must read:

- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/EXPERIMENT_ADEQUACY_GATE.md`
- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `results/20260703_srr_recovery_goal/controller_report.md`
- `results/20260703_srr_propref_repair/review.md`
- `results/20260703_nnunet_oof_component/review.md`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `jobs/src/run_srr_propref_myops_fold0.sh`
- `results/20260703_cine_motion/result.md` and `review.md` if present

## Controller workflow

1. Launch `20260703_srr_formal_training` first. This is the primary task. It explicitly authorizes formal GPU training using the repaired SRR-ProposeRefine runner.
2. If MyoPS formal jobs are submitted and still pending/running, controller status is not complete. Write `NEEDS_MONITOR` or `EXECUTOR_RUNNING`, including job ids, output roots, and next monitor command.
3. Only after MyoPS launch is confirmed, or while MyoPS is waiting without consuming controller work, launch `20260703_cine_temporal_resume` if it does not consume MyoPS-critical GPU resources.
4. Do not launch learned anchor-refine from this controller. That requires a later GPT task after formal SRR or OOF evidence becomes promotable/useful.
5. Every executor must stop at `EXECUTED_UNAUDITED` after writing result artifacts, unless jobs are still running; then use `NEEDS_MONITOR` or `EXECUTOR_RUNNING`.
6. Every auditor must check artifact presence and experiment adequacy. Artifact presence alone cannot support a route-negative stop.
7. The controller report must include operational and scientific status fields required by `prompts/CONTROLLER_TASK_PROTOCOL.md`.

## Required controller outcome logic

- If MyoPS jobs are running/pending: `controller_run_status: INCOMPLETE`, `scientific_resolution_status: SCIENTIFIC_UNRESOLVED`, `next_required_action: monitor formal training jobs`.
- If MyoPS jobs finish and adequacy passes with signal: `route_promotion_decision` may be `PROMOTE` or `NO_PROMOTION` depending on audit.
- If MyoPS jobs finish but adequacy fails: use `SCIENTIFIC_UNDERTRAINED`, `SCIENTIFIC_PIPELINE_BUG`, `NEEDS_REVISION`, or `NEEDS_EVIDENCE`; do not use `STOP_NO_PROPREF_SIGNAL`.
- If Cine runs, it is diagnostic unless official/hosted evidence exists.

## Blocked actions

Validation packaging, validation upload, upload-ready package generation, fold expansion, hosted metric claims, label/evaluator/fold split changes, old SRR-v2 tuning routes, and learned anchor-refine training are blocked unless a later GPT-authored task explicitly authorizes them.
