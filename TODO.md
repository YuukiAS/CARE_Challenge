# CARE Challenge: Myocardium 当前模型研究与改进 TODO

更新时间：2026-05-17

本文件只保留当前仍需要执行或复核的内容；历史修复细节见 `docs/notes/*_improvement_round*.md` 与 `results/experiments/*_iteration_log.md`。

当前判断基于：

- 本地文献：`docs/literature/`
- baseline report：`prompts/Baseline_report.md`
- nnU-Net 5-fold reference：`results/metrics/nnUNet.md`
- 官方 validation leaderboard：已刷新 `python scripts/leaderboard/fetch_care2026_scores.py`，最新 `fetched_at_utc=20260517T133101Z`
- round3 本地指标：`results/metrics/unified/*/fold_0/evaluation_summary.json`

---

## 1. 两套参考标准

### 1.1 nnU-Net 本地 5-fold 强基线

| 数据集 / 任务 | 主要对照类 | nnU-Net 5-fold mean Dice | 备注 |
| --- | --- | ---: | --- |
| `Dataset501_CAREMyoPS` | `myops_scar` / class_5 | **0.5592** | MyoPS-Net、U-MyoPS 必须超过 |
| `Dataset501_CAREMyoPS` | `myops_edema` / class_4 | **0.4197** | MyoPS-Net、U-MyoPS 必须超过 |
| `Dataset502_CARECineMyoPS` | `myocardium_cinemyops` / class_1 | **0.6808** | 当前仓库把 hosted `myocardium_cinemyops` 对齐到 class_1 |
| `Dataset502_CARECineMyoPS` | scar sanity / class_3 | 0.2586 | 用于检查 CineMyoPS 论文 pathology head 是否有信号 |

### 1.2 官方 validation leaderboard 最新参考

| 官方 validation 任务 | Rank 1 user | time | Dice / score | HD |
| --- | --- | --- | ---: | ---: |
| `myops_scar` | ZQH | 20260515 16:16:04 | **0.8390** | 6.2775 |
| `myops_edema` | ZQH | 20260515 16:16:04 | **0.8536** | 8.6853 |
| `myocardium_cinemyops` | NCC1H | 20260515 16:16:58 | **0.2594** | 38.1004 |

解读：

- 官方 validation 不能和本地 train/protocol validation 直接等同，但它是真正的 hosted metric 实现。
- MyoPS 官方 validation 输入全是三序列完整，和本地 fold0 中大量 LGE-only / 缺 T2 病例不同；因此本地分组指标必须和 overall 指标一起看。
- Cine leaderboard top 仍低，说明 hosted `myocardium_cinemyops` 口径可能与本地 class_1 不完全一致；需要后续 submission 校准。

---

## 2. Round3 后当前本地表现

| 模型 / 任务 | 当前最可信结果 | myops_scar | myops_edema | myocardium_cinemyops / class_1 | 状态 |
| --- | --- | ---: | ---: | ---: | --- |
| nnU-Net `Dataset501_CAREMyoPS` | 5-fold complete | **0.5592** | **0.4197** | - | MyoPS 强基线 |
| MyoPS-Net baseline | fold0 `challenge3` | 0.4637 | 0.2794 | - | round2/3 对照 |
| MyoPS-Net round2 | fold0 modality dropout | 0.4584 | 0.1496 | - | overall 退步 |
| MyoPS-Net round3 | fold0 mask-gated loss | **0.4965** | 0.1293 | - | scar 有进展；overall edema 失败 |
| U-MyoPS old PSNV8 final | fold0 explicit export | 0.2823 | 0.6507 | - | edema 被 empty-GT 拉高 |
| U-MyoPS round3 ScarCE2 final | fold0 trainer/checkpoint-isolated export | **0.2932** | 0.6338 | - | scar 仅小幅提升；完整三序列仍失败 |
| nnU-Net `Dataset502_CARECineMyoPS` | 5-fold complete | - | - | **0.6808** | Cine 本地强基线 |
| CineMyoPS round3 BNCalib | fold0 isolated train + BN recalib export | - | - | 0.0000 | 仍全 0，系统闭环未成立 |

关键分组结果：

| 模型 | subset | n | edema / class_4 | scar / class_5 |
| --- | --- | ---: | ---: | ---: |
| MyoPS-Net round3 | C0+LGE+T2 | 16 | 0.3555 | **0.6171** |
| MyoPS-Net round3 | LGE-only | 24 | 0.0000 | 0.4311 |
| MyoPS-Net round3 | C0+LGE | 4 | 0.0000 | 0.4072 |
| U-MyoPS round3 ScarCE2 | scar-positive-only | 43 | 0.6253 | 0.3000 |
| U-MyoPS round3 ScarCE2 | complete modalities | 16 | 0.0554 | 0.0767 |
| U-MyoPS Stage2 label oracle | all / positive / complete | 44 | 1.0000 | 1.0000 |
| CineMyoPS BNCalib | protocol val | 13 | - | class_1/class_2/class_3 all 0 |

结论：

1. **MyoPS-Net 是唯一有局部正向进展的模型**：round3 scar 从 0.4637 到 0.4965；完整三序列 scar 已到 0.6171，超过 nnU-Net 的 overall scar reference。但 overall edema 继续下降，因为 T2-missing groups 的 edema 输出/评估仍不合理。
2. **U-MyoPS 排除了 label/remap/oracle 问题**：Task901 oracle 为 1.0，说明 Stage2 labels、slice order、geometry 正确；ScarCE2 正确导出后只从 0.2823 到 0.2932，完整三序列 scar 仍约 0.077。瓶颈更可能是 Stage1 prior / Stage2 输入通道语义。
3. **CineMyoPS round3 仍无有效预测**：BN recalibration 和 isolated retraining 后 normal eval/export 仍全 0；训练期 online eval 有非零，但 validation inference / export 全背景，下一步必须调试 inference softmax/combination 语义，而不是继续训练。

---

## 3. 当前最高优先级

### 3.1 CineMyoPS：先修 inference 语义，不再盲训

当前证据：

- round2 train-mode BN diagnostic 能产生非空输出，但语义差。
- round3 BN recalibration export-only：13/13 全 0。
- round3 isolated BNCalib 训练：post-training validation inference 和 unified eval 仍全 0。
- 训练 loop 的 online eval 非零，说明 training forward path 有信号；失败发生在 validation/predict/export path 或 compact softmax combination。

下一步：

1. 对同一 val case / same slice 比较：
   - training forward `compact_softmax`
   - `predict_preprocessed_data_return_seg_and_softmax`
   - exported NIfTI labels
2. dump `cardiac_seg` logits、`pathology_seg` logits、combined compact softmax 的 channel mean/max/argmax counts。
3. 做 export-only combine-mode ablation：
   - current product rule
   - cardiac-only anatomy export
   - myocardium-gated pathology export
   - optional train-mode diagnostic export
4. 如果 cardiac-only 能恢复 class_1，则 round4 应修 `_combine_compact_softmax`；如果所有 eval-mode logits 仍背景化，则再处理 BN/normalization。

Prompt：`prompts/CineMyoPS/prompt4_inference_semantics.md`

### 3.2 MyoPS-Net：T2-aware edema routing / output gating

当前证据：

- round3 mask-gated loss 改善了 scar 和完整三序列子集：
  - overall scar `0.4637 -> 0.4965`
  - T2-present scar `0.6043 -> 0.6171`
  - T2-present edema `0.3143 -> 0.3555`
- overall edema `0.2794 -> 0.1293`，说明 T2-missing groups 仍在拉低 class_4。
- 官方 MyoPS validation 是完整三序列输入，因此完整三序列子集比 LGE-only edema 更接近 submission 条件，但本地 nnU-Net 对照仍要求 overall 不崩。

下一步：

1. 不先训练，先做 export/postprocess ablation：
   - T2-missing case suppress class_4
   - pathology 限制在 myocardium/LGE scar support 附近
   - small component removal，重点看 HD 风险
2. 若 export-only routing 改善 overall edema 且不伤 T2-present subset，再做一个 8h fold0 小训练。
3. 不扩展 folds，直到 scar 接近/超过 0.5592 且 edema 回到接近 0.4197。

Prompt：`prompts/MyoPS-Net/prompt4_t2aware_edema_routing.md`

### 3.3 U-MyoPS：Stage2 输入/先验消融，不再加 CE weight

当前证据：

- ScarCE2 正确导出后 scar 只到 0.2932。
- Stage2 label oracle 为 1.0，排除 label remap、slice order、geometry。
- 低分病例多为 C0/LGE/T2 完整的 Case20xx/30xx，说明完整 U-MyoPS path 并未发挥论文优势。
- Stage1 prior 与 pathology overlap 在若干低分病例很弱，例如 Case2031 / Case3040。

下一步：

1. 先做 Stage2 input channel QC：aligned C0/T2/LGE、prior 的非零率、强度统计、和 pathology support overlap。
2. 做 controlled input ablation：
   - existing Stage1 prior
   - LGE-only / no-prior
   - oracle myocardium prior 或 GT-derived prior（只作诊断，不作提交）
3. 只跑一个 fold0 8h 内短训，判断失败来自 Stage1 prior、输入通道、还是 PSNV8 training 本身。

Prompt：`prompts/U-MyoPS/prompt4_stage2_prior_ablation.md`

---

## 4. 第四轮 prompt 文件

已准备 / 需要执行：

- `prompts/CineMyoPS/prompt4_inference_semantics.md`
- `prompts/MyoPS-Net/prompt4_t2aware_edema_routing.md`
- `prompts/U-MyoPS/prompt4_stage2_prior_ablation.md`

推荐执行顺序：

1. **CineMyoPS prompt4**：当前仍全 0，必须先恢复正常 eval/export 语义。
2. **MyoPS-Net prompt4**：已有局部进展，最有可能通过 routing/postprocess 快速提升。
3. **U-MyoPS prompt4**：需要输入/先验消融，可能工程量更大。

---

## 5. 多轮运行规则

- 每个模型每轮训练/评估 job walltime 目标不超过 **8 小时**。
- 每轮只验证一个主要假设，并在 `results/experiments/*_iteration_log.md` 记录代码改动、命令/env、fold、walltime、actual epochs、checkpoint、stop reason、target metrics before/after。
- 不使用 1000/2000 epoch 长训补弱结果。
- 不复用 stale prediction cache；prediction / metric dir 必须包含模型、round、trainer、checkpoint 或 config tag。
- 性能汇报必须说明 folds 是否完整；当前三个自定义模型都仍是 fold0，不允许声称超过 5-fold nnU-Net。
- 每次查官方 validation 分数前先运行 `scripts/leaderboard/fetch_care2026_scores.py`。
