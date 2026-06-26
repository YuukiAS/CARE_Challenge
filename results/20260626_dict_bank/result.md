# Result 20260626 Dictionary Bank

status: `IN_PROGRESS`

## Current Summary

Implemented and submitted five fold0 dictionary bank variants on top of the selected recovered SRR route. This task is still running; no model selection has been made yet.

The five submitted routes are:

- `multiscale_dictionary`: adds pooled context retrieval in addition to full-resolution retrieval.
- `task_specific_dictionary`: separates anatomy, scar, and edema dictionary banks.
- `cross_modal_interaction_dictionary`: adds legal modality interaction experts that are masked off when modalities are missing.
- `anchor_guided_dictionary`: adds task-specific router bias toward LGE-scar, T2-edema, C0/anatomy, and shared prior anchors.
- `hierarchical_router_dictionary`: mixes feature-conditioned routing with a legal availability-subset prior.

## Commands And Verification So Far

- `git pull --ff-only`: pulled `prompts/tasks/20260626_next_goal.md` and subtasks.
- `./envs/env_CARE/bin/python -m py_compile ...`: passed for SRR model, runner, and reporter files.
- `./envs/env_CARE/bin/python -m unittest src.care_myocardium.tests.test_srr_losses src.care_myocardium.tests.test_srr_missingness src.care_myocardium.tests.test_srr_shapes`: `Ran 7 tests`, `OK`.
- One-step preflight gates for all five dictionary variants passed under `results/20260626_dict_bank/preflight/variants/`.
- `bash -n jobs/src/run_dict_bank_*.sh`: passed.
- `sbatch` submitted five `htzhulab` jobs: `56611484`, `56611485`, `56611486`, `56611487`, `56611488`.

## Queue Evidence At Submission

`squeue -j 56611484,56611485,56611486,56611487,56611488` showed all five jobs pending on `htzhulab`:

- `56611484` `SRRD1MultiF0`: `PD`, reason `Resources`.
- `56611485` `SRRD2TaskF0`: `PD`, reason `Priority`.
- `56611486` `SRRD4InterF0`: `PD`, reason `Priority`.
- `56611487` `SRRD5AnchorF0`: `PD`, reason `Priority`.
- `56611488` `SRRD6HierF0`: `PD`, reason `Priority`.

This follows the task and Slurm skill requirement to prefer `htzhulab`.

## Not Yet Done

- No formal metrics have completed.
- No `selection.md` has been written.
- No compactness task has started, because it depends on `selection.md:SELECT_*`.
- No validation upload, external upload, external data, external weights, fold expansion, or evaluator/label split change was performed.
