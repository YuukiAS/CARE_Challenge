# CARE Myocardium 三个 Leaderboard 的提升空间与方向分析

> 撰写目的：基于当前 baseline 表现、CARE 数据特性、Myocardium track 规则（仅允许 pre-trained model，不允许混入外部数据）、以及参考论文（MyoPS-Net, U-MyoPS, CineMyoPS）综合判断，给三个 Leaderboard 各自给出可提升空间、瓶颈、可尝试方向。供团队战略决策、Codex 任务下发、Deep Research prompt 设计共用。

---

## 0. 全局约束与共识

| 维度 | 现状 | 影响 |
| --- | --- | --- |
| 数据规模 | MyoPS 220 例 / CineMyoPS 64 例 | 小数据下 architecture 创新受限，更应押稳定路线 |
| 模态完整性 | MyoPS 三序列完整仅 36.4%（80/220）；52.7% 仅有 LGE | 缺模态是 Lb1/Lb2 的根本瓶颈 |
| 规则 | 只允许 pre-trained model，**不允许**混入外部公开数据集 | 无法直接用 MyoPS 2020 / EMIDEC / ACDC 扩充训练集；只能借 checkpoint |
| 评测指标 | Dice + HD（mm） | HD 对边界质量敏感，后处理可能给 HD 带来非线性收益 |
| 评测对象 | 三 Leaderboard 独立排名 | 任何一个完全弃疗都会影响整体表现 |

> 核心战略：**Lb3 优先（差距最大、可改善路径最明确） + Lb1 适度补强（modality dropout） + Lb2 保住底线（受物理限制，不硬卷）**。

---

## 1. Lb1 — MyoPS Scar（C0+LGE+T2 → scar）

### 当前位置与天花板
- **当前**：MyoPS-Net challenge3 变体已修复实现错配，scar Dice 估计落在 0.50–0.55 区间（仅 fold 0）。
- **论文同任务上限**：MyoPS-Net 在完整 5 序列条件下 scar Dice ≈ 0.66；3 序列条件下 0.55–0.60。
- **现实可达上限**：~0.62–0.68（如果 modality dropout + anatomy backbone init 都做到位）。

### 核心瓶颈
1. **数据异质性**：116 例 LGE-only 病例无法享受多模态融合的红利，把整体均值往下拉。
2. **零张量污染（已修）**：之前对缺模态用零图填充并喂入多模态模型，已通过 challenge3 变体解决。
3. **小数据 + 多 head 架构**：MyoPS-Net 三个 encoder + 三个 decoder 在 220 例上训练样本不足，容易过拟合。
4. **HD 指标对 outlier 敏感**：后处理（最大连通域、形态学清理）若不做，HD 会被几个边界离群点拉得很差。

### 可尝试方向（按 ROI 排序）
| 方向 | 难度 | 预期增量 | 备注 |
| --- | --- | --- | --- |
| **Modality dropout 训练**（C0/T2 通道随机置零 50%） | 低 | +0.05~0.08 Dice | 最高 ROI；规则完全合规，不需要外部资源 |
| **Anatomy backbone 用 MedSAM/SAM-Med 初始化** | 中 | +0.02 Dice | 主要稳住 myo/LV/RV，间接帮助 pathology 分支聚焦 |
| **HD 友好的后处理**（最大连通域 + 边界平滑） | 低 | HD 显著改善（Dice 不变） | 应该立刻加到 unified eval 链路里 |
| **完整 5 折 + ensemble**（不同 fold 的 checkpoint 融合） | 低 | +0.01~0.02 Dice | 工程性补强 |
| **替换 backbone 为 nnUNet ResEnc/MedNeXt** | 中 | +0.02~0.03 Dice | 更现代的 backbone，但要小心过拟合 64-220 小数据 |
| 跨模态 distillation（teacher 用全模态，student 用部分） | 高 | +0.03~0.05 | 受规则限制，teacher 也只能用 CARE 数据训，红利有限 |

### 推荐组合
**Modality dropout（必做） + 后处理改进（必做） + MedSAM anatomy init（试做） + 5 折 ensemble（必做）**。
预期 Dice：0.55 → **0.62±0.03**；HD 显著改善。

---

## 2. Lb2 — MyoPS Edema（C0+LGE+T2 → edema）

### 当前位置与天花板
- **当前**：紧凑 class_4 Dice ≈ 0.12（按"edema∪scar"则约 0.50）。修正监督口径后预计落在 0.30–0.40 严格 Dice。
- **论文同任务上限**：MyoPS-Net 在完整 5 序列条件下 edema Dice ≈ 0.74；3 序列条件下 0.55–0.65。
- **现实可达上限**：~0.40–0.55（受 LGE-only 116 例的物理限制压制）。

### 核心瓶颈（这一项最难）
1. **物理性限制（最致命）**：edema 在临床上需要 T2-weighted 序列才能稳定可视化。CARE 220 例里只有 80 例（36.4%）有 T2，剩下 140 例**理论上拍不到 edema 信号**，再聪明的模型也只能猜。
2. **训练监督口径混乱（已修）**：原代码把 "edema = edema ∪ scar"，已在 challenge3 变体改回严格 edema。
3. **样本极度不平衡**：edema 体素占比远低于 myo/LV，loss 不加权时模型倾向于不预测。
4. **跨中心 T2 协议差异**：CenterB/C 提供的 T2 acquisition 参数可能不一致，归一化要考虑。

### 可尝试方向
| 方向 | 难度 | 预期增量 | 备注 |
| --- | --- | --- | --- |
| **样本权重 + Tversky/Focal Loss** | 低 | +0.03~0.05 Dice | 缓解类别不平衡，必做 |
| **Modality dropout + modality-aware head** | 中 | +0.05~0.10 Dice | 让模型知道"我现在没 T2，只敢预测 LGE 上有 hyperintensity 的 edema" |
| **后处理 + 双 head 集成**（"全模态 expert" + "LGE-only expert" 按输入路由） | 中 | +0.03~0.05 Dice | 不算违规，是算法 routing |
| 引入 T2 mapping 估计（自监督生成"虚拟 T2"）作为辅助通道 | 高 | 实验性 | 风险高，可能起负作用；研究性尝试 |
| nnUNet baseline 的 class-specific 后处理 | 低 | HD 改善 | 必做 |

### 推荐组合
**严格的 challenge3 监督（已做） + Tversky/Focal loss + modality dropout + 后处理 + 不期望奇迹**。
预期 Dice：0.30 → **0.40±0.05**；这是物理上能做到的现实范围。**不应在此投入超过 20% 精力**。

---

## 3. Lb3 — CineMyoPS Scar（cine 单序列 → scar）

### 当前位置与天花板
- **当前**：generic nnUNet + middle frame baseline，scar Dice ≈ 0.261（实际 middle frame ≈ ES，相当于把 nnUNet 喂了最差的一帧）。
- **论文上限**：CineMyoPS 在 145 例上 scar Dice = 0.53；inter-observer Dice ≈ 0.69。
- **现实可达上限**：~0.45–0.55（数据规模是论文的 ~1/2，但帧选择、架构、监督都对了之后能逼近论文）。

### 核心瓶颈
1. **架构错位（最致命）**：当前是 generic nnUNet 单帧 baseline，**完全没有 motion estimation 模块**，等于把论文方法降级成了对照组。
2. **帧选择错误（已识别）**：middle frame ≈ ES（end-systole），是和 ED 标签错位最严重的帧。CARE 实测 t=0 = ED。
3. **数据规模小**：64 例（51 训练 / 13 验证按 5 折），motion + anatomy + pathology 三模块端到端训练有过拟合风险。
4. **跨中心域偏移**：center_alpha/beta 的 cine 协议不一致（帧数都是 30，但 contrast、心率分布可能差）。

### 可尝试方向（按 ROI 排序）
| 方向 | 难度 | 预期增量 | 备注 |
| --- | --- | --- | --- |
| **接入 V6WithoutIMG 风格架构 + motion+anatomy+scar** | 高 | +0.15~0.25 Dice | **最大杠杆**，Codex 在做 |
| **ED frame 固定为 t=0**（已数据验证） | 低 | +0.05 Dice | 必做，不需要复杂 ED detection |
| **4/6 帧均匀采样**（论文优化的帧数） | 低 | 已包含在架构改造里 | 通过 `CINE_NUM_FRAMES=4` 控制 |
| **CineMyoPS 百度云 checkpoint 作 init**（B-试验） | 中 | ±0.05 Dice（不确定方向） | **不要事先押注**；domain shift 可能让其反而变差 |
| **5 折 ensemble + 后处理** | 低 | +0.02~0.03 Dice | 必做 |
| 用 ACDC pre-trained anatomy backbone（如有公开 checkpoint） | 中 | +0.02~0.03 Dice | anatomy 模块有现成 init |
| 引入 self-supervised cine 时序预训（contrastive）| 高 | 实验性 | 数据量小，可能 overfit pretext |

### 推荐组合
**Codex 完成 V6WithoutIMG 实现（必做） + ED=t=0（必做） + 5 折 + 后处理（必做） + checkpoint fine-tune 作 B-试验（值得做但别押注）**。
预期 Dice：0.26 → **0.50±0.05**；这是三个 Lb 中**收益最大、最确定**的提升。

---

## 4. 三个 Leaderboard 的相对优先级

```
投入比例建议：Lb3 ████████████  (50%)
              Lb1 ████████      (35%)
              Lb2 ████          (15%)
```

| Lb | 当前 → 预期 | 投入 | 关键动作 |
| --- | --- | --- | --- |
| **Lb3 CineMyoPS** | 0.26 → 0.50 (**+0.24**) | 50% | Codex 完成 + ED=t=0 + 5 折 |
| **Lb1 MyoPS Scar** | 0.55 → 0.62 (**+0.07**) | 35% | Modality dropout + 后处理 + ensemble |
| **Lb2 MyoPS Edema** | 0.30 → 0.40 (**+0.10**) | 15% | Tversky/Focal loss + modality dropout + 不期望奇迹 |

---

## 5. 规则下"pre-trained model"的真实可用范围

| Pre-trained 资产 | 是否合规 | 实际价值 | 适用 Lb |
| --- | --- | --- | --- |
| MedSAM / SAM-Med2D / SAM-Med3D | ✅ | 中（anatomy backbone init） | Lb1/Lb2/Lb3 都可 |
| CineMyoPS 百度云 checkpoint | ✅ | **低-中（domain shift 风险）** | Lb3 only |
| nnUNet Decathlon Heart / ACDC pre-trained | ✅（如果是公开发布的） | 中（cardiac anatomy backbone） | Lb3 anatomy 模块 |
| BiomedCLIP / CLIP | ✅ | 几乎无用 | / |
| MyoPS-Net / U-MyoPS 官方 checkpoint | / | 不存在（作者未发布） | / |
| 自己在 MyoPS 2020 上预训再 fine-tune | ⚠️ 灰区，**保守应避免** | 高 | / |

**关键判断**：CARE Myocardium 的两个核心痛点（**缺模态 + cine 时序运动建模**）几乎都不在现成 pre-trained model 的能力圈内。规则名义上很大方，但实际可挖资产有限。**算法层面的修复（modality dropout、loss 改造、ED 帧、motion 模块）才是这个 challenge 的主要杠杆**。

---

## 6. 不应分散精力的事

- ❌ 不要在 Lb2 edema 上死磕 architecture（受物理限制）。
- ❌ 不要把 CineMyoPS checkpoint 当主路径（domain shift 风险）。
- ❌ 不要押 BiomedCLIP / 通用 foundation model 当 backbone（细分病理任务收益太小）。
- ❌ 不要"自己在 MyoPS 2020 上预训"（规则灰区，被判违规风险大）。
- ❌ 不要在做完五折前就调超参（fold 0 的数字不代表 5 折均值）。

---

## 7. 立即行动清单

1. **Codex 完成 CineMyoPS V6WithoutIMG-style 实现**（已在做，等 smoke test）。
2. **MyoPS-Net 加入 modality dropout 训练**（待发 Codex prompt）。
3. **后处理（最大连通域 + 形态学清理）加到 unified eval 链路**。
4. **完成五折训练**（三个模型分别）。
5. **CineMyoPS checkpoint B-试验**（可选）：等主路径跑完再做对照。
6. **跑 Deep Research**：关注 2024 至今的 cardiac MR pathology 相关进展（见单独 prompt）。
