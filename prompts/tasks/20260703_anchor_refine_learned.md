---
task_key: "20260703_anchor_refine_learned"
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
mechanism_class: "CARE model refinement"
target_metric: "myops_scar, myops_edema"
required_evidence: ["result.md", "review.md", "MANIFEST.md"]
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: Learned Anchor Refine

Use this task only after reviewed prerequisite evidence exists from the SRR repair and component scorer tasks. Produce a trained fold0 refinement artifact with audited metrics, or write `NEEDS_EVIDENCE`. Do not treat deterministic postprocessing as learned training.
