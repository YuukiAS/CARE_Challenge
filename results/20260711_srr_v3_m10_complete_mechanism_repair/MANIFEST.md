# M10 Controller Packet Manifest

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Packet state: `NEEDS_MONITOR`

## Files

| Path | Purpose |
| --- | --- |
| `result.md` | Controller result and blocker summary. |
| `controller_context.json` | Machine-readable bootstrap context and read receipts. |
| `controller_ledger.csv` | Append-only controller phase ledger. |
| `controller_bootstrap_snapshot.md` | Human-readable hard-gate snapshot. |
| `controller_resume_bootstrap.md` | Historical resumed bootstrap after prerequisite repair. |
| `implementation_snapshot.md` | Confirms no implementation occurred. |
| `finalizer_state.json` | Deterministic terminal accounting for the blocked prerequisite packet. |
| `validator_report.md` | Validation command report. |
| `controller_report.md` | Controller decision report. |
| `completion_check.md` | Completion state and gate table. |
| `review_request.md` | Request for later separate read-only review of the blocked packet. |
| `prerequisite_repair.md` | Later integration-layer repair note for the prerequisite blocker; not runtime completion evidence. |
| `subagents/m10_shared_architecture_executor_prompt.md` | Wave 1 executor handoff prompt. |
| `subagents/m10_myops_training_executor_prompt.md` | Wave 2 executor handoff prompt. |
| `wave1_launch_receipt.json` | Controller receipt for serial wave 1 worker launch. |
| `wave1_merge_receipt.md` | Controller verification and merge/freeze decision for wave 1. |
| `wave2_launch_receipt.json` | Controller receipt for serial wave 2 worker launch. |
| `wave2_monitor_receipt.md` | Controller receipt for wave 2 monitor state and terminal failure update. |
| `wave2_terminal_failure_receipt.md` | Terminal Slurm accounting, log failure cause, dependency repair, and fail-closed aggregation receipt. |
| `wave2_startup_failed_jobs.csv` | Permanent zero-credit accounting for original startup-failed Wave 2 jobs. |
| `wave2_env_preflight.sh` | Slurm compute-node environment preflight wrapper for the authorized replacement attempt. |
| `wave2_replacement_preflight_receipt.md` | Replacement authorization, hashes, preflight command, and pending preflight job receipt. |
| `executors/m10_myops_training_executor/` | Wave 2 executor monitor packet; not completion evidence. |
| `subagents/reviewer_prompt.md` | Reviewer handoff prompt for this blocked packet only. |
| `mapper_report_draft.md` | Mapper draft non-run receipt. |
| `architecture_delta_draft.md` | Draft architecture delta after wave 1 merge. |
| `mapper_report_final.md` | Mapper final non-run receipt. |
| `architecture_delta_final.md` | Confirms no M10 architecture delta was applied. |
| `executor_waves/README.md` | Executor wave non-launch receipt. |

## Exclusions

`review.md` is intentionally absent. Wave 2 terminal failure files are not completion evidence. No checkpoints, predictions, NIfTI outputs, upload zips, raw data, large logs, secrets, environment dumps, or runtime result trees are included.
