# Implementation Snapshot

Implemented changes:

- `scripts/ops/start_care_tmux_watcher.py`: state-aware watcher, iteration ledger, final receipt, foreground test mode.
- `scripts/ops/care_milestone_finalizer.py`: retryable accounting exhaustion fields and 60-minute default accounting retry.
- `scripts/ops/submit_care_dependency_finalizer.py`: aligned default accounting retry.
- `scripts/ops/prepare_care_executor_wave.py`: executor wave preparation, worktree/namespace setup, launch receipt, explicit `NEEDS_SUBAGENT_LAUNCH` when Codex subagent launch is unavailable.
- `scripts/ops/merge_care_executor_wave.py`: ordered executor branch merge with clean-branch checks and conflict fail-closed state.
- `scripts/ops/validate_executor_plan.py`: strict path overlap, lane, uniqueness, dependency cycle, and MyoPS/Cine isolation validation.
- `scripts/architecture/reconcile_review_status.py`: deterministic post-review status reconciliation from committed `review.md`.
- `scripts/architecture/generate_care_architecture_wiki.py`: machine-source diagram generation for current and history views, newline normalization, and concrete M8/M9 gap/delta graphs.
- `scripts/architecture/validate_care_architecture_wiki.py`: stricter component/source/diagram/history validation, including placeholder diagram token rejection.
- `scripts/architecture/create_care_history_snapshot.py`: future M10+ snapshot creation now records that `delta-from-Mprevious` will be generated and appends a deterministic comparison entry when a real snapshot is created.
- `scripts/validation/validate_handoff_policy.py`: M10/system-level history-reading gate, mandatory milestone-staging frontmatter gate, separate GPT planning-review gate, default staging/plan discovery, and executor-plan consistency validation.
- `src/care_myocardium/tests/test_handoff_policy_validator.py`: synthetic coverage for watcher, accounting retry, executor wave validation/merge, history migration, diagram consistency, GPT history gates, review reconciliation, M10 staging frontmatter/planning review blockers, executor-plan required completion fields, and future M10/M11 history deltas.

No model code, model training, validation package, upload, checkpoint, NIfTI, prediction output, or historical M8/M9 result packet was modified.

By user instruction, `prompts/shared/M10_srr_v3_complete_mechanism_repair.md`
and
`prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml`
were not edited. The repaired validator now blocks those current files until a
separate GPT planning review/frontmatter/plan-repair maintenance step updates
them.
