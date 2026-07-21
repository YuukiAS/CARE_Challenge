# CARE final output readability refactor

## Why this was needed

Before this change, CARE could produce technically complete answers that started from repository labels, status tokens, paths, loss names, or command traces. That style was precise for machines but hard for a scientific lead to read, because the reader had to decode internal names before understanding the actual judgment.

## New default

Future user-facing CARE analysis must first state the scientific meaning in natural Chinese: what the main problem is, why it happened, what should happen next, and what should not be done yet. Internal labels, paths, metrics, commands, YAML fields, and state tokens remain allowed, but only after the meaning is clear and only as locating evidence.

## Policy and template changes

Added `prompts/FINAL_OUTPUT_READABILITY_POLICY.md` as the canonical readability gate. Hooked it into `AGENTS.md`, `START_HERE_FOR_GPT.md`, `GPT_PLANNER_CARE_PROTOCOL.md`, `prompts/AGENT_RULES.md`, `prompts/CHATGPT_RULES.md`, `prompts/GPT_HARD_GATE_PROMPT.md`, and `prompts/ACTIVE_POLICY_FILES.yaml`.

Updated the task, controller, result, and review templates so future reports include a final readability check and put technical details after the human judgment. The controller template was also aligned with the current default controller-as-coordinator flow: no default `review.md`, no default independent reviewer gate, and terminal completion through `controller_report.md` plus `completion_check.md`.


## Critic and reviewer default check

The active default remains controller-centered: future tasks use `planning_review_required: false` and `review_required: false` unless the Planner or user explicitly opts into the legacy critic or reviewer path. Focused active-policy search confirmed the remaining critic/reviewer wording is either an explicit opt-in rule, a historical compatibility rule, or a test that verifies the explicit old gates still work. Missing `planning_review.md` and missing `review.md` do not block default new tasks.

## Validator and tests

Enhanced `scripts/validation/validate_handoff_policy.py` with active policy/template checks and opt-in full readability checks for new readability fixtures or staged prompts. The validator catches machine-style first paragraphs, internal labels used as headings, unexplained mechanism sections, formulas without natural-language context, bare training-stage checklists, and unexplained English-token stacking.

Added `tests/validation/test_final_output_readability_policy.py` to cover both passing examples and known-bad examples. The checks are scoped to active policy/templates and new readability/staged-prompt content, so historical result, review, and route evidence are not bulk-scanned or rewritten.

## Compatibility

This change does not rewrite historical experiment packets. Machine-readable fields, paths, commands, status enums, schema keys, validator tokens, and evidence indexes remain valid. The new requirement only changes how future final analysis is presented to users, Planner, controller summaries, and explicit reviewer conclusions.

## Test results

- `./envs/env_CARE/bin/python -m py_compile scripts/validation/validate_handoff_policy.py`: exit code 0.
- `./envs/env_CARE/bin/python scripts/validation/validate_handoff_policy.py --policy --warnings-as-errors`: exit code 0; handoff policy validation passed.
- `./envs/env_CARE/bin/python -m pytest -q tests/validation/test_final_output_readability_policy.py tests/validation/test_sprint_flow_policy.py`: exit code 0; 18 passed.
