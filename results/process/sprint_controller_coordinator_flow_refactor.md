# Sprint Controller/Coordinator Flow Refactor

## Why the old flow blocked

Before this repair, the canonical Agent-Flow policy treated several risk fields as automatic planning-critic triggers: `task_kind: scientific_milestone`, `risk_level: high`, `architecture_impact: system`, `slurm_runtime_continuity_required: true`, `executor_count > 1`, `route_change: true`, and `scientific_decision_scope != none`. The handoff validator then required `planning_review_required: true`, a non-empty planning review token, and a reviewed commit before a READY staging prompt could proceed.

The runtime side also defaulted to `review_required: true`, `review_mode: independent_thread`, and `reviewer: separate_readonly`. That made ordinary future sprint completion depend on a post-execution `review.md` or audited-go style continuation token, even when the intended flow was for the Controller to verify the task and return results to the Planner.

## New default flow

Future Batch 5 and later sprint tasks default to:

```text
Planner
-> Controller/Coordinator
-> Executor
-> Controller verification and repair loop
-> deterministic finalizer/validators
-> local lightweight commit
-> Planner reads results and decides the next task
```

Default policy fields are now:

```yaml
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
review_required: false
review_mode: none
reviewer: none
controller_is_coordinator: true
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
```

Only `controller_verification_decision: VERIFIED_COMPLETE` means the current task is complete. It requires machine-checkable evidence for required outputs, contract compliance, validators, terminal job accounting, aggregation, and git decisions. `SUBMITTED`, `PENDING`, `RUNNING`, `NEEDS_MONITOR`, and `AWAITING_SACCT` remain non-completion states.

## Explicit optional legacy flows retained

The planning critic remains valid when a Planner or user explicitly sets:

```yaml
planning_review_required: true
planning_reviewer: separate_gpt_thread
```

In that case the old planning review receipt, hash, token, and reviewed commit checks still apply.

The independent reviewer remains valid when a Planner or user explicitly sets:

```yaml
review_required: true
review_mode: independent_thread | short_goal
reviewer: separate_readonly
```

In that case reviewer handoff files are still required. Default sprint packets no longer need `review.md`.

## Files changed

- `prompts/AGENT_FLOW_V2_PROTOCOL.md`, `prompts/HANDOFF_GATE_POLICY.md`, `prompts/GPT_HARD_GATE_PROMPT.md`, `START_HERE_FOR_GPT.md`, `GPT_PLANNER_CARE_PROTOCOL.md`, `AGENTS.md`, `prompts/HANDOFF_ROLES.md`, `prompts/HANDOFF_STATE_MACHINE.md`, and `prompts/CONTROLLER_TASK_PROTOCOL.md`: documented Controller as coordinator/acceptance owner and made critic/reviewer opt-in.
- `prompts/schemas/agent_flow_policy.yaml`: replaced automatic critic triggers with defaults, opt-in sections, risk-classification fields, default sprint flow, and controller completion fields.
- `prompts/schemas/controller_packet.schema.yaml`: removed reviewer handoff files from base required files and made them conditional on explicit `review_required`.
- `prompts/schemas/milestone_staging.schema.yaml`: made reviewer prompt an additional section only for `review_required` tasks.
- `scripts/validation/validate_handoff_policy.py`: changed planning critic enforcement to explicit opt-in, removed default high-risk reviewer gate, added `VERIFIED_COMPLETE` completion checks, added conditional reviewer handoff validation, and kept monitor/nonterminal states fail-closed.
- `prompts/templates/TASK_TEMPLATE.md`: updated the default task template to no critic/no reviewer.
- `tests/validation/test_sprint_flow_policy.py`: added regression coverage for new default flow, explicit old gates, Batch 4 receipt recognition, and known-bad incomplete packets.

## Controller acceptance enforcement

The Controller is now required to verify executor work instead of only collecting a summary. The protocol requires it to inspect git diff, changed files, command results, contract-sensitive fields, required outputs, training adequacy, Slurm terminal accounting, aggregation, validator exits, and known-bad regressions after each wave. Same-scope implementation/runtime defects stay inside the current task and must be repaired before terminal completion.

A `VERIFIED_COMPLETE` packet must have:

```text
controller_verification_decision: VERIFIED_COMPLETE
contract_compliance_status: PASS | COMPLETE | COMPLIANT
required_outputs_complete: true
validators_passed: true
all_jobs_terminal: true
aggregation_complete: true
next_required_action: RETURN_TO_PLANNER
```

## Batch 4 compatibility

Batch 4 was not rewritten. Its existing explicit planning review receipt remains present at `prompts/tasks/20260721_srr_batch4_forced_fold0_training_planning_review.md` with `planning_review_decision: AUDITED_GO`, `planning_review_token: BATCH4_PLANNING_AUDITED_GO`, and the reviewed controller prompt path. Existing tasks that explicitly request planning review or runtime review continue through the legacy-compatible paths.

No Batch 4 Slurm job was started, cancelled, modified, or submitted.

## Validation run

| Command | Exit | Result |
| --- | ---: | --- |
| `./envs/env_CARE/bin/python -m py_compile scripts/validation/validate_handoff_policy.py` | 0 | Python syntax valid |
| `./envs/env_CARE/bin/python scripts/validation/validate_handoff_policy.py --policy --warnings-as-errors` | 0 | handoff policy validation passed |
| `./envs/env_CARE/bin/python -m pytest -q tests/validation/test_sprint_flow_policy.py` | 0 | 10 passed |
| `./envs/env_CARE/bin/python -m pytest -q tests/validation/test_sprint_flow_policy.py tests/srr_production/test_myops_batch4_contract.py` | 0 | 22 passed, 3 warnings |
| `./envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/tasks/20260721_srr_batch4_forced_fold0_training_executor_plan.yaml` | 0 | executor plan validation passed |

## Remaining limitations

This repair changes the canonical default and validator behavior for future tasks. It intentionally does not bulk-rewrite historical route plans, old milestone packets, legacy reviewer prompts, or the current Batch 4 controller contract. Those files remain historical evidence or explicit opt-in tasks.
