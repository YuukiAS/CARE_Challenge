# Result 20260703 Experiment Adequacy Gate

status: EXECUTED_UNAUDITED
self_assessed_status: completed

## Execution Summary

已更新 CARE handoff/controller 协议，使 controller operational completion、
diagnostic artifact publication、scientific route resolution、experiment adequacy
四件事分开报告。新的规则禁止在 `experiment_adequacy_gate` 未通过时使用
`STOP_NO_SIGNAL`、`STOP_NO_PROPREF_SIGNAL`、`STOP_NO_CLEAN_ANCHOR_SIGNAL`、
`STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL` 等科学负结论；此类结果必须写成
`SCIENTIFIC_UNDERTRAINED`、`SCIENTIFIC_UNRESOLVED`、`SCIENTIFIC_NEEDS_EVIDENCE`、
`SCIENTIFIC_NEEDS_REVISION` 或 `SCIENTIFIC_PIPELINE_BUG`。

## Files Read

- `AGENTS.md`: repo-level handoff and CARE rules.
- `prompts/AGENT_RULES.md`: Codex execution, audit, controller, git, and failure rules.
- `prompts/CHATGPT_RULES.md`: GPT planning and task frontmatter rules.
- `prompts/HANDOFF_ROLES.md`: execution controller responsibilities.
- `prompts/HANDOFF_STATE_MACHINE.md`: controlled states.
- `prompts/CONTROLLER_TASK_PROTOCOL.md`: controller report structure and gates.
- `prompts/CARE_OVERLAY_GATES.md`: CARE-specific evidence and submission gates.
- `prompts/MECHANISM_GATE_TEMPLATE.md`: generic gate template.
- `prompts/templates/TASK_TEMPLATE.md`: execution task template.
- `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`: controller task template.
- `prompts/templates/RESULT_TEMPLATE.md`: executor report template.
- `prompts/templates/REVIEW_TEMPLATE.md`: auditor review template.
- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`: prior diagnostic publication split.
- `scripts/validation/validate_handoff_policy.py`: handoff validator.
- `src/care_myocardium/tests/test_handoff_policy_validator.py`: validator tests.
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md` and `references/reference.md`: medical-imaging model evidence standards.

## Files Modified

- `AGENTS.md`: added experiment adequacy and scientific-resolution boundary in top-level handoff rules.
- `prompts/AGENT_RULES.md`: added new frontmatter fields, audit obligations, and STOP_NO_* restrictions.
- `prompts/CHATGPT_RULES.md`: added task-generation requirements for minimum effective training, experiment adequacy, route negative, and scientific completion gates.
- `prompts/HANDOFF_ROLES.md`: added operational completion, experiment adequacy, and route-negative responsibilities.
- `prompts/HANDOFF_STATE_MACHINE.md`: added scientific states and rules separating controller completion from scientific resolution.
- `prompts/CONTROLLER_TASK_PROTOCOL.md`: added gate definitions, required report ending, and examples A/B/C.
- `prompts/CARE_OVERLAY_GATES.md`: added CARE experiment adequacy contract.
- `prompts/MECHANISM_GATE_TEMPLATE.md`: added experiment adequacy and route negative gate sections.
- `prompts/templates/TASK_TEMPLATE.md`: added minimum effective training and route negative fields.
- `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`: added minimum effective training fields and required report statuses.
- `prompts/templates/RESULT_TEMPLATE.md`: added experiment adequacy evidence section.
- `prompts/templates/REVIEW_TEMPLATE.md`: added adequacy/route-negative/scientific status audit sections.
- `prompts/EXPERIMENT_ADEQUACY_GATE.md`: added migration note and examples.
- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`, `prompts/README.md`, `results/README.md`, `docs/README.md`: linked and clarified the new split.
- `prompts/tasks/20260703_hardmode_goal.md`: minimally updated current controller task with experiment adequacy gates and STOP_NO_* restriction.
- `scripts/validation/validate_handoff_policy.py`: added operational/scientific controller report checks and route-negative adequacy checks.
- `src/care_myocardium/tests/test_handoff_policy_validator.py`: added tests for undertrained stop rejection, supported stop, unresolved next action, and review evidence.
- `results/20260703_experiment_adequacy_gate/MANIFEST.md`: this result package index.
- `results/20260703_experiment_adequacy_gate/result.md`: this report.
- `results/20260703_experiment_adequacy_gate/review.md`: concise self-review.

## Commands Run

```bash
python -m unittest src.care_myocardium.tests.test_handoff_policy_validator
```

- purpose: run validator unit tests.
- result: passed, 9 tests.
- exit_status: 0

```bash
python scripts/validation/validate_handoff_policy.py
```

- purpose: run default handoff policy validation.
- result: passed.
- exit_status: 0

```bash
python scripts/validation/validate_handoff_policy.py --strict-tasks prompts/tasks/20260703_hardmode_goal.md
```

- purpose: verify current git-enabled hardmode controller task has explicit adequacy and route-negative gates.
- result: passed.
- exit_status: 0

```bash
python scripts/validation/validate_handoff_policy.py results/20260703_experiment_adequacy_gate
```

- purpose: validate this result package.
- result: passed.
- exit_status: 0

```bash
git diff --check
```

- purpose: check whitespace errors in tracked diff.
- result: passed.
- exit_status: 0

```bash
rg -n "promotion gate satisfied|promotion gate is satisfied|status: complete|status: NEEDS_GPT_PLANNER|STOP_NO_SIGNAL|STOP_NO_PROPREF_SIGNAL|STOP_NO_CLEAN_ANCHOR_SIGNAL|STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL|controller_run_status|scientific_resolution_status|experiment_adequacy_decision" AGENTS.md prompts/*.md prompts/templates/*.md prompts/tasks/20260703_hardmode_goal.md results/README.md docs/README.md scripts/validation/validate_handoff_policy.py src/care_myocardium/tests/test_handoff_policy_validator.py
```

- purpose: inspect old ambiguous phrases and confirm protocol surfaces disambiguate them.
- result: matches are in new required fields, examples, tests, or explicit prohibition text; no `promotion gate satisfied` match.
- exit_status: 0

## Test Results

- `python -m unittest src.care_myocardium.tests.test_handoff_policy_validator`: passed.
- `python scripts/validation/validate_handoff_policy.py`: passed.
- `python scripts/validation/validate_handoff_policy.py --strict-tasks prompts/tasks/20260703_hardmode_goal.md`: passed.
- `python scripts/validation/validate_handoff_policy.py results/20260703_experiment_adequacy_gate`: passed.
- `git diff --check`: passed.
- grep for old ambiguous phrases: reviewed; matches are disambiguated/prohibitive examples, not old policy.

## Artifact Paths

- `results/20260703_experiment_adequacy_gate/MANIFEST.md`: artifact index.
- `results/20260703_experiment_adequacy_gate/result.md`: execution report.
- `results/20260703_experiment_adequacy_gate/review.md`: concise self-review.

## Diff Summary

Added one protocol migration note and one result package. Updated Bridge Kit/CARE
handoff docs, templates, current hardmode controller task, validator, tests, and
README surfaces. No model code, label mapping, fold split, evaluator, submission
package, prediction, checkpoint, NIfTI, or upload artifact was changed.

## Claims

- `claim.operational_scientific_split`: Controller operational completion is now separated from scientific route resolution.
- `claim.experiment_adequacy_gate`: CARE model/training routes now require effective training, sanity, provenance, and baseline evidence before promotion or scientific stop.
- `claim.route_negative_gate`: STOP_NO_* conclusions now require adequacy PASS, baseline comparability, absence of pipeline explanations, and auditor approval.
- `claim.validator_updated`: Validator/tests cover missing report fields, undertrained STOP_NO rejection, supported stop, unresolved next action, and review evidence.

## Failure Information

none

## Incomplete Items

none

## Human Approval Needed

none for this protocol/docs/test patch.

## Git Commit And Push

- auto_git_commit: not run
- commit_executed: false
- commit_sha: none
- auto_git_push: not run
- push_executed: false
- remote: none
- route_promotion_gate: not applicable; protocol patch only
- diagnostic_publication_gate: not applicable; protocol patch result package only
- diagnostic_publication_scope: reviewed protocol docs, templates, validator, tests, and this result package
- diagnostic_publication_only_no_route_promotion: true
- reason_if_not_executed: user suggested a commit message but did not explicitly ask this session to commit/push

## Self-Assessed Status

completed
