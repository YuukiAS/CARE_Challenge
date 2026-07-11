# Agent-flow v2 pre-M10 final repair result

Task key: `20260711_agent_flow_v2_pre_m10_final_repair`

Controller status: `PACKET_COMMITTED_FOR_REVIEW`

This packet records handoff, Slurm continuity, parallel executor, wiki/history, and validator repairs only. It did not design or execute M10, train models, submit ordinary training jobs, modify historical M8/M9 result packets, package validation, upload, or push.

Requested baseline commit for this follow-up repair: `20650aa5a7082433449c2012c752774edf9b44fb`.

Live HEAD at repair start was `094dd905c368f66204d6b62e223f962813346a46`, a local unpushed M10 controller-initialization packet. This follow-up did not revert that local packet; it repaired the pre-M10 controller infrastructure and current `20260711_agent_flow_v2_pre_m10_final_repair` packet on top of it.

## Fixed conflicts

- Replaced watcher exit-code-only behavior with state-aware finalizer polling. `NEEDS_MONITOR`, `AWAITING_SACCT_RETRY_EXHAUSTED`, and `INITIALIZING` continue polling; terminal ready states stop cleanly; failure states stop nonzero.
- Made `AWAITING_SACCT_RETRY_EXHAUSTED` retryable and added retry metadata to `finalizer_state.json`.
- Added first-party executor wave preparation and merge helpers, with fail-closed executor-plan validation for lane, path overlap, duplicate namespaces, merge order, dependency cycles, and MyoPS/Cine isolation.
- Restored M8/M9 original analysis sources from git history into immutable `ORIGINAL_ANALYSIS.md` files with SHA256 records.
- Rebuilt M8/M9 history mapping, comparison, component pages, architecture YAML, D2/SVG/PNG diagrams, and current wiki component mapping.
- Fixed the history diagrams that previously showed placeholder relationships such as `历史组件关系` or generic `component_delta`. The history graph edges now describe concrete component relationships and the validator rejects these placeholder tokens.
- Added GPT M10/system-level history-reading gates and prompt merge-position rules.
- Added deterministic post-review wiki reconciliation script.
- Added missing `controller_report.md` and made controller packet completeness fail closed in the handoff validator.
- Changed history generation, validation, and review reconciliation from hard-coded `M08/M09` choices to dynamic `wiki/history/M*/` discovery with `^M[0-9]{2,}$` validation.
- Added `scripts/architecture/create_care_history_snapshot.py` so future M10 mapper final can create `wiki/history/M10/` from the current wiki without overwriting existing history.
- Implemented actual `AWAITING_SACCT_RETRY_EXHAUSTED` continuation via namespace-local state-aware tmux watcher or resubmitted finalizer, with receipt fields for command, session/job id, log, lock, and result directory.
- Strengthened multi-executor merge to verify completion packets from executor worktree/branch, enforce completion tokens, reject monitor/evidence/revision tokens, and record source branch head plus merged commit details.
- Made watcher startup write real stdout/stderr to `log_path` and reject duplicate tmux sessions.
- Added mandatory machine YAML frontmatter validation for `prompts/shared/M[0-9]*_*.md` milestone staging files. `## Execution Contract` is now only a human-readable mirror.
- Added pre-execution planning review gates for M10/system-level/high-risk staging: `planner GPT -> separate GPT critic -> Codex merge/validator -> controller`.
- Expanded default handoff validation to scan milestone staging files, `prompts/tasks/*executor_plan.yaml`, and planning review files, and to validate `executor_plan_path` consistency.
- Added dynamic future-history delta generation for M10/M11 and later: `delta-from-Mprevious` is computed from both versions' `COMPONENTS.csv` and `architecture.yaml`, not from a generic placeholder.

## Verification

Required lightweight checks were run. The handoff validator now intentionally
blocks the current unmodified M10 staging/plan until planning frontmatter,
separate GPT planning review, and executor-plan completion fields are repaired:

```text
python scripts/validation/validate_handoff_policy.py --strict-tasks --warnings-as-errors
  -> exit 1, expected planning gate block:
     prompts/shared/M10_srr_v3_complete_mechanism_repair.md lacks YAML frontmatter
     prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml has invalid lane and missing required_completion_* fields
python scripts/architecture/validate_care_architecture_wiki.py --strict --history
  -> pass
python scripts/architecture/generate_care_architecture_wiki.py --check-all
  -> pass
python scripts/ops/validate_executor_plan.py prompts/templates/EXECUTOR_PLAN_TEMPLATE.yaml
  -> pass
python scripts/architecture/create_care_history_snapshot.py --milestone M10 --dry-run
  -> pass, reports future delta-from-M09 generation
python -m unittest src.care_myocardium.tests.test_handoff_policy_validator
  -> Ran 62 tests ... OK
python -m py_compile scripts/validation/validate_handoff_policy.py scripts/ops/validate_executor_plan.py scripts/architecture/create_care_history_snapshot.py scripts/architecture/generate_care_architecture_wiki.py scripts/architecture/validate_care_architecture_wiki.py
  -> pass
git diff --check
  -> pass
```

The unit test suite reported `Ran 62 tests ... OK`. Its printed merge-conflict and monitor-token lines are intentional known-bad tests.

This follow-up did not modify `prompts/shared/M10_srr_v3_complete_mechanism_repair.md` or `prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml`, by user instruction. The new validator errors on those files are the planning review guard working as intended.
