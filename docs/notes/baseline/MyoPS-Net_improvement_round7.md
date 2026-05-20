# MyoPS-Net Improvement Round7

Date: 2026-05-18

## Goal

Round7 tested export-only edema calibration while preserving the best known MyoPS-Net scar route. No training was run. All variants used fold0 only, protocol validation cases only, and checkpoint/config-specific output directories.

Primary labels:

- `class_4`: CARE `myops_edema`
- `class_5`: CARE `myops_scar`

Reference thresholds from the current nnU-Net baseline:

| metric | nnU-Net 5-fold mean |
| --- | ---: |
| myops_edema / class_4 | 0.4197 |
| myops_scar / class_5 | 0.5592 |

## Implementation

- Added `code/MyoPS-Net/apply_round7_edema_calibration.py`.
- Added `jobs/MyoPS-Net/sbatch_round7_edema_calibration.sh`.
- Updated `jobs/MyoPS-Net/README.md` with the round7 command and outputs.
- Extended `code/MyoPS-Net/export_val_predictions.py` with `--edema-softmax-dir` so a future probability threshold sweep can export T2-branch edema softmax maps without changing label export semantics.

The round7 label-level variants never use GT labels to modify predictions. Every variant reapplies round4 `combined_safe` `class_5` scar as the final scar route.

## Commands

Local CPU evaluation commands were run directly with `./env_CARE/bin/python`; no Slurm training job was submitted.

Reusable Slurm entrypoint:

```bash
sbatch jobs/MyoPS-Net/sbatch_round7_edema_calibration.sh
```

Common evaluation settings:

```bash
--fold-json data/benchmarks/protocol/splits_MyoPS.json
--fold 0
--foreground-classes 4,5
--skip-dice-if-gt-empty
```

## Outputs

| variant | prediction dir | metric dir |
| --- | --- | --- |
| `keep_round4_scar_round5_edema_complete` | `results/predictions/MyoPS-Net_round7_keep_round4_scar_round5_edema_complete/fold_0` | `results/metrics/unified/MyoPS-Net_round7_keep_round4_scar_round5_edema_complete/fold_0` |
| `edema_component_filter` | `results/predictions/MyoPS-Net_round7_edema_component_filter/fold_0` | `results/metrics/unified/MyoPS-Net_round7_edema_component_filter/fold_0` |
| `round5_edema_component_filter` | `results/predictions/MyoPS-Net_round7_round5_edema_component_filter/fold_0` | `results/metrics/unified/MyoPS-Net_round7_round5_edema_component_filter/fold_0` |
| `edema_support_limited` | `results/predictions/MyoPS-Net_round7_edema_support_limited/fold_0` | `results/metrics/unified/MyoPS-Net_round7_edema_support_limited/fold_0` |

Each metric dir contains `evaluation_summary.json`, `modality_group_metrics.md`, `calibration_summary.md`, and aggregate fold0 summaries.

## Overall Results

| variant | n | myops_edema / class_4 | myops_scar / class_5 | foreground_mean | result |
| --- | ---: | ---: | ---: | ---: | --- |
| round4 `combined_safe` reference | 44 | 0.3733 | 0.5048 | 0.4589 | best prior export-only route |
| `keep_round4_scar_round5_edema_complete` | 44 | 0.3403 | 0.5048 | 0.4529 | worsened edema |
| `edema_component_filter` | 44 | 0.3730 | 0.5048 | 0.4588 | no useful change |
| `round5_edema_component_filter` | 44 | 0.3437 | 0.5048 | 0.4535 | worsened edema |
| `edema_support_limited` | 44 | 0.3733 | 0.5048 | 0.4589 | identical to round4 |
| nnU-Net Dataset501 5-fold reference | 5 folds | 0.4197 | 0.5592 | NA | still stronger |

## Modality-Group Results

| variant | group | n | myops_edema / class_4 | myops_scar / class_5 | foreground_mean |
| --- | --- | ---: | ---: | ---: | ---: |
| `keep_round4_scar_round5_edema_complete` | C0+LGE | 4 | NA | 0.4068 | 0.4068 |
| `keep_round4_scar_round5_edema_complete` | C0+LGE+T2 | 16 | 0.3403 | 0.6258 | 0.4831 |
| `keep_round4_scar_round5_edema_complete` | LGE | 24 | NA | 0.4404 | 0.4404 |
| `edema_component_filter` | C0+LGE | 4 | NA | 0.4068 | 0.4068 |
| `edema_component_filter` | C0+LGE+T2 | 16 | 0.3730 | 0.6258 | 0.4994 |
| `edema_component_filter` | LGE | 24 | NA | 0.4404 | 0.4404 |
| `round5_edema_component_filter` | C0+LGE | 4 | NA | 0.4068 | 0.4068 |
| `round5_edema_component_filter` | C0+LGE+T2 | 16 | 0.3437 | 0.6258 | 0.4848 |
| `round5_edema_component_filter` | LGE | 24 | NA | 0.4404 | 0.4404 |
| `edema_support_limited` | C0+LGE | 4 | NA | 0.4068 | 0.4068 |
| `edema_support_limited` | C0+LGE+T2 | 16 | 0.3733 | 0.6258 | 0.4996 |
| `edema_support_limited` | LGE | 24 | NA | 0.4404 | 0.4404 |

## Changed Voxels

| variant | C0+LGE+T2 changed voxels | class_4 before -> after | class_4 added | class_4 removed | class_5 before -> after |
| --- | ---: | ---: | ---: | ---: | ---: |
| `keep_round4_scar_round5_edema_complete` | 31,150 | 23,166 -> 39,452 | 23,718 | 7,432 | 38,566 -> 38,566 |
| `edema_component_filter` | 354 | 23,166 -> 22,812 | 0 | 354 | 38,566 -> 38,566 |
| `round5_edema_component_filter` | 30,460 | 23,166 -> 38,762 | 23,319 | 7,723 | 38,566 -> 38,566 |
| `edema_support_limited` | 0 | 23,166 -> 23,166 | 0 | 0 | 38,566 -> 38,566 |

## Interpretation

- The best scar-preserving route remains round4 `combined_safe`.
- Replacing complete-case edema with fullmod/round5 edema hurt all-case and complete-case edema after preserving round4 scar.
- Small-component filtering removed only 354 edema voxels and slightly reduced edema Dice.
- Prediction-derived support limiting made no label changes because round4 `combined_safe` was already support-limited.
- No export-only variant improved edema beyond `0.39`; none approached the nnU-Net edema reference `0.4197`.

## Decision

MyoPS-Net should not be expanded to folds 1-4 from this line of postprocessing. It does not currently look realistic for MyoPS-Net alone to beat nnU-Net on both CARE primary MyoPS metrics through export-only calibration.

Recommended next step:

- For submission: keep nnU-Net as the primary MyoPS candidate, or use MyoPS-Net only as a diagnostic/ensemble component after validation packaging proves benefit.
- For MyoPS-Net research: stop postprocessing rounds here. The next legitimate fold0 attempt must be model-level and distinct, such as a T2-present edema expert, T2-aware edema head, modality-mask/dropout fusion, or robust missing-modality adaptation, with <=8h walltime.

Do not continue fullmod expert long training or threshold/postprocess stacking unless new softmax evidence shows a clear edema gain without sacrificing scar.
