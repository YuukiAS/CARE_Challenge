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
