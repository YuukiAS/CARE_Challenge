# U-MyoPS Improvement Suggestion

> 撰写目的：基于当前 baseline 表现、CARE 数据特性、Myocardium track 规则（仅允许 pre-trained model，不允许混入外部数据）、以及 U-MyoPS 的两阶段跨序列对齐设计，给 U-MyoPS 在 `myops_scar` 和 `myops_edema` 两个 leaderboard metric 上的提升空间、瓶颈与优先行动建议。

---

## 0. 全局约束与共识

| 维度 | 现状 | 对 U-MyoPS 的影响 |
| --- | --- | --- |
| 数据规模 | MyoPS 220 例 | 两阶段模型容易受 fold 划分、checkpoint/cache 和 Stage1 prior 质量影响 |
| 模态完整性 | 三序列完整仅 80/220；大量病例 LGE-only | U-MyoPS 的跨序列对齐和 Stage2 pathology head 必须显式处理缺模态 |
| 规则 | 只允许 pre-trained model，**不允许**混入外部公开数据集 | 不能用 MyoPS 2020 / EMIDEC / ACDC 扩充训练；只能用公开 checkpoint 初始化 |
| 评测指标 | Dice + HD（mm） | HD 对离群小连通域敏感，后处理收益可能大于 Dice 变化 |
| 主要目标 | `myops_scar`, `myops_edema` | myocardium/LV 等只能作为 sanity check，不应作为优化主目标 |

核心策略：**先修系统链路，再做缺模态鲁棒训练，最后做五折和后处理**。U-MyoPS 的首要风险不是模型容量不足，而是 Stage1/Stage2 bridge、标签映射、checkpoint/export/eval cache 和缺模态策略的错配。

---

## 1. myops_scar 提升空间

### 当前位置与天花板

- **当前现象**：U-MyoPS fold 0 曾出现 `myops_scar` 极低而 `myops_edema` 较高的异常组合，优先怀疑系统性错配而非真实能力上限。
- **论文设计优势**：U-MyoPS 通过跨序列对齐和两阶段结构缓解多序列 CMR 的空间错位，理论上适合 scar 分割。
- **现实可达上限**：若 Stage1/Stage2 链路、标签映射、缺模态训练和 export 全部正确，`myops_scar` 应至少接近 nnU-Net 参照，并有机会达到 **0.55-0.65** 区间。

### 核心瓶颈

1. **Stage1/Stage2 语义桥接风险最高**：Stage2 label 中 `1=edema`, `2=scar`，统一评测 compact label 中 `4=edema`, `5=scar`。任何 remap 反转都会造成 scar 崩溃。
2. **checkpoint/cache 可能污染结论**：smoke run、continue training、`model_best` / `model_final_checkpoint` 和 export fallback 混用时，fold0 指标可能不是当前最优 checkpoint。
3. **缺模态处理不足**：大量 LGE-only case 会削弱跨序列对齐模块的收益；若 C0/T2 以零图形式污染 Stage2，scar head 容易学到错误条件分布。
4. **Stage1 prior 对齐风险**：Stage1 prior 必须与 fold val case、spacing、case id 和 slice 顺序完全一致，否则 Stage2 pathology head 会被错误 anatomy prior 误导。
5. **HD 对小假阳性敏感**：scar 小连通域和边界 outlier 会显著恶化 HD。

### 可尝试方向（按 ROI 排序）

| 方向 | 难度 | 预期增量 | 备注 |
| --- | --- | --- | --- |
| **彻底核查 Stage2 label remap** | 低 | 修复级收益 | 第一优先级；确认训练、export、eval 全链路 `edema/scar` 语义一致 |
| **锁定 checkpoint/export/cache 策略** | 低 | 修复级收益 | 明确 `model_best` 与 `model_final_checkpoint`，避免旧预测参与 aggregate |
| **Stage1 prior 对齐体检** | 中 | 修复级收益 | 抽查 case id、geometry、unique labels、非零体素 |
| **modality dropout / modality-aware training** | 中 | +0.05-0.08 Dice | 随机 drop C0/T2，让模型适应 LGE-only 与多模态混合分布 |
| **scar-positive slice sampling 与 loss weighting** | 低 | +0.03-0.05 Dice | 缓解小病灶被背景和 myocardium 压制 |
| **最大连通域 + 小区域清理 + 边界平滑** | 低 | HD 显著改善 | 作为 unified eval/export 后处理，避免小假阳性拉爆 HD |
| **五折训练 + ensemble** | 低 | +0.01-0.03 Dice | 链路修复后再做，避免放大错误缓存 |

### 推荐组合

**先完成 U-MyoPS scar 低分诊断和最小修复，再做 modality dropout + scar-positive sampling + 后处理 + 五折 ensemble**。

预期：若低分来自 pipeline/remap/cache，修复后可能从异常低分直接回到接近 nnU-Net 的水平；在此基础上，合理目标是 `myops_scar` **0.55-0.65**，HD 同步改善。

---

## 2. myops_edema 提升空间

### 当前位置与天花板

- **当前现象**：U-MyoPS 的 edema 可能看起来高于 scar，但必须确认是否存在 `edema` 与 `edema ∪ scar` 口径混用。
- **论文同类任务上限**：完整多序列条件下 edema 可以较高，但 CARE 中仅 36.4% 病例有完整三序列。
- **现实可达上限**：严格 edema Dice 更现实的目标是 **0.35-0.50**，受缺 T2 的物理限制明显。

### 核心瓶颈

1. **物理性限制**：edema 主要依赖 T2-weighted 信号；大量无 T2 病例只能从 LGE/C0 间接猜测。
2. **监督口径必须严格**：`edema` 不能被训练或评测成 `edema ∪ scar`，否则离线指标和 leaderboard 目标不一致。
3. **类别不平衡严重**：edema 体素少，普通 Dice/CE 容易让模型偏向不预测。
4. **跨中心 T2 差异**：不同中心 T2 acquisition 和强度分布差异会放大 Stage2 的不稳定性。

### 可尝试方向（按 ROI 排序）

| 方向 | 难度 | 预期增量 | 备注 |
| --- | --- | --- | --- |
| **严格核查 edema 监督口径** | 低 | 修复级收益 | 确认 Stage2 train label、export、eval 都是 strict edema |
| **Tversky/Focal loss 或 class weight** | 低 | +0.03-0.05 Dice | 对小病灶和 false negative 更友好 |
| **modality-aware head / routing** | 中 | +0.05-0.10 Dice | 有 T2 与无 T2 病例采用不同置信策略 |
| **T2-present group 单独分析** | 低 | 诊断收益 | 区分模型问题与物理不可见问题 |
| **class-specific 后处理** | 低 | HD 改善 | 清理孤立 edema 小块，避免 HD outlier |

### 推荐组合

**严格监督口径 + T2-present/T2-missing 分组评估 + Tversky/Focal loss + modality-aware training + 后处理**。

预期：`myops_edema` 不应投入过多架构创新精力，合理目标是 **0.40 左右**，若 T2-present 子集明显更高则说明模型方向正确。

---

## 3. Pre-trained model 使用建议

| Pre-trained 资产 | 是否合规 | 对 U-MyoPS 的价值 | 适用位置 |
| --- | --- | --- | --- |
| MedSAM / SAM-Med2D / SAM-Med3D | 合规 | 中 | Stage1 anatomy 或 encoder initialization |
| nnUNet Decathlon Heart / ACDC pre-trained | 合规（公开发布前提） | 中 | anatomy prior 初始化 |
| MyoPS-Net / U-MyoPS 官方 checkpoint | 基本不可用 | 低 | 作者通常未发布可直接复用 checkpoint |
| 自己在 MyoPS 2020 上预训再 fine-tune | 灰区，保守应避免 | 高但有违规风险 | 不建议 |

关键判断：U-MyoPS 的主要收益来自**链路正确性、缺模态鲁棒性和两阶段 prior 对齐**，不是盲目更换 backbone。

---

## 4. 不应分散精力的事

- 不要在 scar 异常低分尚未定位前调大模型或换 backbone。
- 不要把 `edema` 做成 `edema ∪ scar` 来追求表面分数。
- 不要用外部公开数据重新预训练后再 fine-tune。
- 不要在只有 fold0 且 cache 未清理时判断真实 5-fold 能力。
- 不要把 myocardium/LV 等 sanity metric 当作 CARE2026 三个 leaderboard 的主目标。

---

## 5. 立即行动清单

1. 完成 `U-MyoPS_myops_scar_diagnosis.md`，确认 scar 低分是否来自 remap、checkpoint、cache 或 Stage1/Stage2 bridge。
2. 固化 export/eval 命令，避免 smoke checkpoint 和旧 prediction cache 污染结果。
3. 对 fold0 val case 统计 `edema/scar` GT 与 prediction unique labels、体素数、per-case Dice。
4. 加入 modality dropout、scar/edema positive sampling、Tversky/Focal 或 class weights。
5. 将最大连通域、小区域清理、边界平滑接入统一评测或 submission export。
6. 链路稳定后跑 5 folds，并按 `results/metrics/nnUNet.md` 格式报告完整结果。
