# Validator Report

This follow-up intentionally strengthens the planning validator so the current
unmodified M10 staging/plan is no longer executable as-is.

## Commands run

```text
python scripts/validation/validate_handoff_policy.py --strict-tasks --warnings-as-errors
exit: 1
expected blocker:
  - prompts/shared/M10_srr_v3_complete_mechanism_repair.md lacks real YAML frontmatter
  - prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml uses invalid lane `myops_cine_sequential`
  - the same executor plan is missing `required_completion_file`
  - the same executor plan is missing `required_completion_token`

python scripts/architecture/validate_care_architecture_wiki.py --strict --history
exit: 0

python scripts/architecture/generate_care_architecture_wiki.py --check-all
exit: 0

python scripts/architecture/create_care_history_snapshot.py --milestone M10 --dry-run
exit: 0
output: future `wiki/history/M10/figures/delta-from-M09.d2/svg/png` would be generated

python scripts/ops/validate_executor_plan.py prompts/templates/EXECUTOR_PLAN_TEMPLATE.yaml
exit: 0

python -m unittest src.care_myocardium.tests.test_handoff_policy_validator
exit: 0
output: Ran 62 tests ... OK

python -m py_compile scripts/validation/validate_handoff_policy.py scripts/ops/validate_executor_plan.py scripts/architecture/create_care_history_snapshot.py scripts/architecture/generate_care_architecture_wiki.py scripts/architecture/validate_care_architecture_wiki.py
exit: 0

git diff --check
exit: 0
```

## Coverage added or exercised

- M10 staging without frontmatter fails.
- `## Execution Contract` code block without frontmatter fails.
- `READY` M10 without `planning_review_token` fails.
- planning reviewer declared as controller/runtime subagent fails.
- frontmatter/body contract mismatch fails.
- missing `executor_plan_path` fails.
- invalid executor-plan lane fails.
- missing `required_completion_file` fails.
- missing `required_completion_token` fails.
- task `executor_count` differing from plan executor count fails.
- default validator discovers the current M10 staging file and executor plan.
- M10 history sources include `delta-from-M09`.
- M11 history sources include `delta-from-M10`.
- future history generic placeholder delta fails.
- existing watcher, accounting retry, executor wave validation/merge,
  history migration, diagram consistency, controller packet completeness, and
  post-review reconciliation tests continue to pass.

The failing handoff-policy command is the intended repaired gate. This
controller did not edit the M10 staging file or executor plan, so the next
maintenance step must repair those planning artifacts before M10 can execute.
