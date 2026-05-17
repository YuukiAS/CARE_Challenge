# CARE Challenge: Myocardium 当前模型研究与改进 TODO

更新时间：2026-05-17

本文件只保留当前仍需要执行或复核的内容；已经完成的历史修复说明移入 prompt / notes，不再作为 TODO 主体。当前判断基于：

- 本地文献：`docs/literature/`
- baseline report：`prompts/Baseline_report.md`
- nnU-Net 5-fold reference：`results/metrics/nnUNet.md`
- 官方 validation leaderboard：已运行 `python scripts/leaderboard/fetch_care2026_scores.py`，最新 `fetched_at_utc=20260517T075854Z`
- 现有模型指标：`results/metrics/unified/*/fold_0/evaluation_summary.json`

---

## 1. 两套参考标准

### 1.1 nnU-Net 本地 5-fold 强基线

| 数据集 / 任务 | 主要对照类 | nnU-Net 5-fold mean Dice | 备注 |
| --- | --- | ---: | --- |
| `Dataset501_CAREMyoPS` | `myops_scar` / class_5 | **0.5592** | MyoPS-Net、U-MyoPS 必须超过 |
| `Dataset501_CAREMyoPS` | `myops_edema` / class_4 | **0.4197** | MyoPS-Net、U-MyoPS 必须超过 |
| `Dataset502_CARECineMyoPS` | `myocardium_cinemyops` / class_1 | **0.6808** | 当前仓库把 hosted `myocardium_cinemyops` 对齐到 class_1 |
| `Dataset502_CARECineMyoPS` | scar sanity / class_3 | 0.2586 | 论文 CineMyoPS 的 pathology scar 参考，不等同当前主 leaderboard 名称 |

> 注意：CineMyoPS 的论文任务是 cine-only scar/edema pathology segmentation；当前 CARE 仓库与 AGENTS.md 将 leaderboard 主目标写成 `myocardium_cinemyops`，并用 Dataset502 class_1 做本地对照。后续 submission 后需要用官方 validation 结果确认 hosted metric 是否确实与本地 class_1 最一致。

### 1.2 官方 validation leaderboard 最新参考

| 官方 validation 任务 | Rank 1 user | time | Dice / score | HD |
| --- | --- | --- | ---: | ---: |
| `myops_scar` | ZQH | 20260515 16:16:04 | **0.8390** | 6.2775 |
| `myops_edema` | ZQH | 20260515 16:16:04 | **0.8536** | 8.6853 |
| `myocardium_cinemyops` | NCC1H | 20260515 16:16:58 | **0.2594** | 38.1004 |

解读：

- 官方 validation 不能和本地 train/protocol validation 直接等同，但它是真正的 hosted metric 实现。
- MyoPS validation top 分数远高于之前 TODO 中的 20260513 旧值，说明 validation 输入完整三序列时上限可能比本地缺模态训练评估乐观。
- Cine leaderboard top 仍低，说明 hosted CineMyoPS metric 很可能比本地 class_1 myocardium Dice 更难或口径不同；必须通过 submission 校验。

---

## 2. 文献思想与 CARE 数据差异

| 模型 | 论文核心思想 | 论文输入 / 输出 | CARE 当前差异 | 当前实现理解度 |
| --- | --- | --- | --- | --- |
| MyoPS-Net | CMFF 跨模态特征融合 + MPC 心肌先验 + PI scar-in-edema 约束；强调 flexible multi-sequence | 最完整设定为 C0/LGE/T2/T1 mapping/T2*；公开 MyoPS 使用 C0/LGE/T2 的 MyoPS-Net-L；输出 scar/edema | CARE 只有 C0/LGE/T2，且训练 220 例中仅 80 例三序列完整、24 例缺 T2、116 例 LGE-only；无 T1m/T2* | 已做 challenge3 三模态改造，基本理解论文主线；但 flexible missing-modality 还没有充分实现为 mask-aware/dropout/routing |
| U-MyoPS | 先把未配准 bSSFP/T2 warp 到 LGE common space，再用 MSF + SPG 做 pathology segmentation | 输入完整 bSSFP/LGE/T2；重点解决多序列空间失配；输出 scar、edema、healthy myocardium | CARE 大量病例缺 C0/T2；Stage1/Stage2 bridge 需要额外构建；论文 edema 常按 scar+edema union 解释，CARE 主指标要求 strict class_4 | Stage1 manifest、Stage2 raw task、remap/export 已补；但 Stage1 prior 质量、缺模态策略、Stage2 scar 召回仍未达到论文思想 |
| CineMyoPS | cine-only，通过 motion estimation + anatomy segmentation + time-series aggregation 预测 pathology | 输入完整 cine sequence；ED 作为 reference；输出 scar/edema；4/6 frames 为论文推荐 | CARE CineMyoPS 64 例，当前本地对照还包含 myocardium/LV/scar compact labels；旧 Task025 单帧/middle frame 与论文不符 | Task026 ED-first、4D channels、CARECineMyoPSTrainer 已开始接近论文；但 fold0 当前 unified eval 全 0，说明实现尚未形成可信闭环 |

---

## 3. 当前本地表现

| 模型 / 任务 | 当前最可信结果 | myops_scar | myops_edema | myocardium_cinemyops / class_1 | 状态 |
| --- | --- | ---: | ---: | ---: | --- |
| nnU-Net `Dataset501_CAREMyoPS` | 5-fold complete | **0.5592** | **0.4197** | - | MyoPS 强基线 |
| MyoPS-Net | fold0 current unified eval | 0.4637 | 0.2794 | - | 两项仍低于 nnU-Net |
| U-MyoPS old default | fold0 stale/default cache | 0.0699 | 0.5646 | - | 旧结果不可作为最终结论 |
| U-MyoPS `model_best` | fold0 explicit checkpoint eval | 0.2800 | 0.6517 | - | scar 仍显著低；edema 受 empty-GT case 影响需分组解释 |
| U-MyoPS `model_final_checkpoint` | fold0 explicit checkpoint eval | 0.2823 | 0.6507 | - | 与 `model_best` 接近 |
| nnU-Net `Dataset502_CARECineMyoPS` | 5-fold complete | - | - | **0.6808** | Cine 本地 class_1 强基线 |
| CineMyoPS | fold0 current unified eval | - | - | 0.0000 | pipeline/export/eval 尚未闭环 |

关键结论：

1. **MyoPS-Net 尚未超过 nnU-Net**：challenge3 修复了 T1m/T2* 零分支污染，但 edema/scar 都仍低，说明只裁掉无效 mapping 分支不够。
2. **U-MyoPS 的旧 scar=0.0699 已不代表最新 checkpoint**：显式 checkpoint 复评后 scar 到约 0.28，但距离 nnU-Net 0.5592 仍很远；Stage1/Stage2 对 CenterB/CenterC 等完整三序列病例的 pathology 对齐可能失败。
3. **CineMyoPS 当前不是模型性能问题，而是系统问题**：unified eval 全 0 必须先定位预测文件、checkpoint、label remap、Task025/Task026 混用和 export 路径。

---

## 4. 三个模型的主要问题与改进方向

### 4.1 MyoPS-Net

主要问题：

- 论文的 flexible multi-sequence 被简化成 challenge3 三模态输入；对 CARE 的 LGE-only / 缺 T2 分布还没有真正做 mask-aware learning。
- Edema 训练信号受 T2 缺失限制；严格 class_4 Dice 不能用论文式 edema union 解释。
- 目前只有 fold0 可信结果，缺 5-fold 完整性和 ensemble。
- 需要确认 `MYOPS_NET_VARIANT=challenge3`、pathology sampler、loss weights、export remap 在训练/推理/评测全链路一致。

下一步：

1. 写入显式 modality mask 或至少在 dataloader 中区分 real-zero vs missing-zero。
2. 做 modality dropout：训练时随机 drop C0/T2，但保留 LGE 主通道；validation 按三组报告 LGE-only、C0+LGE、C0+LGE+T2。
3. 对 scar/edema positive slices 做采样和 class-specific loss：scar 以召回为主，edema 对 T2-present 子集单独加权。
4. 添加 class-specific 后处理：清理孤立小块、限制 pathology 在 myocardium prior/邻域内，重点改善 HD。
5. 跑 5 folds，先要求本地 fold-wise mean 超过 nnU-Net 0.5592 / 0.4197，再做 validation package。

### 4.2 U-MyoPS

主要问题：

- 论文假设完整 bSSFP/LGE/T2，CARE 训练集中只有 80/220 完整；Stage1 registration/MSF 的优势在 LGE-only case 中基本不可用。
- 最新 `model_best` / `model_final_checkpoint` scar 约 0.28，说明 label remap 已不是唯一问题；更像 Stage1 prior/Stage2 scar recall/中心分布失败。
- Edema 高分中大量 empty-GT case 被计为 1.0，不能直接说明 strict edema 已真正超过 nnU-Net。
- Stage2 只输出 pathology 4/5，不输出 anatomy；需要检查 SPG/prior 是否和论文的 common-space 语义一致。

下一步：

1. 对 fold0 per-case 做中心和模态分组，特别复核 Case20xx / Case30xx 的 Stage1 aligned C0/T2/LGE、myocardium prior 与 GT pathology 空间重叠。
2. 把 U-MyoPS 的 edema 汇报拆成 all cases、GT-positive-only、T2-present-only，避免 empty-GT 平均误导。
3. Stage2 加 scar-positive patch/slice sampling、scar CE/Tversky/Focal 权重，并与当前 `nnUNetTrainerPSNV8ScarCE2` 做消融。
4. 对缺模态 case 做 routing：完整三序列走 U-MyoPS full path；LGE-only / 缺 T2 走退化路径或降低 C0/T2 prior 权重。
5. 链路稳定后再跑 fold1-4；不要在 scar 仍 0.28 时直接做 5-fold 规模化。

### 4.3 CineMyoPS

主要问题：

- 旧 Task025 单帧 / middle frame 不符合论文；Task026 ED-first 是正确方向，但当前 fold0 unified eval 全 0，说明预测闭环仍断。
- 论文 CineMyoPS 输出 scar/edema；当前 CARE 本地任务还同时评估 myocardium/LV/scar，且主 leaderboard 名称为 `myocardium_cinemyops`，需要 submission 校准。
- `CARECineMyoPSTrainer` scar-only pathology head 是否能同时产生 class_1 myocardium 预测，必须通过 prediction unique labels 验证。
- 需要确认训练和 export 都使用同一个 Task026、fold、checkpoint、`CINE_NUM_FRAMES`，没有混入 Task025 旧路径。

下一步：

1. 先修全 0：检查 `results/predictions/CineMyoPS/fold_0/*.nii.gz` 数量、unique labels、非零体素、spacing/origin/direction。
2. 重新跑 `sanity_check_task026.py`、`verify_ed_at_t0.py`，确认 ED-first + sampled frames 没有被 export 改坏。
3. 明确 `CARECineMyoPSTrainer` 输出语义：本地 class_1 myocardium、class_2 LV、class_3 scar 是否都可训练/预测。
4. fold0 跑通后同时报告 class_1 和 class_3：class_1 对照本地 `myocardium_cinemyops`，class_3 对照论文 scar 思想。
5. 只有非空预测且 fold0 达到可比水平后，再跑 5 folds、ensemble 和 validation submission。

---

## 5. 新增 prompt 文件

已准备三个下一步改进 prompt：

- `prompts/MyoPS-Net/prompt2_improve_myopsnet.md`
- `prompts/U-MyoPS/prompt2_improve_umyops.md`
- `prompts/CineMyoPS/prompt2_improve_cinemyops.md`

使用顺序建议：

1. 先跑 CineMyoPS prompt，修复全 0 和 Task026 闭环。
2. 再跑 U-MyoPS prompt，集中修 Stage1/Stage2 scar 召回。
3. 最后跑 MyoPS-Net prompt，做缺模态鲁棒训练和 5-fold。

---

## 6. 多轮运行策略

默认采用“持续小步迭代”，不是一次性长训：

- 每个模型每一轮训练/评估 job walltime 目标不超过 **8 小时**。
- 每轮只验证一个主要假设，并在 `results/experiments/*_iteration_log.md` 记录代码改动、运行命令、实际 epoch、best checkpoint、停止原因和指标变化。
- 优先给训练器或 Slurm 入口加 early stopping / max runtime / best checkpoint selection；不要用 1000/2000 epoch 长训赌结果。
- 三个模型的 fold0 实验预算尽量按相近 walltime 对齐，先比较方向，再决定是否扩展到 5 folds。
- 除非涉及数据合规、label 定义、官方 submission 口径或需要用户账号/手动提交，否则后续 agent 应继续下一轮小改动，不要每轮都停下来问。

建议执行方式：

1. 不需要另开“goal mode”也能做，但每次启动一个模型 prompt 时，应把上述预算约束作为硬要求。
2. 如果要让我在同一个会话里持续推进多轮，可以明确说“开始一个持续目标：按 TODO 和三个 prompt 迭代改进模型，单轮不超过 8 小时”。这时再使用 goal 追踪更合适。
3. 三个模型可按优先级串行推进：CineMyoPS 全 0闭环 → U-MyoPS scar 召回 → MyoPS-Net 缺模态鲁棒。

---

## 7. 当前最高优先级清单

1. **CineMyoPS**：恢复非空、语义正确、空间对齐的 fold0 predictions。
2. **U-MyoPS**：解释并修复完整三序列病例 scar 崩溃；重新报告 GT-positive-only edema。
3. **MyoPS-Net**：实现/验证 modality-aware training，而不是仅靠零填充。
4. **Leaderboard**：每次提交或查分前先运行 `scripts/leaderboard/fetch_care2026_scores.py`，记录 `fetched_at_utc`。
5. **报告格式**：模型性能问题必须先确认 all folds 是否完成；完整汇报按 `results/metrics/nnUNet.md` 的结构写。
