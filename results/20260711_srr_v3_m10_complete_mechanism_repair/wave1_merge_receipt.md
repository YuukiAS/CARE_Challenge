# M10 Wave 1 Merge Receipt

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Executor: `m10_shared_architecture_executor`

Controller decision: `WAVE1_READY_FOR_CONTROLLER_MERGE_ACCEPTED`

## Completion Receipt

Wave 1 wrote:

```text
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_shared_architecture_executor/result.md
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_shared_architecture_executor/completion_check.md
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_shared_architecture_executor/commands_run.md
results/20260711_srr_v3_m10_complete_mechanism_repair/executors/m10_shared_architecture_executor/MANIFEST.md
```

Completion token:

```text
READY_FOR_CONTROLLER_MERGE
```

## Controller Verification

| Check | Result |
| --- | --- |
| `review.md` absent | pass |
| Wave 1 required output files exist | pass |
| `pytest src/care_myocardium/tests/test_srr_v3_m10_fidelity.py` | `5 passed` |
| Allowed regression subset | `15 passed, 3 warnings` |
| Touched Python compile | pass |
| `validate_executor_plan.py` | pass |
| `git diff --check` | pass |

## Carry-Forward

The broader compatibility command:

```text
pytest src/care_myocardium/tests/test_srr_proposal_prototypes.py
```

currently fails two tests because `scripts/training/run_srr_propref_myops_fold0.py::propref_loss` expects `args.variant` while those existing tests pass an older args fixture. That training script is outside wave 1 write scope and inside wave 2 write scope, so the controller carries it forward to `m10_myops_training_executor`.

## Freeze

Wave 1 shared architecture is frozen for wave 2. If wave 2 finds a shared architecture or loss wiring defect, the controller must return to wave 1 rather than hot-patching shared model/loss files in wave 2.
