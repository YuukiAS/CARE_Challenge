# Cascade OOF Refiner Preflight Summary

Task: `prompts/tasks/20260629_cascade_teacher_route.md`

## CPU Preflight

- Entrypoint: `scripts/training/run_laneA_round10_refiner_train.py`
- Run name: `nnunet_anatomy_prior_refiner_cpu_preflight`
- Output root: `results/20260629_cascade_teacher_route/preflight/nnunet_anatomy_prior_refiner_cpu_preflight`
- Scope: CPU data/gradient preflight only; full validation export and evaluation were skipped.
- Teacher source: existing nnU-Net501 OOF probabilities for fold0 train rows and fold0 probabilities for validation rows.

## Result

- Training steps: `2`
- Mean loss: `0.4042`
- Loss finite: `True`
- Scar changed voxels in train patches: `0`
- No-T2 new edema voxels in train patches: `0`

## Interpretation

The OOF teacher/refiner data path is executable in the task-scoped `/users` result tree. This does not prove cascade efficacy; it only clears the CPU preflight for the `nnunet_anatomy_prior_refiner` entrypoint. Formal GPU training and full validation export remain pending.
