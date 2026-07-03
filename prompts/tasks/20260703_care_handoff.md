---
task_key: "20260703_care_handoff"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "none"
executor: "Codex executor session"
auditor: "none"
risk_level: "low"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: false
mechanism_class: "documentation_handoff_overlay"
target_metric: "none"
required_evidence: ["modified handoff docs", "modified templates", "validation output"]
forbidden_substitutes: ["training", "submission upload", "cross-repo edits"]
promotion_gate: "Docs/templates updated only; no CARE model or submission promotion."
failure_escalation_policy: "If protocol conflicts require upstream changes, report recommendation and stop."
allowed_next_states: ["EXECUTED_UNAUDITED", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: true
allow_git_push: true
---

# Task: strengthen CARE handoff overlay

Update CARE-specific handoff rules and templates so they reference the Bridge Kit two-layer controller protocol and the medical-imaging skill without copying or conflicting with them. Do not run training, package submissions, upload, or modify other repositories.
