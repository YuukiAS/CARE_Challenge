# Lane A Round04 Active Fold0 Short Train Execution

Plan metadata:
- Type: active round execution
- Lane: Lane A, MyoPS scar/edema
- Round scope: Round04 fold0 short train
- Status: completed, gate failed; do not advance to longer fold0 train
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: `docs/plans/laneA_round03_next_edema_trainable_smoke_execution.md`
- Function: execute one bounded fold0 short train for `edema_focal_tversky + no_t2_edema_loss_downweighting`
- Do not: train folds 1-4, run a full schedule, create validation zip, upload, download weights, pull external repos, change label semantics, overwrite nnU-Net501 baseline cache
- Rule exception: user suggested `laneA_round04_active_fold0_short_train.md`, but `care_myocardium_plan_registry_rules.md` requires active execution filenames to include `_execution.md`; this file uses the compliant name.

## Execution Scope

Candidate:

- base model path: existing local nnU-Net501 fold0 `checkpoint_best.pth`, used only as a local initialization checkpoint.
- candidate experiment name: `laneA_edema_focal_tversky_t2down_fold0_short`.
- candidate output root: `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/laneA_edema_focal_tversky_t2down_fold0_short__nnUNetPlans__3d_fullres/fold_0/`.
- diagnostic output root: `results/diagnostics/care_myocardium/laneA_myops/round04_fold0_short_train/`.

Training cap:

- fold: `0` only.
- epochs: `20`.
- train iterations per epoch: `25`.
- validation iterations per epoch: `10`.
- initial LR: `0.0001`.
- auxiliary loss: class_4 edema focal Tversky, `aux_weight=0.25`.
- no-T2 class_4 auxiliary weight: `0.25`.
- T2-present class_4 auxiliary weight: `1.0`.

The class_4 auxiliary term is added to the unchanged nnU-Net multiclass base loss. Class_5 scar remains covered by the base loss and is evaluated as a guardrail.

## Command

```bash
sbatch jobs/nnUNet/laneA_round04_fold0_short_train.sh
```

Submitted job:

```text
51648053
```

Retry after pre-source logging fix:

```text
51648166
```

Retry with Slurm stdout/stderr enabled for startup diagnostics:

```text
51648270
```

Retry after explicit Slurm working directory fix:

```text
51648597
```

Retry after forcing `CARE_ROOT` to the repository root:

```text
51648698
```

Retry after hardcoding Slurm `CARE_ROOT=/overflow/htzhu/CARE`:

```text
51649051
```

## Required Outputs

- `results/diagnostics/care_myocardium/laneA_myops/round04_fold0_short_train/train_config.yaml`
- `results/diagnostics/care_myocardium/laneA_myops/round04_fold0_short_train/train_command.txt`
- `results/diagnostics/care_myocardium/laneA_myops/round04_fold0_short_train/fold0_short_train_metrics.csv`
- `results/diagnostics/care_myocardium/laneA_myops/round04_fold0_short_train/fold0_short_train_summary.md`
- `results/diagnostics/care_myocardium/laneA_myops/round04_fold0_short_train/baseline_vs_candidate_by_subset.csv`
- `results/diagnostics/care_myocardium/laneA_myops/round04_fold0_short_train/case_level_failure_flags.csv`
- `results/diagnostics/care_myocardium/laneA_myops/round04_fold0_short_train/round4_laneA_decision.md`

## Gate

Pass only if candidate shows a clear positive signal on T2-present GT-positive edema or CenterC complete-case edema, without HD95/component/remote-FP regression, scar class_5 regression, or no-T2 empty-GT false positives.

## Execution Result

Completed run:

- Slurm job: `51649051`.
- Training completed 20 bounded epochs and exported 44/44 fold0 validation predictions.
- The Slurm job exited failed because the chained evaluator initially missed the `scar_gt_positive` CSV field. The evaluator was fixed and rerun locally against the completed candidate predictions.
- Candidate prediction directory: `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/laneA_edema_focal_tversky_t2down_fold0_short__nnUNetPlans__3d_fullres/fold_0/validation`.
- Diagnostic output directory: `results/diagnostics/care_myocardium/laneA_myops/round04_fold0_short_train/`.

Final gate:

```text
fail_stop_no_longer_train
```

Key subset deltas from `baseline_vs_candidate_by_subset.csv`:

| subset | edema Dice delta | edema HD95 improvement delta | edema component improvement delta | edema remote FP improvement delta | scar Dice delta | scar HD95 improvement delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all_case | -0.1252 | -2.1090 | -1.3864 | -2.0000 | -0.0037 | -1.3937 |
| T2-present GT-positive | 0.0094 | -1.1069 | 1.3750 | -0.3125 | -0.0149 | -1.4646 |
| CenterC | 0.0068 | 0.5097 | 2.2222 | -0.3333 | -0.0161 | -0.9040 |
| no-T2 empty-GT | NA | 0.0000 | -2.9643 | -2.9643 | 0.0027 | -1.3501 |

Interpretation:

- Although T2-present and CenterC edema Dice show small positive deltas, the candidate fails because HD95/remote-FP behavior regresses on T2-present cases and no-T2 empty-GT cases gain new edema false positives.
- Scar guardrail is not clean: all-case scar HD95 worsens by `1.3937`, and multiple case-level scar HD95 guardrail flags are present.
- Do not extend this candidate to longer fold0 training, fold1-4, or validation submission.
