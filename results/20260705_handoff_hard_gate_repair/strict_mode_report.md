# Strict Mode Report

## Commands

```bash
./envs/env_CARE/bin/python scripts/validation/validate_srr_v25_anti_laziness.py --repo-root . --controller prompts/tasks/20260704_srr_v25_full_completion_goal.md --results-root results --json
```

Result: exit `1`, `issue_count: 18`, `error_count: 18`, `warning_count: 0`.

```bash
./envs/env_CARE/bin/python scripts/validation/validate_srr_v25_anti_laziness.py --repo-root . --controller prompts/tasks/20260704_srr_v25_full_completion_goal.md --results-root results --json --diagnostic-non-strict
```

Result: exit `0`, same findings.

## Decision

strict_mode_gate: `PASS`

Errors no longer exit zero in default completion mode. Zero exit with errors requires explicit `--diagnostic-non-strict`.
