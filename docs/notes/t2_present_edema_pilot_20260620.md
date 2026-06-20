# T2-present edema pilot

Date: 2026-06-19
Task: `prompts/tasks/20260620_t2_present_edema_pilot_task.md`

## Scope

This note records an isolated MyoPS T2-present edema mechanism diagnostic and feature-routing pilot. It does not modify baseline training entrypoints, does not create validation packages, does not upload anything, and does not treat no-T2 cases as strong edema-negative samples.

Main generated outputs:

- `scripts/experiments/t2_present_edema_pilot.py`
- `jobs/experiments/run_t2_present_edema_pilot.sh`
- `results/experiments/t2_present_edema_20260619_131434/`

The pilot used `envs/env_CARE/bin/python` and read raw MyoPS train/validation files plus Dataset501 label mapping.

No GPU training was started. The repo did not have a ready isolated complete-case edema expert entrypoint, and `env_CARE` did not have MONAI installed. Building a new nnU-Net complete-case task/training route would be a larger engineering change than this pilot allowed, so the task's feature/routing fallback path was used.

## Data mechanism

Current repository statistics match the expected missingness structure:

| split | modality group | cases |
| --- | --- | ---: |
| train | `C0+LGE+T2` | 80 |
| train | `C0+LGE` | 24 |
| train | `LGE-only` | 116 |
| raw validation | `C0+LGE+T2` | 15 |

Label mechanism by training modality group:

| group | cases | edema-positive | scar-positive | mean edema voxel fraction | median/mean T2 edema-vs-myo contrast |
| --- | ---: | ---: | ---: | ---: | ---: |
| `C0+LGE+T2` | 80 | 80 | 79 | 0.0040 | 0.9209 |
| `C0+LGE` | 24 | 0 | 18 | 0.0000 | NA |
| `LGE-only` | 116 | 0 | 115 | 0.0000 | NA |

Center-level pattern:

| center | cases | complete/T2-present | edema-positive | note |
| --- | ---: | ---: | ---: | --- |
| CenterB | 35 | 35 | 35 | complete group |
| CenterC | 45 | 45 | 45 | complete group |
| CenterA | 81 | 0 | 0 | LGE-only; scar-positive in 81/81 |
| CenterH | 35 | 0 | 0 | LGE-only; scar-positive in 34/35 |
| CenterE/F/G | 24 total | 0 | 0 | C0+LGE; scar-positive in 18/24 |

Interpretation: no-T2 cases should remain excluded from dense edema-negative supervision. They are informative for scar/anatomy/missingness analysis, but the current labels do not support treating them as true edema negatives.

## Feature-routing pilot

The pilot evaluated a diagnostic rule on all 80 complete cases:

- robust-z T2 intensity threshold,
- GT myocardium/scar support prior dilated by 2 iterations,
- connected-component filter at 50 mm3,
- threshold selected on fold0 complete train cases.

This is an oracle-prior feasibility baseline, not a submission-ready model. It tests whether the complete-case T2 signal can support edema localization under a simple routing rule.

Selected config:

| threshold | prior iterations | min component mm3 | selection cases | mean Dice | mean precision | mean recall | mean components |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 | 2 | 50 | 64 | 0.3223 | 0.3331 | 0.4225 | 15.0156 |

Metrics:

| split | cases | Dice | precision | recall | HD | HD95 | components |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fold0 complete train | 64 | 0.3223 | 0.3331 | 0.4225 | 36.0893 | 19.7387 | 15.0156 |
| fold0 complete val | 16 | 0.2910 | 0.2982 | 0.4643 | 38.6553 | 24.0819 | 15.3125 |
| all complete | 80 | 0.3160 | 0.3261 | 0.4308 | 36.6025 | 20.6073 | 15.0750 |
| all complete CenterB | 35 | 0.3711 | 0.4480 | 0.3639 | 29.2543 | 14.9910 | 11.9143 |
| all complete CenterC | 45 | 0.2732 | 0.2313 | 0.4829 | 42.3178 | 24.9755 | 17.5333 |

## Decision

The data mechanism strongly supports a T2-aware/expert/routing direction for `myops_edema`: all 80 complete cases are edema-positive, all 140 no-T2 cases have no edema label, and validation raw input is 15/15 complete.

The simple T2 threshold + oracle prior baseline is not strong enough as a model route. Fold0 complete validation Dice is only 0.2910 and HD95 is 24.0819, with many predicted components. This argues against promoting a threshold/filter rule directly, but it does support using T2-present complete cases as the supervised edema signal for a more formal expert.

Recommended next step: a new task should run a baseline-preserving, complete-case T2 edema expert or residual head initialized from the existing nnU-Net representation, with no-T2 cases excluded from dense class-4 negative supervision. Missingness mask, late fusion, and ModDrop/HeMIS-style designs remain relevant. CAA-Seg/AWSnet can stay as bounded reference checks, not the immediate execution path.
