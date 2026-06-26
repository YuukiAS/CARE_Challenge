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

## Queue Evidence After Cine Temporal Push

At `2026-06-26 04:17 EDT`, the five dictionary jobs were still pending:

| job | variant | state | reason | estimated start |
| --- | --- | --- | --- | --- |
| `56611484` | `multiscale_dictionary` | `PD` | `Resources` | `2026-06-26T16:36:43` |
| `56611485` | `task_specific_dictionary` | `PD` | `Priority` | `2026-06-26T21:15:24` |
| `56611486` | `cross_modal_interaction_dictionary` | `PD` | `Priority` | `2026-06-27T00:10:00` |
| `56611487` | `anchor_guided_dictionary` | `PD` | `Priority` | `2026-06-27T04:50:00` |
| `56611488` | `hierarchical_router_dictionary` | `PD` | `Priority` | `2026-06-27T07:40:00` |

Fallback queues were checked before duplicating or moving work. `a100-gpu` had a deep pending queue with many long gridsearch jobs. `volta-gpu` also had many pending and running long jobs. There was no clear evidence that fallback would complete these five 7.5h formal jobs earlier, and the task's allowed 5 parallel GPU jobs were already submitted. The current action is to keep the `htzhulab` submissions live and monitor.

## Queue Evidence After First Required Wait

After one complete 2-hour wait cycle, at `2026-06-26 06:23 EDT`, `56611484` had started:

| job | variant | state | elapsed | node/reason |
| --- | --- | --- | --- | --- |
| `56611484` | `multiscale_dictionary` | `R` | `01:21:50` | `g1807htzh01` |
| `56611485` | `task_specific_dictionary` | `PD` | `0:00` | `Resources` |
| `56611486` | `cross_modal_interaction_dictionary` | `PD` | `0:00` | `Priority` |
| `56611487` | `anchor_guided_dictionary` | `PD` | `0:00` | `Priority` |
| `56611488` | `hierarchical_router_dictionary` | `PD` | `0:00` | `Priority` |

`scontrol show job 56611484` reported `JobState=RUNNING`, `NodeList=g1807htzh01`, `AllocTRES=...gres/gpu:nvidia_h100_nvl=1`, and `EndTime=2026-06-26T12:31:51`. The live log is `logs/SRRD1MultiF0_56611484_20260626_050152.log`. A checkpoint file exists under the ignored formal output path, confirming the job entered training/checkpoint logic; no formal metrics have completed yet.

## Queue Evidence After Third Wait

At `2026-06-26 10:27 EDT`, two variants were running:

| job | variant | state | elapsed | node/reason |
| --- | --- | --- | --- | --- |
| `56611484` | `multiscale_dictionary` | `R` | `05:25:56` | `g1807htzh01` |
| `56611485` | `task_specific_dictionary` | `R` | `00:48:39` | `g180702` |
| `56611486` | `cross_modal_interaction_dictionary` | `PD` | `0:00` | `Resources` |
| `56611487` | `anchor_guided_dictionary` | `PD` | `0:00` | `Priority` |
| `56611488` | `hierarchical_router_dictionary` | `PD` | `0:00` | `Priority` |

D1 and D2 both have live Python training processes and ignored checkpoints under their variant directories. D2's live log is `logs/SRRD2TaskF0_56611485_20260626_093909.log`. Current start estimates for the remaining pending variants are:

- `56611486` D4 `cross_modal_interaction_dictionary`: `2026-06-26T12:31:51`
- `56611487` D5 `anchor_guided_dictionary`: `2026-06-26T17:09:08`
- `56611488` D6 `hierarchical_router_dictionary`: `2026-06-26T20:05:00`

## Not Yet Done

- No formal metrics have completed.
- No `selection.md` has been written.
- No compactness task has started, because it depends on `selection.md:SELECT_*`.
- No validation upload, external upload, external data, external weights, fold expansion, or evaluator/label split change was performed.
