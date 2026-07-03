# Manifest: 20260703 SRR Recovery Goal

task: `prompts/tasks/20260703_srr_recovery_goal.md`
controller_report: `results/20260703_srr_recovery_goal/controller_report.md`
execution_plan: `results/20260703_srr_recovery_goal/execution_plan.md`

## Controller Artifacts

- `execution_plan.md`: controller subagent sequence, session ids, completed
  gates, and blocked actions.
- `controller_report.md`: final controller status, audited decisions,
  diagnostic publication decision, and next required action.

## Subtask Artifacts

- `results/20260703_srr_failure_audit/result.md`
- `results/20260703_srr_failure_audit/review.md`
- `results/20260703_srr_propref_repair/result.md`
- `results/20260703_srr_propref_repair/review.md`
- `results/20260703_nnunet_oof_component/result.md`
- `results/20260703_nnunet_oof_component/review.md`
- `results/20260703_anchor_refine_learned/result.md`
- `results/20260703_anchor_refine_learned/review.md`

## Publication Boundary

Diagnostic publication only; no route promotion. The reviewed packet may include
small reports, compact diagnostic tables, and first-party reproducibility
scripts. It must not include checkpoints, predictions, NIfTI outputs, upload
packages, hosted validation packages, credentials, `.env` files, or full result
trees.
