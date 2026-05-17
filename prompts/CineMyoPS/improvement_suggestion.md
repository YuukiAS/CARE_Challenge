# CineMyoPS Improvement Suggestion

> 撰写目的：基于当前 baseline 表现、CARE CineMyoPS 数据特性、Myocardium track 规则（仅允许 pre-trained model，不允许混入外部数据）、以及 CineMyoPS 论文中的 motion/anatomy/pathology 设计，给 `myocardium_cinemyops` leaderboard metric 的提升空间、瓶颈与优先行动建议。

---

## 0. 全局约束与共识

| 维度 | 现状 | 对 CineMyoPS 的影响 |
| --- | --- | --- |
| 数据规模 | CineMyoPS 64 例 | 端到端 motion + anatomy + pathology 训练有过拟合风险 |
| 输入模态 | cine 单序列，通常 30 frames | 必须利用时序 motion 信息，单帧 nnU-Net 不是论文主方法 |
| 标签时相 | CARE 实测 `t=0` 为 ED | middle frame 约等于 ES，会和 ED 标签错位 |
| 规则 | 只允许 pre-trained model，**不允许**混入外部公开数据集 | 可用公开 checkpoint 初始化，但不能混入额外训练数据 |
| 主要目标 | `myocardium_cinemyops` | 优化重点是 CineMyoPS leaderboard，不是 MyoPS scar/edema |

核心策略：**先确保预测非空、标签正确、ED-first 数据链路正确，再接入论文风格的 motion-aware 架构，最后做五折、ensemble 和后处理**。

---

## 1. 当前位置与天花板

- **当前 baseline**：generic nnU-Net + middle frame 或单帧策略曾得到较低 scar/pathology 表现；若当前统一评测为全 0，则优先视为 pipeline/export/remap 问题。
- **论文上限**：CineMyoPS 在 145 例上 scar Dice 约 0.53；inter-observer Dice 约 0.69。
- **现实可达上限**：CARE 数据规模约为论文的一半；在 ED frame、4/6 帧采样、motion/anatomy/pathology 结构和后处理正确后，目标约 **0.45-0.55**。

---

## 2. 核心瓶颈

1. **pipeline 全 0 风险最高**：若 prediction 全 0，首先检查 Task026 数据、checkpoint、export、label remap、prediction cache 和 eval pred dir。
2. **架构错位**：generic nnU-Net 单帧 baseline 没有 motion estimation 模块，无法利用 cine 时序信息。
3. **帧选择错误**：middle frame 约为 ES，与 ED 标签错位最严重；CARE 实测 `t=0` 是 ED，应固定 ED-first。
4. **数据规模小**：64 例数据不足以支撑过大的 motion/anatomy/pathology 模块无约束训练。
5. **跨中心域偏移**：center_alpha / center_beta 的 cine protocol、contrast、心率分布可能不同。
6. **HD 对小假阳性敏感**：scar 或 myocardium 边界小 outlier 会显著拉低 HD。

---

## 3. 可尝试方向（按 ROI 排序）

| 方向 | 难度 | 预期增量 | 备注 |
| --- | --- | --- | --- |
| **恢复非空且语义正确的 predictions** | 低-中 | 修复级收益 | 当前若全 0，这是第一优先级 |
| **ED frame 固定为 `t=0`** | 低 | +0.05 Dice | 已有数据验证时不需要复杂 ED detection |
| **Task026 ED-first + 4/6 帧均匀采样一致性** | 低 | +0.03-0.06 Dice | 训练、推理、export 必须使用同一 frame policy |
| **接入 V6WithoutIMG 风格 motion+anatomy+scar 架构** | 高 | +0.15-0.25 Dice | 最大杠杆，最接近论文主方法 |
| **CineMyoPS 百度云 checkpoint 初始化 B-试验** | 中 | -0.05 到 +0.05 Dice | domain shift 不确定，不应作为主路径 |
| **ACDC / cardiac anatomy checkpoint 初始化** | 中 | +0.02-0.03 Dice | 主要帮助 anatomy 模块 |
| **五折 ensemble + 后处理** | 低 | +0.02-0.03 Dice | 链路稳定后必做 |
| **self-supervised cine 时序预训** | 高 | 实验性 | 数据少，可能 overfit pretext |

---

## 4. 推荐组合

**当前最小闭环**：

1. 确认 `results/predictions/CineMyoPS/fold_0` 包含所有 val cases，且 prediction unique labels 包含 `1/2/3`。
2. 确认 `Task026_Cine_4D` 使用 ED-first，`t=0` 作为 ED，训练和 export 的 `num_frames` 一致。
3. 修复 label map：CARE compact 到 Cine compact 应保持 `0=background`, `1=myocardium`, `2=LV_blood`, `3=scar`，不要混入 raw id。
4. 重新 export/eval fold0，确认不是旧 cache 或空预测。

**主实验路径**：

1. 完成 V6WithoutIMG-style motion/anatomy/pathology 实现。
2. 使用 `CINE_NUM_FRAMES=4` 或论文推荐帧数，固定 ED-first sampling。
3. 跑 5 folds 并做 ensemble。
4. 加入最大连通域、小区域清理、边界平滑等后处理。
5. 将百度云 checkpoint fine-tune 作为 B-试验，不作为默认主路径。

预期：`myocardium_cinemyops` 相关 Dice 从单帧低基线提升到 **0.50±0.05** 是三个 leaderboard 中收益最大、路径最明确的方向。

---

## 5. Pre-trained model 使用建议

| Pre-trained 资产 | 是否合规 | 对 CineMyoPS 的价值 | 适用位置 |
| --- | --- | --- | --- |
| CineMyoPS 百度云 checkpoint | 合规 | 低-中，不确定 | B-试验；domain shift 可能变差 |
| nnUNet Decathlon Heart / ACDC pre-trained | 合规（公开发布前提） | 中 | anatomy 模块初始化 |
| MedSAM / SAM-Med2D / SAM-Med3D | 合规 | 中 | anatomy segmentation prior/init |
| BiomedCLIP / CLIP | 合规 | 低 | 对 cine pathology segmentation 帮助有限 |
| 自己在额外 cine 数据上预训再 fine-tune | 灰区，保守应避免 | 可能高但有违规风险 | 不建议 |

关键判断：CineMyoPS 的核心差距来自**时序运动建模和 ED frame 对齐**，不是通用 pre-trained model。

---

## 6. 不应分散精力的事

- 不要在 prediction 全 0 或 label remap 未确认前调模型。
- 不要继续使用 middle frame 作为默认输入。
- 不要把百度云 checkpoint 当主路径；它只能作为 B-试验。
- 不要用外部数据自行预训练后再 fine-tune。
- 不要在 Task025 / Task026 输出混用时汇报 leaderboard 结论。
- 不要只看 myocardium/LV sanity metric，最终结论要回到 `myocardium_cinemyops`。

---

## 7. 立即行动清单

1. 运行 CineMyoPS 低分诊断 prompt，确认当前 fold0 是否是全 0、旧 cache、错误 pred dir 或 remap 问题。
2. 跑 `sanity_check_task026.py` 和 `verify_ed_at_t0.py`，固化 ED-first 数据准备。
3. 抽样统计每个 val case prediction 的 unique labels、非零体素数、尺寸、spacing/origin/direction。
4. 完成 V6WithoutIMG-style motion/anatomy/pathology 主路径实现和 smoke test。
5. 用 `CINE_NUM_FRAMES=4` 跑 fold0，再扩展到 5 folds。
6. 加入后处理和 ensemble，并按 `results/metrics/nnUNet.md` 的结构报告完整结果。
