---
task_key: "YYYYMMDD_short_slug"
project: "CARE_Challenge"
status: "READY"
task_type: "controller"
controller_mode: true
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "Codex controller session"
executor: "separate Codex executor session/subagent"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "segmentation | registration | cine_temporal | missing_modality | proposal_refinement | external_adapter | submission_packaging"
target_metric: "myops_scar | myops_edema | myocardium_cinemyops | explicitly caveated local proxy"
required_evidence: ["executor_result", "auditor_review", "controller_report", "promotion_gate_evidence"]
forbidden_substitutes: ["controller inventing a new route", "executor self-review", "audit bypass", "unauthorized fold expansion or upload"]
promotion_gate: "All executor claims audited; CARE overlay and skill gates satisfied; no human-approval block."
failure_escalation_policy: "Escalate inside this policy only; new scientific direction requires NEEDS_GPT_PLANNER."
executor_subtasks: ["results/<task_key>/subagents/executor_prompt.md"]
auditor_subtasks: ["results/<task_key>/subagents/auditor_prompt.md"]
controller_report_path: "results/<task_key>/controller_report.md"
allowed_next_states: ["EXECUTION_PLANNED", "EXECUTED_UNAUDITED", "AUDITOR_RUNNING", "AUDITED_GO", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_SUBAGENT_LAUNCH", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# CARE Controller Task: <short title>

## Goal
State the CARE objective, target metric, and authorized mechanism route. The controller may supervise execution only inside this GPT-authored scope.

## Workflow
1. GPT planner writes this controller task.
2. User starts a Codex controller session and gives it this task.
3. The controller creates or launches a separate executor session and a separate read-only auditor session.
4. Executor writes `result.md` and artifact paths.
5. Auditor reads task/result/MANIFEST/artifacts and writes read-only `review.md`.
6. Controller writes `results/<task_key>/controller_report.md` with subtask paths, session/log evidence, claim summary, audited decision, promotion decision, and git action status.
7. GPT strategic controller reads the controller report before choosing the next CARE direction.

## Subagent Fallback
If the Codex runtime cannot automatically launch subagents or new sessions, write `results/<task_key>/subagents/executor_prompt.md` and `results/<task_key>/subagents/auditor_prompt.md`, set state to `NEEDS_SUBAGENT_LAUNCH` or `NEEDS_HUMAN_APPROVAL`, and stop. Do not pretend executor/auditor separation happened.

## CARE Gate References
Use the Bridge Kit controller protocol for state and report structure. Use the medical-imaging skill for generic mechanism completion. Use `prompts/CARE_OVERLAY_GATES.md` for CARE leaderboard, label/export, T2-edema, Cine, controller, submission, and failure-escalation constraints.

## Git Policy
CARE controller commit/push is not the Bridge Kit default. Commit only if `allow_git_commit: true`, push only if `allow_git_push: true`, and only after audit and promotion gate approval. Record skipped git actions and reasons in the controller report.

## Escalation
If the result shows SRR, proposal, registration, Cine, missing-modality, or external-adapter work needs a new scientific direction, write `NEEDS_GPT_PLANNER` and stop.
