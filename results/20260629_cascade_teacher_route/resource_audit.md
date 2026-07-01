# Cascade Teacher Resource Audit

- Branch/HEAD: `main` / `10c2bb9a231817cf6adfd6040a0e1cfa70fc7822`
- Workspace: `/users/a/e/aereinh/CARE`
- External upload: not used.
- Validation package generation: not used.
- `/overflow` writes: not used.
- Current blocker for formal cascade training: train-side teacher predictions are missing.
- Completed non-blocking work: generated task-scoped teacher cache preflight at `results/20260629_cascade_teacher_route/teacher_cache/` with no `/overflow` writes.
- Fold0-only train-side nnU-Net teacher predictions are missing (`0/176`), but the OOF-5 teacher cache now provides train coverage (`176/176`) by using folds 1-4 validation exports for fold0 train cases.
- Prepared train-side nnU-Net inference entrypoint: `jobs/src/run_cascade_teacher_train_inference.sh`.
- The train-side inference job has not been submitted; it is now a fallback, not the primary route, because OOF-5 teacher coverage is complete without extra GPU inference.
- Prepared OOF-5 cascade refiner entrypoint: `jobs/src/run_cascade_oof_refiner.sh`.
- OOF-5 cascade refiner has not been submitted because four repaired/SRR-v2 GPU tasks are already pending.
- Non-blocking work still possible: repaired/SRR-v2 monitoring and submitting OOF refiner after pending count drops.
