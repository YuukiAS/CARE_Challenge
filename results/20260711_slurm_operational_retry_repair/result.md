# Slurm Operational Retry Protocol Repair Result

task_type: protocol_infrastructure_repair
source_task: TODO.md from origin/main commit 061b396
runtime_review_written: false
m10_training_executed: false
slurm_jobs_submitted: false
route_promotion_decision: NOT_APPLICABLE
scientific_resolution_status: NOT_APPLICABLE

## Scope

Implemented the TODO repair for CARE controller handling of retryable Slurm startup/runtime failures. The repair is generic protocol and infrastructure work. It does not change M10 scientific formulas, variants, budgets, splits, metrics, route decisions, or executor counts.

## Changes

- Added operational retry state and controlled block taxonomy to the handoff state machine.
- Defined same-task, same-executor, same-command-semantics operational replacement attempts as already authorized by the original task.
- Added controller decision rules requiring task-local recovery before escalating to planner or human authorization.
- Added Slurm skill rules for compute-node preflight, `afterok` training dependencies, `afterany` finalizer accounting, retry ledgers, and zero training credit for failed startup attempts.
- Extended executor-plan and controller-packet schemas with retry/preflight/finalizer fields.
- Added helper scripts for training preflight and dependency-chain submission.
- Updated finalizer and watcher behavior so retryable operational failures hand back to the controller for same-scope retry instead of stopping as a permanent block.
- Added validator checks and regression tests for the M10 `mpmath` startup-failure failure mode and invalid training `afterany` chains.

## Verification

```text
python scripts/ops/validate_executor_plan.py prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml
python scripts/validation/validate_handoff_policy.py --policy --warnings-as-errors
python -m py_compile scripts/ops/validate_executor_plan.py scripts/ops/care_milestone_finalizer.py scripts/ops/start_care_tmux_watcher.py scripts/ops/submit_care_dependency_finalizer.py scripts/ops/run_care_training_preflight.py scripts/ops/submit_care_training_chain.py scripts/validation/validate_handoff_policy.py
python -m unittest src.care_myocardium.tests.test_handoff_policy_validator src.care_myocardium.tests.test_operational_retry_policy
python scripts/validation/validate_handoff_policy.py --repository-readiness --warnings-as-errors
python scripts/architecture/validate_care_architecture_wiki.py --strict --history
git diff --check
```

## Boundary

The root `TODO.md` task file was removed after implementation because repository architecture validation rejects root TODO analysis files after wiki/history migration. No `review.md` was written.
