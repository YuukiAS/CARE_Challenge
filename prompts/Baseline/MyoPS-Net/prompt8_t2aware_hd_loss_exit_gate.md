# MyoPS-Net round8 prompt: T2-aware edema expert, HD-aware loss, and baseline exit gate

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续 MyoPS-Net。本轮是 baseline 去留判定的第 8 轮；目标是做最后一次有实质模型变化的 MyoPS-Net 尝试，而不是继续 export-only postprocess。

## 背景与硬事实

官方 hybrid zip 的 MyoPS branch 使用 nnU-Net baseline，返回：

| hosted metric | OrganAgent Dice | HD | rank context |
| --- | ---: | ---: | --- |
| `myops_scar` | 0.5969 | 16.2536 | rank 4/5，Dice 中等，HD 优于部分高 Dice 提交但远差于 rank1 |
| `myops_edema` | 0.6496 | 22.0125 | rank 4/5，Dice 高于 zxz，HD 略差于 zxz |

当前 MyoPS-Net 本地最好：

| variant | myops_edema | myops_scar |
| --- | ---: | ---: |
| round4/round7 `combined_safe` | 0.3733 | 0.5048 |
| nnU-Net 5-fold reference | 0.4197 | 0.5592 |

结论：MyoPS-Net 仍明显落后 nnU-Net；round8 若不能给出接近/超过 nnU-Net 的证据，round9/10 不应继续在 MyoPS-Net 上堆小修。

## 必须先读

- `docs/notes/MyoPS-Net_improvement_round7.md`
- `results/experiments/MyoPS-Net_iteration_log.md`
- `docs/notes/Dice_HD.md`
- `results/leaderboard/care2026_myocardium_myops_scar_latest.csv`
- `results/leaderboard/care2026_myocardium_myops_edema_latest.csv`
- `prompts/DeepResearch/DeepResearch_prompt.md`
- `prompts/DeepResearch/Result1.pdf`
- `prompts/DeepResearch/Result2.pdf`
- `results/metrics/nnUNet.md`
- `AGENTS.md`

DeepResearch 相关提示：MyoPS 方向可借鉴 CAA-Seg/SSA 的多序列对齐、YoloSAM/ROI 的病灶定位、AdaMM 的缺模态蒸馏、Unified Focal/Tversky 与 HD-aware loss。round8 先做 MyoPS-Net 内的最小可落地版本。

## Round8 主要假设

> MyoPS-Net 当前失败不是后处理不足，而是 edema/scar 小病灶在缺模态训练中被稀释。一个 T2-present edema expert + scar-preserving branch，加 HD-aware / boundary-aware loss 与 anatomy ROI 约束，可能在完整三序列 validation 条件下超过 nnU-Net；若 fold0 仍失败，则 MyoPS-Net baseline 应停止。

## 任务

1. **先做官方 nnU-Net MyoPS error profile**
   - 基于本地 protocol fold0 和官方 leaderboard，写出 Dice/HD mismatch 分析。
   - 对 nnU-Net fold0 / MyoPS-Net round4 计算每例 component count、small remote components、bbox outlier、pathology volume ratio。
   - 输出 `results/diagnostics/MyoPS-Net_round8_nnunet_vs_myopsnet_hd_profile.{csv,md}`。

2. **实现一个短训 T2-aware edema/scar expert**
   - 只使用 T2-present/complete cases 做 edema 强监督，保留 scar route，不要让 missing-T2 empty cases 主导 edema。
   - 输入必须显式带 modality mask 或分组采样；不要只用零填充假装完整模态。
   - Loss 至少包含：
     - class-balanced Dice/Tversky or Focal-Tversky for class_4/class_5；
     - boundary/HD surrogate 或 surface loss（实现要简单可控）；
     - anatomy/pathology ROI penalty：病灶远离 myocardium support 时惩罚。
   - 训练 fold0，<=8h，early stopping；不要扩 folds。

3. **评估必须同时看 Dice 和 HD**
   - 输出 unified Dice。
   - 增加 HD/HD95 或 component/outlier proxy。
   - 分组报告：all cases、C0+LGE+T2、LGE-only、C0+LGE；edema 必须报告 GT-positive/T2-present。

4. **明确 exit gate**
   - 如果 round8 fold0 不能达到：
     - scar >= 0.535 且 edema >= 0.40，或
     - complete-case edema/scar 明显超过 nnU-Net fold0 同组，
     则建议停止 MyoPS-Net baseline 主线。
   - 停止后在 `src/` 新模型路线中优先做 CAA-Seg/SSA + nnU-Net/MedNeXt style pathology head，而不是继续 MyoPS-Net。

## 判定标准

- Strong success: all-case edema >= 0.4197 且 scar >= 0.5592，并且 HD/outlier 不恶化。
- Partial success: complete-case edema/scar 明显超过 nnU-Net 或官方验证条件更可能受益；可进入 round9 validation packaging。
- Failure: 仍低于 nnU-Net，或 Dice 提升但 HD/outlier 明显恶化；停止 MyoPS-Net 主线。

## 禁止事项

- 不要再做纯 threshold/component 后处理 round。
- 不要训练 1000/2000 epochs。
- 不要把 empty-GT edema 的 1.0 当成 edema 成功。
- 不要牺牲 scar 去换 edema，两个 hosted MyoPS 指标都要看。
- 不要用外部数据训练；DeepResearch 结果只能作为结构/损失/预训练合规线索。

## 交付物

- `docs/notes/MyoPS-Net_improvement_round8.md`
- 追加 `results/experiments/MyoPS-Net_iteration_log.md`
- 新训练/评估脚本和 README 更新
- Dice + HD/component diagnostics
- 明确回答：MyoPS-Net 是否还能在 round9/10 前超过 nnU-Net；如果不能，给出 `src/` 新模型迁移建议
