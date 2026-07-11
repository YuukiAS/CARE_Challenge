# M10 Completion Check

Completion state: `NEEDS_MONITOR`

This is not `PACKET_COMMITTED_FOR_REVIEW` for a completed M10 runtime milestone. It records that wave 2 submitted Slurm jobs and is awaiting terminal runtime evidence plus post-job aggregation.

## Required Gates

| Gate | Status |
| --- | --- |
| M10 section in `prompts/shared/EXECUTOR_PROMPTS.md` | pass |
| Strict executor plan path used | pass |
| `scripts/ops/validate_executor_plan.py` | pass |
| M9 audited predecessor token | pass |
| agent-flow generic repair audited predecessor token | pass |
| Planner draft commit ancestor of HEAD | pass |
| Canonical merged contract hash recomputed and matched | pass |
| Historical staging hash retained as pre-merge record | pass |
| Wave 1 executor receipt | pass: `READY_FOR_CONTROLLER_MERGE` |
| Wave 1 controller merge | pass |
| Wave 2 launch receipt | pass |
| Wave 2 executor receipt | monitor: `NEEDS_MONITOR` |
| Live Slurm status | monitor: all seven jobs pending |

## Decision

The controller must wait for wave 2 terminal job states and post-job aggregation before any controller merge, wave 3 launch, or review request. Submitted, pending, running, or accounting-wait states are not completion evidence.

No `review.md` was written.
