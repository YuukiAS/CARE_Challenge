# U-MyoPS（论文 baseline）

CARE 对本模型的入口脚本在 **`code/U-MyoPS/`** 与本目录；上游代码在 **`third_party/U-MyoPS_myops`**。

**完整中文说明（目录结构、Stage1/2、缺口、环境、`models/` 权重）：请阅读**

→ **[`third_party/U-MyoPS_myops/README-CN.md`](../../third_party/U-MyoPS_myops/README-CN.md)**

下文仅保留最常用的命令与环境提示。

---

## 快速参考

- **Stage 1**：联合配准 + 心肌 — `code/U-MyoPS/run_stage1.sh`。上游默认 `--phase` 为 `metric`（几乎不训练）；CARE 默认 **`UMYOPS_STAGE1_PHASE=train`**。
- **Stage 1 数据协议（CARE patch）**：prepare 脚本现在会为每个病例写 `subject_meta.json`，按有效 `z` slices + per-slice bbox 训练/推断；不再默认丢成单个中心层。`run_stage1.sh` 也会在 staging 缺失 manifest 时自动重建。
- **Stage 1 legacy layout**：`code/U-MyoPS/prepare_stage1_layout.sh` 会自动把 CARE staging 接到上游 `jrs` 期待的 `third_party/U-MyoPS_myops/data/gen_<data_source>/{data,croped}`。
- **Stage 2**：病理 nnU-Net v1 — `code/U-MyoPS/run_stage2.sh` → `pathology_segmentation_train.py`。
- **Python**：默认 `CARE_CineMyoPS_ENV`（常与 CineMyoPS v1 共用），一般为 `env_CARE_nnUNet_v1`；可用 `UMYOPS_PYTHON` / `LEGACY_PYTHON` 覆盖。
- **本地**：`run.sh` = prepare → Stage1；**`env_nnunet.sh`** 中 **`UMYOPS_RUN_STAGE2=1`** 才在同一 shell 跑 Stage2。
- **Slurm / 统一 benchmark**：在 **`jobs/run_unified_benchmark_all.sh`** 与 **`run_unified_benchmark_test.sh`** 里，`BENCHMARK_MODEL_PLAN` 下方用 **`UMYOPS_BENCHMARK_STAGES`**（默认 **`stage1`**）控制：仅 Stage1、仅 Stage2、或 **`both`** / **`all`**（Stage1→Stage2，`afterok`）。仅当计划中 **`U-MyoPS=run`** 时生效。脚本：`sbatch_stage1.sh`、`sbatch_stage2.sh`。

### Stage2 前置（必读）

Stage2 使用 **本仓库内** 的 nnU-Net v1 路径（**不是** `data/nnUNet` 的 v2）：

- `third_party/U-MyoPS_myops/outputs/nnunet/raw/nnUNet_raw_data/<UMYOPS_STAGE2_TASK>/`
- `third_party/U-MyoPS_myops/outputs/nnunet/prepro/...`（需先 **`plan_and_preprocess`**，例如存在 `nnUNetPlansv2.1_plans_2D.pkl` 当 `UMYOPS_STAGE2_DIM=2d`）

默认会按 fold 生成独立 Task，因为 prior 通道来自该 fold 的 Stage1 输出：

- `UMYOPS_STAGE2_TASK=Task901_CARE_UmyopsPathology`
- `UMYOPS_STAGE2_PER_FOLD_TASK=1`
- fold 0 实际 Task 名会解析为 `Task901_CARE_UmyopsPathology_fold0`

手动构建 Stage2 raw Task + preprocess：

```bash
FOLD=0 bash code/U-MyoPS/prepare_stage2_task.sh
```

### GPU 冒烟（推荐验收）

在已有 Stage2 `plan_and_preprocess` 产物时，用少量 epoch 验证 nnU-Net v1 训练能启动（默认 **Stage2**，不重跑 preprocess）：

从仓库根目录提交 Slurm（以便 **`SLURM_SUBMIT_DIR`** 指向 `CARE_ROOT`；脚本在调度器 spool 中执行时不能依赖 `BASH_SOURCE` 的目录名解析兄弟脚本）：

```bash
cd /overflow/htzhu/CARE
sbatch jobs/U-MyoPS/sbatch_smoke.sh

# 只跑 Stage1 短训（子集数据 + 少量 epoch）
UMYOPS_SMOKE_TARGET=stage1 UMYOPS_STAGE1_EPOCHS=3 UMYOPS_PREPARE_MAX_CASES=12 sbatch jobs/U-MyoPS/sbatch_smoke.sh
```

`sbatch_stage1.sh` / `sbatch_stage2.sh` 若已由外层设置 **`LOG_FILE`**（例如 `sbatch_smoke.sh`），则沿用该路径，便于冒烟与正式任务区分。

### Stage2 导出 + unified eval（fold 0，GPU）

对指定 nnU-Net checkpoint 做推理（非默认 checkpoint 时使用 GPU fallback）→ CARE 4/5 remap → `evaluate_predictions.py`：

```bash
cd /overflow/htzhu/CARE
UMYOPS_EXPORT_CHECKPOINT=model_best sbatch jobs/U-MyoPS/sbatch_export_eval_fold0.sh
```

产物：`results/predictions/U-MyoPS_<chk>/fold_0/`、`results/metrics/unified/U-MyoPS_<chk>/fold_0/evaluation_summary.json`。迭代记录见 `results/experiments/U-MyoPS_iteration_log.md`。

### Round4/5 LGE-only no-prior 对照

Round4 已确认 `Task912_CARE_UmyopsLGEOnlyNoPrior_fold0` 能显著修复 scar：`model_final_checkpoint` 在 task-specific `v2` 导出下达到 all-cases `myops_scar=0.5248`、`myops_edema=0.6726`；完整三序列病例 scar 为 `0.6524`，但 edema 只有 `0.1622`。因此当前 U-MyoPS 更适合作为 scar 专家，不应直接当作完整 MyoPS edema 方案。

下一步使用短导出脚本比较 final/best checkpoint，不重新训练：

```bash
cd /overflow/htzhu/CARE
sbatch jobs/U-MyoPS/sbatch_round5_export_compare.sh
```

输出：

- `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_final_checkpoint/fold_0/evaluation_summary.json`
- `results/metrics/unified/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0/evaluation_summary.json`
- grouped diagnostics in the same metric directories

注意：`code/U-MyoPS/export_stage2_val_predictions.py` 的 fallback temp root 已包含 task name，避免不同 Stage2 Task 复用旧 nnU-Net prediction cache。比较 variant 时不要手动指向旧 cache。

### Round6 missing-modality scar calibration

Round6 不训练，比较 U-MyoPS Task912 `model_best` 与 nnU-Net501 fold0，并生成纯 U-MyoPS scar 标定与明确标注的 hybrid routing 预测目录：

```bash
cd /overflow/htzhu/CARE
sbatch jobs/U-MyoPS/sbatch_round6_scar_calibration.sh
```

诊断输出：

- `results/diagnostics/baseline_paper_models/U-MyoPS/round06_scar_vs_nnunet/per_case_umyops_vs_nnunet_scar.csv`
- `results/diagnostics/baseline_paper_models/U-MyoPS/round06_scar_vs_nnunet/per_case_umyops_vs_nnunet_scar.md`

预测/指标输出包括：

- `U-MyoPS_round6_scar_component_filter_100`
- `U-MyoPS_round6_scar_component_filter_250`
- `U-MyoPS_round6_missing_volume_cap_1500`
- `U-MyoPS_round6_scar_complete_umyops_missing_nnunet`（hybrid scar diagnostic）
- `U-MyoPS_round6_complete_umyops_missing_nnunet`（hybrid full diagnostic）

含 `nnunet` 的 round6 目录是 hybrid diagnostic，不是纯 U-MyoPS，也不是论文完整 U-MyoPS 复现。

### Stage2 继续训练（不重建 Task）

在已有 `fold_k` 输出目录上追加 epoch：

```bash
sbatch --export=ALL,UMYOPS_STAGE2_CONTINUE=1,UMYOPS_STAGE2_EPOCHS=50,UMYOPS_STAGE2_AUTO_PREP=0,FOLD=0 -t 08:00:00 \
  jobs/U-MyoPS/sbatch_stage2.sh
```

这一步会：

- 从 Stage1 `gen_res/` 构建 4 通道 raw Task
- 写入 `imagesTr/labelsTr/dataset.json`
- 运行 vendored nnU-Net v1 `nnUNet_plan_and_preprocess`
- 把 `data/benchmarks/protocol/splits_MyoPS.json` 写成该 Task 的 `splits_final.pkl`

未完成 Task 与预处理时，Stage2 会在缺 plans pkl 等步骤报错。

`run_stage2.sh` 已导出绝对路径的 `nnUNet_raw_data_base`、`nnUNet_preprocessed`、`RESULTS_FOLDER`，与工作目录无关。

如果希望 Stage2 sbatch 自动完成上面的桥接与 preprocess，可开启：

```bash
export UMYOPS_STAGE2_AUTO_PREP=1
```

这不会改变 `UMYOPS_RUN_STAGE2` 的默认值；本地 `run.sh` 仍默认只跑 Stage1。

Stage1 兼容目录默认自动准备：

```bash
export UMYOPS_STAGE1_AUTO_LAYOUT=1
```

---

## 权重收集

```bash
bash jobs/collect_benchmark_weights.sh --only U-MyoPS --folds "0 1 2 3 4"
```

输出 **`models/U-MyoPS/fold_k/stage1`** 与 **`stage2`**；详见 **`README-CN.md`** 第六节。

Stage1 路径发现会优先匹配这些变量，对应训练时的 `model_id` 片段：

- `UMYOPS_NET`，默认 `tps`
- `UMYOPS_DATA_SOURCE`，默认 `ZS_unaligned`
- `UMYOPS_WEIGHT`，默认 `1.0`

如果这些变量与实际训练不一致，收集脚本会退回到 `third_party/U-MyoPS_myops/outputs/*_foldk` 的启发式发现逻辑。
