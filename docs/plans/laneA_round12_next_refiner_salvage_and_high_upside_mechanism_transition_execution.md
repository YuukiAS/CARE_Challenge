# Lane A Round12 Next Refiner Salvage And High-Upside Mechanism Transition Execution Plan

Plan metadata:

- Type: next execution controller
- Lane: Lane A / MyoPS scar-edema
- Round scope: Round12
- Status: planned, not executed
- Parent roadmap: CARE Myocardium Phase0/Phase1 diagnostics and Lane A Round2-Round11 evidence chain
- Parent plans: `laneA_round10_active_edema_only_residual_refiner_execution.md`, `laneA_round11_active_component_safe_bidirectional_edema_refiner_execution.md`
- Function: controller document for a future goal-mode run
- Do not: train, submit Slurm, create validation zip, upload, download weights, pull external repos, change production code, or modify existing predictions during this planning pass

## 1. 当前证据链和阶段判断

Lane A 到 Round11 的证据链已经足够清楚：当前问题不是靠继续加 epoch 或微调局部规则可以解决的。

- Round2: `edema inference postprocess` route fail。小组件删除和 ROI 阈值能减少 component，但 GT-positive edema 的 Dice/HD95 不 clean，因此不能作为主线。
- Round3: loss wiring / gradient / tiny-overfit 可跑，但这只是工程链路通过，不代表真实 fold0 性能。
- Round4: `edema_focal_tversky + no_t2_edema_loss_downweighting` 在真实 fold0 short train 中 fail，原因包括 remote FP、no-T2 FP、HD95 恶化和 scar guardrail 不干净。
- Round5: controlled mechanism audit 显示 alignment / CAA-Seg-SSA 为 `watch`，boundary/distance 为 `watch`，anatomy soft prior 进入 bounded diagnostic。
- Round6: 当前 anatomy soft attenuation fail。missing-modality audit 指出 no-T2 empty-GT 不能作为 class_4 edema 强 negative，explicit modality presence 和 uncertainty-aware supervision 是后续信号。
- Round7: first-party 6-channel modality-presence pipeline 工程可行，但简单 presence channels + scalar no-T2 weighting 没有通过 tiny gate。
- Round8: T2-present edema expert / separated edema supervision tiny gate 有信号，但 scratch / near-scratch very-short fold0 train 全面崩溃。
- Round9: nnU-Net501 checkpoint 可迁移到 6-channel model，初始 logits 可与 baseline 完全一致；但 whole-network checkpoint-initialized fine-tune 只有极弱 edema signal，component / HD95 / scar guardrail 不干净。
- Round10: add-only edema residual refiner 安全性更好，scar unchanged，no-T2 clean，但只有极小 Dice gain，HD95/component 不 clean，Case2031 和 Case3012 component worsened。
- Round11: component-safe bidirectional refiner 仍然 fail，scar unchanged、no-T2 clean，但 CenterC、remote FP 和 component guardrail 不干净；Case3011、Case3040 出现 `edema_remote_fp_worse`。
- Round11 failure summary: Case2031 是 `threshold_fragmentation / refiner_random_edge_activation / T2_support_weak_or_ambiguous`；Case3012 触发 component fallback 并回退 baseline；Case3011 是 `add_residual_remote_island / T2_support_weak_or_ambiguous`；Case3040 是 `refiner_random_edge_activation / add_residual_remote_island / T2_support_weak_or_ambiguous`。

最新判断：当前 refiner 失败更像 residual 在 CenterC/T2 弱支持区域产生 remote/edge activation，而不是简单训练 epoch 不够。Lane A Round12 不应继续 add-only refiner 或 bidirectional refiner 的普通训练，不应扩 fold1-4，不应提交 validation，不应回到 Focal Tversky、小组件删除、hard ROI、anatomy attenuation 或 whole-network fine-tune。

Round12 应分为两个方向：

1. 对 refiner 做最后一次严格、无训练或极少训练的 deployable fallback-rule salvage 诊断。
2. 准备把 Lane A 主线切换到更高收益机制：T2/LGE intensity prior、anatomy/lesion consistency、boundary/HD-aware objective 和 missing-modality representation 的 controlled integration。

## 2. Output Root

所有 Round12 输出必须隔离到：

```text
results/diagnostics/phase0_phase1/laneA_myops/round12_refiner_salvage_high_upside_transition/
```

建议输出文件：

- `round12_goal_execution_readme.md`
- `round12_reproducibility_gate.csv`
- `round12_deployable_fallback_proxy_grid.csv`
- `round12_deployable_fallback_proxy_grid.md`
- `round12_salvage_decision_table.md`
- `round12_t2_lge_intensity_prior_audit.csv`
- `round12_t2_lge_intensity_prior_audit.md`
- `round12_anatomy_lesion_consistency_audit.csv`
- `round12_anatomy_lesion_consistency_audit.md`
- `round12_boundary_hd_failure_audit.csv`
- `round12_boundary_hd_failure_audit.md`
- `round12_external_method_readiness_matrix.csv`
- `round12_external_method_readiness_matrix.md`
- `round12_decision_table.md`
- `round12_round13_recommendation.md`

若生成 overlays 或 feature visualizations，放到：

```text
results/diagnostics/phase0_phase1/laneA_myops/round12_refiner_salvage_high_upside_transition/overlays/
```

## 3. 主路线 A: `deployable_refiner_fallback_salvage_diagnostic`

目标：只用 Round11 已有 residual/fusion outputs 做一次严格的可部署 fallback-rule salvage 诊断，不训练新模型。

关键原则：

- post-hoc 手工回退 Case3011/Case3040 是 oracle/case-specific，不可部署。
- Round12 fallback rule 不能使用 GT、case ID、hosted feedback 或人工指定 failure case 来决定是否回退。
- fallback 只能基于推理时可用 proxy：baseline prediction/probability、refiner residual、image intensity、anatomy support、modality metadata、component geometry。
- class_5 scar 必须保持 baseline unchanged。
- no-T2 empty-GT 必须保持 clean。

候选 deployable fallback proxy：

- residual magnitude: 新增区域 residual 均值、最大值、分位数、add/remove imbalance。
- new component size: 新增 component voxel count、component count increase、largest component fraction。
- distance to baseline edema: 新增 component 到 baseline edema component 的最小/均值/最大距离。
- distance to myocardium/anatomy support: 新增 component 到 myocardium/LV/RV 或 dilated myocardium support 的距离。
- T2 intensity support: T2 z-score、percentile support、局部 T2 contrast、T2 support 弱/模糊区域标记。
- LGE/T2 consistency: LGE/T2 normalized contrast 是否支持 edema-like region，而非边缘随机激活。
- residual outside support: residual 是否落在 baseline low-probability、anatomy weak-support 或 T2 weak-support 区域。
- remote distance threshold: 新增 component 远离 baseline edema / myocardium support 时回退。
- no-T2 FP risk: no-T2 case 任何新增 class_4 edema 均必须触发强 fallback 或 close watch。

输出必须比较：

- baseline
- Round10 add-only refiner
- Round11 bidirectional refiner
- oracle fallback, only for upper-bound reference and clearly marked non-deployable
- each deployable proxy rule

通过标准：

- 至少一条 deployable rule 能在不看 GT 的情况下消除或显著减少 Case3011/Case3040-style remote/component worsening。
- scar unchanged。
- no-T2 empty-GT 不新增 edema FP。
- CenterC/remote FP 不恶化。
- T2-present GT-positive 或 CenterC edema 保留 Round10/11 的微小 Dice gain，或至少不比 baseline 更差。
- HD95/component 不能用牺牲真实 GT-positive edema 的方式表面改善。

失败标准：

- 只有 oracle / case-specific fallback 能改善。
- deployable proxy 消除 remote FP 的同时把 GT-positive edema 也压掉。
- 只能得到 +0.001 到 +0.003 Dice，但 CenterC、HD95、remote FP 或 component 没有 clean signal。
- 需要 GT、case ID、人工列表或 hosted feedback 才能选择 fallback。

若通过：refiner 可保留为 optional calibration module，但仍不自动进入 validation submission。若失败：refiner route 正式 `stop-as-mainline`，只作为 future baseline-preserving substrate。

## 4. 主路线 B: `high_upside_mechanism_transition_readiness`

目标：为下一阶段 controlled external/high-upside mechanism integration 做准备。本计划不要求立即训练外部 repo，不要求下载大权重，也不要求完整复现论文。Deep Research 只作为 mechanism source。

当前 failure mechanism 的优先级高于论文新旧顺序。Round11 指向的主要问题是 CenterC/T2-present edema localization、T2 support weak or ambiguous、remote/edge activation、baseline probability 对 edema 支持不足、no-T2 supervision ambiguity。

### 4.1 `T2_LGE_intensity_prior_route`

机制来源：I-MMSeg / intensity-prior 思想，但先做 CARE-first feature/audit。

目标：

- 判断 T2/LGE intensity 是否能区分 GT edema、baseline FP、refiner remote FP 和 anatomy-adjacent non-edema。
- 生成 T2 support map、LGE/T2 contrast features、z-score/percentile normalized intensity summaries。
- 对 Case2031、Case3011、Case3012、Case3040 和 CenterC complete cases 做重点分析。

允许：

- CARE-only intensity statistics。
- 轻量 feature map / overlay。
- 不依赖外部训练数据的 intensity prior diagnostic。

禁止：

- 直接接入完整 I-MMSeg CLIP/GPT/text-prompt pipeline。
- 下载大权重。
- 用 validation pseudo-label 做 supervised training。

### 4.2 `anatomy_lesion_consistency_route`

机制来源：Cascaded FSN / PT-Net / anatomy-aware loss。

目标：

- 构建 lesion-anatomy consistency feature，而不是 hard ROI deletion。
- 判断 edema GT、baseline FP、Round10/11 remote FP 与 myocardium/LV/RV/dilated support 的关系。
- 判断是否需要下一轮把 anatomy support 作为 refiner/model feature、soft penalty 或 consistency regularizer。

禁止：

- hard deletion。
- simple distance attenuation 复用 Round6 failed route。
- 把 anatomy prior 当作绝对真值。

### 4.3 `boundary_HD_objective_route`

机制来源：InverseForm / surface loss / HD-aware loss。

目标：

- 判断 Round10/11 failure 是 boundary overreach、component split、remote component、volume overprediction 还是 baseline under-support。
- 为下一轮 loss 设计提供证据：只允许 small-weight auxiliary 或 diagnostic，不再让 recall-heavy loss 主导训练。

禁止：

- 直接回到 Focal Tversky 主导训练。
- 只优化 Dice 或 foreground mean。

### 4.4 `missing_modality_representation_route`

机制来源：AdaMM / UniME / CoPeDiT / MoE / MMPL-Seg。

目标：

- 只做 metadata audit 和 one-case feasibility readiness。
- 先确认 complete-case teacher 是否可靠、no-T2 supervision policy 是否可定义、external data/compliance 是否允许。

禁止：

- 完整训练 external missing-modality repo。
- 使用 external image/label data 训练。
- validation pseudo-label supervised training。

### 4.5 `alignment_route`

机制来源：CAA-Seg / SSA。

当前状态：`watch`。

提升条件：

- failure overlay 或 intensity audit 显示 C0/LGE/T2 多序列错位、slice mismatch、registration drift 或 anatomy mismatch 与 CenterC edema failure 明显相关。

## 5. 过渡路线: `refiner_to_high_upside_decision_gate`

目标：定义 refiner 何时正式停止、何时作为 optional module、何时转入 high-upside route。

判定规则：

- 如果 deployable fallback salvage 只能带来 +0.001 到 +0.003 Dice，且不能改善 CenterC/HD95/remote FP，则不值得继续 refiner。
- 如果 fallback salvage clean 但收益极小，只能作为 optional safe calibration，不作为 Lane A 主线。
- 如果 intensity/anatomy/boundary audit 显示明确可分信号，则 Round13 进入对应 high-upside route。
- 如果所有 audit 都没有信号，再考虑更大 representation/backbone 或 external repo metadata audit。
- 任何 external repo 必须先通过 license/compliance、pretrained data source、external data risk、input-output shape、label mapping、one-case smoke，才能进入 fold0 smoke。

## 6. 阶段化执行门控

### Stage 1: `round12_reproducibility_and_round11_failure_summary_gate`

目标：复核 Round11 failure-summary 的输入、输出、重点 case 和 metrics。

允许：

- 读取已有 Round10/Round11 outputs、baseline predictions、GT、image/modalities、residual/fusion outputs。
- 生成 `round12_reproducibility_gate.csv` 和 `round12_goal_execution_readme.md`。
- 检查 Case2031、Case3012、Case3011、Case3040 的 metrics、failure tags、overlay manifest 和 file paths。

禁止：

- 训练。
- 提交 Slurm。
- 改已有 prediction、GT、evaluator、label semantics。

通过标准：

- Round11 outputs 可定位。
- Case2031、Case3012、Case3011、Case3040 的 failure reason 和 metrics 可复现。
- baseline/refiner/GT/image 文件一致。

失败标准：

- 关键 case 文件缺失且无法定位。
- Round11 summary 与 metrics 无法对齐。
- 发现 cache/prediction 污染或 label/evaluator silent change。

下一阶段：通过后进入 Stage 2；失败则停止并补齐 provenance。

### Stage 2: `deployable_fallback_proxy_grid`

目标：在不训练的情况下设计和测试可部署 fallback proxy。

允许：

- 用 residual magnitude、new component geometry、distance to baseline edema、distance to anatomy support、T2 support、LGE/T2 intensity consistency、largest component fraction 等 proxy 做 rule grid。
- 输出 `round12_deployable_fallback_proxy_grid.csv` 和 `.md`。
- 明确标记 oracle fallback 与 deployable fallback 的区别。

禁止：

- 用 GT、case ID、manual failure list 或 hosted feedback 选择 fallback。
- 手工指定 Case3011/3040 回退作为真实方案。
- 改训练代码或训练模型。

通过标准：

- 至少一条 deployable rule 能消除或显著降低 remote/component worsening。
- scar unchanged。
- no-T2 empty-GT clean。
- CenterC/remote FP 不恶化。
- 保留或改善 T2-present/CenterC edema 的微小 signal。

失败标准：

- deployable proxy 都无法优于 Round11。
- 只有 oracle fallback 有效。
- fallback rule 过度压制 GT-positive edema。

下一阶段：无论通过与否都进入 Stage 3 做 salvage decision；但只有通过才允许把 refiner 作为 optional calibration。

### Stage 3: `refiner_salvage_decision_gate`

目标：决定 refiner 是否还有 deployable salvage 空间。

允许：

- 汇总 baseline、Round10、Round11、oracle fallback、deployable fallback 的 subset metrics。
- 输出 `round12_salvage_decision_table.md`。

禁止：

- 因 tiny Dice gain 自动继续训练 refiner。
- 创建 validation zip。

通过标准：

- `optional_calibration`: deployable fallback clean，scar/no-T2 stable，CenterC/remote FP 不恶化，但收益很小。
- `stop_as_mainline`: fallback 不 clean，或收益不能覆盖 complexity/risk。

失败标准：

- 结论依赖 all-case aggregate 或 empty-GT artifact。
- 需要 GT/case-specific rule 才能成立。

下一阶段：进入 Stage 4 high-upside audits。若 refiner `stop_as_mainline`，后续仅把 refiner 当 auxiliary substrate。

### Stage 4: `T2_LGE_intensity_prior_audit`

目标：判断 T2/LGE intensity prior 是否能解释 CenterC/T2-present edema failure 和 refiner remote activation。

允许：

- 统计 edema GT、baseline FP、Round10/11 added voxels、remote components 的 T2/LGE intensity distributions。
- 生成 z-score、percentile、local contrast、inside/outside anatomy support summaries。
- 重点输出 Case2031、Case3011、Case3012、Case3040 和 CenterC complete cases。
- 输出 `round12_t2_lge_intensity_prior_audit.csv` 和 `.md`。

禁止：

- 完整接入 I-MMSeg。
- 下载 foundation weights。
- 用外部数据训练 intensity prior。

通过标准：

- T2/LGE intensity feature 能把 GT edema 与 remote FP / edge activation 分开到可部署程度。
- 能给 Round13 提供明确 feature 或 prior map 方案。

失败标准：

- intensity distributions 高度重叠，不能解释 failure。
- 结论只在少数 oracle GT case 上成立，无法转成 deployable proxy。

下一阶段：进入 Stage 5。

### Stage 5: `anatomy_lesion_consistency_audit`

目标：判断 lesion-anatomy consistency 是否能帮助区分真实 edema 与 refiner remote/edge FP。

允许：

- 分析 edema GT、baseline FP、Round10/11 added voxels 到 myocardium/LV/RV/dilated support 的距离和 overlap。
- 评估 anatomy support mismatch、component outside support、lesion adjacency consistency。
- 输出 `round12_anatomy_lesion_consistency_audit.csv` 和 `.md`。

禁止：

- hard ROI deletion。
- simple distance attenuation 作为正式方案。
- 把 anatomy GT 当绝对不可错 prior。

通过标准：

- anatomy-lesion consistency proxy 能解释 remote FP 或 CenterC HD95 outlier。
- 能提出 soft feature / soft penalty / consistency regularizer 的 Round13 implementation path。

失败标准：

- anatomy proxy 与 failure 无关。
- proxy 会删掉真实 GT-positive edema。

下一阶段：进入 Stage 6。

### Stage 6: `boundary_HD_failure_audit`

目标：判断下一阶段是否需要 boundary/HD-aware objective。

允许：

- 对 baseline、Round10、Round11 和 deployable fallback 的 boundary overreach、component split、remote component、volume ratio、HD95 outlier 做 case-level audit。
- 输出 `round12_boundary_hd_failure_audit.csv` 和 `.md`。

禁止：

- 用 boundary loss 单独主导训练计划。
- 忽略 Dice/scar/no-T2 guardrails。

通过标准：

- boundary/HD failure pattern 清晰，且适合小权重 surface/distance objective 或 component consistency penalty。

失败标准：

- 主要 failure 是 representation/intensity support 不足，而非 boundary objective 可修。

下一阶段：进入 Stage 7。

### Stage 7: `external_method_readiness_matrix`

目标：为 Round13 controlled external/high-upside mechanism integration 建立 readiness matrix。

允许：

- metadata-level audit external methods。
- 按机制槽位整理：I-MMSeg, Cascaded FSN/PT-Net, InverseForm/surface loss, AdaMM/UniME/CoPeDiT/MoE/MMPL-Seg, CAA-Seg/SSA, BiomedParse/MedNeXt/nnU-Net Task114/M&Ms。
- 输出 `round12_external_method_readiness_matrix.csv` 和 `.md`。

禁止：

- 无差别 clone/train repo。
- 下载大权重。
- 外部数据训练。

通过标准：

- 至少一个 Round13 mechanism route 有明确 trigger、input-output mapping、compliance status、one-case smoke design。

失败标准：

- readiness matrix 不能区分 priority，只变成论文清单。

下一阶段：进入 Stage 8。

### Stage 8: `round13_transition_recommendation_gate`

目标：根据 Stage 2-7 证据决定 Round13 方向。

允许：

- 输出 `round12_decision_table.md` 和 `round12_round13_recommendation.md`。
- 给每条路线标记 `go`、`watch`、`postpone`、`stop`。

禁止：

- 把 all-case aggregate 当成功标准。
- 在无 gate 的情况下建议 validation submission。

推荐判定：

- `refiner_optional_calibration`: deployable fallback clean 但收益很小。
- `refiner_stop_mainline`: deployable fallback 不 clean或收益不足。
- `intensity_prior_go`: T2/LGE intensity 可解释 remote activation 和 GT edema support。
- `anatomy_consistency_go`: anatomy-lesion feature 可解释 remote FP 且不会 hard-delete true lesions。
- `boundary_watch_or_go`: boundary/HD pattern 清楚，但只能作为小权重辅助。
- `missing_modality_postpone_or_metadata_go`: 只有 compliance 和 teacher feasibility 清楚后再进入。
- `alignment_watch`: 只有 overlay/intensity audit 指向错位时升级。

## 7. 指标和硬门槛

所有 Round12 diagnostic 必须分别报告：

- `myops_edema` class_4
- `myops_scar` class_5 guardrail
- all-case
- T2-present
- T2-present GT-positive
- complete-modality
- CenterB
- CenterC
- C0+LGE no-T2
- LGE-only
- no-T2 empty-GT

必须同时报告：

- Dice
- HD
- HD95
- component count
- remote FP count
- small FP count
- pred edema voxels
- GT edema voxels
- pred/GT volume ratio
- largest component fraction
- no-T2 edema FP voxel count
- no-T2 edema FP case count
- scar unchanged / scar Dice / scar HD95 guardrail
- case-level failure flags

任何结论不得使用 foreground mean 或 all-case aggregate 掩盖单项失败。

## 8. 明确禁止事项

Round12 plan execution 禁止：

- training unless a later user explicitly authorizes a tiny one-case smoke after diagnostics.
- Slurm submission.
- fold1-4 or 5-fold expansion.
- validation zip creation or upload.
- large pretrained weight download.
- external repo bulk clone/build/train.
- external image/label data training.
- validation pseudo-label supervised training.
- GT/case-ID/manual-list based fallback as deployable rule.
- production model/trainer changes during diagnostic stages.

## 9. Resource Stance

用户 token、Slurm、GPU 资源充足，后续 goal-mode 可以尽可能多往前推进；但 Round12 主要是 no-training / low-risk diagnostic and transition planning，不应消耗 GPU 训练，除非后续阶段被用户明确授权为 tiny one-case smoke。推进方式必须 staged, gated, evidence-driven。不要因为资源充足就跳过 diagnostics 直接训练 external repo 或提交 validation。

## 10. Next Goal Execution Prompt Draft

下面 prompt 可直接用于后续 goal-mode：

```text
你现在在 /overflow/htzhu/CARE 中工作。请执行 Lane A Round12：
docs/plans/laneA_round12_next_refiner_salvage_and_high_upside_mechanism_transition_execution.md

目标是尽可能推进 Round12，但必须 staged, gated, evidence-driven。先复核 Round11 failure summary，确认 Case2031、Case3012、Case3011、Case3040 的 metrics、failure tags、baseline/refiner/GT/image/residual 文件一致。然后在不训练的情况下执行 deployable fallback proxy grid：比较 residual magnitude、new component size、distance to baseline edema、distance to myocardium/anatomy support、T2 support、LGE/T2 consistency、largest component fraction、remote distance、residual outside support、add/remove imbalance、component count increase、no-T2 FP risk 等规则。禁止用 GT、case ID、manual failure list 或 hosted feedback 选择 fallback。

接着执行 high-upside mechanism readiness audits：T2/LGE intensity prior audit、anatomy-lesion consistency audit、boundary/HD failure audit、external method readiness matrix。Deep Research 只作为 mechanism source，不要无差别拉取 repo，不要下载大权重，不要训练外部模型。最后输出 round12_decision_table.md 和 round12_round13_recommendation.md，明确 refiner 是 optional calibration、stop-as-mainline，还是进入某个 high-upside route。

所有输出放在：
results/diagnostics/phase0_phase1/laneA_myops/round12_refiner_salvage_high_upside_transition/

必须生成：
round12_goal_execution_readme.md
round12_reproducibility_gate.csv
round12_deployable_fallback_proxy_grid.csv
round12_deployable_fallback_proxy_grid.md
round12_salvage_decision_table.md
round12_t2_lge_intensity_prior_audit.csv
round12_t2_lge_intensity_prior_audit.md
round12_anatomy_lesion_consistency_audit.csv
round12_anatomy_lesion_consistency_audit.md
round12_boundary_hd_failure_audit.csv
round12_boundary_hd_failure_audit.md
round12_external_method_readiness_matrix.csv
round12_external_method_readiness_matrix.md
round12_decision_table.md
round12_round13_recommendation.md

如生成 overlays 或 feature visualizations，放在：
results/diagnostics/phase0_phase1/laneA_myops/round12_refiner_salvage_high_upside_transition/overlays/

禁止 validation submission、validation zip、fold1-4、5-fold、大规模 external repo training、下载大权重、外部数据训练、validation pseudo-label supervised training。资源充足，可以尽可能推进所有 diagnostic stages，但每个阶段必须 gate；失败即停或降级记录，不得自动跳到训练或 submission。
```
