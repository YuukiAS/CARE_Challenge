# Result 20260703 Diagnostic Publication Gate

status: EXECUTED_UNAUDITED
self_assessed_status: completed

## Execution Summary

已更新 CARE handoff/controller 协议，使 route promotion gate 与 diagnostic
artifact publication gate 分开。新的规则允许 controller 在 audit/re-audit 通过、
无 route promotion、但 diagnostic publication gate 满足时，发布 reviewed minimal
diagnostic packet；同时明确该发布不授权 validation packaging/upload、fold
expansion、hosted metric claim、label/evaluator/fold split change 或 next-stage
training。

## Files Read

- `AGENTS.md`: 顶层 CARE/Bridge Kit 规则和 result publication boundary。
- `prompts/AGENT_RULES.md`: Codex 执行、controller、git sync policy。
- `prompts/CHATGPT_RULES.md`: GPT task generation 和 controller planning rules。
- `prompts/HANDOFF_ROLES.md`: strategic planner / execution controller role split。
- `prompts/HANDOFF_STATE_MACHINE.md`: controlled states。
- `prompts/CONTROLLER_TASK_PROTOCOL.md`: controller required shape/report rules。
- `prompts/CARE_OVERLAY_GATES.md`: CARE-specific controller and submission gates。
- `prompts/templates/TASK_TEMPLATE.md`: execution task frontmatter template。
- `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`: controller task frontmatter/report template。
- `prompts/templates/RESULT_TEMPLATE.md`: executor report template。
- `prompts/templates/REVIEW_TEMPLATE.md`: auditor review template。
- `prompts/README.md`, `results/README.md`, `scripts/README.md`: docs/README surfaces。
- `prompts/tasks/20260703_hardmode_goal.md`: existing controller task with git allowed and promotion-only wording.
- `src/care_myocardium/tests/test_*.py`: local unittest style reference.

## Files Modified

- `AGENTS.md`: result publication boundary now allows reviewed diagnostic packets and forbids full result trees/heavy artifacts; controller git sync now keys off route promotion or diagnostic publication gates.
- `prompts/AGENT_RULES.md`: added route/diagnostic gate fields and updated controller/git policy.
- `prompts/CHATGPT_RULES.md`: task-generation rules now require diagnostic publication fields for controller tasks and document legacy defaults.
- `prompts/HANDOFF_ROLES.md`: execution controller responsibilities now include both gate decisions.
- `prompts/HANDOFF_STATE_MACHINE.md`: added `AUDITED_DIAGNOSTIC_PUBLISH` state and blocked-action semantics.
- `prompts/CONTROLLER_TASK_PROTOCOL.md`: added gate semantics, publication scope, blocked actions, report ending fields, and git trigger rules.
- `prompts/CARE_OVERLAY_GATES.md`: CARE overlay now blocks CARE high-risk actions after diagnostic publication.
- `prompts/templates/TASK_TEMPLATE.md`: added compatible diagnostic publication fields.
- `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`: added required fields and required controller report ending.
- `prompts/templates/RESULT_TEMPLATE.md`: added git/report fields for route and diagnostic gate status.
- `prompts/templates/REVIEW_TEMPLATE.md`: added separate route promotion and diagnostic publication decisions.
- `prompts/README.md`, `results/README.md`, `scripts/README.md`: documented new policy and validator location.
- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`: added migration note.
- `prompts/tasks/20260703_hardmode_goal.md`: updated current controller task to use the new diagnostic publication fields and git policy.
- `scripts/validation/validate_handoff_policy.py`: added lightweight handoff policy validator.
- `src/care_myocardium/tests/test_handoff_policy_validator.py`: added unit tests for validator behavior.
- `results/20260703_diagnostic_publication_gate/MANIFEST.md`: added this result package index.
- `results/20260703_diagnostic_publication_gate/result.md`: this report.
- `results/20260703_diagnostic_publication_gate/review.md`: concise self-review.

## Commands Run

```bash
python -m unittest src.care_myocardium.tests.test_handoff_policy_validator
```

- purpose: run new validator unit tests.
- result: passed, 5 tests.
- exit_status: 0

```bash
python scripts/validation/validate_handoff_policy.py
```

- purpose: run default handoff policy validation over updated policy docs/templates.
- result: passed.
- exit_status: 0

```bash
python scripts/validation/validate_handoff_policy.py --strict-tasks prompts/tasks/20260703_hardmode_goal.md
```

- purpose: verify the current git-enabled hardmode controller task has explicit route/diagnostic gates.
- result: passed.
- exit_status: 0

```bash
git diff --check
```

- purpose: check whitespace errors in tracked diff.
- result: passed.
- exit_status: 0

```bash
python scripts/validation/validate_handoff_policy.py results/20260703_diagnostic_publication_gate
```

- purpose: validate this result/review package is not misclassified as a controller publication report.
- result: passed.
- exit_status: 0

```bash
rg -n "promotion gate is satisfied|no route promotion gate is satisfied|only after audit and promotion gate|promotion gate approval|audit passes, the promotion gate|audit passes.*promotion gate|promotion gate.*commit and push|commit/push.*promotion gate" AGENTS.md prompts results/README.md scripts/README.md
```

- purpose: search for stale promotion-only commit/push language in the updated handoff surfaces.
- result: no matches.
- exit_status: 1 from `rg` because no matches were found.

## Test Results

- `python -m unittest src.care_myocardium.tests.test_handoff_policy_validator`: passed.
- `python scripts/validation/validate_handoff_policy.py`: passed.
- `python scripts/validation/validate_handoff_policy.py --strict-tasks prompts/tasks/20260703_hardmode_goal.md`: passed.
- `python scripts/validation/validate_handoff_policy.py results/20260703_diagnostic_publication_gate`: passed.
- `git diff --check`: passed.
- stale promotion-only grep: no matches.

## Artifact Paths

- `results/20260703_diagnostic_publication_gate/MANIFEST.md`: artifact index.
- `results/20260703_diagnostic_publication_gate/result.md`: execution report.
- `results/20260703_diagnostic_publication_gate/review.md`: concise self-review.

## Diff Summary

Added one policy migration note, one validator script, one unit test file, and
one result package. Updated Bridge Kit/CARE protocol docs, templates, READMEs,
and the current hardmode controller task to distinguish route promotion from
diagnostic publication.

## Claims

- `claim.route_promotion_split`: Protocol files now define `route_promotion_gate` separately from `diagnostic_publication_gate`.
- `claim.diagnostic_scope_defined`: Diagnostic publication scope and forbidden artifact classes are documented.
- `claim.blocked_actions_defined`: Validation packaging/upload, fold expansion, hosted metric claims, label/evaluator/fold split changes, and next-stage training remain blocked after diagnostic publication.
- `claim.controller_report_fields`: Controller report templates require route promotion decision, diagnostic publication decision, git decisions, published files, blocked actions, and reasons.
- `claim.validator_added`: A repository validator and unit tests now cover key policy checks.

## Failure Information

none

## Incomplete Items

none

## Human Approval Needed

none for this docs/protocol patch. Actual future diagnostic publication commits/pushes still depend on the relevant controller task authorization and audit/re-audit.

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
- reason_if_not_executed: user requested suggested commit message but did not explicitly ask this session to commit/push

## Self-Assessed Status

completed
