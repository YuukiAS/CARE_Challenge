# MANIFEST: 20260704_anchor_srr_v25_goal

task: `prompts/tasks/20260704_anchor_srr_v25_goal.md`
controller_report: `results/20260704_anchor_srr_v25_goal/controller_report.md`
audit_summary: `results/20260704_anchor_srr_v25_goal/audit_summary.md`

## Controller Artifacts

- `execution_plan.md` — controller phase plan, dependency gates, and active subagent registry.
- `controller_report.md` — final controller status report after formal aggregation and read-only audit.
- `audit_summary.md` — read-only auditor summary of current MyoPS/Cine gate decisions after Slurm array `57782211`.
- `MANIFEST.md` — index for controller artifacts.
- `subagents/` — prompt handoff files if automatic subagent launch becomes unavailable or prompts need archival.

## Status

controller_state: AUDITED_DIAGNOSTIC_PUBLISH
latest_update: Read-only audit refreshed for current formal MyoPS state. Adequacy PASS and nnU-Net anchor consumption PASS; no route promotion; current anchored packet route-negative stop supported versus same-split nnU-Net; validation packaging/upload blocked.
