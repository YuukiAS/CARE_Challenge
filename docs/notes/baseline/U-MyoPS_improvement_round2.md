# U-MyoPS 改进 round2：fold0 scar 召回诊断与短训入口

日期：2026-05-17

## 约束

- 严格按 `AGENTS.md` 的 iterative model-improvement runs 执行。
- 本轮只处理 fold0，不扩展 fold1-4。
- Stage1/Stage2 Slurm 入口已改为单 job `08:00:00`，Stage2 训练进程默认 `UMYOPS_STAGE2_MAX_RUNTIME_SECONDS=27000`。
- 本轮主假设：`myops_scar` 低分主要来自 Stage2 scar 召回/采样与完整三序列病例失败；不是 export/cache 或简单 label remap。

## 文献与实现对照

Ding 2023 的 U-MyoPS 核心是把 bSSFP/T2 注册到 LGE common space，再用 myocardium spatial prior 支持 pathology segmentation。CARE 当前 fold0 的失败点与论文假设不一致：

- 论文假设 bSSFP/LGE/T2 完整；CARE fold0 validation 里完整三序列病例集中在 Case20xx/30xx，且这些病例 scar/edema 最差。
- 论文 edema 解释包含 union 口径；CARE 主指标必须 strict `class_4=myops_edema`。
- 当前 export remap 已固定为 Stage2 `1->4 edema`, `2->5 scar`，且 `whichsubnet=scar`。

## 指标重报

现有显式 checkpoint 的 fold0 分组指标如下。empty-GT 规则：预测和 GT 都为空时，该类 Dice 计为 `1.0`。

### `model_final_checkpoint`

| group | n | myops_edema | myops_scar |
| --- | ---: | ---: | ---: |
| all_cases | 44 | 0.6507 | 0.2823 |
| edema_gt_positive_only | 16 | 0.0393 | 0.0781 |
| edema_t2_present_only | 16 | 0.0393 | 0.0781 |
| scar_gt_positive_only | 43 | 0.6425 | 0.2888 |
| scar_complete_modalities_only | 16 | 0.0393 | 0.0781 |

### `model_best`

| group | n | myops_edema | myops_scar |
| --- | ---: | ---: | ---: |
| all_cases | 44 | 0.6517 | 0.2800 |
| edema_gt_positive_only | 16 | 0.0421 | 0.0782 |
| edema_t2_present_only | 16 | 0.0421 | 0.0782 |
| scar_gt_positive_only | 43 | 0.6436 | 0.2865 |
| scar_complete_modalities_only | 16 | 0.0421 | 0.0782 |

结论：

- all-cases edema 的 0.65 是被 empty-GT case 拉高；strict GT-positive/T2-present edema 只有约 0.04。
- scar-positive-only 仍只有约 0.29，且完整三序列子集只有约 0.078，说明 U-MyoPS 论文应当擅长的 full path 在 fold0 未成立。
- `model_best` 与 `model_final_checkpoint` 差异很小，当前瓶颈不是单一 checkpoint 选择。

诊断产物：

- `results/metrics/unified/U-MyoPS_model_final_checkpoint/fold_0/grouped_diagnostics.md`
- `results/metrics/unified/U-MyoPS_model_best/fold_0/grouped_diagnostics.md`
- `results/metrics/unified/U-MyoPS_model_final_checkpoint/fold_0/per_case_counts.csv`
- `results/metrics/unified/U-MyoPS_model_final_checkpoint/fold_0/stage1_prior_qc.csv`

## Stage1 prior 体检

抽查低 scar 病例和 Case20xx/Case30xx 后：

- Stage1 prior、aligned C0/T2/LGE 与 GT geometry 都匹配，case id、spacing/origin/direction 没有发现明显错配。
- 但 prior 与 GT support Dice 较弱，低分病例多在 `0.28-0.47`；Case8021 只有 `0.1457`。
- Case2031 prior 与 pathology overlap 只有 `336` voxels，Case3040 只有 `286` voxels，说明空间 prior 可能没有稳定覆盖 pathology 区域。
- 缺 C0/T2 的 Case8021 中 aligned C0/T2 非零体素为 `0`，没有把零图当作真实缺失模态监督；但这类 case 不应作为完整 U-MyoPS path 成功证据。

低分病例示例（`model_final_checkpoint`）：

| case | scar Dice | pred scar voxels | GT scar voxels | modalities |
| --- | ---: | ---: | ---: | --- |
| Case3012 | 0.0000 | 137 | 2818 | C0/LGE/T2 |
| Case3040 | 0.0000 | 91 | 2794 | C0/LGE/T2 |
| Case2007 | 0.0000 | 10 | 1303 | C0/LGE/T2 |
| Case2031 | 0.0000 | 261 | 864 | C0/LGE/T2 |
| Case2020 | 0.0000 | 15 | 561 | C0/LGE/T2 |
| Case3044 | 0.0007 | 111 | 5781 | C0/LGE/T2 |

## 代码改动

- `jobs/U-MyoPS/sbatch_stage1.sh`、`jobs/U-MyoPS/sbatch_stage2.sh`：walltime 改为 `08:00:00`。
- `jobs/U-MyoPS/sbatch_stage2.sh`：记录 `UMYOPS_STAGE2_EPOCHS`、trainer、`whichsubnet` 和 max runtime guard。
- `third_party/U-MyoPS_myops/jrs/nnunet/run/load_pretrained_weights.py`：兼容 PyTorch 2.6，允许加载本地可信 nnU-Net checkpoint。
- `third_party/U-MyoPS_myops/jrs/nnunet/training/network_training/nnUNetTrainerPSNV8.py`：best checkpoint/plateau 指标默认改为 scar/class_2，加入 max runtime guard 和 patience 记录。
- `third_party/U-MyoPS_myops/jrs/nnunet/training/network_training/nnUNetTrainerPSNV8ScarCE2.py`：scar CE weight=2.0，同时默认 `oversample_foreground_percent=0.75` 并强制 oversample class 2。
- `third_party/U-MyoPS_myops/jrs/nnunet/training/dataloading/dataset_loading.py`：oversampling 时支持 `UMYOPS_STAGE2_FORCE_OVERSAMPLE_CLASS=2`。
- `scripts/evaluation/report_umyops_round2.py`：生成分组指标、per-case voxel count、Stage1 prior QC。

## 当前短训

已提交 fold0 单假设短训：

```bash
sbatch --parsable --export=ALL,UMYOPS_STAGE2_TRAINER=nnUNetTrainerPSNV8ScarCE2,UMYOPS_STAGE2_EPOCHS=80,FOLD=0,UMYOPS_STAGE2_WHICH_SUBNET=scar,UMYOPS_STAGE2_PRETRAINED_WEIGHTS=/overflow/htzhu/CARE/third_party/U-MyoPS_myops/outputs/nnunet/output/nnUNet/2d/Task901_CARE_UmyopsPathology_fold0/nnUNetTrainerPSNV8__nnUNetPlansv2.1/fold_0/model_final_checkpoint.model,UMYOPS_STAGE2_MAX_RUNTIME_SECONDS=27000,UMYOPS_STAGE2_PATIENCE=20,UMYOPS_STAGE2_EARLYSTOP_METRIC=scar jobs/U-MyoPS/sbatch_stage2.sh
```

- Job: `51256750`
- Log: `logs/U-MyoPS_Stage2_51256750_20260517_042736.log`
- 训练已完成：跑满 80 epoch，未触发 patience early stop；每个 epoch 约 37 秒。
- 训练期 internal Stage2 online metric 中 scar/class_2 多数在 0.58-0.61 区间波动，但这还不是统一 CARE compact label 的病例级 Dice。
- 新 trainer 目录当前只有 `model_final_checkpoint.model`，未看到 2026-05-17 的 `model_best.model`：
  - `third_party/U-MyoPS_myops/outputs/nnunet/output/nnUNet/2d/Task901_CARE_UmyopsPathology_fold0/nnUNetTrainerPSNV8ScarCE2__nnUNetPlansv2.1/fold_0/model_final_checkpoint.model`

## round2 后续状态

round2 训练完成后，尚未形成可信的 unified export/eval 闭环：

- `results/metrics/unified/` 中没有 `nnUNetTrainerPSNV8ScarCE2` 对应的新 fold0 metric 目录。
- `jobs/U-MyoPS/sbatch_export_eval_fold0.sh` 调用 `export_stage2_val_predictions.py` 时没有传 `--trainer`，而 export 脚本默认 `--trainer nnUNetTrainerPSNV8`。如果直接用现有默认导出，会回到旧 trainer，而不是 round2 的 `nnUNetTrainerPSNV8ScarCE2`。
- 因此 round2 的“训练期 internal scar/class_2 高分”和 CARE unified metric 之间尚未校准，不能据此判断 ScarCE2 是否有效。

## 结论与下一步

当前最主要原因仍不能归结为“训练不够久”。在继续改 Stage2 loss 之前，必须先完成三件事：

1. 显式导出 `nnUNetTrainerPSNV8ScarCE2` 的 `model_final_checkpoint` 到独立 prediction/metric 目录。
2. 对 Task901 Stage2 labels 做 oracle remap：`1->4 edema`, `2->5 scar`，直接和 Dataset501 fold0 GT 比较；如果 oracle 都低，说明 Stage2 task construction / geometry / label remap 有问题，继续训练没有意义。
3. 修复 best checkpoint 保存与 export trainer 参数，避免以后把旧 `nnUNetTrainerPSNV8` 结果误当作 ScarCE2。

暂不值得启动 fold1-4。round3 应先闭合 export/eval 与 label 语义校验；只有 ScarCE2 unified fold0 明显高于旧 checkpoint，才继续训练或扩展。
