# U-MyoPS iteration log

## 2026-05-17 round2 fold0 diagnostics + scar-positive Stage2 short run

### 目标

- 遵守单 job 不超过 8 小时、先 fold0、小步迭代。
- 不扩展 fold1-4。
- 本轮只验证一个主要假设：Stage2 scar 召回/采样和 scar-weighted checkpoint selection 是否能修复 fold0 scar false negative。

### 诊断

- 读取 `prompts/U-MyoPS/prompt2_improve_umyops.md`、`prompts/U-MyoPS/U-MyoPS_myops_scar_diagnosis.md`、`prompts/U-MyoPS/improvement_suggestion.md`、`prompts/Baseline_report.md`、`TODO.md`、Ding 2023 PDF 元信息与文本摘录。
- 对已有 `model_best` / `model_final_checkpoint` 生成分组指标：
  - `results/metrics/unified/U-MyoPS_model_best/fold_0/grouped_diagnostics.md`
  - `results/metrics/unified/U-MyoPS_model_final_checkpoint/fold_0/grouped_diagnostics.md`
- 生成 fold0 aggregate：
  - `results/metrics/unified/U-MyoPS_model_best/aggregate.json`
  - `results/metrics/unified/U-MyoPS_model_best/aggregate.md`
  - `results/metrics/unified/U-MyoPS_model_final_checkpoint/aggregate.json`
  - `results/metrics/unified/U-MyoPS_model_final_checkpoint/aggregate.md`

### 当前结果

| checkpoint | group | n | myops_edema | myops_scar |
| --- | --- | ---: | ---: | ---: |
| model_final_checkpoint | all_cases | 44 | 0.6507 | 0.2823 |
| model_final_checkpoint | edema_gt_positive_only | 16 | 0.0393 | 0.0781 |
| model_final_checkpoint | edema_t2_present_only | 16 | 0.0393 | 0.0781 |
| model_final_checkpoint | scar_gt_positive_only | 43 | 0.6425 | 0.2888 |
| model_final_checkpoint | scar_complete_modalities_only | 16 | 0.0393 | 0.0781 |
| model_best | all_cases | 44 | 0.6517 | 0.2800 |
| model_best | edema_gt_positive_only | 16 | 0.0421 | 0.0782 |
| model_best | edema_t2_present_only | 16 | 0.0421 | 0.0782 |
| model_best | scar_gt_positive_only | 43 | 0.6436 | 0.2865 |
| model_best | scar_complete_modalities_only | 16 | 0.0421 | 0.0782 |

### 代码改动

- `jobs/U-MyoPS/sbatch_stage1.sh`: Slurm walltime `08:00:00`.
- `jobs/U-MyoPS/sbatch_stage2.sh`: Slurm walltime `08:00:00`; exports `UMYOPS_STAGE2_MAX_RUNTIME_SECONDS=27000` by default and logs budget variables.
- `third_party/U-MyoPS_myops/jrs/nnunet/run/load_pretrained_weights.py`: uses `torch.load(..., weights_only=False)` when available for trusted local checkpoints.
- `third_party/U-MyoPS_myops/jrs/nnunet/training/network_training/nnUNetTrainerPSNV8.py`: scar/class_2 selected validation metric, patience/runtime guard logging.
- `third_party/U-MyoPS_myops/jrs/nnunet/training/network_training/nnUNetTrainerPSNV8ScarCE2.py`: scar CE weight 2.0, foreground oversampling 0.75, force oversample class 2.
- `third_party/U-MyoPS_myops/jrs/nnunet/training/dataloading/dataset_loading.py`: honors `UMYOPS_STAGE2_FORCE_OVERSAMPLE_CLASS`.
- `scripts/evaluation/report_umyops_round2.py`: grouped metrics, per-case counts, Stage1 prior QC.
- `docs/notes/U-MyoPS_improvement_round2.md`: Chinese report.

### 验证

```bash
python -m py_compile scripts/evaluation/report_umyops_round2.py third_party/U-MyoPS_myops/jrs/nnunet/run/load_pretrained_weights.py third_party/U-MyoPS_myops/jrs/nnunet/training/dataloading/dataset_loading.py third_party/U-MyoPS_myops/jrs/nnunet/training/network_training/nnUNetTrainerPSNV8.py third_party/U-MyoPS_myops/jrs/nnunet/training/network_training/nnUNetTrainerPSNV8ScarCE2.py
python scripts/evaluation/report_umyops_round2.py --checkpoint-tag model_final_checkpoint
python scripts/evaluation/report_umyops_round2.py --checkpoint-tag model_best
python scripts/evaluation/aggregate_folds.py --inputs results/metrics/unified/U-MyoPS_model_final_checkpoint/fold_0/evaluation_summary.json --output-json results/metrics/unified/U-MyoPS_model_final_checkpoint/aggregate.json --output-md results/metrics/unified/U-MyoPS_model_final_checkpoint/aggregate.md
python scripts/evaluation/aggregate_folds.py --inputs results/metrics/unified/U-MyoPS_model_best/fold_0/evaluation_summary.json --output-json results/metrics/unified/U-MyoPS_model_best/aggregate.json --output-md results/metrics/unified/U-MyoPS_model_best/aggregate.md
```

### Submitted run

```bash
sbatch --parsable --export=ALL,UMYOPS_STAGE2_TRAINER=nnUNetTrainerPSNV8ScarCE2,UMYOPS_STAGE2_EPOCHS=80,FOLD=0,UMYOPS_STAGE2_WHICH_SUBNET=scar,UMYOPS_STAGE2_PRETRAINED_WEIGHTS=/overflow/htzhu/CARE/third_party/U-MyoPS_myops/outputs/nnunet/output/nnUNet/2d/Task901_CARE_UmyopsPathology_fold0/nnUNetTrainerPSNV8__nnUNetPlansv2.1/fold_0/model_final_checkpoint.model,UMYOPS_STAGE2_MAX_RUNTIME_SECONDS=27000,UMYOPS_STAGE2_PATIENCE=20,UMYOPS_STAGE2_EARLYSTOP_METRIC=scar jobs/U-MyoPS/sbatch_stage2.sh
```

- Job ID: `51256750`
- Log: `logs/U-MyoPS_Stage2_51256750_20260517_042736.log`
- Initial check: running on `g1807htzh01`; local final checkpoint loaded successfully.
- Actual epochs: 80
- Stop reason: reached requested max epoch, not patience early stop.
- Internal Stage2 online metric: scar/class_2 mostly 0.58-0.61, best observed around 0.6115.
- New checkpoint: `third_party/U-MyoPS_myops/outputs/nnunet/output/nnUNet/2d/Task901_CARE_UmyopsPathology_fold0/nnUNetTrainerPSNV8ScarCE2__nnUNetPlansv2.1/fold_0/model_final_checkpoint.model`
- New 2026-05-17 `model_best.model`: not found in the ScarCE2 fold directory.
- Post-run unified metrics: not available yet; export/eval has not been rerun with `--trainer nnUNetTrainerPSNV8ScarCE2`.

### 当前决策

- 不启动 fold1-4。
- Do not run more Stage2 training until ScarCE2 export/eval and Stage2 label oracle checks are complete.
- Round3 should fix export trainer selection, force checkpoint-specific/cache-isolated inference, run Task901 label oracle remap vs Dataset501 GT, and only then decide whether the bottleneck is training, task construction, or remap/geometry.

## 2026-05-17 round3 ScarCE2 export/eval + Stage2 oracle

### 目标

- 不继续训练。
- 验证 round2 ScarCE2 是否只是没有正确导出。
- 验证 Task901 Stage2 internal labels 与 Dataset501 fold0 GT 的 label/geometry 语义。

### 代码改动

- `jobs/U-MyoPS/sbatch_export_eval_fold0.sh`
  - supports `UMYOPS_EXPORT_TRAINER`.
  - prediction/metric tag includes trainer and checkpoint.
  - defaults `UMYOPS_EXPORT_FORCE_FALLBACK=1`.
  - passes `--trainer`, `--checkpoint`, `--force-fallback`.
  - runs grouped diagnostics and aggregate after eval.
- `code/U-MyoPS/export_stage2_val_predictions.py`
  - fallback tmp cache includes trainer and checkpoint.
- `scripts/evaluation/report_umyops_stage2_oracle.py`
  - new Task901 label oracle script.
- `scripts/evaluation/report_umyops_round2.py`
  - geometry tolerance uses `atol=1e-5`.
- `third_party/U-MyoPS_myops/jrs/nnunet/training/network_training/nnUNetTrainerPSNV8.py`
  - added initial best checkpoint fallback for future training runs.

### Stage2 oracle

Command:

```bash
python scripts/evaluation/report_umyops_stage2_oracle.py --fold 0
```

Output:

- `results/metrics/unified/U-MyoPS_stage2_oracle/fold_0/grouped_diagnostics.md`
- `results/metrics/unified/U-MyoPS_stage2_oracle/fold_0/grouped_metrics.json`
- `results/metrics/unified/U-MyoPS_stage2_oracle/fold_0/per_case_counts.csv`

Result:

| group | n | myops_edema | myops_scar |
| --- | ---: | ---: | ---: |
| all_cases | 44 | 1.0000 | 1.0000 |
| edema_gt_positive_only | 16 | 1.0000 | 1.0000 |
| edema_t2_present_only | 16 | 1.0000 | 1.0000 |
| scar_gt_positive_only | 43 | 1.0000 | 1.0000 |
| scar_complete_modalities_only | 16 | 1.0000 | 1.0000 |

Geometry mismatches: none.

Interpretation: Task901 labels, remap `1->4` / `2->5`, slice order, and geometry are not the cause of low unified scar.

### ScarCE2 export/eval

Command:

```bash
sbatch --parsable --export=ALL,UMYOPS_EXPORT_TRAINER=nnUNetTrainerPSNV8ScarCE2,UMYOPS_EXPORT_CHECKPOINT=model_final_checkpoint,UMYOPS_STAGE2_WHICH_SUBNET=scar,UMYOPS_EXPORT_FORCE_FALLBACK=1 jobs/U-MyoPS/sbatch_export_eval_fold0.sh
```

- Job ID: `51264404`
- Log: `logs/U-MyoPS_ExportEval_51264404_20260517_060141.log`
- Cache root: `results/predictions/_tmp/U-MyoPS/fold_0_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/validation_raw`
- Prediction dir: `results/predictions/U-MyoPS_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/fold_0`
- Metric dir: `results/metrics/unified/U-MyoPS_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/fold_0`

Result:

| trainer/checkpoint | group | n | myops_edema | myops_scar |
| --- | --- | ---: | ---: | ---: |
| ScarCE2 final | all_cases | 44 | 0.6338 | 0.2932 |
| ScarCE2 final | edema_gt_positive_only | 16 | 0.0554 | 0.0767 |
| ScarCE2 final | edema_t2_present_only | 16 | 0.0554 | 0.0767 |
| ScarCE2 final | scar_gt_positive_only | 43 | 0.6253 | 0.3000 |
| ScarCE2 final | scar_complete_modalities_only | 16 | 0.0554 | 0.0767 |

Comparison to old PSNV8 final:

- all-cases scar: `0.2823 -> 0.2932`
- scar-positive-only: `0.2888 -> 0.3000`
- complete-modality scar: `0.0781 -> 0.0767`
- GT-positive/T2-present edema: `0.0393 -> 0.0554`

### Best checkpoint behavior

- No `model_best.model` exists for the completed ScarCE2 run.
- Cause: base `NetworkTrainer.manage_patience()` does not save a best checkpoint at initial best initialization, and this run did not later exceed the initial moving-average best.
- Fix added for future PSNV8-derived runs: save initial best fallback after first validation if `model_best.model` does not exist.
- Current round does not rename or copy final as best.

### Decision

- ScarCE2 was correctly exported in round3, and it only marginally improves all-cases scar while failing complete-modality scar.
- Stage2 label oracle is perfect, so Task901 label construction/remap/geometry is not the bottleneck.
- Do not continue CE/sampling escalation or longer training.
- Next attributable round should test Stage1 prior / Stage2 input semantics, preferably with an oracle/controlled prior ablation on fold0 before any more training.
- Do not run fold1-4.

## 2026-05-17 round4 Stage2 prior/input ablation

### 目标

- 遵守单 job 不超过 8 小时、先 fold0、小步迭代。
- 本轮只验证一个主要假设：Stage1 prior / aligned C0-T2-LGE inputs 是否伤害 Stage2 pathology localization。
- 不运行 Stage1 full retraining，不扩展 fold1-4。

### 代码改动

- `code/U-MyoPS/build_stage2_task_from_stage1.py`
  - added `--input-variant {existing_full,lge_only_no_prior,oracle_prior_diagnostic}`.
  - `lge_only_no_prior`: zero prior/C0/T2, keep LGE.
  - `oracle_prior_diagnostic`: GT-derived diagnostic support prior; marked non-submission-legal.
  - Variant channels use Dataset501 GT geometry as canonical reference.
- `code/U-MyoPS/prepare_stage2_task.sh`
  - passes `UMYOPS_STAGE2_INPUT_VARIANT`.
  - added `UMYOPS_STAGE2_SKIP_BUILD` and `UMYOPS_STAGE2_SKIP_PREPROCESS`.
- `jobs/U-MyoPS/sbatch_export_eval_fold0.sh`
  - supports `UMYOPS_EXPORT_TASK` and `UMYOPS_EXPORT_TAG` for variant-isolated export/eval.
- `scripts/evaluation/report_umyops_stage2_input_qc.py`
  - new Stage2 input/prior QC report for focus cases.
- `docs/notes/U-MyoPS_improvement_round4.md`
  - round4 report, currently pending training metrics.

### Input QC

Commands:

```bash
python scripts/evaluation/report_umyops_stage2_input_qc.py --fold 0 --task-name Task901_CARE_UmyopsPathology_fold0 --out-dir results/metrics/unified/U-MyoPS_stage2_input_qc/fold_0
python scripts/evaluation/report_umyops_stage2_input_qc.py --fold 0 --task-name Task912_CARE_UmyopsLGEOnlyNoPrior_fold0 --out-dir results/metrics/unified/U-MyoPS_stage2_input_qc_lge_only_no_prior/fold_0
python scripts/evaluation/report_umyops_stage2_input_qc.py --fold 0 --task-name Task913_CARE_UmyopsOraclePriorDiagnostic_fold0 --out-dir results/metrics/unified/U-MyoPS_stage2_input_qc_oracle_prior_diagnostic/fold_0
```

Outputs:

- `results/metrics/unified/U-MyoPS_stage2_input_qc/fold_0/input_qc.md`
- `results/metrics/unified/U-MyoPS_stage2_input_qc_lge_only_no_prior/fold_0/input_qc.md`
- `results/metrics/unified/U-MyoPS_stage2_input_qc_oracle_prior_diagnostic/fold_0/input_qc.md`

Existing full-input focus-case findings:

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

`lge_only_no_prior` QC confirms prior/C0/T2 channel nonzero counts are all zero on focus cases while LGE remains non-empty.

### Controlled variant setup

Raw/preprocessed lge-only task:

```bash
UMYOPS_STAGE2_TASK=Task912_CARE_UmyopsLGEOnlyNoPrior FOLD=0 UMYOPS_STAGE2_INPUT_VARIANT=lge_only_no_prior UMYOPS_STAGE2_FORCE_CLEAN=1 bash code/U-MyoPS/prepare_stage2_task.sh
UMYOPS_STAGE2_TASK=Task912_CARE_UmyopsLGEOnlyNoPrior FOLD=0 UMYOPS_STAGE2_SKIP_BUILD=1 UMYOPS_STAGE2_SKIP_PREPROCESS=1 bash code/U-MyoPS/prepare_stage2_task.sh
```

- Task: `Task912_CARE_UmyopsLGEOnlyNoPrior_fold0`
- Plans: `third_party/U-MyoPS_myops/outputs/nnunet/prepro/Task912_CARE_UmyopsLGEOnlyNoPrior_fold0/nnUNetPlansv2.1_plans_2D.pkl`
- Splits: `third_party/U-MyoPS_myops/outputs/nnunet/prepro/Task912_CARE_UmyopsLGEOnlyNoPrior_fold0/splits_final.pkl`

Raw oracle diagnostic task:

```bash
./env_CARE_nnUNet_v1/bin/python code/U-MyoPS/build_stage2_task_from_stage1.py --fold 0 --base-task-name Task913_CARE_UmyopsOraclePriorDiagnostic --task-root-base third_party/U-MyoPS_myops/outputs/nnunet/raw/nnUNet_raw_data --stage1-net tps --stage1-data-source ZS_unaligned --stage1-weight 1.0 --prior-tag img_de_branch_lab --input-variant oracle_prior_diagnostic --per-fold-task --force-clean
```

- Task: `Task913_CARE_UmyopsOraclePriorDiagnostic_fold0`
- Training: not run in this round.

### Submitted run

```bash
sbatch --parsable --export=ALL,UMYOPS_STAGE2_TASK=Task912_CARE_UmyopsLGEOnlyNoPrior,UMYOPS_STAGE2_TASK_NAME=Task912_CARE_UmyopsLGEOnlyNoPrior_fold0,UMYOPS_STAGE2_TRAINER=nnUNetTrainerPSNV8ScarCE2,UMYOPS_STAGE2_EPOCHS=80,FOLD=0,UMYOPS_STAGE2_WHICH_SUBNET=scar,UMYOPS_STAGE2_MAX_RUNTIME_SECONDS=27000,UMYOPS_STAGE2_PATIENCE=20,UMYOPS_STAGE2_EARLYSTOP_METRIC=scar,UMYOPS_STAGE2_AUTO_PREP=0 jobs/U-MyoPS/sbatch_stage2.sh
```

- Job ID: `51268767`
- Status: cancelled before running, no node assigned (`sacct`: `CANCELLED by 397557`, `Elapsed=00:00:00`)
- Replacement job ID: `51268833`
- Replacement status at log update: `PENDING (Resources)`
- Walltime: `08:00:00`
- Runtime guard: `27000` seconds
- Fold: `0`
- Checkpoint/metrics: not available yet.

### 当前决策

- Do not submit fold1-4.
- Do not submit another Stage2 training variant while `51268767` is pending/running.
- After `51268767` completes, export/eval with tag `round4_lge_only_no_prior` and compare complete-modality scar against ScarCE2 `0.0767`.

## 2026-05-17 round4 result + round5 export compare prepared

### Completed job

- Training job: `51268833`, completed earlier; export/eval job `51354240` completed with `ExitCode=0:0`, elapsed `00:00:29`.
- Export log: `logs/U-MyoPS_ExportEval_51354240_20260517_230644.log`.
- Valid task-specific metric dir: `results/metrics/unified/U-MyoPS_round4_lge_only_no_prior_model_final_checkpoint_v2/fold_0`.

### Result

| result | group | n | myops_edema / class_4 | myops_scar / class_5 |
| --- | --- | ---: | ---: | ---: |
| round4 LGE-only/no-prior final | all_cases | 44 | 0.6726 | 0.5248 |
| round4 LGE-only/no-prior final | scar_gt_positive_only | 43 | 0.6650 | 0.5370 |
| round4 LGE-only/no-prior final | complete/T2-present | 16 | 0.1622 | 0.6524 |
| round3 ScarCE2 final | all_cases | 44 | 0.6338 | 0.2932 |
| nnU-Net Dataset501 5-fold | reference | 5 folds | 0.4197 | 0.5592 |

### Interpretation

- The hypothesis is supported: original Stage1 prior / aligned C0/T2 channels were suppressing Stage2 scar. Removing them and using LGE-only restored scar from `0.2932` to `0.5248` all-cases.
- Complete-modality scar `0.6524` exceeds the nnU-Net scar reference, but all-cases scar is still slightly below `0.5592`.
- Edema all-cases is inflated by empty-GT cases; on T2-present/edema-positive cases it remains weak (`0.1622`). Current U-MyoPS should be treated as a scar specialist, not the final edema model.

### Code change

- `code/U-MyoPS/export_stage2_val_predictions.py`: fallback temporary prediction root now includes task name, preventing cross-task stale nnU-Net cache reuse.
- `jobs/U-MyoPS/sbatch_round5_export_compare.sh`: added export-only comparison for `model_final_checkpoint` vs `model_best` on `Task912_CARE_UmyopsLGEOnlyNoPrior_fold0`.

### Next command

```bash
sbatch jobs/U-MyoPS/sbatch_round5_export_compare.sh
```

## 2026-05-17 round5 final-vs-best export compare

### Goal

- No training in this round.
- Compare `model_final_checkpoint` and `model_best` for `Task912_CARE_UmyopsLGEOnlyNoPrior_fold0`.
- Decide whether U-MyoPS should continue as a scar-specialist branch.

### Command

```bash
sbatch jobs/U-MyoPS/sbatch_round5_export_compare.sh
```

- Job ID: `51354910`
- Node: `g1807htzh01.ll.unc.edu`
- Log: `logs/U-MyoPS_r5_export_51354910_20260517_233346.log`
- Status: completed.

### Cache isolation

- Final checkpoint metrics:
  - `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_final_checkpoint/fold_0/evaluation_summary.json`
  - `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_final_checkpoint/fold_0/grouped_diagnostics.md`
- Best checkpoint metrics:
  - `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0/evaluation_summary.json`
  - `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0/grouped_diagnostics.md`
- Raw fallback caches include the Stage2 task name and checkpoint tag:
  - `results/predictions/_tmp/U-MyoPS/fold_0_Task912_CARE_UmyopsLGEOnlyNoPrior_fold0_nnUNetTrainerPSNV8ScarCE2_model_final_checkpoint/validation_raw`
  - `results/predictions/_tmp/U-MyoPS/fold_0_Task912_CARE_UmyopsLGEOnlyNoPrior_fold0_nnUNetTrainerPSNV8ScarCE2_model_best/validation_raw`

### Results

| checkpoint | group | n | myops_edema | myops_scar |
| --- | --- | ---: | ---: | ---: |
| `model_final_checkpoint` | all_cases | 44 | 0.6726 | 0.5248 |
| `model_final_checkpoint` | scar_gt_positive_only | 43 | 0.6650 | 0.5370 |
| `model_final_checkpoint` | complete/T2-present | 16 | 0.1622 | 0.6524 |
| `model_best` | all_cases | 44 | 0.6518 | 0.5307 |
| `model_best` | scar_gt_positive_only | 43 | 0.6437 | 0.5430 |
| `model_best` | complete/T2-present | 16 | 0.1675 | 0.6463 |

### Decision

- `model_best` is the preferred Task912 checkpoint for scar, but all-case scar `0.5307` remains below the nnU-Net MyoPS 5-fold reference `0.5592`.
- Complete-modality/T2-present scar remains strong (`0.6463`), supporting U-MyoPS as a scar-specialist candidate for validation-like complete cases.
- Edema remains weak on the T2-present/GT-positive subset (`0.1675`), so U-MyoPS should not be used as the edema branch.
- Next useful round should test hybrid validation packaging/routing: U-MyoPS Task912 `model_best` for scar only, with nnU-Net or MyoPS-Net providing edema.

### Report

- `docs/notes/U-MyoPS_improvement_round5.md`

## 2026-05-18 round6 missing-modality scar calibration

### Goal

- No training and no folds 1-4.
- Compare U-MyoPS Task912 `model_best` against nnU-Net501 fold0 case by case.
- Test export-only pure U-MyoPS scar calibration and clearly marked hybrid routing variants.

### Code changes

- `code/U-MyoPS/apply_round6_scar_calibration.py`
  - writes per-case U-MyoPS vs nnU-Net scar diagnostics;
  - creates pure U-MyoPS component/volume scar calibration variants;
  - creates hybrid diagnostic variants that replace missing-modality cases with nnU-Net.
- `jobs/U-MyoPS/sbatch_round6_scar_calibration.sh`
  - runs calibration and unified evaluation for each variant.
- `jobs/U-MyoPS/README.md`
  - documents round6 command and warns that `nnunet` variants are hybrid diagnostic outputs.

### Command

```bash
sbatch jobs/U-MyoPS/sbatch_round6_scar_calibration.sh
```

- Job ID: `51367847`
- Node: `g1807htzh01.ll.unc.edu`
- Log: `logs/U-MyoPS_r6_calibration_51367847_20260518_024923.log`
- Status: completed.

### Per-case comparison

Outputs:

- `results/diagnostics/baseline_paper_models/U-MyoPS/round06_scar_vs_nnunet/per_case_umyops_vs_nnunet_scar.csv`
- `results/diagnostics/baseline_paper_models/U-MyoPS/round06_scar_vs_nnunet/per_case_umyops_vs_nnunet_scar.md`
- `results/diagnostics/baseline_paper_models/U-MyoPS/round06_scar_vs_nnunet/manifest.json`

| group | n | U-MyoPS scar | nnU-Net scar | U - nnU-Net |
| --- | ---: | ---: | ---: | ---: |
| all | 44 | 0.5307 | 0.5602 | -0.0295 |
| complete | 16 | 0.6463 | 0.6933 | -0.0471 |
| missing-modality | 28 | 0.4646 | 0.4841 | -0.0195 |
| scar-positive | 43 | 0.5430 | 0.5732 | -0.0302 |

Worst U-MyoPS gaps include `Case3038` complete under-segmentation (`0.3256` vs nnU-Net `0.7583`) and `Case5005` missing-modality under-segmentation (`0.3034` vs `0.5726`). The round5 gap is therefore not only missing-T2 behavior.

### Results

| variant | type | all-case edema | all-case scar | scar-positive scar | complete/T2-present scar |
| --- | --- | ---: | ---: | ---: | ---: |
| `U-MyoPS_round6_scar_component_filter_100` | pure U-MyoPS | 0.6518 | 0.5284 | 0.5406 | 0.6513 |
| `U-MyoPS_round6_scar_component_filter_250` | pure U-MyoPS | 0.6518 | 0.5352 | 0.5244 | 0.6202 |
| `U-MyoPS_round6_missing_volume_cap_1500` | pure U-MyoPS | 0.6518 | 0.5309 | 0.5432 | 0.6463 |
| `U-MyoPS_round6_scar_complete_umyops_missing_nnunet` | hybrid scar | 0.6518 | 0.5431 | 0.5557 | 0.6463 |
| `U-MyoPS_round6_complete_umyops_missing_nnunet` | hybrid full | 0.6973 | 0.5431 | 0.5557 | 0.6463 |

### Decision

- Pure U-MyoPS did not cross nnU-Net: best pure all-case scar is `0.5352`, below nnU-Net fold0 `0.5602` and 5-fold mean `0.5592`.
- Hybrid routing also did not cross nnU-Net: missing-modality nnU-Net fallback reaches only `0.5431` all-case scar because complete U-MyoPS is also below same-fold nnU-Net.
- Edema remains unsolved; T2-present/GT-positive edema is still `0.1675`.
- Current next step should not be more export-only scar calibration. Either keep U-MyoPS as a complete-case scar-specialist diagnostic, or run a separate paper-faithful Stage1 repair round focused on prior quality and missing-modality-aware gating.

### Report

- `docs/notes/U-MyoPS_improvement_round6.md`

## 2026-05-18 round7 LGE + dilated Stage1 prior

### Goal

- Return from export-only calibration to a more paper-aligned Stage1-prior route.
- Test one fold0 hypothesis: a CARE-aware dilated Stage1 prior plus real LGE can preserve the U-MyoPS prior-aware idea without reintroducing unreliable C0/T2 aligned channels.
- Keep training within the 8h round budget.

### Command

```bash
sbatch jobs/U-MyoPS/sbatch_round7_lge_dilated_prior.sh
```

- Job ID: `51368430`
- Node: `g1807htzh01`
- Log: `logs/U-MyoPS_r7_lge_dilated_prior_51368430_20260518_031147.log`
- Task: `Task914_CARE_UmyopsLGEDilatedPrior_fold0`
- Input variant: `lge_dilated_prior`
- Prior dilation radius XY: `8`
- Trainer: `nnUNetTrainerPSNV8ScarCE2`
- Stop reason: completed 80 epochs; final internal scar/class_2 validation metric `0.6170`.

### Outputs

- `results/metrics/unified/U-MyoPS_round7_lge_dilated_prior_model_best/fold_0/evaluation_summary.json`
- `results/metrics/unified/U-MyoPS_round7_lge_dilated_prior_model_best/fold_0/grouped_diagnostics.md`
- `results/metrics/unified/U-MyoPS_round7_lge_dilated_prior_model_final_checkpoint/fold_0/evaluation_summary.json`
- `results/metrics/unified/U-MyoPS_round7_lge_dilated_prior_model_final_checkpoint/fold_0/grouped_diagnostics.md`

### Results

| checkpoint | group | n | myops_edema | myops_scar |
| --- | --- | ---: | ---: | ---: |
| `model_best` | all_cases | 44 | 0.7039 | 0.5539 |
| `model_best` | scar_gt_positive_only | 43 | 0.6970 | 0.5668 |
| `model_best` | complete/T2-present | 16 | 0.1858 | 0.6571 |
| `model_best` | missing-modality | 28 | 1.0000 | 0.4949 |
| `model_final_checkpoint` | all_cases | 44 | 0.7039 | 0.5538 |
| `model_final_checkpoint` | scar_gt_positive_only | 43 | 0.6971 | 0.5667 |
| `model_final_checkpoint` | complete/T2-present | 16 | 0.1858 | 0.6571 |
| `model_final_checkpoint` | missing-modality | 28 | 1.0000 | 0.4948 |

### Decision

- Round7 is the best pure U-MyoPS scar result so far: `0.5539`, improving over round5 `0.5307` and round6 pure best `0.5352`.
- It still does not cross nnU-Net Dataset501 5-fold scar `0.5592` or fold0 scar `0.5602`.
- Edema remains not solved; the all-case edema value is inflated by empty-GT cases, while edema GT-positive/T2-present remains only about `0.1858`.
- Do not expand U-MyoPS folds yet. If continuing, run only a small prior reliability/gating or low-case failure analysis round.

### Report

- `docs/notes/U-MyoPS_improvement_round7.md`

## 2026-05-19 round8 prior reliability gate

### Goal

- No training and no fold expansion.
- Test export-only Stage1 prior reliability gates and component/volume cleanup on round7 `model_best`.
- Include HD/HD95 because current official MyoPS scar leaderboard shows Dice/HD mismatch risk.

### Command

```bash
./env_CARE/bin/python code/U-MyoPS/apply_round8_prior_reliability_gate.py
```

### Inputs

- Baseline predictions: `results/predictions/U-MyoPS_round7_lge_dilated_prior_model_best/fold_0`
- LGE-only fallback: `results/predictions/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0`
- Stage1 prior root: `third_party/U-MyoPS_myops/outputs/asn_myo_tps_tps_ZS_unaligned_1.0_fold0/gen_res`
- Latest leaderboard refreshed with `python scripts/leaderboard/fetch_care2026_scores.py`; current `OrganAgent` MyoPS scar validation row is Dice `0.5969`, HD `16.2536`, using nnU-Net for the MyoPS branch.

### Diagnostics

- Taxonomy: `results/diagnostics/baseline_paper_models/U-MyoPS/round08_prior_gate/case_failure_taxonomy.csv`
- Main low-case classes:
  - `Case7005`: empty GT scar but non-empty U-MyoPS prediction.
  - `Case1029`, `Case8021`: very low prior/pathology overlap.
  - `Case1053`, `Case5005`, `Case2020`: under-segmentation.
  - `Case3004`: over-segmentation.
  - Many remaining cases are localization/mixed rather than simple volume failures.

### Results

| variant | all-case scar Dice | scar-positive Dice | complete/T2-present scar | missing-modality scar | scar HD | scar HD95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| round7 baseline | 0.5539 | 0.5668 | 0.6571 | 0.4949 | 35.0772 | 14.6865 |
| `drop_empty_gt_like_false_positive_proxy` | 0.5581 | 0.5478 | 0.6255 | 0.5196 | 34.4867 | 13.8297 |
| `tiny_c0_lge_no_t2_suppression` | 0.5766 | 0.5668 | 0.6571 | 0.5306 | 34.2800 | 14.3527 |
| `prior_reliable_keep_lge_fallback` | 0.5426 | 0.5552 | 0.6500 | 0.4812 | 35.8062 | 16.0122 |
| `component_hd_guard` | 0.5553 | 0.5682 | 0.6567 | 0.4974 | 28.3333 | 13.8978 |
| `volume_ratio_guard` | 0.5542 | 0.5671 | 0.6570 | 0.4954 | 31.5742 | 14.6030 |

### Decision

- `tiny_c0_lge_no_t2_suppression` crosses the local all-case scar threshold, but only by deleting one tiny prediction in `Case7005`, an empty-GT case. It is diagnostic-only and not enough evidence for a robust U-MyoPS branch.
- `component_hd_guard` is the best reliable export-only rule: Dice improves slightly and HD improves substantially, but scar Dice remains below nnU-Net Dataset501 fold0 `0.5602` and 5-fold mean `0.5592`.
- Do not expand U-MyoPS folds 1-4.
- Do not replace the current nnU-Net MyoPS submission branch with U-MyoPS.
- If continuing U-MyoPS at all, round9 should be a single very small model-side HD/outlier fine-tune based on `component_hd_guard`; otherwise stop the U-MyoPS baseline mainline and move to a new `src/` model or stronger nnU-Net/MyoPS-Net improvements.

### Report

- `docs/notes/baseline/U-MyoPS_improvement_round8.md`
