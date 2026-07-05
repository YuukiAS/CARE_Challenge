# Unit Test Report

## Tests Added Or Updated

Updated `src/care_myocardium/tests/test_srr_v25_anti_laziness_validator.py` to cover:

- missing required result directory is an error;
- exact required output filename mismatch is an error;
- controller task graph and controller report subtask list mismatch is an error;
- final review without completion-check readiness is an error;
- strict/default validator mode returns nonzero on errors;
- explicit diagnostic non-strict mode returns zero while preserving errors;
- current `20260704_srr_v25_full_completion_goal` bad packet fails regression;
- smoke-scale training evidence cannot support completion, route promotion, or scientific stop;
- controller report missing terminal fields is an error.

## Commands

```bash
./envs/env_CARE/bin/python -m unittest src.care_myocardium.tests.test_srr_v25_anti_laziness_validator
```

Result: exit `0`, `Ran 12 tests`, `OK`.

```bash
./envs/env_CARE/bin/python -m unittest src.care_myocardium.tests.test_handoff_policy_validator
```

Result: exit `0`, `Ran 9 tests`, `OK`.

```bash
./envs/env_CARE/bin/python -m py_compile scripts/validation/validate_srr_v25_anti_laziness.py src/care_myocardium/tests/test_srr_v25_anti_laziness_validator.py
```

Result: exit `0`.

```bash
git diff --check -- scripts/validation/validate_srr_v25_anti_laziness.py src/care_myocardium/tests/test_srr_v25_anti_laziness_validator.py prompts/AGENT_RULES.md prompts/CHATGPT_RULES.md prompts/templates/CONTROLLER_TASK_TEMPLATE.md prompts/CARE_OVERLAY_GATES.md
```

Result: exit `0`.
