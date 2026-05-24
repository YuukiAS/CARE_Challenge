# MyoPS-Net Iteration Log

## 2026-05-17 round2_moddrop_fold0

### 主要假设

CARE MyoPS 训练集中缺模态比例高，现有三模态 `challenge3` 训练把真实缺失 C0/T2 与普通零强度混在一起。先做一个可归因的小轮次：记录 source modality mask，并只对 source-present 的 C0/T2 做轻量 modality dropout；LGE 始终保留。

### 代码改动

- `code/MyoPS-Net/prepare_myops_net_layout.py`: staging 写出 `modalities_present.json`，记录每例 `c0/lge/t2` 是否真实存在。
- `third_party/MyoPS-Net/utils/dataloader.py`: dataloader 读取 source modality mask，返回 `source_mask` / `train_mask`，按 source-present C0/T2 应用 dropout。
- `third_party/MyoPS-Net/utils/tools.py`: 修复全零 placeholder 在 `Truncate` 归一化时产生 NaN 的问题。
- `third_party/MyoPS-Net/train.py`: 记录 train/val 模态组合、每 epoch source/effective dropout 组合、best/last checkpoint、runtime guard、patience stop summary。
- `jobs/MyoPS-Net/sbatch.sh`: 默认 Slurm walltime 改为 `08:00:00`，恢复 timestamped tee logging，并支持隔离的 prediction/metric 输出目录。
- `code/MyoPS-Net/report_modality_groups.py`: 按 LGE-only、C0+LGE、C0+LGE+T2 汇总 fold metrics。

### 命令与预算

```bash
sbatch --export=ALL,FOLD=0,PREPARE=1,MYOPS_NET_DATA=/overflow/htzhu/CARE/data/benchmarks/MyoPS-Net/fold_0_moddrop_round2,MYOPS_NET_WORKDIR=/overflow/htzhu/CARE/results/checkpoints/MyoPS-Net/fold_0_moddrop_round2,MYOPS_NET_VARIANT=challenge3,MYOPS_NET_END_EPOCH=120,MYOPS_NET_MAX_RUNTIME_HOURS=7.75,MYOPS_NET_EARLY_STOP_PATIENCE=20,MYOPS_NET_MODALITY_DROPOUT=1,MYOPS_NET_DROPOUT_C0=0.10,MYOPS_NET_DROPOUT_T2=0.20,MYOPS_NET_PATHOLOGY_SAMPLER=1,MYOPS_NET_EXPORT_EVAL=1,MYOPS_NET_PRED_DIR=/overflow/htzhu/CARE/results/predictions/MyoPS-Net_moddrop_round2/fold_0,MYOPS_NET_EVAL_OUTPUT_DIR=/overflow/htzhu/CARE/results/metrics/unified/MyoPS-Net_moddrop_round2/fold_0 jobs/MyoPS-Net/sbatch.sh
```

- Slurm job: `51256887`
- Slurm walltime: `08:00:00`
- Training runtime guard: `MYOPS_NET_MAX_RUNTIME_HOURS=7.75`
- Fold: `0` only
- Max epochs: `120`
- Early stop patience: `20` validation epochs
- Checkpoint dir: `results/checkpoints/MyoPS-Net/fold_0_moddrop_round2`
- Prediction dir: `results/predictions/MyoPS-Net_moddrop_round2/fold_0`
- Metric dir: `results/metrics/unified/MyoPS-Net_moddrop_round2/fold_0`
- Log: `logs/MyoPS-Net_51256887_20260517_042939.log`

### 启动时核查

- `challenge3` 已用于 training/export 参数。
- `modalities_present.json` 已生成。
- 训练集 source 组合：`LGE` 92 cases / 1369 slices，`C0+LGE` 20 cases / 141 slices，`C0+LGE+T2` 64 cases / 287 slices。
- 验证集 source 组合：`LGE` 24 cases / 309 slices，`C0+LGE` 4 cases / 27 slices，`C0+LGE+T2` 16 cases / 72 slices。
- Pathology sampler enabled: scar-positive 1429 slices, edema-positive 259 slices, both 234 slices.

### 当前基线与分组诊断

已有 fold0 baseline (`results/metrics/unified/MyoPS-Net/fold_0/evaluation_summary.json`):

| subset | n cases | myops_edema class_4 | myops_scar class_5 | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| all fold0 | 44 | 0.2794 | 0.4637 | 0.4039 |
| C0+LGE | 4 | NA | 0.3910 | 0.3910 |
| C0+LGE+T2 | 16 | 0.3143 | 0.6043 | 0.4593 |
| LGE | 24 | 0.0000 | 0.3820 | 0.3690 |

nnU-Net 5-fold baseline from prompt: `myops_scar=0.5592`, `myops_edema=0.4197`.

### 结果

- Stop reason: `early_stop_patience`
- Actual epochs: 49
- Best epoch: 29
- Elapsed: 2787.7 seconds
- Best 2D pathology Dice: 0.2027
- Export/eval checkpoint: `checkpoints/best.pth`

| metric | baseline fold0 | round2_moddrop_fold0 | change |
| --- | ---: | ---: | ---: |
| myops_edema / class_4 | 0.2794 | 0.1496 | -0.1298 |
| myops_scar / class_5 | 0.4637 | 0.4584 | -0.0053 |
| foreground_mean | 0.4039 | 0.3317 | -0.0722 |

| modality group | n cases | myops_edema class_4 | myops_scar class_5 | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| C0+LGE | 4 | 0.0000 | 0.4557 | 0.2278 |
| C0+LGE+T2 | 16 | 0.3367 | 0.5943 | 0.4655 |
| LGE | 24 | 0.0000 | 0.3682 | 0.2598 |

### 下一步判定

- 如果 fold0 `myops_scar` and `myops_edema` both improve or at least edema improves without scar collapse, keep the hypothesis and run folds 1-4 with the same isolated naming.
- Hypothesis result: rejected for overall performance. T2-present edema improved slightly, but overall edema and scar did not improve.
- Do not expand to 5 folds.
- Next round should implement source/effective modality mask aware loss gating, especially skipping T2 edema loss and C0-T2 invariant loss for truly missing T2 cases.

## 2026-05-17 round3_maskgated_fold0

### 主要假设

Round2 的 modality dropout 失败，可能不是因为缺模态方向完全无效，而是因为缺失 C0/T2 或被 dropout 的 C0/T2 仍然参与对应 branch segmentation loss 和 invariant loss。本轮只验证 source/effective modality mask aware loss gating。

### 代码改动

- `third_party/MyoPS-Net/criterion/loss.py`: `MyoPSLoss.forward(..., train_mask=...)` 按有效 sub-batch 计算 C0/LGE/T2 branch loss；C0-LGE 和 C0-T2 invariant loss 只在两端模态有效时计算；空有效样本返回 0 loss。`challenge3` 下 inclusive loss 仍为 0。
- `third_party/MyoPS-Net/train.py`: 将 `train_mask` 传入 loss；每个 epoch 记录有效 loss 样本数：`c0_branch`, `lge_branch`, `t2_branch`, `c0_lge_invariant`, `c0_t2_invariant`。
- `third_party/MyoPS-Net/utils/config.py`: 增加 `--mask_gated_loss`，由 `MYOPS_NET_MASK_GATED_LOSS=1` 控制。
- `code/MyoPS-Net/run_train.sh` / `jobs/MyoPS-Net/sbatch.sh`: 透传并打印 `MYOPS_NET_MASK_GATED_LOSS`。

### 命令与预算

```bash
sbatch --export=ALL,FOLD=0,PREPARE=1,MYOPS_NET_DATA=/overflow/htzhu/CARE/data/benchmarks/MyoPS-Net/fold_0_maskgated_round3,MYOPS_NET_WORKDIR=/overflow/htzhu/CARE/results/checkpoints/MyoPS-Net/fold_0_maskgated_round3,MYOPS_NET_VARIANT=challenge3,MYOPS_NET_END_EPOCH=120,MYOPS_NET_MAX_RUNTIME_HOURS=7.75,MYOPS_NET_EARLY_STOP_PATIENCE=20,MYOPS_NET_MODALITY_DROPOUT=0,MYOPS_NET_MASK_GATED_LOSS=1,MYOPS_NET_PATHOLOGY_SAMPLER=1,MYOPS_NET_SAMPLE_WEIGHT_SCAR=2.0,MYOPS_NET_SAMPLE_WEIGHT_EDEMA=8.0,MYOPS_NET_EXPORT_EVAL=1,MYOPS_NET_PRED_DIR=/overflow/htzhu/CARE/results/predictions/MyoPS-Net_maskgated_round3/fold_0,MYOPS_NET_EVAL_OUTPUT_DIR=/overflow/htzhu/CARE/results/metrics/unified/MyoPS-Net_maskgated_round3/fold_0 jobs/MyoPS-Net/sbatch.sh
```

- Slurm job: `51264396`
- Slurm walltime: `08:00:00`
- Training runtime guard: `MYOPS_NET_MAX_RUNTIME_HOURS=7.75`
- Fold: `0` only
- Max epochs: `120`
- Early stop patience: `20` validation epochs
- Checkpoint dir: `results/checkpoints/MyoPS-Net/fold_0_maskgated_round3`
- Prediction dir: `results/predictions/MyoPS-Net_maskgated_round3/fold_0`
- Metric dir: `results/metrics/unified/MyoPS-Net_maskgated_round3/fold_0`
- Log: `logs/MyoPS-Net_51264396_20260517_060037.log`

### 启动时核查

- `challenge3` enabled; `MYOPS_NET_MODALITY_DROPOUT=0`; `MYOPS_NET_MASK_GATED_LOSS=1`.
- Staging generated `modalities_present.json`.
- Train groups: `LGE` 92 cases / 1369 slices, `C0+LGE` 20 cases / 141 slices, `C0+LGE+T2` 64 cases / 287 slices.
- Val groups: `LGE` 24 cases / 309 slices, `C0+LGE` 4 cases / 27 slices, `C0+LGE+T2` 16 cases / 72 slices.
- Epoch 1 effective loss counts: `c0_branch=890`, `lge_branch=1792`, `t2_branch=823`, `c0_lge_invariant=890`, `c0_t2_invariant=823`.

### 结果状态

- Stop reason: `early_stop_patience`
- Actual epochs: 49
- Best epoch: 29
- Elapsed: 1771.6 seconds
- Best 2D pathology Dice: 0.2039
- Export/eval checkpoint: `checkpoints/best.pth`
- Mask-gated loss: enabled

Prediction sanity:

- Prediction files: 44/44
- Non-empty predictions: 44/44
- Label set: compact CARE labels only, `(0, 4, 5)`
- Bad labels: none

| metric | baseline fold0 | round2_moddrop_fold0 | round3_maskgated_fold0 | nnU-Net 5-fold reference |
| --- | ---: | ---: | ---: | ---: |
| myops_edema / class_4 | 0.2794 | 0.1496 | 0.1293 | 0.4197 |
| myops_scar / class_5 | 0.4637 | 0.4584 | 0.4965 | 0.5592 |
| foreground_mean | 0.4039 | 0.3317 | 0.3129 | NA |

| modality group | n cases | myops_edema class_4 | myops_scar class_5 | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| C0+LGE | 4 | 0.0000 | 0.4072 | 0.2036 |
| C0+LGE+T2 | 16 | 0.3555 | 0.6171 | 0.4863 |
| LGE | 24 | 0.0000 | 0.4311 | 0.2155 |

### 下一步判定

- Hypothesis result: partially supported but not sufficient. Loss gating improved T2-present edema/scar and LGE-only scar, but overall edema worsened because T2-missing groups still produce edema false positives that score as 0 under `--skip-dice-if-gt-empty`.
- Do not expand to folds 1-4.
- Next round should isolate output/inference routing for edema: when T2 is absent, suppress or exclude the T2 edema branch from final `class_4`, or train an edema expert only for T2-present/GT-positive cases. Do not keep forcing LGE-only cases to predict edema.

## 2026-05-17 round4_t2aware_export_fold0

### 主要假设

Round3 的 scar 和 T2-present pathology 已经改善，但 local fold0 overall edema 被 T2-missing source groups 的 class_4 false positives 拖垮。本轮只做 export-only routing/postprocess 消融，不启动新训练。

### 代码改动

- `code/MyoPS-Net/export_val_predictions.py`: 可选写出 C0 cardiac branch myocardium support masks。
- `code/MyoPS-Net/apply_round4_postprocess.py`: 新增 round4 postprocess 入口，支持 `t2_missing_suppress_edema`, `myocardium_limited_pathology`, `small_component_filter`, `combined_safe`，并记录 changed voxels by class/source group。

### 输入与预算

- Fold: `0` only
- Training: none
- Source checkpoint: `results/checkpoints/MyoPS-Net/fold_0_maskgated_round3/checkpoints/best.pth`
- Source predictions: `results/predictions/MyoPS-Net_maskgated_round3/fold_0`
- Source metadata: `data/benchmarks/MyoPS-Net/fold_0_maskgated_round3/modalities_present.json`
- Baseline round3 metrics: edema 0.1293, scar 0.4965, foreground_mean 0.3129.
- HD/HD95: not computed; Dice and changed-voxel counts were sufficient for this routing decision.

### 变体结果

| variant | rule | myops_edema class_4 | myops_scar class_5 | foreground_mean | affects official T2-present cases |
| --- | --- | ---: | ---: | ---: | --- |
| `t2_missing_suppress_edema` | T2 absent: class_4 -> 0 | 0.3555 | 0.4965 | 0.4490 | no |
| `myocardium_limited_pathology` | remove class_4/class_5 outside prediction-derived support | 0.1358 | 0.4986 | 0.3172 | yes |
| `small_component_filter` | remove class_4/class_5 3D components `<20` voxels | 0.1293 | 0.4963 | 0.3128 | yes |
| `combined_safe` | T2 suppression + prediction-derived support | 0.3733 | 0.5048 | 0.4589 | yes |

### Source-group summary

| variant | group | n cases | myops_edema class_4 | myops_scar class_5 | foreground_mean |
| --- | --- | ---: | ---: | ---: | ---: |
| `t2_missing_suppress_edema` | C0+LGE | 4 | NA | 0.4072 | 0.4072 |
| `t2_missing_suppress_edema` | C0+LGE+T2 | 16 | 0.3555 | 0.6171 | 0.4863 |
| `t2_missing_suppress_edema` | LGE | 24 | NA | 0.4311 | 0.4311 |
| `myocardium_limited_pathology` | C0+LGE | 4 | 0.0000 | 0.4087 | 0.2043 |
| `myocardium_limited_pathology` | C0+LGE+T2 | 16 | 0.3733 | 0.6258 | 0.4996 |
| `myocardium_limited_pathology` | LGE | 24 | 0.0000 | 0.4288 | 0.2144 |
| `small_component_filter` | C0+LGE | 4 | 0.0000 | 0.4099 | 0.2050 |
| `small_component_filter` | C0+LGE+T2 | 16 | 0.3555 | 0.6180 | 0.4867 |
| `small_component_filter` | LGE | 24 | 0.0000 | 0.4295 | 0.2148 |
| `combined_safe` | C0+LGE | 4 | NA | 0.4068 | 0.4068 |
| `combined_safe` | C0+LGE+T2 | 16 | 0.3733 | 0.6258 | 0.4996 |
| `combined_safe` | LGE | 24 | NA | 0.4404 | 0.4404 |

### Changed-voxel notes

- `t2_missing_suppress_edema`: changed only T2-missing cases; removed 447237 class_4 voxels from C0+LGE and 8136171 class_4 voxels from LGE; no T2-present changes.
- `myocardium_limited_pathology`: changed T2-present cases; removed 4154 class_4 and 2351 class_5 voxels in C0+LGE+T2.
- `small_component_filter`: changed T2-present cases; removed 566 class_4 and 213 class_5 voxels in C0+LGE+T2; not useful overall.
- `combined_safe`: changed T2-missing edema plus prediction-derived support; removed all T2-missing class_4 and removed 4154 class_4 / 2351 class_5 voxels in C0+LGE+T2.

### 下一步判定

- Hypothesis result: supported. T2-missing class_4 false positives were the dominant local overall-edema failure.
- `t2_missing_suppress_edema` is safe for official validation compatibility because official validation cases are expected to be T2-present.
- `combined_safe` is the strongest fold0 local result, but it changes T2-present predictions; use it only if official-validation-specific rationale accepts that change.
- Do not expand to folds 1-4 yet. One more fold0-only round can train or route a T2-present edema expert while preserving LGE scar supervision.

## 2026-05-17 round4_t2aware_export_only_fold0

### 主要假设

Round3 的 T2-present pathology 已改善，但整体 `myops_edema` 被 T2-missing cases 的 class_4 false positives 拖垮。本轮先做 export-only T2-aware routing / postprocess ablation，不启动训练。

### 代码改动

- `code/MyoPS-Net/export_val_predictions.py`: 增加可选 `--myocardium-support-dir`，可保存 C0 branch myocardium support mask。CPU 导出太慢，本轮最终未依赖该 support。
- `code/MyoPS-Net/apply_round4_postprocess.py`: 新增 postprocess ablation 脚本，支持 `t2_missing_suppress_edema`, `myocardium_limited_pathology`, `small_component_filter`, `combined_safe`，并输出 changed-voxel summaries。

### 输入与输出

- Source checkpoint: `results/checkpoints/MyoPS-Net/fold_0_maskgated_round3/checkpoints/best.pth`
- Source predictions: `results/predictions/MyoPS-Net_maskgated_round3/fold_0`
- Fold: `0` only
- No training job was launched.

Variant outputs:

| variant | prediction dir | metric dir |
| --- | --- | --- |
| `t2_missing_suppress_edema` | `results/predictions/MyoPS-Net_round4_t2_missing_suppress_edema/fold_0` | `results/metrics/unified/MyoPS-Net_round4_t2_missing_suppress_edema/fold_0` |
| `myocardium_limited_pathology` | `results/predictions/MyoPS-Net_round4_myocardium_limited_pathology/fold_0` | `results/metrics/unified/MyoPS-Net_round4_myocardium_limited_pathology/fold_0` |
| `small_component_filter` | `results/predictions/MyoPS-Net_round4_small_component_filter/fold_0` | `results/metrics/unified/MyoPS-Net_round4_small_component_filter/fold_0` |
| `combined_safe` | `results/predictions/MyoPS-Net_round4_combined_safe/fold_0` | `results/metrics/unified/MyoPS-Net_round4_combined_safe/fold_0` |

### 整体结果

| variant | myops_edema / class_4 | myops_scar / class_5 | foreground_mean | official T2-present affected |
| --- | ---: | ---: | ---: | --- |
| round3 mask-gated | 0.1293 | 0.4965 | 0.3129 | NA |
| `t2_missing_suppress_edema` | 0.3555 | 0.4965 | 0.4490 | false |
| `myocardium_limited_pathology` | 0.1358 | 0.4986 | 0.3172 | true |
| `small_component_filter` | 0.1293 | 0.4963 | 0.3128 | true |
| `combined_safe` | 0.3733 | 0.5048 | 0.4589 | true |
| nnU-Net 5-fold reference | 0.4197 | 0.5592 | NA | NA |

### T2-present subgroup

| variant | myops_edema / class_4 | myops_scar / class_5 | foreground_mean |
| --- | ---: | ---: | ---: |
| round3 mask-gated | 0.3555 | 0.6171 | 0.4863 |
| `t2_missing_suppress_edema` | 0.3555 | 0.6171 | 0.4863 |
| `myocardium_limited_pathology` | 0.3733 | 0.6258 | 0.4996 |
| `small_component_filter` | 0.3555 | 0.6180 | 0.4867 |
| `combined_safe` | 0.3733 | 0.6258 | 0.4996 |

### Changed voxels

| variant | changed voxels | class_4 removed | class_5 removed |
| --- | ---: | ---: | ---: |
| `t2_missing_suppress_edema` | 8,583,408 | 8,583,408 | 0 |
| `myocardium_limited_pathology` | 28,522 | 25,773 | 2,749 |
| `small_component_filter` | 13,432 | 12,278 | 1,154 |
| `combined_safe` | 8,596,557 | 8,587,562 | 8,995 |

### 下一步判定

- Hypothesis result: supported. T2-missing edema suppression alone recovers overall edema from 0.1293 to 0.3555 without changing T2-present cases or scar.
- Strongest export-only variant: `combined_safe`, with overall edema 0.3733, scar 0.5048, and T2-present scar 0.6258.
- Do not expand to folds 1-4: scar remains below nnU-Net 5-fold reference 0.5592, and `combined_safe` changes official T2-present cases.
- Recommendation: keep `combined_safe` as the best MyoPS-Net official-validation-specific ablation candidate, but keep nnU-Net as primary unless leaderboard validation shows this route helps. Do not start longer MyoPS-Net training; any next training must be a distinct T2-present edema expert or calibrated official-validation export.

## 2026-05-17 round5 result + round6 hybrid export prepared

### Completed result

Round5 full-modality expert completed on complete C0+LGE+T2 fold0 cases:

| variant | eval scope | n | myops_edema / class_4 | myops_scar / class_5 |
| --- | --- | ---: | ---: | ---: |
| round5 full-modality expert | complete C0+LGE+T2 val cases | 16 | 0.3746 | 0.6163 |
| round4 `combined_safe` | all val cases | 44 | 0.3733 | 0.5048 |
| nnU-Net Dataset501 5-fold | reference | 5 folds | 0.4197 | 0.5592 |

### Interpretation

- Scar improved strongly on complete-modality cases and exceeds the nnU-Net scar reference on that subgroup.
- Edema remains below nnU-Net, so the full-modality expert does not solve Lb2.
- Round5 was not an all-case solution because staging/eval was filtered to 16 complete cases.

### Prepared round6

- `code/MyoPS-Net/build_round6_hybrid.py`: routes complete C0+LGE+T2 cases to round5 fullmod predictions and T2-missing cases to round4 fallback predictions.
- `jobs/MyoPS-Net/sbatch_round6_hybrid_export.sh`: export-only, 2h walltime, no training. It evaluates:
  - `results/metrics/unified/MyoPS-Net_round6_fullmod_on_allval/fold_0`
  - `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0`

### Next command

```bash
sbatch jobs/MyoPS-Net/sbatch_round6_hybrid_export.sh
```

## 2026-05-17 round6_hybrid_export_fold0

### 主要假设

Round5 full-modality expert 在完整 C0+LGE+T2 子集上 scar 较强，但尚未证明能成为 all-case fold0 改进。本轮不训练，只导出 fullmod-on-allval，并构建 complete cases -> round5、T2-missing cases -> round4 `combined_safe` 的 hybrid routing。

### 代码改动

- `code/MyoPS-Net/build_round6_hybrid.py`: 增加 `--fold-json` / `--fold`，只路由 protocol fold0 validation cases。第一次 job 发现 `modalities_present.json` 含 train+val 全部病例，不能作为 case list。
- `jobs/MyoPS-Net/sbatch_round6_hybrid_export.sh`: 传入 `--fold-json` 和 `--fold`。
- `jobs/MyoPS-Net/README.md`: 记录 routing case list 必须来自 fold split。

### 作业与输出

- Failed diagnostic job: `51354700`; fullmod-on-allval export/eval succeeded, hybrid routing failed on train case `Case1001`.
- Completed job: `51354774`; export-only, no training.
- Fullmod metric dir: `results/metrics/unified/MyoPS-Net_round6_fullmod_on_allval/fold_0`
- Hybrid metric dir: `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0`
- Routing summary: `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0/routing_summary.json`

### 整体结果

| variant | scope | n | myops_edema / class_4 | myops_scar / class_5 | foreground_mean |
| --- | --- | ---: | ---: | ---: | ---: |
| round4 `combined_safe` | all val cases | 44 | 0.3733 | 0.5048 | 0.4589 |
| round5 fullmod expert | complete C0+LGE+T2 only | 16 | 0.3746 | 0.6163 | 0.4954 |
| round6 fullmod on all-val | all val cases | 44 | 0.1362 | 0.3843 | 0.2603 |
| round6 hybrid fullmod + round4 | all val cases | 44 | 0.3746 | 0.5013 | 0.4574 |
| nnU-Net Dataset501 5-fold reference | all folds | 5 folds | 0.4197 | 0.5592 | NA |

### Source-group summary

| variant | modality group | n cases | myops_edema / class_4 | myops_scar / class_5 | foreground_mean |
| --- | --- | ---: | ---: | ---: | ---: |
| fullmod-on-allval | C0+LGE | 4 | 0.0000 | 0.4118 | 0.2059 |
| fullmod-on-allval | C0+LGE+T2 | 16 | 0.3746 | 0.6163 | 0.4954 |
| fullmod-on-allval | LGE | 24 | 0.0000 | 0.2251 | 0.1125 |
| hybrid | C0+LGE | 4 | NA | 0.4068 | 0.4068 |
| hybrid | C0+LGE+T2 | 16 | 0.3746 | 0.6163 | 0.4954 |
| hybrid | LGE | 24 | NA | 0.4404 | 0.4404 |

Routing counts: `fullmod_t2_present=16`, `fallback_t2_missing=28`.

### 下一步判定

- Fullmod expert collapses on missing-modality cases if used directly on all-val: all-case scar 0.3843 and LGE-only scar 0.2251.
- Hybrid routing prevents that collapse, but does not improve round4 all-case performance: edema changes 0.3733 -> 0.3746, scar drops 0.5048 -> 0.5013.
- Hybrid remains below nnU-Net on both primary labels: edema 0.3746 < 0.4197 and scar 0.5013 < 0.5592.
- Do not expand folds 1-4. Keep nnU-Net as primary MyoPS baseline/submission path. If MyoPS-Net continues, restrict it to one small T2-present edema calibration/expert round; do not continue generic fullmod or long training.

## 2026-05-18 round7_edema_calibration_and_scar_preservation

### 主要假设

Round5/fullmod expert 的 complete-case edema 可能能补 round4 `combined_safe` 的 edema，同时 round4 是更稳的 all-case scar route。本轮只做 export-only calibration，不训练，不扩展 folds 1-4。

### 代码改动

- `code/MyoPS-Net/apply_round7_edema_calibration.py`: 新增 scar-preserving round7 label-level 校准脚本；所有变体最后重用 round4 `class_5` scar。
- `jobs/MyoPS-Net/sbatch_round7_edema_calibration.sh`: 新增 2h fold0 可复现实验入口。
- `code/MyoPS-Net/export_val_predictions.py`: 新增 `--edema-softmax-dir`，为后续如需 T2 edema probability threshold sweep 提供 softmax 导出能力。
- `jobs/MyoPS-Net/README.md`: 记录 round7 变体、运行命令和输出目录。

### 命令与运行

- Local CPU-only postprocess/evaluation was run with `./env_CARE/bin/python`; no training job and no GPU Slurm job were submitted.
- Reusable command: `sbatch jobs/MyoPS-Net/sbatch_round7_edema_calibration.sh`.
- Fold/scope: fold0 protocol validation, n=44.
- Evaluation: `scripts/evaluation/evaluate_predictions.py --foreground-classes 4,5 --skip-dice-if-gt-empty`.

### 输出

| variant | prediction dir | metric dir |
| --- | --- | --- |
| `keep_round4_scar_round5_edema_complete` | `results/predictions/MyoPS-Net_round7_keep_round4_scar_round5_edema_complete/fold_0` | `results/metrics/unified/MyoPS-Net_round7_keep_round4_scar_round5_edema_complete/fold_0` |
| `edema_component_filter` | `results/predictions/MyoPS-Net_round7_edema_component_filter/fold_0` | `results/metrics/unified/MyoPS-Net_round7_edema_component_filter/fold_0` |
| `round5_edema_component_filter` | `results/predictions/MyoPS-Net_round7_round5_edema_component_filter/fold_0` | `results/metrics/unified/MyoPS-Net_round7_round5_edema_component_filter/fold_0` |
| `edema_support_limited` | `results/predictions/MyoPS-Net_round7_edema_support_limited/fold_0` | `results/metrics/unified/MyoPS-Net_round7_edema_support_limited/fold_0` |

### 整体结果

| variant | n | myops_edema / class_4 | myops_scar / class_5 | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| round4 `combined_safe` reference | 44 | 0.3733 | 0.5048 | 0.4589 |
| `keep_round4_scar_round5_edema_complete` | 44 | 0.3403 | 0.5048 | 0.4529 |
| `edema_component_filter` | 44 | 0.3730 | 0.5048 | 0.4588 |
| `round5_edema_component_filter` | 44 | 0.3437 | 0.5048 | 0.4535 |
| `edema_support_limited` | 44 | 0.3733 | 0.5048 | 0.4589 |
| nnU-Net Dataset501 5-fold reference | 5 folds | 0.4197 | 0.5592 | NA |

### Source-group summary

| variant | modality group | n cases | myops_edema / class_4 | myops_scar / class_5 | foreground_mean |
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

### 下一步判定

- No export-only round7 variant improved edema beyond `0.39`; best result remains round4 `combined_safe` edema 0.3733 and scar 0.5048.
- Round5/fullmod edema copied onto complete cases worsened edema after preserving round4 scar.
- Component filtering did not help; support limiting was a no-op because round4 combined_safe had already constrained pathology support.
- Do not expand folds 1-4 and do not continue postprocess stacking. Keep nnU-Net as the primary MyoPS submission/baseline route.
- If continuing MyoPS-Net, the next round must be a distinct <=8h fold0 model-level attempt: T2-present edema expert, T2-aware edema head, modality-mask/dropout fusion, or robust missing-modality adaptation.

## 2026-05-19 round8_t2aware_hd_loss_exit_gate

### 主要假设

MyoPS-Net 的失败不再归因于 export 后处理，而是小病灶在缺模态训练中被稀释。本轮做最后一次模型级 fold0 尝试：complete-case T2-aware edema/scar expert，加入 Focal-Tversky、boundary/HD surrogate 和 myocardium ROI penalty。如果仍不能接近 nnU-Net，则停止 MyoPS-Net 主线。

### Leaderboard refresh

Command:

```bash
python scripts/leaderboard/fetch_care2026_scores.py
```

Latest hosted OrganAgent nnU-Net branch:

| hosted metric | Dice | HD | rank |
| --- | ---: | ---: | ---: |
| `myops_scar` | 0.5969 | 16.2536 | 4/5 |
| `myops_edema` | 0.6496 | 22.0125 | 4/5 |

### 代码改动

- `code/MyoPS-Net/report_round8_hd_profile.py`: 新增 nnU-Net vs MyoPS-Net fold0 Dice/HD/HD95/component/outlier 诊断。
- `third_party/MyoPS-Net/criterion/loss.py`: 新增可选 round8 loss 项：binary Focal-Tversky、boundary-gradient loss、myocardium ROI penalty。
- `jobs/MyoPS-Net/sbatch_round8_t2aware_hd_expert.sh`: 新增 <=8h fold0 complete-case expert 训练、raw export/eval、round4-scar hybrid eval。
- `jobs/MyoPS-Net/README.md`: 记录 round8 命令、输出和 exit gate。

### Diagnostics

Output:

- `results/diagnostics/baseline_paper_models/MyoPS-Net/round08_hd_profile/MyoPS-Net_round8_nnunet_vs_myopsnet_hd_profile.csv`
- `results/diagnostics/baseline_paper_models/MyoPS-Net/round08_hd_profile/MyoPS-Net_round8_nnunet_vs_myopsnet_hd_profile.md`

| model | class | Dice | HD | HD95 | mean components | small comps | remote comps |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MyoPS-Net round4 combined_safe | edema | 0.3733 | 29.1300 | 18.9050 | 3.7273 | 102 | 4 |
| MyoPS-Net round4 combined_safe | scar | 0.5048 | 32.6475 | 21.2635 | 1.2955 | 4 | 1 |
| nnU-Net fold0 | edema | 0.3944 | 29.6089 | 20.0115 | 3.3182 | 109 | 1 |
| nnU-Net fold0 | scar | 0.5602 | 25.9706 | 13.6005 | 4.6818 | 144 | 2 |

### 作业

- Slurm job: `51529189`
- Log: `logs/MyoPS-Net_Round8HD_51529189_20260519_083832.log`
- Partition: `htzhulab`
- Walltime request: 8h
- Actual stop: `early_stop_patience`
- Actual elapsed: 777.3 sec
- Best epoch: 12/80
- Best 2D validation: scar 0.0996, edema 0.0566, weighted metric 0.0709

Training split and validation split:

| split | modality filter | cases | slice lines |
| --- | --- | ---: | ---: |
| train | C0+LGE+T2 complete only | 64 | 1435 |
| val | full protocol fold0 | 44 | 408 |

### Outputs

| variant | prediction dir | metric dir |
| --- | --- | --- |
| raw expert | `results/predictions/MyoPS-Net_round8_t2aware_hd_raw/fold_0` | `results/metrics/unified/MyoPS-Net_round8_t2aware_hd_raw/fold_0` |
| round4-scar hybrid | `results/predictions/MyoPS-Net_round8_t2aware_hd_round4scar_hybrid/fold_0` | `results/metrics/unified/MyoPS-Net_round8_t2aware_hd_round4scar_hybrid/fold_0` |
| edema softmax maps | `results/predictions/MyoPS-Net_round8_t2aware_hd_edema_softmax/fold_0` | diagnostic only |

### 整体结果

| variant | n | myops_edema / class_4 | myops_scar / class_5 | edema HD | scar HD | edema HD95 | scar HD95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| nnU-Net fold0 | 44 | 0.3944 | 0.5602 | 10.7669 | 25.9706 | 7.2769 | 13.6005 |
| round4 `combined_safe` | 44 | 0.3733 | 0.5048 | 29.1300 | 32.6475 | 18.9050 | 21.2635 |
| round8 raw expert | 44 | 0.2779 | 0.2426 | 17.2042 | 48.7825 | 10.0216 | 23.3077 |
| round8 round4-scar hybrid | 44 | 0.3293 | 0.5048 | 15.6402 | 32.6475 | 9.1328 | 21.2635 |

### Source-group summary

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

### Exit gate

Failed. Round8 does not meet either continuation criterion:

- All-case gate scar >=0.535 and edema >=0.40: raw expert 0.2426/0.2779, hybrid 0.5048/0.3293.
- Complete-case superiority vs nnU-Net: raw expert 0.6135 scar and 0.3474 edema vs nnU-Net 0.6933 scar and 0.3944 edema.

### 下一步判定

- Stop MyoPS-Net baseline-improvement mainline before round9/10.
- Do not expand folds 1-4.
- Keep nnU-Net as the MyoPS submission baseline.
- If continuing custom modeling, move to `src/` with a new architecture: CAA-Seg/SSA-style sequence alignment, anatomy/pathology cascade, and nnU-Net/MedNeXt-style pathology head. Reuse only the useful infrastructure from MyoPS-Net rounds: diagnostics, modality metadata, T2-present subgroup reporting, and ROI/boundary loss ideas.
