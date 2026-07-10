# Review Request

Please run an independent read-only review of `20260711_agent_flow_v2_pre_m10_final_repair`.

Reviewer scope:

- Verify controller did not design or execute M10.
- Verify no model code, training, validation packaging, upload, historical M8/M9 result packet, checkpoint, NIfTI, prediction output, or secret was modified.
- Verify watcher/finalizer changes implement state-aware continuity and do not treat `NEEDS_MONITOR` or `AWAITING_SACCT_RETRY_EXHAUSTED` as success.
- Verify executor wave prepare/merge scripts and validator fail closed for overlap, duplicates, lane isolation, cycles, and merge conflicts.
- Verify M8/M9 history originals, manifest coverage, proposal migration, comparison, diagrams, and placeholder-token rejection.
- Verify GPT M10/system-level history-reading gates and prompt merge-position rules.
- Verify `scripts/architecture/reconcile_review_status.py` only copies controlled fields from committed `review.md`.
- Verify `controller_report.md` exists and contains the required ending fields.
- Verify controller packet completeness validation rejects missing required files.
- Verify history generator, validator, and reconciliation support future versions such as `M10` without hard-coded `M08/M09` choices.
- Verify `scripts/architecture/create_care_history_snapshot.py --milestone M10 --dry-run` works and does not overwrite existing history.
- Verify `AWAITING_SACCT_RETRY_EXHAUSTED` launches a real continuation watcher or resubmitted finalizer and records the session/job id.
- Verify multi-executor merge checks executor worktree/branch packets, parses completion tokens, rejects monitor/incomplete tokens, and records merge details.
- Verify watcher `log_path` receives stdout/stderr and duplicate session startup fails closed.

The reviewer must not modify code, run training, launch Slurm jobs, generate missing artifacts, or push.
