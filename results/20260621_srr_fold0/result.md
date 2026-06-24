# Result 20260621 SRR Fold0

status: `REVISE_ROUTING`

## Execution Summary

Executed `prompts/tasks/20260621_srr_fold0.md` after `results/20260621_srr_spec/result.md` reached `GO_FOLD0`.

Two fold0 variants were implemented and run on `htzhulab` with task-scoped, variant-scoped, fold-scoped, checkpoint/config-scoped outputs:

- `conditional_dualhead_control`: availability-aware late fusion with separate anatomy/scar/edema heads, no SRR gate.
- `srr_minimal`: Result4 shared/private selective representation retrieval with the same heads and T2-masked edema supervision.

No network, external upload, validation submission, upload-ready package, external data, external weights, folds 1-4, third-party baseline patching, or no-T2 edema hard-negative supervision was used.

## Gate Decision

`REVISE_ROUTING`

SRR showed positive local fold0 signal over the conditional control on the primary comparison deltas, but retrieval routing was not clean enough to advance to ablation:

- edema GT-positive Dice delta B-A: `+0.0323`
- scar all-cases Dice delta B-A: `+0.0250`
- edema GT-positive HD95 delta B-A: `-15.4582`
- routing caveat: logged row-level expert weights reached `1.0000`; scar routing was strongly concentrated on expert1, mean `0.9431`

Per task rules, because the decision is not `GO_ABLATION`, I did not continue to `prompts/tasks/20260621_srr_ablation.md`.

## Slurm Jobs

Initial jobs:

| job | variant | state | elapsed | role |
| --- | --- | --- | --- | --- |
| `55720659` | `conditional_dualhead_control` | `COMPLETED` | `00:12:20` | short wiring evidence only |
| `55720658` | `srr_minimal` | `COMPLETED` | `00:19:09` | short wiring evidence only |

Corrected formal jobs:

| job | variant | state | elapsed | GPU | stop reason |
| --- | --- | --- | --- | --- | --- |
| `55723114` | `conditional_dualhead_control` | `COMPLETED` | `04:06:08` | `gres/gpu:nvidia_h100_nvl=1` | `max_steps` |
| `55723115` | `srr_minimal` | `COMPLETED` | `04:31:04` | `gres/gpu:nvidia_h100_nvl=1` | `max_runtime_seconds` |

Logs:

- `logs/SRRCondF0_55720659_20260621_191600.log`
- `logs/SRRMinF0_55720658_20260621_191600.log`
- `logs/SRRCondF0_55723114_20260621_193914.log`
- `logs/SRRMinF0_55723115_20260621_193914.log`

## Training Summary

| variant | train cases | val cases | complete train cases | best step | elapsed seconds | checkpoint |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `conditional_dualhead_control` | 176 | 44 | 64 | 450000 | 14733.0592 | `results/20260621_srr_fold0/variants/conditional_dualhead_control/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt` |
| `srr_minimal` | 176 | 44 | 64 | 105000 | 16229.6263 | `results/20260621_srr_fold0/variants/srr_minimal/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt` |

Each corrected variant exported `44` fold0 validation predictions under:

- `results/20260621_srr_fold0/variants/conditional_dualhead_control/predictions/fold_0/checkpoint_best/`
- `results/20260621_srr_fold0/variants/srr_minimal/predictions/fold_0/checkpoint_best/`

## Key Metrics

| variant | class | group | n | Dice | HD | HD95 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `conditional_dualhead_control` | `myops_edema` | all cases | 44 | 0.2901 | 104.8699 | 81.8594 |
| `conditional_dualhead_control` | `myops_edema` | GT-positive | 16 | 0.1103 | 176.9680 | 138.1377 |
| `conditional_dualhead_control` | `myops_scar` | all cases | 44 | 0.0581 | 169.7511 | 113.4492 |
| `srr_minimal` | `myops_edema` | all cases | 44 | 0.5973 | 69.9282 | 49.0718 |
| `srr_minimal` | `myops_edema` | GT-positive | 16 | 0.1426 | 174.8206 | 122.6796 |
| `srr_minimal` | `myops_scar` | all cases | 44 | 0.0832 | 168.3660 | 120.8677 |

Full metrics are in:

- `results/20260621_srr_fold0/metrics_summary.md`
- `results/20260621_srr_fold0/subgroup_metrics.csv`
- `results/20260621_srr_fold0/component_hd_by_case.csv`

## Retrieval Diagnostics

`results/20260621_srr_fold0/retrieval_usage.md` reports:

- anatomy: expert means `expert0=0.5130`, `expert1=0.0012`, `expert2=0.0004`, `expert3=0.4854`; max row `1.0000`
- scar: expert means `expert0=0.0006`, `expert1=0.9431`, `expert2=0.0558`, `expert3=0.0005`; max row `1.0000`
- edema: expert means `expert0=0.4126`, `expert1=0.2996`, `expert2=0.2864`, `expert3=0.0015`; max row `1.0000`

This supports `REVISE_ROUTING`: SRR is not a stop, but the router/regularizer needs revision before the ablation task.

## Commands

- `./envs/env_CARE/bin/python scripts/training/run_srr_myops_fold0.py ... --skip-export` for both variants.
- `bash -n jobs/src/run_srr_myops_fold0_conditional.sh`
- `bash -n jobs/src/run_srr_myops_fold0_srr.sh`
- `sbatch jobs/src/run_srr_myops_fold0_conditional.sh`
- `sbatch jobs/src/run_srr_myops_fold0_srr.sh`
- `squeue -j 55723114,55723115 -o '%.18i %.9P %.30j %.8u %.2t %.10M %.10l %.20R'`
- `sacct -j 55723114,55723115 --format=JobID,JobName,State,ExitCode,Elapsed,AllocTRES%50 -P`
- `./envs/env_CARE/bin/python -m py_compile scripts/evaluation/report_srr_fold0.py`
- `./envs/env_CARE/bin/python scripts/evaluation/report_srr_fold0.py --root results/20260621_srr_fold0`

## Code And Artifact Paths

Code added or updated:

- `src/care_myocardium/models/srr_myops.py`
- `src/care_myocardium/losses/srr_losses.py`
- `scripts/training/run_srr_myops_fold0.py`
- `scripts/evaluation/report_srr_fold0.py`
- `jobs/src/run_srr_myops_fold0_conditional.sh`
- `jobs/src/run_srr_myops_fold0_srr.sh`
- `jobs/src/run_srr_myops_fold0_conditional_long.sh` (backup wrapper, not submitted)
- `jobs/src/run_srr_myops_fold0_srr_long.sh` (backup wrapper, not submitted)

Required task artifacts:

- `results/20260621_srr_fold0/result.md`
- `results/20260621_srr_fold0/MANIFEST.md`
- `results/20260621_srr_fold0/decision.md`
- `results/20260621_srr_fold0/setup.md`
- `results/20260621_srr_fold0/metrics_summary.md`
- `results/20260621_srr_fold0/subgroup_metrics.csv`
- `results/20260621_srr_fold0/component_hd_by_case.csv`
- `results/20260621_srr_fold0/retrieval_usage.csv`
- `results/20260621_srr_fold0/retrieval_usage.md`

## Caveats

- Metrics are local fold0 compact-label diagnostics, not hosted validation metrics.
- The first two jobs were too short for formal evidence and are retained only as wiring evidence.
- SRR all-case edema is inflated by no-T2 empty-GT stability; the gate decision uses GT-positive/T2-present edema and scar sanity, not empty-GT gain alone.
- The decision prevents ablation/expansion until routing is revised.
- Backup long-run wrappers under `jobs/src/*_long.sh` were not submitted and did not contribute metrics.
