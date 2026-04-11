# CARE Myocardium — nnU-Net baseline（验证集）

本文档汇总 **MyoPS（Dataset 501）** 与 **CineMyoPS（Dataset 502）** 在默认 nnU-Net v2 流程下的 **fold 0 验证集** 表现。指标来源：`data/nnUNet/nnUNet_results/.../fold_0/validation/summary.json`（或 `$nnUNet_results` 等价路径）与对应训练日志中的 `Mean Validation Dice`。

## 共同实验设置

| 项目 | 内容 |
|------|------|
| Plans | `nnUNetPlans` |
| 配置 | `3d_fullres` |
| Fold | `0` |
| 训练器 | `nnUNetTrainer`（默认） |
| 编译 | `torch.compile` 开启 |
| 训练轮数 | 1000 epochs（0–999） |

## 整体指标（前景平均）

| 任务 | Dataset ID | 划分（fold 0） | Mean Validation Dice | Mean IoU（前景） |
|------|------------|----------------|----------------------|------------------|
| MyoPS | 501 | 176 train / **44 val** | **0.7113** | **0.607** |
| CineMyoPS | 502 | 51 train / **13 val** | **0.6263** | **0.513** |

数值与 `summary.json` 中 `foreground_mean.Dice` / `foreground_mean.IoU` 一致。

## MyoPS — 按类别 Dice

多序列输入（LGE / T2 / C0），五类前景（`dataset.json`）。

| ID | 结构 | Mean Dice |
|----|------|-----------|
| 1 | myocardium | 0.751 |
| 2 | LV_blood | 0.915 |
| 3 | RV_blood | 0.876 |
| 4 | edema | 0.424 |
| 5 | scar | 0.591 |

**说明：** 类别 4（edema）整体最低。部分验证病例在 GT 中无某些类别时，逐例指标中可能出现 `NaN`，但数据集级 `mean` 仍给出上表。

## CineMyoPS — 按类别 Dice

单通道 Cine，三类前景；瘢痕在数据集中为紧凑标签 ID 3（`dataset.json`）。

| ID | 结构 | Mean Dice |
|----|------|-----------|
| 1 | myocardium | 0.687 |
| 2 | LV_blood | 0.900 |
| 3 | scar | 0.292 |

**说明：** 心肌与血池 Dice 较高，**瘢痕（3）明显偏低**，是拉低整体 Mean Validation Dice 的主因。

## 结果与日志路径

**Summary JSON（推荐引用）：**

- MyoPS: `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer__nnUNetPlans__3d_fullres/fold_0/validation/summary.json`
- CineMyoPS: `data/nnUNet/nnUNet_results/Dataset502_CARECineMyoPS/nnUNetTrainer__nnUNetPlans__3d_fullres/fold_0/validation/summary.json`

**对应训练日志（Job 示例）：**

- MyoPS: `logs/MyoPS_42707775_20260410_004654.log`
- CineMyoPS: `logs/CineMyoPS_42782948_20260410_122834.log`

## 简要结论

在相同 **3d_fullres、fold 0、1000 epoch** 设定下，**MyoPS 前景平均 Dice ≈ 0.71**，**CineMyoPS ≈ 0.63**。任务难度与模态差异并存：Cine 上单帧瘢痕分割更难；MyoPS 上 edema 相对最弱。

---

## 论文基准方法（待填）

与 nnU-Net 默认训练器对比时，将下列公开实现跑在 **CARE** 数据上；指标与日志路径在跑通后填入。

| 方法 | 源码 | 数据根目录 | 主要指标（TBD） | 结果 / 日志路径（TBD） |
|------|------|------------|-----------------|------------------------|
| **MyoPS-Net** | [QJYBall/MyoPS-Net](https://github.com/QJYBall/MyoPS-Net) | `data/CARE_Challenge/MyoPS_train` → 准备至 `data/benchmarks/MyoPS-Net/` | Dice / HD 等 | `data/benchmarks/MyoPS-Net/outputs/` 或上游约定路径；入口 `code/MyoPS-Net/run.sh` |
| **U-MyoPS**（myops） | [NanYoMy/myops](https://github.com/NanYoMy/myops) | `data/CARE_Challenge/MyoPS_train` → `data/benchmarks/U-MyoPS/` | 同上 | `third_party/U-MyoPS_myops/` 旁日志；详见 `code/U-MyoPS/run.sh` |
| **CineMyoPS** | [NanYoMy/CineMyoPS](https://github.com/NanYoMy/CineMyoPS) | `data/CARE_Challenge/CineMyoPS_train` → `data/benchmarks/CineMyoPS/` | 同上 | `third_party/CineMyoPS/` / `outputs/`；入口 `code/CineMyoPS/run.sh` |

**说明：** 三处实现的数据格式与 nnU-Net Dataset501/502 不同，需适配脚本；完整训练前建议先小规模 smoke run。
