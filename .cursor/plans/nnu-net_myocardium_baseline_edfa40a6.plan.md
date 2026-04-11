---
name: nnU-Net Myocardium Baseline
overview: 在 `env_CARE` 中准备依赖与 nnU-Net 数据管线；交付可一键运行的训练/测试脚本（.sh 或单入口 .py）供你在 GPU 服务器上提交全量实验。本地无 GPU 节点仅使用 2–3 个 case 做冒烟检查（转换 + plan_and_preprocess + 完整性校验），不进行大规模训练或全量测试。
todos:
  - id: env-install
    content: 在 env_CARE 安装 PyTorch/nnunetv2 及 I/O 依赖；提供 env_nnunet.sh 与 requirements 片段
    status: completed
  - id: scripts-pipeline
    content: 实现数据转换（MyoPS/Cine）、dataset.json、可选 --max-cases；主入口 run_smoke.sh + run_full_train.sh（或等价 .py）
    status: completed
  - id: smoke-local
    content: 本地仅用 2–3 case 跑通 convert → plan_and_preprocess → verify_dataset_integrity（不跑长训练）
    status: completed
  - id: docs-server
    content: 撰写 SERVER.md：服务器上全量训练/推理/评测命令与预期产物路径
    status: completed
isProject: false
---

# nnU-Net 复现（MyoPS + CineMyoPS）执行计划

## 本地（当前节点）与服务器分工


| 阶段        | 环境           | 做什么                                                                                                                                 | 不做什么                            |
| --------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| **开发与验收** | 无 GPU / 本机   | 安装依赖到 `[env_CARE](/overflow/htzhu/CARE/env_CARE)`；写好脚本；**最多 2–3 个 case** 跑 **转换 + `nnUNetv2_plan_and_preprocess` + 数据集完整性检查**，确认无报错 | **大规模训练**、长时推理、全量指标；不假设本地有 CUDA |
| **正式实验**  | 你提交的 GPU 服务器 | 全量数据转换（或同步已生成 `nnUNet_raw`）、完整 `train`、验证集 `predict`、Dice/HD                                                                        | —                               |


## 范围与原则（对齐 [CARE_myocardium_deep_research.md](/overflow/htzhu/CARE/CARE_myocardium_deep_research.md)）

- **仅 CARE Myocardium 赛道数据**：使用 `[data/Myocardium](/overflow/htzhu/CARE/data/Myocardium)`，不碰其余三个 task。
- **两套独立 baseline**：**Dataset A = MyoPS_train**；**Dataset B = CineMyoPS_train**。
- **标签与多模态处理**：同前版计划（三通道 LGE/T2/C0、缺模态补零、LGE 参考重采样；Cine 4D→3D 策略固定写死在脚本与文档中）；readme 中 **Scar 为 2221 或 1** 需统一映射。

## 环境与依赖（固定 `/overflow/htzhu/CARE/env_CARE`）

- 使用 conda 前缀 `[env_CARE](/overflow/htzhu/CARE/env_CARE)`（Python 3.12），安装 `nnunetv2`、`torch`、`torchvision`、`nibabel`、`SimpleITK` 等（**服务器上请安装 CUDA 版 torch**；本地冒烟可无 GPU，仅 CPU 跑预处理）。
- `nnUNet_raw`、`nnUNet_preprocessed`、`nnUNet_results` 指向项目下目录（如 `nnUNet_raw`、`nnUNet_preprocessed`、`nnUNet_results`），由根目录 `env_nnunet.sh` 统一 `export`。

## 交付物：你最终只跑一个入口即可（服务器）

建议结构（路径可微调，写进 `SERVER.md`）：

- `env_nnunet.sh`：环境变量；`conda activate env_CARE` 可通过 `activate.d` 自动 source。
- `scripts/convert_myops_to_nnunet.py`：MyoPS → `nnUNet_raw/DatasetXXX`，支持 `--max-cases 3`（冒烟）。
- `scripts/convert_cine_to_nnunet.py`：CineMyoPS → 另一 Dataset ID，支持 `--max-cases 3`。
- `**scripts/run_smoke.sh`**（或 `run_smoke.py`）：顺序执行——`--max-cases 3` 转换 → `nnUNetv2_plan_and_preprocess -d ... --verify_dataset_integrity`（两套 Dataset 各一次或参数化选择）；**不包含** `nnUNetv2_train` 长运行。
- `**scripts/run_full_train.sh`**（或分步 `01_plan.sh` / `02_train.sh` / `03_predict.sh`）：供服务器使用，包含：
  - 全量转换（不加 max-cases）或跳过若已同步数据；
  - `nnUNetv2_plan_and_preprocess`；
  - `nnUNetv2_train`（fold、configuration 可参数化）；
  - `nnUNetv2_predict` + 可选评测脚本。
- `**SERVER.md`**：一行说明「在 GPU 节点如何 `bash scripts/run_full_train.sh`」、默认 `DATASET_ID`、预计磁盘与时长、如何拉取 `nnUNet_results`。

本地冒烟成功的判据：`run_smoke.sh` 以 exit code 0 结束，且日志中无 dataset 校验错误。

## Dataset A / B 技术要点（摘要，与旧版一致）

- **MyoPS**：三通道 `LGE`/`T2`/`C0`，LGE 为参考网格，缺模态补零。
- **CineMyoPS**：`*_Cine.nii.gz`；若为 4D，在脚本中固定一种 3D 导出策略并在 `SERVER.md` 说明。

## 风险与缓解


| 风险          | 缓解                                         |
| ----------- | ------------------------------------------ |
| 本地无 GPU     | 只跑预处理与脚本逻辑验证；训练一律服务器                       |
| 冒烟 case 过少  | 至少选 1 例多模态齐全 + 1 例缺模态，覆盖转换分支               |
| 服务器环境与本地不一致 | `requirements.txt` + 注明 CUDA 与 torch 版本需匹配 |


## 实施顺序（执行计划时）

1. 依赖 + 目录变量脚本。
2. 转换脚本 + `--max-cases` + 两套 `dataset.json` 模板。
3. `run_smoke.sh` + 2–3 case 本地验证。
4. `run_full_train.sh` + `SERVER.md`（不写「初步数值结论」，留给你全量跑完后填；若需可附「结论模板」段落）。

