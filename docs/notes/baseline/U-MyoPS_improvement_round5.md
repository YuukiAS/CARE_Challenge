# U-MyoPS round5: final-vs-best checkpoint and scar-specialist decision

Date: 2026-05-17

## Goal

Round5 is export/evaluation only. It compares `model_final_checkpoint` and `model_best` for the LGE-only/no-prior Stage2 task:

- task: `Task912_CARE_UmyopsLGEOnlyNoPrior_fold0`
- trainer: `nnUNetTrainerPSNV8ScarCE2`
- fold: `0`
- checkpoint candidates: `model_final_checkpoint`, `model_best`

No Stage2 training was started in this round.

## Execution

Command:

```bash
sbatch jobs/U-MyoPS/sbatch_round5_export_compare.sh
```

Slurm job:

- job ID: `51354910`
- node: `g1807htzh01.ll.unc.edu`
- log: `logs/U-MyoPS_r5_export_51354910_20260517_233346.log`
- status: completed; both checkpoint exports wrote evaluation outputs.

Checkpoint files for the Task912 run exist:

- `third_party/U-MyoPS_myops/outputs/nnunet/output/nnUNet/2d/Task912_CARE_UmyopsLGEOnlyNoPrior_fold0/nnUNetTrainerPSNV8ScarCE2__nnUNetPlansv2.1/fold_0/model_best.model`
- `third_party/U-MyoPS_myops/outputs/nnunet/output/nnUNet/2d/Task912_CARE_UmyopsLGEOnlyNoPrior_fold0/nnUNetTrainerPSNV8ScarCE2__nnUNetPlansv2.1/fold_0/model_final_checkpoint.model`

## Cache isolation

Round5 used checkpoint- and task-specific prediction/metric directories:

- final raw fallback cache: `results/predictions/_tmp/U-MyoPS/fold_0_Task912_CARE_UmyopsLGEOnlyNoPrior_fold0_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/validation_raw`
- best raw fallback cache: `results/predictions/_tmp/U-MyoPS/fold_0_Task912_CARE_UmyopsLGEOnlyNoPrior_fold0_nnUNetTrainerPSNV8ScarCE2_model_best/validation_raw`
- final metrics: `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_final_checkpoint/fold_0`
- best metrics: `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0`

The final checkpoint export reused the existing Task912/task-specific raw fallback cache from the earlier round4 `v2` export. The best checkpoint export ran a new fallback inference into its own `model_best` cache. No round5 output reuses the old `U-MyoPS_round4_*_v2` metric directory.

## Results

nnU-Net MyoPS 5-fold reference from `results/metrics/nnUNet.md`:

| metric | nnU-Net |
| --- | ---: |
| `myops_edema` / class_4 | 0.4197 |
| `myops_scar` / class_5 | 0.5592 |

Round5 grouped metrics:

| checkpoint | group | n | myops_edema | myops_scar |
| --- | --- | ---: | ---: | ---: |
| `model_final_checkpoint` | all_cases | 44 | 0.6726 | 0.5248 |
| `model_final_checkpoint` | scar_gt_positive_only | 43 | 0.6650 | 0.5370 |
| `model_final_checkpoint` | complete/T2-present | 16 | 0.1622 | 0.6524 |
| `model_best` | all_cases | 44 | 0.6518 | 0.5307 |
| `model_best` | scar_gt_positive_only | 43 | 0.6437 | 0.5430 |
| `model_best` | complete/T2-present | 16 | 0.1675 | 0.6463 |

Metric files:

- `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_final_checkpoint/fold_0/evaluation_summary.json`
- `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_final_checkpoint/fold_0/grouped_diagnostics.md`
- `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0/evaluation_summary.json`
- `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0/grouped_diagnostics.md`

## Interpretation

`model_best` is the better all-case scar checkpoint, but the gain is small:

- all-case scar: `0.5248 -> 0.5307`
- scar-positive-only: `0.5370 -> 0.5430`
- complete/T2-present scar: `0.6524 -> 0.6463`

This does not push U-MyoPS over the nnU-Net all-case scar reference (`0.5592`). It does confirm the round4 conclusion: LGE-only/no-prior U-MyoPS is a plausible scar specialist on complete-modality cases, where scar remains above `0.64`, but it is not proven better than nnU-Net across all fold0 validation cases.

Edema should not be claimed as solved. The all-case edema value is inflated by empty-GT cases. On the edema-positive/T2-present subset, `model_best` reaches only `0.1675`, far below the nnU-Net all-case edema reference and not a useful edema branch.

## Decision

Continue U-MyoPS only as a scar-specialist candidate branch, using `model_best` as the preferred checkpoint for Task912. Do not expand U-MyoPS alone to folds 1-4 yet, and do not use it as the edema model.

The next useful step is hybrid validation packaging/routing:

- MyoPS scar candidate: U-MyoPS Task912 `model_best`.
- MyoPS edema branch: keep nnU-Net or a stronger MyoPS-Net edema candidate.
- Routing policy: only use U-MyoPS scar where local validation-like conditions support it, especially complete-modality cases; otherwise keep nnU-Net scar until a hybrid comparison proves an all-case gain.

If local validation packaging cannot route scar and edema independently, the conservative default remains nnU-Net for MyoPS submission.
