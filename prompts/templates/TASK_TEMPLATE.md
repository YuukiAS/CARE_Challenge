---
task_key: "YYYYMMDD_short_slug"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "none"
executor: "Codex executor session"
auditor: "separate Codex auditor session or ChatGPT reviewer"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "segmentation | registration | cine_temporal | missing_modality | proposal_refinement | external_adapter | submission_packaging"
target_metric: "myops_scar | myops_edema | myocardium_cinemyops | explicitly caveated local proxy"
same_split_baseline: "path or description; evidence not found if unavailable"
required_subgroups: ["all-case", "T2-present/complete", "GT-positive", "no-T2 empty-GT stability", "CenterB/CenterC if relevant"]
required_secondary_metrics: ["HD95", "component_count", "remote_FP", "volume_ratio"]
required_evidence: ["checkpoint", "prediction_path", "metric_csv", "run_log", "same_split_baseline", "cache_isolation", "label_export_QC"]
forbidden_substitutes: ["preflight-only completion", "compact-label proxy as challenge improvement", "no-T2 as edema negative", "frame0-only as temporal completion"]
promotion_gate: "CARE overlay plus medical-imaging skill gate satisfied; read-only review supports claims."
failure_escalation_policy: "Use prompts/CARE_OVERLAY_GATES.md; if new route is needed, return NEEDS_GPT_PLANNER."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: <short title>

## Goal
State the CARE objective in challenge terms. Name the primary target metric (`myops_scar`, `myops_edema`, or `myocardium_cinemyops`) or clearly mark a local proxy.

## Protocol And Gate References
Use the Bridge Kit state machine for task/result/review flow. Use `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md` for generic medical-imaging mechanism completion. Use `prompts/CARE_OVERLAY_GATES.md` for CARE-specific leaderboard, label, T2-edema, Cine, controller, submission, and failure-escalation constraints. Do not paste the full skill into this task.

## Authorized Scope
List the files, scripts, data splits, cached artifacts, and commands the executor may touch. State what is explicitly out of scope.

## Mechanism Class And Completion Definition
Name the mechanism class and the concrete evidence needed to satisfy the skill gate and CARE overlay. Include the same-split baseline and expected subgroup/secondary metrics.

## Forbidden Substitutes
List routes that cannot count as completion, such as smoke-only runs, compact-label sanity gains, frame0-only Cine proxies, or no-T2 edema negatives.

## Evidence Requirements
List required paths and tables for checkpoint, prediction, metric CSV, logs, cache isolation, label/export QC, and subgroup metrics. Missing evidence must be written as `evidence not found` or `未找到证据`.

## Review Requirement
Set `review_required: true` for medium/high-risk CARE work. The executor must stop at `EXECUTED_UNAUDITED`; only a separate auditor or GPT reviewer can support promotion.

## Failure Escalation Policy
Define the bounded next action if the route fails. If the next step requires a new scientific direction, the executor must write `NEEDS_GPT_PLANNER` and stop.

## Git Policy
Use `allow_git_commit` and `allow_git_push` for CARE local authorization. Do not commit or push unless the task explicitly allows it and the audit/promotion gate is satisfied.
