# Agent-flow v2 pre-M10 final repair result

Task key: `20260711_agent_flow_v2_pre_m10_final_repair`

Controller status: `PACKET_COMMITTED_FOR_REVIEW`

This packet records handoff, Slurm continuity, parallel executor, wiki/history, and validator repairs only. It did not design or execute M10, train models, submit ordinary training jobs, modify historical M8/M9 result packets, package validation, upload, or push.

## Fixed conflicts

- Replaced watcher exit-code-only behavior with state-aware finalizer polling. `NEEDS_MONITOR`, `AWAITING_SACCT_RETRY_EXHAUSTED`, and `INITIALIZING` continue polling; terminal ready states stop cleanly; failure states stop nonzero.
- Made `AWAITING_SACCT_RETRY_EXHAUSTED` retryable and added retry metadata to `finalizer_state.json`.
- Added first-party executor wave preparation and merge helpers, with fail-closed executor-plan validation for lane, path overlap, duplicate namespaces, merge order, dependency cycles, and MyoPS/Cine isolation.
- Restored M8/M9 original analysis sources from git history into immutable `ORIGINAL_ANALYSIS.md` files with SHA256 records.
- Rebuilt M8/M9 history mapping, comparison, component pages, architecture YAML, D2/SVG/PNG diagrams, and current wiki component mapping.
- Fixed the history diagrams that previously showed placeholder relationships such as `历史组件关系` or generic `component_delta`. The history graph edges now describe concrete component relationships and the validator rejects these placeholder tokens.
- Added GPT M10/system-level history-reading gates and prompt merge-position rules.
- Added deterministic post-review wiki reconciliation script.

## Verification

All required lightweight checks passed:

```text
python scripts/validation/validate_handoff_policy.py --strict-tasks --warnings-as-errors
python scripts/architecture/validate_care_architecture_wiki.py --strict --history
python scripts/architecture/generate_care_architecture_wiki.py --check-all
python scripts/ops/validate_executor_plan.py prompts/templates/EXECUTOR_PLAN_TEMPLATE.yaml
python -m unittest src.care_myocardium.tests.test_handoff_policy_validator
python -m py_compile scripts/ops/care_milestone_finalizer.py scripts/ops/submit_care_dependency_finalizer.py scripts/ops/start_care_tmux_watcher.py scripts/ops/validate_executor_plan.py scripts/ops/prepare_care_executor_wave.py scripts/ops/merge_care_executor_wave.py scripts/architecture/reconcile_review_status.py scripts/architecture/generate_care_architecture_wiki.py scripts/architecture/validate_care_architecture_wiki.py scripts/validation/validate_handoff_policy.py
bash -n jobs/src/care_milestone_finalizer.sh
git diff --check
```

The unit test suite reported `Ran 44 tests ... OK`. Its printed merge-conflict line is from the intentional known-bad merge-conflict test.
