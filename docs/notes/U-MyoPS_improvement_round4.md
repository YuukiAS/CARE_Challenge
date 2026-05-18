# U-MyoPS round4: Stage2 prior/input ablation

Date: 2026-05-17

## Goal

Round4 tests one hypothesis: after the perfect Stage2 label oracle and the weak ScarCE2 gain, the bottleneck may be the Stage1 prior / aligned C0-T2-LGE inputs rather than label remap or export semantics.

This round stays on fold0, uses a single <=8h training job, and does not expand to folds 1-4.

## Code changes

- `code/U-MyoPS/build_stage2_task_from_stage1.py`
  - added `--input-variant {existing_full,lge_only_no_prior,oracle_prior_diagnostic}`;
  - `lge_only_no_prior` writes zero prior/C0/T2 channels and keeps LGE;
  - `oracle_prior_diagnostic` writes a GT-derived diagnostic support prior;
  - variant channels use the Dataset501 GT image as canonical geometry to avoid direction/spacing drift.
- `code/U-MyoPS/prepare_stage2_task.sh`
  - passes `UMYOPS_STAGE2_INPUT_VARIANT`;
  - added `UMYOPS_STAGE2_SKIP_BUILD` / `UMYOPS_STAGE2_SKIP_PREPROCESS` support for reusing completed raw/preprocessed tasks.
- `jobs/U-MyoPS/sbatch_export_eval_fold0.sh`
  - supports `UMYOPS_EXPORT_TASK` and `UMYOPS_EXPORT_TAG` for cache-isolated variant export/eval.
- `scripts/evaluation/report_umyops_stage2_input_qc.py`
  - reports focus-case prior/support Dice, pathology overlap, predicted-vs-GT scar voxels, channel nonzero counts, and channel statistics.

## Input QC artifacts

Existing full-input QC:

- `results/metrics/unified/U-MyoPS_stage2_input_qc/fold_0/input_qc.md`
- `results/metrics/unified/U-MyoPS_stage2_input_qc/fold_0/case_qc.csv`
- `results/metrics/unified/U-MyoPS_stage2_input_qc/fold_0/channel_qc.csv`

LGE-only/no-prior QC:

- `results/metrics/unified/U-MyoPS_stage2_input_qc_lge_only_no_prior/fold_0/input_qc.md`
- `results/metrics/unified/U-MyoPS_stage2_input_qc_lge_only_no_prior/fold_0/case_qc.csv`
- `results/metrics/unified/U-MyoPS_stage2_input_qc_lge_only_no_prior/fold_0/channel_qc.csv`

Oracle-prior diagnostic raw/QC, not trained:

- raw task: `third_party/U-MyoPS_myops/outputs/nnunet/raw/nnUNet_raw_data/Task913_CARE_UmyopsOraclePriorDiagnostic_fold0`
- `results/metrics/unified/U-MyoPS_stage2_input_qc_oracle_prior_diagnostic/fold_0/input_qc.md`

## Focus-case QC summary

Existing Stage1 prior on the worst scar cases is geometrically valid but has weak support/pathology overlap:

| case | complete | prior/support Dice | prior/pathology overlap | pred scar | GT scar |
| --- | ---: | ---: | ---: | ---: | ---: |
| Case2002 | 1 | 0.4389 | 1514 | 129 | 998 |
| Case2007 | 1 | 0.2850 | 1027 | 0 | 1303 |
| Case2020 | 1 | 0.3912 | 1081 | 4 | 561 |
| Case2031 | 1 | 0.3851 | 336 | 217 | 864 |
| Case2033 | 1 | 0.4014 | 700 | 306 | 1100 |
| Case3004 | 1 | 0.4599 | 2734 | 784 | 2326 |
| Case3012 | 1 | 0.4138 | 2953 | 293 | 2818 |
| Case3040 | 1 | 0.4665 | 286 | 0 | 2794 |
| Case3044 | 1 | 0.4733 | 1011 | 118 | 5781 |
| Case7005 | 0 | 0.4537 | 0 | 89 | 0 |
| Case8021 | 0 | 0.1457 | 33 | 24 | 60 |

For `lge_only_no_prior`, prior/C0/T2 are all zero in the focus-case QC and LGE remains non-empty. This verifies the controlled input ablation is isolated from the original Stage1 prior and aligned C0/T2 channels.

## Controlled ablation status

Built and preprocessed:

- `Task912_CARE_UmyopsLGEOnlyNoPrior_fold0`
- plans: `third_party/U-MyoPS_myops/outputs/nnunet/prepro/Task912_CARE_UmyopsLGEOnlyNoPrior_fold0/nnUNetPlansv2.1_plans_2D.pkl`
- splits: `third_party/U-MyoPS_myops/outputs/nnunet/prepro/Task912_CARE_UmyopsLGEOnlyNoPrior_fold0/splits_final.pkl`

Submitted one fold0 training job:

```bash
sbatch --parsable --export=ALL,UMYOPS_STAGE2_TASK=Task912_CARE_UmyopsLGEOnlyNoPrior,UMYOPS_STAGE2_TASK_NAME=Task912_CARE_UmyopsLGEOnlyNoPrior_fold0,UMYOPS_STAGE2_TRAINER=nnUNetTrainerPSNV8ScarCE2,UMYOPS_STAGE2_EPOCHS=80,FOLD=0,UMYOPS_STAGE2_WHICH_SUBNET=scar,UMYOPS_STAGE2_MAX_RUNTIME_SECONDS=27000,UMYOPS_STAGE2_PATIENCE=20,UMYOPS_STAGE2_EARLYSTOP_METRIC=scar,UMYOPS_STAGE2_AUTO_PREP=0 jobs/U-MyoPS/sbatch_stage2.sh
```

- Job ID: `51268767`
- Status: cancelled before running, no node assigned (`sacct`: `CANCELLED by 397557`, `Elapsed=00:00:00`)
- Replacement job ID: `51268833`
- Replacement status at report update: `PENDING (Resources)`
- Walltime request: `08:00:00`
- Runtime guard: `27000` seconds
- Folds: fold0 only

Expected isolated outputs after the job and export/eval complete:

- `results/predictions/U-MyoPS_round4_lge_only_no_prior/fold_0`
- `results/metrics/unified/U-MyoPS_round4_lge_only_no_prior/fold_0/evaluation_summary.json`
- `results/metrics/unified/U-MyoPS_round4_lge_only_no_prior/fold_0/grouped_diagnostics.md`

## Baseline comparison targets

| result | group | n | myops_edema | myops_scar |
| --- | --- | ---: | ---: | ---: |
| old PSNV8 final | all_cases | 44 | 0.6507 | 0.2823 |
| old PSNV8 final | scar_complete_modalities_only | 16 | 0.0393 | 0.0781 |
| round3 ScarCE2 final | all_cases | 44 | 0.6338 | 0.2932 |
| round3 ScarCE2 final | scar_complete_modalities_only | 16 | 0.0554 | 0.0767 |
| Stage2 label oracle | all_cases | 44 | 1.0000 | 1.0000 |
| nnU-Net Dataset501 5-fold | class mean | 5 folds | 0.4197 | 0.5592 |

## Final round4 interpretation

Task-specific `v2` export/eval for `Task912_CARE_UmyopsLGEOnlyNoPrior_fold0` completed in job `51354240`.

| result | group | n | myops_edema | myops_scar |
| --- | --- | ---: | ---: | ---: |
| round4 LGE-only/no-prior final | all_cases | 44 | 0.6726 | 0.5248 |
| round4 LGE-only/no-prior final | complete/T2-present | 16 | 0.1622 | 0.6524 |
| round3 ScarCE2 final | all_cases | 44 | 0.6338 | 0.2932 |
| nnU-Net Dataset501 5-fold | reference | 5 folds | 0.4197 | 0.5592 |

Conclusion:

- The prior/input-ablation hypothesis is supported. Original Stage1 prior/aligned C0/T2 channels were harming scar learning/export.
- U-MyoPS is now a plausible scar specialist: complete-modality scar exceeds nnU-Net, all-case scar is close but still below nnU-Net.
- Edema remains unreliable on T2-present cases, so U-MyoPS should not be used as the primary edema model.
- Next prepared step is export-only final-vs-best comparison via `jobs/U-MyoPS/sbatch_round5_export_compare.sh`.
