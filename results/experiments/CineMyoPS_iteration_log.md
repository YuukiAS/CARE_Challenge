# CineMyoPS iteration log

## 2026-05-17 round2: fold0 全 0 定位, export-only

- **规则**: 遵守 iterative model-improvement; 无新训练, 无 5-fold, 单个 Slurm job walltime 均小于 8h。
- **目标假设 1**: 全 0 是否来自导出旧 checkpoint。
- **job**: `51256637`
- **command/env**: `FOLD=0 CINE_PRED_CHECKPOINT=model_final_checkpoint CINE_NNUNET_TASK=Task026_Cine_4D CINE_NNUNET_TRAINER=CARECineMyoPSTrainer sbatch jobs/CineMyoPS/sbatch_export_eval.sh`
- **elapsed**: `00:14:36`
- **checkpoint**: `model_final_checkpoint.model`, mtime `2026-05-12 20:05:52 -0400`
- **result**: 13/13 protocol val predictions 仍全 0; `class_1=0.0000`, `class_3=0.0000`。
- **结论**: checkpoint 选择不是唯一根因。

## 2026-05-17 round2: BatchNorm eval-mode 诊断, export-only

- **目标假设 2**: eval-mode BatchNorm running stats 是否导致 inference collapse。
- **code change**: `CARECineMyoPSTrainer.predict_preprocessed_data_return_seg_and_softmax` 增加 `CINE_INFERENCE_TRAIN_MODE=1` 诊断开关。
- **job**: `51259699`
- **command/env**: `FOLD=0 CINE_PRED_CHECKPOINT=model_final_checkpoint CINE_NNUNET_TASK=Task026_Cine_4D CINE_NNUNET_TRAINER=CARECineMyoPSTrainer CINE_INFERENCE_TRAIN_MODE=1 sbatch jobs/CineMyoPS/sbatch_export_eval.sh`
- **elapsed**: `00:06:50`
- **checkpoint**: `model_final_checkpoint.model`, mtime `2026-05-12 20:05:52 -0400`
- **actual epochs**: 0 new epochs; export/eval only against existing 400-epoch checkpoint from 2026-05-12.
- **stop reason**: diagnostic export/eval completed successfully.
- **prediction labels**: non-empty; labels `1/2/3` appear globally, but `class_1` appears only in 3/13 cases and with very few voxels.
- **metrics**: `class_1=0.0003976`, `class_2=0.3090714`, `class_3=0.0016201`, `foreground_mean=0.1036964`.
- **interpretation**: train-mode BatchNorm restores non-empty predictions, so the real failure is likely eval-mode BN running-stat collapse. Output semantics remain unusable for submission.
- **next hypothesis**: add a BN recalibration pass, then re-export in normal eval mode.

## 2026-05-17 round3: eval-mode BN recalibration, export-only

- **规则**: fold0 only; no 5-fold expansion; no official submission; export/eval Slurm walltime `02:00:00`.
- **main hypothesis**: use fold training batches to recalibrate BatchNorm running stats, then predict in normal eval mode instead of `CINE_INFERENCE_TRAIN_MODE=1`.
- **code changes**: added `CINE_BN_RECALIBRATE` / `CINE_BN_RECALIB_BATCHES` to `CARECineMyoPSTrainer`; added config-specific `CINE_OUTPUT_MODEL` prediction/metric directories.
- **failed job**: `51264134`, `logs/CineMyoPS_export_eval_51264134_20260517_051828.log`.
- **failed stop reason**: direct basic DataLoader calibration used pre-augmentation patch size and hit a motion-decoder tensor-size mismatch. Fixed by center-cropping/padding calibration data to final `patch_size`.
- **active job**: `51264154`, `logs/CineMyoPS_export_eval_51264154_20260517_052113.log`.
- **command/env**: `FOLD=0 CINE_NNUNET_TASK=Task026_Cine_4D CINE_NNUNET_TRAINER=CARECineMyoPSTrainer CINE_OUTPUT_MODEL=CineMyoPS_BNRecalibExport_v2 CINE_PRED_CHECKPOINT=model_final_checkpoint CINE_BN_RECALIBRATE=1 CINE_BN_RECALIB_BATCHES=32 sbatch jobs/CineMyoPS/sbatch_export_eval.sh`
- **checkpoint**: existing `model_final_checkpoint.model`, mtime `2026-05-12 20:05:52 -0400`.
- **actual epochs**: 0 new epochs; export/eval only.
- **BN recalibration evidence**: actual batches `32`, BN layers `56`, elapsed `2.57s`; normal eval-mode prediction continued after calibration.
- **prediction/metrics dirs**: `results/predictions/CineMyoPS_BNRecalibExport_v2/fold_0`, `results/metrics/unified/CineMyoPS_BNRecalibExport_v2/fold_0`.
- **stop reason**: export/eval completed.
- **prediction labels**: 13/13 predictions contain only label `0`.
- **metrics**: `class_1=0.000000`, `class_2=0.000000`, `class_3=0.000000`, `foreground_mean=0.000000`.
- **interpretation**: BN recalibration alone does not rescue the old 2026-05-12 checkpoint in normal eval mode; continue with isolated fold0 retraining.

## 2026-05-17 round3: fold0 isolated BNCalib training, budget run

- **规则**: fold0 only; no 5-fold expansion; Slurm walltime `08:00:00`; no long 1000/2000 epoch training.
- **main hypothesis**: retrain an isolated fold0 trainer with eval-time BN recalibration available, without overwriting the 2026-05-12 `CARECineMyoPSTrainer` checkpoint.
- **job**: `51264136`
- **log**: `logs/CineMyoPS_e2e_51264136_20260517_051831.log`
- **command/env**: `FOLD=0 CINE_NNUNET_TASK=Task026_Cine_4D CINE_NNUNET_TRAINER=CARECineMyoPSTrainerBNCalib CINE_OUTPUT_MODEL=CineMyoPS_BNCalib CINE_NNUNET_EPOCHS=200 CINE_SKIP_PREPARE=1 CINE_RUN_EXPORT_EVAL=1 CINE_BN_RECALIBRATE=1 CINE_BN_RECALIB_BATCHES=32 CINE_PRED_CHECKPOINT=model_final_checkpoint sbatch jobs/CineMyoPS/sbatch_fold0_pipeline.sh`
- **checkpoint dir**: `data/nnUNet/nnUNet_results/nnUNet/2d/Task026_Cine_4D/CARECineMyoPSTrainerBNCalib__nnUNetPlansv2.1/fold_0`.
- **planned checkpoint/export**: `model_final_checkpoint` to `results/predictions/CineMyoPS_BNCalib/fold_0`, metrics under `results/metrics/unified/CineMyoPS_BNCalib/fold_0`.
- **actual epochs**: pending; job running at note time.
- **early online eval evidence**: epoch 6 foreground Dice estimate `[0.5838495, 0.8609002, 0.30024827]`; epoch 18 estimate `[0.5591354, 0.8679081, 0.33099163]`. These are not final protocol eval.

## Iteration 2026-05-17T07:26:18-04:00
- **job_id**: 51264136
- **log**: `/overflow/htzhu/CARE/logs/CineMyoPS_e2e_51264136_20260517_051831.log`
- **frame_policy**: Task026 ED-first + 4 sampled frames (Cine 4D raw channels)
- **config**: FOLD=0 CINE_NNUNET_EPOCHS=200 CINE_SKIP_PREPARE=1 CINE_PRED_CHECKPOINT=model_final_checkpoint task=Task026_Cine_4D trainer=CARECineMyoPSTrainerBNCalib output_model=CineMyoPS_BNCalib CINE_BN_RECALIBRATE=1 CINE_BN_RECALIB_BATCHES=32
- **planned_wall**: 8h sbatch limit
- **actual_train_pipeline_s**: 7667
- **unified_eval mean Dice class_1 (myocardium)**: 0.000000 (nnU-Net v2 Dataset502 ref mean myocardium ≈ 0.6808 over folds; compare same metric on protocol val)
- **note**: Leaderboard `myocardium_cinemyops` is a hosted composite; offline protocol metric tracked here is **class_1** vs Dataset502 labels on val split.

## 2026-05-17 round4: inference semantics and combine-mode ablations

- **规则**: no new training; fold0 only; no 5-fold expansion; no official submission.
- **main hypothesis**: round3 online eval was nonzero but validation inference/export was all background, so collapse may be in direct inference, sliding-window aggregation, compact softmax combination, or export label path.
- **code changes**:
  - Added `CINE_COMBINE_MODE` in `CARECineMyoPSTrainer._combine_compact_softmax`.
  - Modes: `current`, `cardiac_only`, `myocardium_gated_scar`, `pathology_direct`.
  - Added `scripts/evaluation/debug_cinemyops_inference_semantics.py`.
  - Added `jobs/CineMyoPS/sbatch_round4_debug.sh` and `jobs/CineMyoPS/sbatch_round4_ablation.sh`.
- **checks**: `py_compile` passed for trainer/debug script; `bash -n` passed for export/eval/debug/ablation scripts.
- **local diagnostic attempt**: `./env_CARE_nnUNet_v1/bin/python scripts/evaluation/debug_cinemyops_inference_semantics.py` was killed with exit code `137`; moved to GPU Slurm.
- **debug job**: `51268602`, command `sbatch jobs/CineMyoPS/sbatch_round4_debug.sh`, walltime `02:00:00`, status at note time `PENDING (Resources)`.
- **ablation job**: `51268612`, command `sbatch jobs/CineMyoPS/sbatch_round4_ablation.sh`, walltime `04:00:00`, status at note time `PENDING (Priority)`.
- **ablation output dirs**:
  - `results/metrics/unified/CineMyoPS_R4_current/fold_0/evaluation_summary.json`
  - `results/metrics/unified/CineMyoPS_R4_cardiac_only/fold_0/evaluation_summary.json`
  - `results/metrics/unified/CineMyoPS_R4_myo_gated_scar/fold_0/evaluation_summary.json`
  - `results/metrics/unified/CineMyoPS_R4_pathology_direct/fold_0/evaluation_summary.json`
- **pending**: record metrics for each mode and decide round5 only after the jobs complete.

## 2026-05-17 round4 result + round5 fixed debug prepared

### Completed result

The combine-mode export-only ablations completed but did not rescue fold0 validation:

| variant | class_1 myocardium | class_2 LV | class_3 scar | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| pre-round4 train-mode diagnostic | 0.0004 | 0.3091 | 0.0016 | 0.1037 |
| `CineMyoPS_R4_current` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `CineMyoPS_R4_cardiac_only` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `CineMyoPS_R4_myo_gated_scar` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `CineMyoPS_R4_pathology_direct` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

### Interpretation

- Changing compact-softmax combination is not sufficient. Either direct branch logits are already collapsed, or sliding-window/export path still erases useful logits before the combine modes can matter.
- The first round4 debug script selected the wrong 2D slice axis/patch and failed before branch-logit inspection, so this question remains unresolved.

### Code change

- `scripts/evaluation/debug_cinemyops_inference_semantics.py`: fixed 2D network patch extraction by inferring the slice axis from trainer patch size and image dimensions.
- `jobs/CineMyoPS/sbatch_round5_debug_fixed.sh`: short GPU diagnostic wrapper writing `results/diagnostics/CineMyoPS_round5/inference_semantics_fixed.json`.

### Next command

```bash
sbatch jobs/CineMyoPS/sbatch_round5_debug_fixed.sh
```

Do not start another CineMyoPS training run until this diagnostic identifies whether the failure is direct logits, sliding-window inference, or export semantics.

## 2026-05-17 round5: fixed inference-axis debug, fold0 only

- **规则**: no new training; fold0 only; no official validation submission; single export/eval job under 8h.
- **main hypothesis**: round4 all-background validation exports were caused by inference semantics. Test direct logits vs sliding-window prediction/export before considering any further training.
- **diagnostic job**: `51354672`
- **diagnostic command**: `sbatch jobs/CineMyoPS/sbatch_round5_debug_fixed.sh`
- **diagnostic log**: `logs/CineMyoPS_r5_debug_51354672_20260517_232602.log`
- **diagnostic JSON**: `results/diagnostics/CineMyoPS_round5/inference_semantics_fixed.json`
- **BN recalibration evidence**: actual batches `32`, BN layers `56`, elapsed `3.23s`.
- **diagnostic finding**:
  - Direct eval forward produced non-background cardiac/pathology logits on selected fold0 val slices.
  - Direct train-mode forward was also non-empty and similar to eval mode.
  - Direct compact combination with `CINE_COMBINE_MODE=current` produced non-background compact labels.
  - `predict_preprocessed_data_return_seg_and_softmax(... do_mirroring=False, use_gaussian=False)` was all background before the code fix.
  - Exported NIfTI predictions before the code fix were all background.
- **interpretation**: failure was not direct-logit collapse, eval-mode BN collapse, or export label remap collapse. The dominant bug was sliding-window inference slicing the wrong spatial axis for Task026 `(T, X, Y, Z)` arrays.
- **code change**:
  - `third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainer.py`
  - Added `_infer_slice_and_inplane_axes(...)`.
  - Updated `predict_preprocessed_data_return_seg_and_softmax` to infer the slice axis from `data.shape[1:]` and `trainer.patch_size` instead of hardcoding the last spatial axis.
- **checks**:
  - `./env_CARE_nnUNet_v1/bin/python -m py_compile third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainer.py scripts/evaluation/debug_cinemyops_inference_semantics.py`
  - `bash -n jobs/CineMyoPS/sbatch_export_eval.sh`
- **fixed export/eval job**: `51354763`
- **fixed export/eval command/env**: `FOLD=0 CINE_NNUNET_TASK=Task026_Cine_4D CINE_NNUNET_TRAINER=CARECineMyoPSTrainerBNCalib CINE_OUTPUT_MODEL=CineMyoPS_R5_fixed_inference CINE_PRED_CHECKPOINT=model_final_checkpoint CINE_BN_RECALIBRATE=1 CINE_BN_RECALIB_BATCHES=32 CINE_COMBINE_MODE=current sbatch jobs/CineMyoPS/sbatch_export_eval.sh`
- **fixed export/eval log**: `logs/CineMyoPS_export_eval_51354763_20260517_232845.log`
- **checkpoint used/exported**: `model_final_checkpoint` from `Task026_Cine_4D/CARECineMyoPSTrainerBNCalib__nnUNetPlansv2.1/fold_0`.
- **prediction dir**: `results/predictions/CineMyoPS_R5_fixed_inference/fold_0`
- **metric dir**: `results/metrics/unified/CineMyoPS_R5_fixed_inference/fold_0`
- **aggregate metric files**: `results/metrics/unified/CineMyoPS_R5_fixed_inference/aggregate.json`, `results/metrics/unified/CineMyoPS_R5_fixed_inference/aggregate.md`
- **prediction labels**: global counts over 13 fold0 protocol val cases `{0: 7267139, 1: 59011, 2: 123664, 3: 58438}`.
- **metrics**: `class_1=0.606663`, `class_2=0.930494`, `class_3=0.394204`, `foreground_mean=0.643787`.
- **stop reason**: diagnostic completed; fixed export/eval completed.
- **round5 report**: `docs/notes/CineMyoPS_improvement_round5.md`
- **next step**: treat `CineMyoPS_R5_fixed_inference` as the new fold0 inference baseline. Do not expand to folds 1-4 or start new training until fixed fold0 label semantics/cache isolation are accepted.

## 2026-05-18 round6: fixed-inference combine ablation and class_1 repair

- **规则**: no new training; fold0 only; no official validation submission; all export/eval jobs under 8h.
- **main hypothesis**: after round5 fixed sliding-window inference, class_1 may be limited by compact softmax combination rather than anatomy logits.
- **queue check**:
  - `htzhulab`: running jobs, no visible pending backlog for this user path.
  - `a100-gpu`: many pending jobs; not a better fallback.
  - `volta-gpu`: many pending jobs; not a better fallback.
  - Decision: keep the short export-only job on `htzhulab`.
- **code/script changes**:
  - Added `jobs/CineMyoPS/sbatch_round6_fixed_inference_modes.sh`.
  - Added `scripts/evaluation/build_cinemyops_class1_overlay.py`.
- **checks**:
  - `bash -n jobs/CineMyoPS/sbatch_round6_fixed_inference_modes.sh`
  - `./env_CARE/bin/python -m py_compile scripts/evaluation/build_cinemyops_class1_overlay.py`
- **fixed-inference modes job**: `51367766`
- **fixed-inference modes command**: `sbatch jobs/CineMyoPS/sbatch_round6_fixed_inference_modes.sh`
- **log**: `logs/CineMyoPS_r6_modes_51367766_20260518_024719.log`
- **shared env**: `FOLD=0 CINE_NNUNET_TASK=Task026_Cine_4D CINE_NNUNET_TRAINER=CARECineMyoPSTrainerBNCalib CINE_PRED_CHECKPOINT=model_final_checkpoint CINE_BN_RECALIBRATE=1 CINE_BN_RECALIB_BATCHES=32 CINE_INFERENCE_TRAIN_MODE=0`
- **stop reason**: all four fixed-inference export/eval modes completed.
- **mode metrics**:
  - `CineMyoPS_R6_current`: `class_1=0.607618`, `class_2=0.930437`, `class_3=0.394587`, `foreground_mean=0.644214`.
  - `CineMyoPS_R6_cardiac_only`: `class_1=0.761128`, `class_2=0.931608`, `class_3=0.000000`, `foreground_mean=0.564245`.
  - `CineMyoPS_R6_myo_gated_scar`: `class_1=0.000000`, `class_2=0.931607`, `class_3=0.000000`, `foreground_mean=0.310536`.
  - `CineMyoPS_R6_pathology_direct`: `class_1=0.693305`, `class_2=0.931627`, `class_3=0.437767`, `foreground_mean=0.687566`.
- **class_1-primary overlay**:
  - Command: `./env_CARE/bin/python scripts/evaluation/build_cinemyops_class1_overlay.py --anatomy-dir results/predictions/CineMyoPS_R6_cardiac_only/fold_0 --pathology-dir results/predictions/CineMyoPS_R6_pathology_direct/fold_0 --output-dir results/predictions/CineMyoPS_R6_class1_primary_overlay/fold_0`
  - Eval command: `./env_CARE/bin/python scripts/evaluation/evaluate_predictions.py --pred-dir results/predictions/CineMyoPS_R6_class1_primary_overlay/fold_0 --gt-dir data/nnUNet/nnUNet_raw/Dataset502_CARECineMyoPS/labelsTr --fold-json data/benchmarks/protocol/splits_CineMyoPS.json --fold 0 --foreground-classes 1,2,3 --output-dir results/metrics/unified/CineMyoPS_R6_class1_primary_overlay/fold_0`
  - Aggregate command: `./env_CARE/bin/python scripts/evaluation/aggregate_folds.py --inputs results/metrics/unified/CineMyoPS_R6_class1_primary_overlay/fold_0/evaluation_summary.json --output-json results/metrics/unified/CineMyoPS_R6_class1_primary_overlay/aggregate.json --output-md results/metrics/unified/CineMyoPS_R6_class1_primary_overlay/aggregate.md`
  - Metrics: `class_1=0.693379`, `class_2=0.931608`, `class_3=0.437388`, `foreground_mean=0.687458`.
- **prediction label counts**:
  - `CineMyoPS_R6_current`: `{0: 7267047, 1: 59208, 2: 123610, 3: 58387}`.
  - `CineMyoPS_R6_cardiac_only`: `{0: 7272813, 1: 111020, 2: 124419}`.
  - `CineMyoPS_R6_myo_gated_scar`: `{0: 7383841, 2: 124411}`.
  - `CineMyoPS_R6_pathology_direct`: `{0: 7271859, 1: 76979, 2: 124444, 3: 34970}`.
  - `CineMyoPS_R6_class1_primary_overlay`: `{0: 7272813, 1: 77054, 2: 124419, 3: 33966}`.
- **interpretation**:
  - `cardiac_only` is the anatomy upper bound and exceeds nnU-Net class_1, but it removes scar and is not paper-faithful.
  - `pathology_direct` is the best paper-aligned fixed-inference strategy: `class_1=0.693305` exceeds nnU-Net 5-fold mean `0.6808` and fold0 `0.6864`, while `class_3=0.437767` exceeds nnU-Net scar sanity `0.2586`.
  - `class1_primary_overlay` is effectively tied with `pathology_direct` and does not justify replacing the simpler combine mode.
  - `myocardium_gated_scar` is invalid for this checkpoint because class_1/class_3 collapse.
- **round6 report**: `docs/notes/CineMyoPS_improvement_round6.md`
- **next step**: use `CINE_COMBINE_MODE=pathology_direct` as the new fold0 fixed-inference CineMyoPS baseline. No anatomy-focused training is needed in the next immediate step unless a later hosted/validation check contradicts the local proxy.

## 2026-05-18 round7: pathology_direct validation packaging

- **规则**: no training; no automatic upload; submission-ready packaging only.
- **main hypothesis**: the validation submission pipeline must explicitly use and record round6 `pathology_direct`, not silently fall back to `current`.
- **code/script changes**:
  - `scripts/submission/prepare_care_myocardium_validation.py`: added `--cine-combine-mode`; passes `CINE_COMBINE_MODE` and `CINE_NUM_FRAMES` into CineMyoPS inference env; records `combine_mode` in Cine manifest metadata; prints Cine env for future audit logs.
  - `jobs/submission/prepare_care_myocardium_validation_cinemyops_pathology_direct.sh`: new 8h `htzhulab` packaging wrapper for `nnUNet` MyoPS + `CineMyoPS` pathology_direct.
- **checks**:
  - `./env_CARE/bin/python -m py_compile scripts/submission/prepare_care_myocardium_validation.py`
  - `bash -n jobs/submission/prepare_care_myocardium_validation_cinemyops_pathology_direct.sh`
- **job**: `51368429`
- **command**: `sbatch jobs/submission/prepare_care_myocardium_validation_cinemyops_pathology_direct.sh`
- **log**: `logs/CAREValCinePD_51368429_20260518_030921.log`
- **configuration**:
  - MyoPS: `nnUNet`, fold `0`, checkpoint `checkpoint_best.pth`.
  - CineMyoPS: `Task026_Cine_4D`, `CARECineMyoPSTrainerBNCalib`, fold `0`, checkpoint `model_final_checkpoint`, `cine_num_frames=4`, `cine_combine_mode=pathology_direct`.
- **workspace**: `results/submissions/care_myocardium_validation/workspaces/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921`
- **upload dir**: `results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921`
- **zip**: `results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921/CARE-Myocardium-OrganAgent.zip`
- **manifest**: `results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921/manifest.json`
- **stop reason**: packaging completed; zip and manifest written.
- **manifest proof**:
  - `combo`: `{"myops_model": "nnUNet", "cine_model": "CineMyoPS"}`
  - `cine.used_folds`: `["0"]`
  - `cine.task`: `Task026_Cine_4D`
  - `cine.trainer`: `CARECineMyoPSTrainerBNCalib`
  - `cine.checkpoint`: `model_final_checkpoint`
  - `cine.num_frames`: `4`
  - `cine.combine_mode`: `pathology_direct`
- **zip QA**:
  - `zip_check.files=30`
  - roots: `CineMyoPS/`, `MyoPS/`
  - MyoPS prediction files: `15`
  - CineMyoPS prediction files: `15`
- **label QA after compact-to-raw conversion**:
  - MyoPS global raw labels: `{0: 4016921, 200: 41199, 500: 56541, 600: 56526, 1220: 20525, 2221: 13281}`.
  - CineMyoPS global raw labels: `{0: 14965592, 200: 115603, 500: 217577, 2221: 58952}`.
  - `pathology_label_fallback.cases=[]`; no one-voxel pathology fallback was needed.
- **interpretation**: validation package truly uses paper-aligned `pathology_direct` CineMyoPS and is upload-ready. It was not uploaded.
- **round7 report**: `docs/notes/CineMyoPS_improvement_round7.md`
