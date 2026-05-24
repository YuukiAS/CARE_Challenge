# MyoPS-Net Improvement Suggestion

> 撰写目的：基于当前 baseline 表现、CARE 数据特性、Myocardium track 规则（仅允许 pre-trained model，不允许混入外部数据）、以及 MyoPS-Net flexible multi-sequence 设计，给 MyoPS-Net 在 `myops_scar` 和 `myops_edema` 两个 leaderboard metric 上的提升空间、瓶颈与优先行动建议。

---

## 0. 全局约束与共识

| 维度 | 现状 | 对 MyoPS-Net 的影响 |
| --- | --- | --- |
| 数据规模 | MyoPS 220 例 | 多 encoder / 多 decoder 结构容易过拟合，需要控制训练和采样 |
| 模态完整性 | 三序列完整仅 80/220；52.7% 仅有 LGE | flexible multi-sequence 是核心优势，但缺模态训练必须和推理一致 |
| 规则 | 只允许 pre-trained model，**不允许**混入外部公开数据集 | 不能用 MyoPS 2020 / EMIDEC / ACDC 扩充训练集；只能借公开 checkpoint 初始化 |
| 评测指标 | Dice + HD（mm） | Dice 需要病灶召回，HD 需要边界和小连通域控制 |
| 主要目标 | `myops_scar`, `myops_edema` | 不应把 myocardium/LV/foreground_mean 当作主优化目标 |

核心策略：**MyoPS-Net 应优先发挥 flexible multi-sequence 的缺模态优势**。当前重点不是换模型，而是保证 challenge3 variant、标签口径、modality dropout、loss/采样和 export/eval 全链路一致。

---

## 1. myops_scar 提升空间

### 当前位置与天花板

- **当前**：MyoPS-Net challenge3 变体已修复零张量污染后，scar Dice 估计落在 0.50-0.55 区间（需以完整 fold 结果为准）。
- **论文同任务上限**：MyoPS-Net 在完整 5 序列条件下 scar Dice 约 0.66；3 序列条件下约 0.55-0.60。
- **现实可达上限**：在 CARE 缺模态条件下，若 modality dropout、后处理、五折 ensemble 做到位，目标约 **0.62-0.68**。

### 核心瓶颈

1. **缺模态病例拉低均值**：116 例 LGE-only 病例无法享受 C0/T2 多模态融合收益。
2. **训练/推理 variant 必须一致**：`MYOPS_NET_VARIANT=challenge3` 应在训练、export、eval 全部一致，避免 T1m/T2starm placeholder 作为零图污染模型。
3. **小数据 + 多分支结构**：MyoPS-Net 三个 encoder/decoder 在 220 例上容易过拟合。
4. **scar-positive slice 稀缺**：普通 slice sampling 会让 scar 病灶被背景和 myocardium 压制。
5. **HD 对 outlier 敏感**：孤立小假阳性会显著恶化 HD。

### 可尝试方向（按 ROI 排序）

| 方向 | 难度 | 预期增量 | 备注 |
| --- | --- | --- | --- |
| **modality dropout 训练**（随机 drop C0/T2） | 低 | +0.05-0.08 Dice | 最高 ROI；完全合规 |
| **确认 challenge3 variant 全链路一致** | 低 | 修复级收益 | 训练、export、eval 都必须不使用 T1m/T2starm 零图 |
| **scar-positive slice sampling / loss weight** | 低 | +0.03-0.05 Dice | 提高小病灶召回 |
| **MedSAM / cardiac anatomy init** | 中 | +0.02 Dice | 主要稳住 anatomy 分支，间接帮助 pathology |
| **最大连通域 + 小区域清理 + 边界平滑** | 低 | HD 显著改善 | Dice 可能变化小，但 leaderboard HD 会受益 |
| **完整 5 folds + ensemble** | 低 | +0.01-0.02 Dice | 工程性补强，需先修 cache 和 export |
| **替换 backbone 为 ResEnc/MedNeXt** | 中 | +0.02-0.03 Dice | 作为后续实验，优先级低于缺模态和采样 |

### 推荐组合

**modality dropout（必做） + challenge3 variant 一致性（必查） + scar-positive sampling/loss weight（必做） + 后处理（必做） + 五折 ensemble（必做） + anatomy init（试做）**。

预期：scar Dice 从约 0.55 提升到 **0.62±0.03**，HD 明显改善。

---

## 2. myops_edema 提升空间

### 当前位置与天花板

- **当前**：严格 `class_4` edema Dice 可能显著低于 nnU-Net；若按 `edema ∪ scar` 口径会虚高，必须避免。
- **论文同任务上限**：MyoPS-Net 在完整 5 序列条件下 edema Dice 约 0.74；3 序列条件下约 0.55-0.65。
- **现实可达上限**：CARE 中大量无 T2 病例使严格 edema Dice 更现实地落在 **0.40-0.55**。

### 核心瓶颈

1. **物理性限制最致命**：edema 主要依赖 T2-weighted 信号；140/220 病例没有 T2 或不完整，模型只能间接猜测。
2. **监督口径必须严格**：不能把 `edema` 训练成 `edema ∪ scar`。
3. **类别不平衡严重**：edema 体素少，容易被普通 loss 忽略。
4. **跨中心 T2 差异**：不同 acquisition 使强度归一化和泛化更难。
5. **LGE-only 情况下置信度应保守**：无 T2 时不应过度预测 edema 小块，否则 HD 和 false positive 变差。

### 可尝试方向（按 ROI 排序）

| 方向 | 难度 | 预期增量 | 备注 |
| --- | --- | --- | --- |
| **严格核查 edema/scar 标签口径** | 低 | 修复级收益 | raw id、compact id、upstream LabelTransform、export remap 全部检查 |
| **Tversky/Focal loss + class weights** | 低 | +0.03-0.05 Dice | 缓解类别不平衡 |
| **modality dropout + modality-aware head** | 中 | +0.05-0.10 Dice | 让模型区分有 T2 和无 T2 的置信策略 |
| **T2-present / T2-missing 分组评估** | 低 | 诊断收益 | 判断问题来自物理不可见还是模型失败 |
| **全模态 expert + LGE-only expert routing** | 中 | +0.03-0.05 Dice | 算法 routing，不引入外部数据 |
| **class-specific 后处理** | 低 | HD 改善 | 控制小假阳性和边界离群 |

### 推荐组合

**严格 challenge3 edema 监督 + Tversky/Focal loss + modality dropout + T2 分组评估 + 后处理**。

预期：严格 edema Dice 目标 **0.40±0.05**。不建议在 edema 上投入过多 architecture 创新精力，除非 T2-present 子集仍显著失败。

---

## 3. Pre-trained model 使用建议

| Pre-trained 资产 | 是否合规 | 对 MyoPS-Net 的价值 | 适用位置 |
| --- | --- | --- | --- |
| MedSAM / SAM-Med2D / SAM-Med3D | 合规 | 中 | anatomy encoder/init |
| nnUNet Decathlon Heart / ACDC pre-trained | 合规（公开发布前提） | 中 | cardiac anatomy initialization |
| BiomedCLIP / CLIP | 合规 | 低 | 对细粒度 CMR pathology 分割帮助有限 |
| MyoPS-Net 官方 checkpoint | 基本不可用 | 低 | 作者未发布可直接复用 checkpoint 的情况下不可依赖 |
| 自己在 MyoPS 2020 上预训再 fine-tune | 灰区，保守应避免 | 高但有违规风险 | 不建议 |

关键判断：CARE 的主要痛点是**缺模态 + 小病灶 + 标签/export 一致性**，不是缺一个通用 foundation model。

---

## 4. 不应分散精力的事

- 不要在五折未完成前基于 fold0 过度调超参。
- 不要让 T1m/T2starm placeholder 零图进入 challenge3 训练或推理。
- 不要把 `edema` 口径改成 `edema ∪ scar`。
- 不要把 BiomedCLIP 或通用视觉模型作为主路径。
- 不要在缺模态和 export/eval cache 未稳定前替换 backbone。

---

## 5. 立即行动清单

1. 运行 MyoPS-Net 低分诊断 prompt，确认 fold0 指标、checkpoint、variant、cache 是否可信。
2. 在 `run_train.sh` 中固化 `MYOPS_NET_VARIANT=challenge3`、modality dropout、scar/edema loss weights 和 positive sampling。
3. 对 val case 按 `LGE-only`、`LGE+C0`、`LGE+C0+T2` 分组报告 `myops_scar` / `myops_edema`。
4. 将最大连通域、小区域清理、边界平滑接入 export 或 unified eval。
5. 跑 5 folds，完成 ensemble 后按 `results/metrics/nnUNet.md` 的结构报告结果。
