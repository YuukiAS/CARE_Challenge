# MyoPS-Net Improvement Round8

Date: 2026-05-19

## Goal

Round8 was the final fold0 model-level MyoPS-Net exit-gate attempt. It combined the refreshed CARE2026 leaderboard with local fold0 Dice/HD diagnostics, then trained a short T2-aware edema/scar expert with HD/boundary-aware and anatomy ROI losses.

This was not another postprocess-only round.

## Leaderboard Context

Refreshed with:

```bash
python scripts/leaderboard/fetch_care2026_scores.py
```

Latest hosted OrganAgent nnU-Net MyoPS branch:

| hosted metric | OrganAgent Dice | HD | rank |
| --- | ---: | ---: | ---: |
| `myops_scar` | 0.5969 | 16.2536 | 4/5 |
| `myops_edema` | 0.6496 | 22.0125 | 4/5 |

Local nnU-Net fold0 pathology reference:

| metric | Dice | HD | HD95 |
| --- | ---: | ---: | ---: |
| myops_edema / class_4 | 0.3944 | 10.7669 | 7.2769 |
| myops_scar / class_5 | 0.5602 | 25.9706 | 13.6005 |

Local nnU-Net 5-fold reference remains edema `0.4197`, scar `0.5592`.

## Error Profile

Output:

- `results/diagnostics/baseline_paper_models/MyoPS-Net/round08_hd_profile/MyoPS-Net_round8_nnunet_vs_myopsnet_hd_profile.csv`
- `results/diagnostics/baseline_paper_models/MyoPS-Net/round08_hd_profile/MyoPS-Net_round8_nnunet_vs_myopsnet_hd_profile.md`

Summary:

| model | class | n eval | mean Dice | mean HD | mean HD95 | mean components | small comps | remote comps | mean pred/GT volume ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MyoPS-Net round4 combined_safe | edema | 16 | 0.3733 | 29.1300 | 18.9050 | 3.7273 | 102 | 4 | 1.3972 |
| MyoPS-Net round4 combined_safe | scar | 44 | 0.5048 | 32.6475 | 21.2635 | 1.2955 | 4 | 1 | 1.2583 |
| nnU-Net fold0 | edema | 16 | 0.3944 | 29.6089 | 20.0115 | 3.3182 | 109 | 1 | 1.6121 |
| nnU-Net fold0 | scar | 44 | 0.5602 | 25.9706 | 13.6005 | 4.6818 | 144 | 2 | 1.1343 |

Interpretation:

- nnU-Net scar has better Dice and substantially better HD/HD95 than MyoPS-Net round4 despite more small components.
- MyoPS-Net round4 edema is slightly cleaner by HD than nnU-Net in the diagnostic table, but Dice is still lower and edema remains below both local and hosted nnU-Net references.
- The hosted leaderboard confirms Dice/HD mismatch matters: OrganAgent has moderate Dice but acceptable HD relative to some peers; however it is still far behind rank1 on both hosted MyoPS Dice and HD.

## Implementation

New/updated code:

- `code/MyoPS-Net/report_round8_hd_profile.py`: per-case Dice/HD/HD95 and component/outlier diagnostics for nnU-Net vs MyoPS-Net.
- `third_party/MyoPS-Net/criterion/loss.py`: added optional round8 loss terms:
  - binary Focal-Tversky for scar/edema;
  - boundary-gradient L1 loss as a simple HD surrogate;
  - myocardium ROI penalty for pathology probability outside GT myocardium/pathology support during training.
- `jobs/MyoPS-Net/sbatch_round8_t2aware_hd_expert.sh`: <=8h fold0 complete-case expert training, raw export/eval, and round4-scar-preserving hybrid eval.
- `jobs/MyoPS-Net/README.md`: round8 command, outputs, and exit gate.

Training design:

- Train split: only complete C0+LGE+T2 cases, `64` cases.
- Validation split: full fold0 protocol validation, `44` cases.
- No modality dropout; modality masks remain explicit through mask-gated loss.
- Pathology sampler enabled with stronger edema weighting.
- Best checkpoint selected by weighted pathology Dice, scar:edema = `1:2`.
- Slurm job: `51529189`, log `logs/MyoPS-Net_Round8HD_51529189_20260519_083832.log`.

## Training Stop

| item | value |
| --- | --- |
| stop reason | `early_stop_patience` |
| elapsed | 777.3 sec |
| requested epochs | 80 |
| actual best epoch | 12 |
| best 2D scar Dice | 0.0996 |
| best 2D edema Dice | 0.0566 |
| best 2D weighted metric | 0.0709 |

The 2D training validation signal was weak throughout, so the final 3D export was expected to be poor.

## Round8 Outputs

| variant | prediction dir | metric dir |
| --- | --- | --- |
| raw expert | `results/predictions/MyoPS-Net_round8_t2aware_hd_raw/fold_0` | `results/metrics/unified/MyoPS-Net_round8_t2aware_hd_raw/fold_0` |
| round4-scar hybrid | `results/predictions/MyoPS-Net_round8_t2aware_hd_round4scar_hybrid/fold_0` | `results/metrics/unified/MyoPS-Net_round8_t2aware_hd_round4scar_hybrid/fold_0` |
| edema softmax | `results/predictions/MyoPS-Net_round8_t2aware_hd_edema_softmax/fold_0` | diagnostic probability maps only |

## Overall Dice and HD

| variant | n | edema Dice | scar Dice | edema HD | scar HD | edema HD95 | scar HD95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| nnU-Net fold0 | 44 | 0.3944 | 0.5602 | 10.7669 | 25.9706 | 7.2769 | 13.6005 |
| MyoPS-Net round4 combined_safe | 44 | 0.3733 | 0.5048 | 29.1300 | 32.6475 | 18.9050 | 21.2635 |
| round8 raw expert | 44 | 0.2779 | 0.2426 | 17.2042 | 48.7825 | 10.0216 | 23.3077 |
| round8 round4-scar hybrid | 44 | 0.3293 | 0.5048 | 15.6402 | 32.6475 | 9.1328 | 21.2635 |

## Modality-Group Dice

| variant | group | n | edema | scar | foreground_mean |
| --- | --- | ---: | ---: | ---: | ---: |
| nnU-Net fold0 | C0+LGE | 4 | NA | 0.3778 | 0.3778 |
| nnU-Net fold0 | C0+LGE+T2 | 16 | 0.3944 | 0.6933 | 0.5439 |
| nnU-Net fold0 | LGE | 24 | NA | 0.5018 | 0.5018 |
| round8 raw expert | C0+LGE | 4 | 0.0000 | 0.2141 | 0.1070 |
| round8 raw expert | C0+LGE+T2 | 16 | 0.3474 | 0.6135 | 0.4805 |
| round8 raw expert | LGE | 24 | NA | 0.0000 | 0.0000 |
| round8 round4-scar hybrid | C0+LGE | 4 | NA | 0.4068 | 0.4068 |
| round8 round4-scar hybrid | C0+LGE+T2 | 16 | 0.3293 | 0.6258 | 0.4776 |
| round8 round4-scar hybrid | LGE | 24 | NA | 0.4404 | 0.4404 |

## Exit Gate

Prompt8 continuation gate:

- all-case scar `>=0.535` and edema `>=0.40`, or
- complete-case edema/scar clearly exceeds nnU-Net fold0 without HD/outlier regression.

Result:

- Raw expert fails all-case: edema `0.2779`, scar `0.2426`.
- Hybrid fails all-case: edema `0.3293`, scar `0.5048`.
- Raw expert also fails complete cases vs nnU-Net: edema `0.3474 < 0.3944`, scar `0.6135 < 0.6933`.
- Hybrid complete cases are lower still for edema: `0.3293`.

## Decision

MyoPS-Net should stop as a baseline-improvement mainline before round9/10. It has now failed:

- export-only postprocess calibration;
- fullmod expert routing;
- T2-aware complete-case expert with lesion-balanced, boundary-aware, and ROI-aware losses.

The model does not look likely to surpass nnU-Net on both CARE MyoPS hosted metrics without replacing the core architecture.

Recommended migration:

- Keep nnU-Net as the MyoPS submission baseline.
- Move new model work into `src/`, not more third-party MyoPS-Net patching.
- Prioritize a CAA-Seg/SSA-style multi-sequence alignment and anatomy/pathology cascade with a nnU-Net/MedNeXt-style pathology head.
- Carry forward the useful pieces from this round: component/HD diagnostics, explicit modality metadata, T2-present subgroup reporting, and ROI/boundary-aware loss terms.

Do not expand MyoPS-Net folds 1-4.
