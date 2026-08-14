# SRR Retrospective

SRR 这条线给 supervisor presentation 的核心教训是：跨源整合本身不是目标，保住临床病理才是目标。CARE 当初引入 selective representation retrieval，是因为多中心、缺模态和异质监督确实需要一种比简单拼通道更谨慎的共享机制；但把这个思想搬到 dense scar/edema segmentation 后，模型不再只是选择可共享表示，还必须决定局部病灶在哪里、边界如何闭合、多个小灶如何保留、何时不能让共享信息覆盖 T2/LGE 病理线索。历史实验支持的结论不是“SRR 理论被证伪”，而是“SRR 不能再作为当前主架构，只能作为历史动机、受控基线和 ablation reference”。

## 1. Original paper idea

本仓库没有找到用户指定论文的原始 PDF：`Representation Retrieval Learning for Heterogeneous Data Integration`。我用 `pdftotext` 检索了当前 CARE checkout 中 111 个 PDF（排除 `.worktrees`、Python env 和依赖副本目录）的题名和关键词，唯一命中是 `docs/notes/deep_research/Result4.pdf`，但该文件题名为 `CARE 2026 Myocardium 的选择性表示检索方法蓝图`，创建于 2026-06-21，是 CARE 内部蓝图，不是原论文本体。

因此，严格按本 goal 的约束，原论文对照部分停止在这里。下面不从该内部蓝图反推原论文的具体数学、实验设置或 blockwise missingness 细节，也不把二手引述当作 source-paper evidence。可以保留的只有一个缺源边界：本次 retrospective 无法直接回答论文原本的 source heterogeneity、representation dictionary/retrieval、missing/blockwise modalities、source-specific/shared representation logic，除非之后补入原始 PDF。

## 2. CARE translation

CARE 当时采用 SRR 的吸引力来自一个合理映射：如果不同中心、不同模态组合和不同监督可用性会让同一个三通道分割模型学到错误 shortcut，那么模型应当只从当前样本可用且可靠的表示中取信息，而不是默认把所有输入压成一个同质特征空间。

本地 CARE 蓝图把这个想法翻译成 availability-aware selective retrieval：输入端处理 LGE、T2、C0 的可用性，模型内部区分 shared/private representation retrieval，scar 走 LGE 主导线索，edema 走 T2 条件线索，并且 no-T2 病例不能被当作 edema-negative 监督。这个翻译很贴合 CARE 的表面问题：MyoPS 训练集存在中心相关的模态缺失，scar/edema 标签和模态证据来源不同，CineMyoPS 又涉及不同时间维度。

但这只是原则层面的吸引力，不等于原论文结构已经可以直接解决 dense pathology segmentation。内部 `Result4.pdf` 自己也把 CARE 目标写成“从当前可信证据里检索对目标最有用的表示”，并提醒不要越界声称原理论已经直接证明 CMR dense segmentation 场景。

## 3. What worked conceptually

SRR 留下了三类有用概念。

| Concept | What transferred to CARE | Evidence anchor |
|---|---|---|
| Availability as first-class input | 缺模态不是普通 dropout，而是需要显式记录和约束的样本条件。 | `wiki/MODEL.md`; `results/20260704_srr_v25_compliance_audit/diagram_contract_mapping.md` |
| Shared/private information split | 多中心/多模态数据确实需要区分可共享病理线索和模态特异线索。 | `docs/notes/deep_research/Result4.pdf`; `wiki/COMPONENTS.csv` |
| Final-output evidence gate | 模块存在、梯度非零、router 有权重，不等于最终分割真的改善。 | `results/20260721_srr_batch6_final_objective_alignment/architecture_delta_final.md`; `results/20260721_srr_batch7_mechanism_closure_repair/validator_status.json` |

这些概念后来被保留下来：no-T2 safety、scar/edema 分开监督、final-mask delta、case-wise help/harm、remote-FP audit、same-population comparison。它们比某个具体 SRR implementation 更值得复用。

## 4. What failed experimentally

实验失败需要分成三层讲，避免把现象直接写成未经证明的因果。

| Layer | Supported statement | Evidence |
|---|---|---|
| Observed experimental failure | 早期 formal route 不是 diagram-compliant SRR-v2/v2.5，best scar Dice 远低于 nnU-Net，且 no-T2 edema 不安全。 | `results/20260704_srr_v25_compliance_audit/result.md`; `results/20260704_srr_v25_compliance_audit/diagram_contract_mapping.md` |
| Observed experimental failure | Batch6 机制路径被接通，但 step300 gate 未达到 usable signal，900-step extension 被正确跳过。 | `results/20260721_srr_batch6_final_objective_alignment/architecture_delta_final.md` |
| Observed experimental failure | M9 follow-up 通过 re-audit 只能支持 diagnostic-only，不支持 route promotion；selected formal M9 SRR-main candidates 仍 negative against tracked M8 nnU-Net anchor。 | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md`; `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_dictionary_fidelity_matrix.csv` |
| Observed experimental failure | Batch0-6 基本没有改变 anchor final mask；Batch7 能改变输出但 scar 略受伤，SRR-Cascade best gain 只有千分级。 | `results/20260730_care_failure_forensics_deep_research_packet/v4_batch_history_recovery.csv`; `docs/presentation/2026_08_01_care_group_meeting/care_model_evidence_master_table.md` |

Plausible mechanism 是：CARE SRR 的 representation retrieval 部分逐步变重，但最终要解决的是 lesion-local morphology。small scar、多连通 scar、diffuse edema、blood-pool confusion、remote FP、T2-present edema boundary 这些失败，不只是“该共享哪个表示”的问题，而是“病灶在心肌壁内如何形成、哪些共享信息会抹掉病理差异”的问题。当前证据与这个解释一致，但不能写成严格因果证明，因为多数历史包是 diagnostic reconstruction、局部 intervention 或 fold0 evidence，不是完整随机化机制实验。

Retrospective interpretation 是：SRR 失败的价值在于暴露了一个更尖锐的问题。旧问题问“不同来源如何共享有用表示”；CARE 后来的问题必须问“什么时候跨源整合有用，什么时候整合会消除临床有意义的病理”。这不是语义包装，而是研究目标的改变。

## 5. Why the mismatch matters

原始 representation-retrieval 思想的自然工作对象是 source-level 或 modality-level representation sharing。CARE dense segmentation 的工作对象是 voxel/lesion-level decision with clinical morphology。两者的假设有交集，但不相同。

| Assumption | Transfer status | CARE consequence |
|---|---|---|
| Heterogeneous sources may share useful structure | Transfers | 多中心和缺模态病例确实需要共享与私有表示。 |
| Missing or blockwise modality availability should be explicit | Transfers as principle | no-T2 病例必须有安全合同，不能当作 edema-negative。 |
| Retrieved representation is enough for the prediction task | Does not transfer cleanly | scar/edema 需要局部形态、边界、连通域和远端 FP 控制。 |
| Source integrativeness is usually beneficial | Does not transfer cleanly | 对病灶分割，共享信息可能提高泛化，也可能把少见病理当作跨源噪声抹掉。 |
| Global source-specific learner can own heterogeneity | Does not transfer directly | CARE 需要 pathology-specific heads、final-output gates、anatomy/ROI safety、case-wise harm audit。 |

所以 SRR 在 CARE 中被迫增加额外 machinery：availability mask、modality stems、dictionary/router diagnostics、scar/edema proposal heads、prototype memory、anatomy prior、soft ROI/refiner、no-T2 safety、branch arbitration、loss wiring、final-output causal interventions、validator known-bad fixtures。这些都不是“多写一点工程”那么简单，而是说明任务已经从 heterogeneous integration 变成 pathology-preserving inference。

## 6. Link to pathology-preserving transportability

当前方向文档没有在 `/users/a/e/aereinh` 下找到名为 `ReliableImagingInference` 的独立目录；本次读取的是 CARE 仓库内当前研究方向材料：`prompts/research/20260731_care_frontier_reset_deep_research_prompt.md` 和 `docs/notes/deep_research/CARE_FRONTIER_RESET_HIGH_GAIN_DESIGN_20260731.pdf`。它们共同把下一阶段问题重置为：历史架构模板不再继承，只继承数据真值、安全规则和失败模式；新路线要判断什么时候整合会帮忙，什么时候整合会删除病理。

这个重置和 SRR 的 lesson 是一致的。SRR 可以作为路径依赖的反例：它把多中心和缺模态当成 cross-source integration 问题，这是对的第一步；但后来 dense segmentation failure 显示，集成策略必须对病理保持敏感。特别是 scar 和 edema 的证据来源、空间形态、缺模态安全、错误代价都不同，不能让 shared representation 或 anchor correction 垄断 final prediction。

因此，新 research question 可以写成：

> When is cross-source integration beneficial, and when does integration remove clinically meaningful pathology?

SRR 对这个问题的贡献不是当前主架构，而是历史动机、受控基线和 ablation reference。

## 7. What should and should not be reused

| Reuse class | Reuse | Do not reuse |
|---|---|---|
| Historical motivation | 用 SRR 解释 CARE 为什么不能把多中心/缺模态当作普通三通道分割。 | 不要声称原论文已经解决 dense CMR lesion morphology。 |
| Controlled baseline | 保留 SRR/anchor-relative final-output delta、same-split help/harm、no-T2 safety、router/dictionary usage audit。 | 不要继续训练旧 SRR 或把旧 SRR 当 current main architecture。 |
| Ablation reference | 用 SRR 作为“selective integration”对照，问共享/私有/availability 何时帮助、何时伤害。 | 不要把 dictionary/prototype/router 名称当作机制闭环证据。 |
| Presentation story | 讲清楚“SRR 失败不是白跑，失败把问题从共享表示推进到病理保真整合”。 | 不要用路线名堆叠替代科学教训；不要把 diagnostic-only 包讲成模型成败终局。 |

Presentation skill feedback:

1. 开场不要从 `SRR-v3`、`M9_NO_PROMOTION` 这类内部标签开始，先说人话：我们学到“共享信息也可能抹掉病理”。
2. 一页只讲一条因果边界：observed failure、plausible mechanism、retrospective interpretation 要分开。
3. 用 SRR 作为转场：从“怎样共享表示”转到“怎样判断共享是否伤害病理”。这比展示十个历史 batch 更适合 supervisor presentation。
4. 对原论文保持诚实：本地没找到原 PDF，就不要在 slide 上列原论文细节；可以写“source paper pending, CARE evidence reviewed”。
