# CARE Agent-Flow v3 Care Visual Smoke Results

Task request:

- `automation/agent_flow_v3/tasks/care-visual-smoke/CONTRACT.md`
- `automation/agent_flow_v3/tasks/care-visual-smoke/REQUEST.json`
- `automation/agent_flow_v3/tasks/care-visual-smoke/CURRENT.json`
- `automation/agent_flow_v3/tasks/care-visual-smoke/VISUAL_SOURCES.json`

Receipts:

- `visual_source_access_receipt.json`: Codex-side local and anonymous raw URL
  SHA check for CARE-ASE, SRR-v3, and MoSAIC.
- `ci_receipt.json`: local validator/test receipt plus GitHub Actions run and
  job success for the published `develop` commit.
- `production_watcher_receipt.json`: live `care_agent_flow_v3:Watcher` status
  proving the production watcher is running and polling the visual-smoke state.
- `scheduled_task_observation.json`: publication and waiting status for the real
  Scheduled Planner/Critic visual smoke.
- `visual_smoke_final.json`: remote observer output for the current
  `origin/develop` state; PASS only when both scheduled-GPT receipts are present,
  valid, and at least two scheduling windows have elapsed.

This directory must not contain Codex-authored substitutes for the required
Scheduled Planner/Critic visual receipts. The smoke passes only after real
scheduled GPT commits write the Planner and Critic receipts on `origin/develop`.
