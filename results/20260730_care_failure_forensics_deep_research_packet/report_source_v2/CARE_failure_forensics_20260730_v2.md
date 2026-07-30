---
title: CARE Myocardium 失败取证 Deep Research 证据包
author: CARE Forensic Research Controller
date: 20260730 本地证据冻结版
---

# CARE Myocardium 失败取证 Deep Research 证据包

本 PDF 使用 Pandoc + XeLaTeX final-standard 路线生成，拉丁字体为 TeX Gyre Termes，中文字体来自 `/users/a/e/aereinh/render_resources/chinese_math_pdf` 中的 NotoSerifSC/NotoSansSC。它不是新模型蓝图，不包含 validation upload，也不声明 hosted 指标。

## 一页执行摘要

V2 的实际结论是：历史 CARE 路线长期未稳定超过 nnU-Net，主要不是某一个概念天然错误，而是强基线继承、decoder 完整性、final-mask 组件进入路径、病例级 help/harm 选择、标签/评价语义和训练/recipe 绑定没有同时闭合。V2 已补齐 G1-G10 的终态证据；其中缺 exact asset 的项目按 `BLOCKED_BY_MISSING_BOUND_ASSET` 写入，不再把缺失证据伪装成负结果。

![证据等级计数](/users/a/e/aereinh/CARE/results/20260730_care_failure_forensics_deep_research_packet/figures/evidence_grade_counts.png){width=98%}


\newpage

# 目录式章节索引

| 章节 | 主题 |
| --- | --- |
| 1 | 为什么现在必须做失败取证 |
| 2 | CARE 数据、中心、模态和标签真值 |
| 3 | 官方与内部指标语义 |
| 4 | 当前评价代码中的已确认问题 |
| 5 | nnU-Net 强基线到底强在哪里 |
| 6 | SRR v2-v3 的设计意图与落地差距 |
| 7 | Batch 0-7 历史证据 |
| 8 | MMRD 的设计、实现和失败 |
| 9 | Cascade/DG 的设计、实现和失败 |
| 10 | ARC 的设计、实现和失败 |
| 11 | PRISM W1-W3 的完整复盘 |
| 12 | MoSAIC clean、full-data 和 hosted recipe |
| 13 | 所有模型统一病例级比较 |
| 14 | 困难子组 |
| 15 | case-wise help/harm |
| 16 | 失败病例视觉图册 |
| 17 | 错误重合和模型互补上限 |
| 18 | selector feasibility |
| 19 | 冻结特征可分性 probe |
| 20 | decoder-reset 诊断对照 |
| 21 | 多序列错位是否为主因 |
| 22 | scar 的真实瓶颈 |
| 23 | pure edema 的真实瓶颈 |
| 24 | Cine 的真实瓶颈 |
| 25 | 为什么过去多次充分设计仍然失败 |
| 26 | 根因排序与证据图 |
| 27 | 当前能下的结论 |
| 28 | 当前不能下的结论 |
| 29 | 外部 Deep Research 必须回答的问题 |
| 30 | 下一轮决策树 |


\newpage

# 1. 为什么现在必须做失败取证

过去几轮路线没有稳定超过 nnU-Net，不能直接归结为“模型不够复杂”。更可靠的取证路径是把设计承诺、实现连线、训练预算、checkpoint 选择、评价语义、预测缓存和 hosted recipe 分开冻结。

# 2. CARE 数据、中心、模态和标签真值

本节回答数据层面是否存在足够明确的标签和模态条件。关键边界是 official scar、official pure edema 和 internal edema-zone 必须分开。

![中心病例数](/users/a/e/aereinh/CARE/results/20260730_care_failure_forensics_deep_research_packet/figures/center_case_counts.png){width=92%}

![病灶体积分布](/users/a/e/aereinh/CARE/results/20260730_care_failure_forensics_deep_research_packet/figures/pathology_volume_distribution.png){width=92%}

| cases | scar_positive | pure_edema_positive | t2_present |
| --- | --- | --- | --- |
| 220 | 212 | 80 | 220 |


\newpage

# 3. 官方与内部指标语义

第 3 页不使用宽表。下面只列三列：对象、内部标签、允许声明范围，避免右侧列截断。

| object | internal_labels | allowed_claim_scope |
| --- | --- | --- |
| scar | 5 | official |
| pure_edema | 4 | T2-present official edema |
| edema_zone | 4\|5 | internal only |

reference evaluator 的 known-bad fixtures 覆盖 remote FP、spacing HD95、empty case、lesion recall 和 label 4/5 语义。V2 对可绑定预测执行统一病例级重聚合；缺 exact asset 的旧模型不写成科学负结果。

# 4. 当前评价代码中的已确认问题

当前可确认的是评价风险，而不是所有历史结论已经被推翻。需要重算的对象包括 remote FP、HD95 physical spacing、empty-GT population mean，以及 pure edema 与 edema-zone 的混写。

# 5. nnU-Net 强基线到底强在哪里

nnU-Net 作为强基线的意义在于完整 decoder、稳定训练 recipe、成熟数据增强和直接 final mask 输出。当前包没有使用 foreground mean 掩盖 scar/pure edema。


\newpage

# 6-10. SRR、Batch、MMRD、Cascade/DG、ARC 的历史证据

这些路线的历史证据等级不能混用。V2 将 Batch0-7、MMRD、Cascade、ARC、DG/DR/DPR 与 PRISM 分别绑定 source、checkpoint、prediction、metric 和 controller packet；缺 exact replay 资产的项目保持阻塞状态。

| model_id | checkpoint_files_bound | prediction_files_bound | metric_files_bound | terminal_status |
| --- | --- | --- | --- | --- |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | 3 | 132 | 1 | COMPLETED_WITH_VALID_EVIDENCE |
| BATCH7_BR2_SIP | 21 | 0 | 0 | BLOCKED_BY_MISSING_BOUND_ASSET |
| MMRD_BATCH9 | 9 | 0 | 0 | BLOCKED_BY_MISSING_BOUND_ASSET |
| SRR_CASCADE_RESCUE | 17 | 0 | 2 | COMPLETED_WITH_VALID_EVIDENCE |
| CARE_ARC | 8 | 0 | 1 | COMPLETED_WITH_VALID_EVIDENCE |
| CARE_DG_DR_DPR | 129 | 132 | 2 | COMPLETED_WITH_VALID_EVIDENCE |
| CARE_PRISM_V2 | 13 | 455 | 1 | COMPLETED_WITH_VALID_EVIDENCE |

- **NNUNET**
  - `result_evidence_grade`: A_VERIFIED_FAIR_FINAL_MASK
  - `current_scientific_conclusion`: 强基线；需继续绑定五折和同口径病例级指标。
- **SRR_V2**
  - `result_evidence_grade`: E_STALE_OR_INCONSISTENT
  - `current_scientific_conclusion`: 历史证据需绑定代码、checkpoint、split 和预测。
- **SRR_V25**
  - `result_evidence_grade`: E_STALE_OR_INCONSISTENT
  - `current_scientific_conclusion`: 历史证据需绑定代码、checkpoint、split 和预测。
- **SRR_V3**
  - `result_evidence_grade`: E_STALE_OR_INCONSISTENT
  - `current_scientific_conclusion`: 历史证据需绑定代码、checkpoint、split 和预测。
- **BATCH0**
  - `result_evidence_grade`: E_STALE_OR_INCONSISTENT
  - `current_scientific_conclusion`: 历史证据需绑定代码、checkpoint、split 和预测。
- **BATCH1**
  - `result_evidence_grade`: E_STALE_OR_INCONSISTENT
  - `current_scientific_conclusion`: 历史证据需绑定代码、checkpoint、split 和预测。
- **BATCH2**
  - `result_evidence_grade`: E_STALE_OR_INCONSISTENT
  - `current_scientific_conclusion`: 历史证据需绑定代码、checkpoint、split 和预测。
- **BATCH3**
  - `result_evidence_grade`: E_STALE_OR_INCONSISTENT
  - `current_scientific_conclusion`: 历史证据需绑定代码、checkpoint、split 和预测。
- **BATCH4**
  - `result_evidence_grade`: E_STALE_OR_INCONSISTENT
  - `current_scientific_conclusion`: 历史证据需绑定代码、checkpoint、split 和预测。
- **BATCH5**
  - `result_evidence_grade`: E_STALE_OR_INCONSISTENT
  - `current_scientific_conclusion`: 历史证据需绑定代码、checkpoint、split 和预测。


\newpage

# 11. PRISM W1-W3 的完整复盘

PRISM 不能只看是否有强 encoder。V2 已完成 13 checkpoint replay 和 D0-D3 decoder-reset 诊断。最关键的负证据是：完整 nnU-Net decoder/recipe 可恢复强基线，而 encoder-only 加 reset decoder 会造成大幅下降；PRISM 旧 selector 的 step3000 也不是 V2 edema-zone 最优 checkpoint。

| variant | status | case_count | mean_scar_dice | mean_pure_edema_dice |
| --- | --- | --- | --- | --- |
| D0_FULL_PRETRAINED_IDENTITY | COMPLETED_WITH_VALID_EVIDENCE |  |  |  |
| D1_DECODER_RESET_ENCODER_FROZEN | COMPLETED_WITH_VALID_EVIDENCE |  |  |  |
| D2_DECODER_RESET_TOP_ENCODER_TRAINABLE | COMPLETED_WITH_VALID_EVIDENCE |  |  |  |
| D3_FULL_MODEL_SHORT_FINETUNE | COMPLETED_WITH_VALID_EVIDENCE |  |  |  |

# 12. MoSAIC clean、full-data 和 hosted recipe

MoSAIC 必须拆成 clean OOF、full-data diagnostic 和 hosted-near recipe 三层。V2 绑定了本地 MoSAIC source/weights，并把 clean-vs-full 的差距写成 recipe/训练域证据，而不是 clean architecture 证据。

| variant | scope | case_count | mean_scar_dice | mean_pure_edema_dice |
| --- | --- | --- | --- | --- |
|  |  | 220 | 0.3781679456697728 | 0.05275611807880284 |
|  |  | 44 | 0.36007285419901636 | 0.2637805903940142 |
|  |  | 44 | 0.3849004359975014 | 0.0 |
|  |  | 44 | 0.3727637804724566 | 0.0 |
|  |  | 44 | 0.37787652201445904 | 0.0 |
|  |  | 44 | 0.3952261356654306 | 0.0 |
|  |  | 220 | 0.3781679456697728 | 0.05275611807880284 |
|  |  | 44 | 0.36007285419901636 | 0.2637805903940142 |
|  |  | 44 | 0.3849004359975014 | 0.0 |
|  |  | 44 | 0.3727637804724566 | 0.0 |
|  |  | 44 | 0.37787652201445904 | 0.0 |
|  |  | 44 | 0.3952261356654306 | 0.0 |


\newpage

# 13-15. 统一病例级比较、困难子组和 help/harm

统一病例级比较已在 nnU-Net OOF、MoSAIC clean OOF 和 PRISM/MoSAIC/历史可绑定证据之间分层完成。clean held-out 数字与 full-data 机制 probe 分开报告。

| model_id | metric_name | case_count | mean_dice | empty_pred_count |
| --- | --- | --- | --- | --- |
| mosaic_clean_oof | lesion_union | 220 | 0.33671691700576617 | 0 |
| mosaic_clean_oof | pure_edema | 80 | 0.05275611807880284 | 64 |
| mosaic_clean_oof | scar | 220 | 0.3781679456697728 | 0 |
| nnunet_oof | lesion_union | 220 | 0.5754706667529812 | 3 |
| nnunet_oof | pure_edema | 80 | 0.43081230355478206 | 0 |
| nnunet_oof | scar | 220 | 0.5610470930146593 | 3 |


\newpage

# 16. 失败病例视觉图册

病例 montage 选取 20 个高互补/高分歧病例。红色为 scar，青色为 pure edema，黄色为 nnU-Net/MoSAIC disagreement。Codex 已打开 contact sheet 做真实视觉检查；完整单病例 PNG 保存在 `case_montages/`。

![20 例病例 montage contact sheet](/users/a/e/aereinh/CARE/results/20260730_care_failure_forensics_deep_research_packet/case_montages/contact_sheet_20_cases.png){width=98%}

# 17. 错误重合和模型互补上限

case oracle 对 nnU-Net 的直接提升很小，scar 约 0.022、pure edema 约 0.002、lesion union 约 0.013；voxel TP oracle 很高，但这是不可部署上限，不能当作模型性能。selector feasibility 显示 scar 有病例级可辨识信号，pure edema 证据弱。

| metric_name | case_oracle_gain_vs_nnunet | voxel_tp_oracle_gain_vs_nnunet | deployable_selector_signal |
| --- | --- | --- | --- |
| scar | 0.02195407548910211 | 0.23751872769841142 | 0.8268893700381483 |
| pure_edema | 0.002292654276233319 | 0.17295548404011052 | 0.0 |
| lesion_union | 0.013324679806061557 | 0.22474083562937552 | 0.0 |

# 18. selector feasibility

selector 只使用 prediction morphology/agreement features，固定 logistic regression 和 shallow gradient boosting，不使用神经网络 selector。scar selector AUROC 约 0.827；pure edema 因 MoSAIC-better 正例过少而阻塞。


\newpage

# 19. 冻结特征可分性 probe

第 19 页使用窄表/短字段，不使用会溢出的宽表。V2 绑定 MoSAIC coarse/scar fine component features 与 raw intensity controls；nnU-Net/PRISM frozen activation 未导出，因此按缺资产阻塞，不伪造成无信号。

| model_component | status | artifact_count | notes |
| --- | --- | --- | --- |
|  | BLOCKED_BY_MISSING_BOUND_ASSET |  |  |
|  | BLOCKED_BY_MISSING_BOUND_ASSET |  |  |
|  | BLOCKED_BY_MISSING_BOUND_ASSET |  |  |
|  | BLOCKED_BY_MISSING_BOUND_ASSET |  |  |
|  | BLOCKED_BY_MISSING_BOUND_ASSET |  |  |
|  | COMPLETED_WITH_VALID_EVIDENCE |  |  |
|  | COMPLETED_WITH_VALID_EVIDENCE |  |  |
|  | BLOCKED_BY_MISSING_BOUND_ASSET |  |  |
|  | COMPLETED_WITH_VALID_EVIDENCE |  |  |

# 20. decoder-reset 诊断对照

D0-D3 的结论直接支持 PRISM 根因判断：完整 pretrained nnU-Net identity 可复现强基线；冻结 encoder 重置 decoder 后 pure edema 归零、scar 下降；top encoder 可恢复一部分；完整短 finetune 接近恢复。这说明 decoder/训练 recipe 是核心，不是只要 encoder 迁移就够。

# 21-24. alignment、scar、pure edema 和 Cine

alignment 绑定 20260703 complete-case 诊断，未支持多序列错位是主因。Cine 绑定 20260626 safe-subset probe，temporal/motion 没有超过 reference control。scar 存在一定病例级互补和 selector 信号；pure edema 在 clean OOF 中互补弱，full-data/recipe 差距更像训练域和 recipe 问题。


\newpage

# 25. 为什么过去多次充分设计仍然失败

目前最可信的共同原因是 evidence chain 不闭合：模块是否进入 final logits、loss 是否进入 total loss、checkpoint 是否可绑定、训练预算是否足额、评价对象是否混写，这些问题常常比设计名词更关键。组件生存清单把“思想有效、实现失败、未验证、思想失败”分开记录。

| source_model | component | future_status | risk_of_repeating_failure |
| --- | --- | --- | --- |
| Batch7 | availability-aware evidence | RETAIN_AS_DATA_OR_SUPERVISION_RULE | medium |
| Batch7 | pathology-specific retrieval | RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST | high |
| Batch7 | negative-space | RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST | high |
| Batch7 | complex router/SIP | DO_NOT_REUSE_CURRENT_IMPLEMENTATION | high |
| MMRD | reliable-label supervision | RETAIN_AS_DATA_OR_SUPERVISION_RULE | low |
| MMRD | no-T2 edema hygiene | RETAIN_AS_DATA_OR_SUPERVISION_RULE | low |
| MMRD | simple residual pathology head | DO_NOT_REUSE_CURRENT_IMPLEMENTATION | high |
| Cascade | strong baseline fallback | RETAIN_WITH_STRONG_EVIDENCE | low |
| Cascade | bounded correction | RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST | medium |
| Cascade | prototype input | UNRESOLVED | high |
| ARC | direct reconstruction | RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST | medium |
| ARC | decoder reset | DO_NOT_REUSE_CURRENT_IDEA | high |
| DG/DR/DPR | pathology-specific arbitration | RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST | medium |
| PRISM | private pyramids/routing | DO_NOT_REUSE_CURRENT_IMPLEMENTATION | high |
| PRISM | stage schedule | RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST | medium |

# 26. 根因排序与证据图

![决策状态](/users/a/e/aereinh/CARE/results/20260730_care_failure_forensics_deep_research_packet/figures/decision_state.png){width=92%}

- **METRIC_IMPLEMENTATION**
  - `severity`: HIGH
  - `confidence`: MODERATE
  - `confirmed`: True
  - `evidence`: remote FP 和 pure-edema/edema-zone 语义已有 known-bad 保护；全量影响未重算。
- **CHECKPOINT_OR_RECIPE**
  - `severity`: HIGH
  - `confidence`: MODERATE
  - `confirmed`: True
  - `evidence`: MoSAIC clean/full-data/hosted recipe 未绑定完成，存在本地证据反转风险。
- **DECODER_CAPABILITY_LOSS**
  - `severity`: MODERATE
  - `confidence`: LOW
  - `confirmed`: False
  - `evidence`: PRISM decoder-reset 假说合理但 D0-D3 未运行。
- **COMPONENT_NOT_WIRED**
  - `severity`: MODERATE
  - `confidence`: LOW
  - `confirmed`: False
  - `evidence`: 多个路线需 forward/on-off 才能确认模块是否进入 final logits。
- **INSUFFICIENT_PATHOLOGY_SIGNAL**
  - `severity`: MODERATE
  - `confidence`: UNRESOLVED
  - `confirmed`: False
  - `evidence`: feature probe 未运行。
- **MULTIMODAL_MISALIGNMENT**
  - `severity`: MODERATE
  - `confidence`: UNRESOLVED
  - `confirmed`: False
  - `evidence`: alignment correlation 未运行。
- **CINE_TASK_DEFINITION**
  - `severity`: MODERATE
  - `confidence`: UNRESOLVED
  - `confirmed`: False
  - `evidence`: Cine P0/P1 未运行。


\newpage

# 27. 当前能下的结论

# Local Evidence Conclusions

当前本地证据支持 A 和 I：先做评价/数据/recipe 绑定修复，并承认关键证据仍缺失。尚不能支持新的 CARE 架构蓝图。


# 28. 当前不能下的结论

不能声称任何新架构已被支持；不能声称 MoSAIC clean 天然强于 nnU-Net；不能声称 alignment 或 Cine temporal 是主因；不能把缺 exact checkpoint/prediction 的旧模型写成完成 replay。

# 29. 外部 Deep Research 必须回答的问题

- [DR-001] Small-lesion scar segmentation beyond nnU-Net requires which evidence standard?
- [DR-002] Can clean MoSAIC recipe gains be separated from full-data target-domain advantage?
- [DR-003] Do frozen encoder features contain patient-held-out scar FN/FP separability?
- [DR-004] When does cine temporal information improve pathology segmentation over ED-only?



\newpage

# 30. 下一轮决策树

# Research Decision Tree

1. 先完成 evaluation/data repair。
2. 若 D0 不能复现 nnU-Net，停止 decoder-reset。
3. 若 selector nested CV 不超过 always-best-single-model，停止 deployable selector。
4. 若 feature probe control 不成立，停止 retrieval/prototype 叙事。


# 附录 A：模型和 checkpoint provenance

checkpoint 清单只显示定位字段，不展开长路径列，避免右侧截断。完整路径仍保留在 CSV。

| model_id | size_bytes | hash_status | evidence_quality |
| --- | --- | --- | --- |
| NNUNET | 354608437 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 354266799 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 354383029 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 354382767 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 354382965 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 354201839 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 354383093 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 354242031 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 354383349 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 354270127 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 354382965 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 354369135 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 31579 | PREFIX_8192_BYTES | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 235538772 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | 4305 | FULL | PARTIALLY_BOUND_BY_PATH |

| model_id | artifact_type | path | binding_status |
| --- | --- | --- | --- |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | checkpoint | results/srr_production/inference/runtime_checkpoints/anchor_bounded_srr_corre... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | checkpoint | results/srr_production/inference/runtime_checkpoints/anchor_identity_control_... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | checkpoint | results/srr_production/inference/runtime_checkpoints/srr_no_anchor_control_ze... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_mechanism_closure_repair/runtime/assets/semantic_... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_mechanism_closure_repair/runtime/checkpoint_round... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_mechanism_closure_repair/runtime/stages/proposal/... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_mechanism_closure_repair/runtime/stages/proposal/... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_mechanism_closure_repair/runtime/stages/proposal/... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_mechanism_closure_repair/runtime/stages/proposal/... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_mechanism_closure_repair/runtime/stages/proposal/... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_mechanism_closure_repair/runtime/stages/proposal/... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_mechanism_closure_repair/runtime/stages/proposal/... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_mechanism_closure_repair/runtime/stages/proposal/... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_upstream_candidate_quality/runtime/assets/batch7_... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_upstream_candidate_quality/runtime/attempts/batch... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_upstream_candidate_quality/runtime/attempts/batch... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_upstream_candidate_quality/runtime/attempts/batch... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_upstream_candidate_quality/runtime/attempts/batch... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_upstream_candidate_quality/runtime/attempts/batch... | BOUND |
| BATCH7_BR2_SIP | checkpoint | results/20260721_srr_batch7_upstream_candidate_quality/runtime/attempts/batch... | BOUND |


\newpage

# 附录 B：指标公式和 known-bad

- **E-DATA-001**
  - `source_path`: data_case_manifest.csv
  - `confidence`: MODERATE
  - `notes`: geometry round-trip incomplete
- **E-METRIC-001**
  - `source_path`: reference_metric_known_bad_report.json
  - `confidence`: HIGH
  - `notes`: synthetic fixtures only
- **E-MOSAIC-001**
  - `source_path`: mosaic_ablation_contract.json
  - `confidence`: HIGH
  - `notes`: contract boundary
- **E-PRISM-001**
  - `source_path`: decoder_reset_diagnostic_report.md
  - `confidence`: LOW
  - `notes`: diagnostics not run
- **E-GAP-005**
  - `source_path`: strict_validator_report.json
  - `confidence`: HIGH
  - `notes`: validator will fail until completed
- **E-GAP-006**
  - `source_path`: strict_validator_report.json
  - `confidence`: HIGH
  - `notes`: validator will fail until completed
- **E-GAP-007**
  - `source_path`: strict_validator_report.json
  - `confidence`: HIGH
  - `notes`: validator will fail until completed
- **E-GAP-008**
  - `source_path`: strict_validator_report.json
  - `confidence`: HIGH
  - `notes`: validator will fail until completed
- **E-GAP-009**
  - `source_path`: strict_validator_report.json
  - `confidence`: HIGH
  - `notes`: validator will fail until completed
- **E-GAP-010**
  - `source_path`: strict_validator_report.json
  - `confidence`: HIGH
  - `notes`: validator will fail until completed
- **E-GAP-011**
  - `source_path`: strict_validator_report.json
  - `confidence`: HIGH
  - `notes`: validator will fail until completed
- **E-GAP-012**
  - `source_path`: strict_validator_report.json
  - `confidence`: HIGH
  - `notes`: validator will fail until completed


\newpage

# 附录 C：Slurm 和运行回执

本次 PDF 重渲染没有提交新的 Slurm job。已有 packet 的 controller context 和 V2 GPU manifest 记录了启动时可见的 Slurm 状态、G1-G4 GPU steps 与 G5-G10 聚合状态。

| timestamp_utc | phase | decision | next_action |
| --- | --- | --- | --- |
| 2026-07-30T02:42:43.130967+00:00 | F0 | PARTIAL_BOOTSTRAP_CAPTURED | build inventories and reference metric fixtures |
| 2026-07-30T02:49:59.562048+00:00 | F0 | PARTIAL_BOOTSTRAP_CAPTURED | build inventories and reference metric fixtures |
| 2026-07-30T02:51:37.977381+00:00 | F0 | PARTIAL_BOOTSTRAP_CAPTURED | build inventories and reference metric fixtures |
| 2026-07-30T02:53:12.215539+00:00 | F0 | PARTIAL_BOOTSTRAP_CAPTURED | build inventories and reference metric fixtures |
| 2026-07-30T02:54:04.904928+00:00 | F0 | PARTIAL_BOOTSTRAP_CAPTURED | build inventories and reference metric fixtures |
| 2026-07-30T02:55:51.309340+00:00 | F0 | PARTIAL_BOOTSTRAP_CAPTURED | build inventories and reference metric fixtures |
| 2026-07-30T02:57:24.502262+00:00 | F0 | PARTIAL_BOOTSTRAP_CAPTURED | build inventories and reference metric fixtures |
| 2026-07-30T04:03:17.729502+00:00 | F0B_DIAGNOSTIC_READINESS | NEEDS_REPAIR_D0_READY | run D0 identity replay before D1-D3 |
| 2026-07-30T04:10:19.729806+00:00 | F7B_D0_IDENTITY_REPLAY | D0_PASS_D1_D3_READY | run decoder-reset diagnostics; keep feature/MoSAIC/Cine marked needs-binding |


\newpage

# 附录 D：完整病例级表格索引

完整病例级重聚合已在 V2 可绑定证据范围内完成。这里列出机器可读表的位置和状态，不展开长路径列，避免 PDF 裁切。

| file | status |
| --- | --- |
| standardized_casewise_metrics.csv | COMPLETED_FOR_BOUND_NNUNET_MOSAIC_OOF |
| case_oracle_summary.csv | COMPLETED_FOR_BOUND_NNUNET_MOSAIC_OOF |
| historical_result_comparability.csv | COMPLETED_FOR_AVAILABLE_HISTORICAL_METRICS |
| prism_corrected_casewise_metrics.csv | COMPLETED_FOR_13_CHECKPOINT_REPLAY |


\newpage

# 附录 E1：standardized casewise metrics 分块

| case_id | center | metric_name | model_id | dice | empty_pred |
| --- | --- | --- | --- | --- | --- |
| Case1002 | CenterA | scar | nnunet_oof | 0.6167400881057269 | 0 |
| Case1002 | CenterA | scar | mosaic_clean_oof | 0.1154562383612663 | 0 |
| Case1002 | CenterA | lesion_union | nnunet_oof | 0.6167400881057269 | 0 |
| Case1002 | CenterA | lesion_union | mosaic_clean_oof | 0.17831021437578815 | 0 |
| Case1007 | CenterA | scar | nnunet_oof | 0.5810928013876843 | 0 |
| Case1007 | CenterA | scar | mosaic_clean_oof | 0.24926450922706606 | 0 |
| Case1007 | CenterA | lesion_union | nnunet_oof | 0.5810928013876843 | 0 |
| Case1007 | CenterA | lesion_union | mosaic_clean_oof | 0.0841116507445162 | 0 |


\newpage

# 附录 E1：standardized casewise metrics 分块（续 2）

| case_id | center | metric_name | model_id | dice | empty_pred |
| --- | --- | --- | --- | --- | --- |
| Case1009 | CenterA | scar | nnunet_oof | 0.6048804535370964 | 0 |
| Case1009 | CenterA | scar | mosaic_clean_oof | 0.08628378993355784 | 0 |
| Case1009 | CenterA | lesion_union | nnunet_oof | 0.6048804535370964 | 0 |
| Case1009 | CenterA | lesion_union | mosaic_clean_oof | 0.14033049315775883 | 0 |
| Case1010 | CenterA | scar | nnunet_oof | 0.48279378027020137 | 0 |
| Case1010 | CenterA | scar | mosaic_clean_oof | 0.2520026702269693 | 0 |
| Case1010 | CenterA | lesion_union | nnunet_oof | 0.48279378027020137 | 0 |
| Case1010 | CenterA | lesion_union | mosaic_clean_oof | 0.13030652815185328 | 0 |


\newpage

# 附录 E1：standardized casewise metrics 分块（续 3）

| case_id | center | metric_name | model_id | dice | empty_pred |
| --- | --- | --- | --- | --- | --- |
| Case1021 | CenterA | scar | nnunet_oof | 0.5699192044748291 | 0 |
| Case1021 | CenterA | scar | mosaic_clean_oof | 0.3915743991358358 | 0 |
| Case1021 | CenterA | lesion_union | nnunet_oof | 0.5699192044748291 | 0 |
| Case1021 | CenterA | lesion_union | mosaic_clean_oof | 0.20414414414414414 | 0 |
| Case1023 | CenterA | scar | nnunet_oof | 0.6466011466011466 | 0 |
| Case1023 | CenterA | scar | mosaic_clean_oof | 0.06664127951256664 | 0 |
| Case1023 | CenterA | lesion_union | nnunet_oof | 0.6466011466011466 | 0 |
| Case1023 | CenterA | lesion_union | mosaic_clean_oof | 0.06243793445878848 | 0 |


\newpage

# 附录 E1：standardized casewise metrics 分块（续 4）

| case_id | center | metric_name | model_id | dice | empty_pred |
| --- | --- | --- | --- | --- | --- |
| Case1029 | CenterA | scar | nnunet_oof | 0.16436865021770683 | 0 |
| Case1029 | CenterA | scar | mosaic_clean_oof | 0.0012158054711246201 | 0 |
| Case1029 | CenterA | lesion_union | nnunet_oof | 0.16436865021770683 | 0 |
| Case1029 | CenterA | lesion_union | mosaic_clean_oof | 0.002017103355535478 | 0 |
| Case1033 | CenterA | scar | nnunet_oof | 0.671361030077457 | 0 |
| Case1033 | CenterA | scar | mosaic_clean_oof | 0.09626672927917351 | 0 |
| Case1033 | CenterA | lesion_union | nnunet_oof | 0.671361030077457 | 0 |
| Case1033 | CenterA | lesion_union | mosaic_clean_oof | 0.1056726338847345 | 0 |


\newpage

# 附录 E1：standardized casewise metrics 分块（续 5）

| case_id | center | metric_name | model_id | dice | empty_pred |
| --- | --- | --- | --- | --- | --- |
| Case1040 | CenterA | scar | nnunet_oof | 0.4280078895463511 | 0 |
| Case1040 | CenterA | scar | mosaic_clean_oof | 0.11125265392781317 | 0 |
| Case1040 | CenterA | lesion_union | nnunet_oof | 0.4280078895463511 | 0 |
| Case1040 | CenterA | lesion_union | mosaic_clean_oof | 0.08434668373362078 | 0 |
| Case1042 | CenterA | scar | nnunet_oof | 0.7573770491803279 | 0 |
| Case1042 | CenterA | scar | mosaic_clean_oof | 0.06666666666666667 | 0 |
| Case1042 | CenterA | lesion_union | nnunet_oof | 0.7573770491803279 | 0 |
| Case1042 | CenterA | lesion_union | mosaic_clean_oof | 0.04156845939575744 | 0 |


\newpage

# 附录 E1：standardized casewise metrics 分块（续 6）

| case_id | center | metric_name | model_id | dice | empty_pred |
| --- | --- | --- | --- | --- | --- |
| Case1045 | CenterA | scar | nnunet_oof | 0.09968847352024922 | 0 |
| Case1045 | CenterA | scar | mosaic_clean_oof | 0.06570996978851963 | 0 |
| Case1045 | CenterA | lesion_union | nnunet_oof | 0.09968847352024922 | 0 |
| Case1045 | CenterA | lesion_union | mosaic_clean_oof | 0.09969824038876043 | 0 |
| Case1047 | CenterA | scar | nnunet_oof | 0.6283120251991847 | 0 |
| Case1047 | CenterA | scar | mosaic_clean_oof | 0.4432244614315497 | 0 |
| Case1047 | CenterA | lesion_union | nnunet_oof | 0.6283120251991847 | 0 |
| Case1047 | CenterA | lesion_union | mosaic_clean_oof | 0.23638550872160274 | 0 |


\newpage

# 附录 E1：standardized casewise metrics 分块（续 7）

| case_id | center | metric_name | model_id | dice | empty_pred |
| --- | --- | --- | --- | --- | --- |
| Case1053 | CenterA | scar | nnunet_oof | 0.5196241017136539 | 0 |
| Case1053 | CenterA | scar | mosaic_clean_oof | 0.11735941320293398 | 0 |
| Case1053 | CenterA | lesion_union | nnunet_oof | 0.5196241017136539 | 0 |
| Case1053 | CenterA | lesion_union | mosaic_clean_oof | 0.053154058808745915 | 0 |
| Case1062 | CenterA | scar | nnunet_oof | 0.5070823546159869 | 0 |
| Case1062 | CenterA | scar | mosaic_clean_oof | 0.18349627401381008 | 0 |
| Case1062 | CenterA | lesion_union | nnunet_oof | 0.5070823546159869 | 0 |
| Case1062 | CenterA | lesion_union | mosaic_clean_oof | 0.0973629374146727 | 0 |


\newpage

# 附录 E1：standardized casewise metrics 分块（续 8）

| case_id | center | metric_name | model_id | dice | empty_pred |
| --- | --- | --- | --- | --- | --- |
| Case1070 | CenterA | scar | nnunet_oof | 0.5004500450045004 | 0 |
| Case1070 | CenterA | scar | mosaic_clean_oof | 0.402416918429003 | 0 |
| Case1070 | CenterA | lesion_union | nnunet_oof | 0.5004500450045004 | 0 |
| Case1070 | CenterA | lesion_union | mosaic_clean_oof | 0.09348922308001249 | 0 |
| Case1073 | CenterA | scar | nnunet_oof | 0.4282765737874097 | 0 |
| Case1073 | CenterA | scar | mosaic_clean_oof | 0.11658653846153846 | 0 |
| Case1073 | CenterA | lesion_union | nnunet_oof | 0.4282765737874097 | 0 |
| Case1073 | CenterA | lesion_union | mosaic_clean_oof | 0.12659045404637345 | 0 |


\newpage

# 附录 E1：standardized casewise metrics 分块（续 9）

| case_id | center | metric_name | model_id | dice | empty_pred |
| --- | --- | --- | --- | --- | --- |
| Case1080 | CenterA | scar | nnunet_oof | 0.6369426751592356 | 0 |
| Case1080 | CenterA | scar | mosaic_clean_oof | 0.1005765534913517 | 0 |
| Case1080 | CenterA | lesion_union | nnunet_oof | 0.6369426751592356 | 0 |
| Case1080 | CenterA | lesion_union | mosaic_clean_oof | 0.07381254482264026 | 0 |
| Case2002 | CenterB | scar | nnunet_oof | 0.5602700096432015 | 0 |
| Case2002 | CenterB | scar | mosaic_clean_oof | 0.7485981308411215 | 0 |
| Case2002 | CenterB | pure_edema | nnunet_oof | 0.5376005596362364 | 0 |
| Case2002 | CenterB | pure_edema | mosaic_clean_oof | 0.44604893702366627 | 0 |


\newpage

# 附录 E1：standardized casewise metrics 分块（续 10）

| case_id | center | metric_name | model_id | dice | empty_pred |
| --- | --- | --- | --- | --- | --- |
| Case2002 | CenterB | lesion_union | nnunet_oof | 0.6753080082135524 | 0 |
| Case2002 | CenterB | lesion_union | mosaic_clean_oof | 0.5788543507641127 | 0 |
| Case2007 | CenterB | scar | nnunet_oof | 0.4898728214790391 | 0 |
| Case2007 | CenterB | scar | mosaic_clean_oof | 0.5997541990987301 | 0 |
| Case2007 | CenterB | pure_edema | nnunet_oof | 0.5701357466063348 | 0 |
| Case2007 | CenterB | pure_edema | mosaic_clean_oof | 0.5136444784493751 | 0 |
| Case2007 | CenterB | lesion_union | nnunet_oof | 0.7220942408376964 | 0 |
| Case2007 | CenterB | lesion_union | mosaic_clean_oof | 0.7312165985539139 | 0 |


\newpage

# 附录 E1：standardized casewise metrics 分块（续 11）

| case_id | center | metric_name | model_id | dice | empty_pred |
| --- | --- | --- | --- | --- | --- |
| Case2008 | CenterB | scar | nnunet_oof | 0.7531584062196307 | 0 |
| Case2008 | CenterB | scar | mosaic_clean_oof | 0.7747178329571106 | 0 |
| Case2008 | CenterB | pure_edema | nnunet_oof | 0.3485546711353163 | 0 |
| Case2008 | CenterB | pure_edema | mosaic_clean_oof | 0.2998538316976404 | 0 |
| Case2008 | CenterB | lesion_union | nnunet_oof | 0.5702576112412178 | 0 |
| Case2008 | CenterB | lesion_union | mosaic_clean_oof | 0.5596801827527127 | 0 |
| Case2017 | CenterB | scar | nnunet_oof | 0.5470588235294118 | 0 |
| Case2017 | CenterB | scar | mosaic_clean_oof | 0.6924019607843137 | 0 |


\newpage

# 附录 E1：standardized casewise metrics 分块（续 12）

| case_id | center | metric_name | model_id | dice | empty_pred |
| --- | --- | --- | --- | --- | --- |
| Case2017 | CenterB | pure_edema | nnunet_oof | 0.6796246648793566 | 0 |
| Case2017 | CenterB | pure_edema | mosaic_clean_oof | 0.3809687984830202 | 0 |
| Case2017 | CenterB | lesion_union | nnunet_oof | 0.8161448741559238 | 0 |
| Case2017 | CenterB | lesion_union | mosaic_clean_oof | 0.5424458495896677 | 0 |
| Case2020 | CenterB | scar | nnunet_oof | 0.4196185286103542 | 0 |
| Case2020 | CenterB | scar | mosaic_clean_oof | 0.0 | 0 |
| Case2020 | CenterB | pure_edema | nnunet_oof | 0.5630676084762866 | 0 |
| Case2020 | CenterB | pure_edema | mosaic_clean_oof | 0.0 | 0 |


\newpage

# 附录 E2：case oracle 和 voxel oracle 分块

| case_id | center | metric_name | best_case_model | case_oracle_dice | voxel_tp_oracle_dice |
| --- | --- | --- | --- | --- | --- |
| Case1002 | CenterA | scar | nnunet_oof | 0.6167400881057269 | 0.7338041142155358 |
| Case1002 | CenterA | lesion_union | nnunet_oof | 0.6167400881057269 | 0.8946663093004557 |
| Case1007 | CenterA | scar | nnunet_oof | 0.5810928013876843 | 0.911968777103209 |
| Case1007 | CenterA | lesion_union | nnunet_oof | 0.5810928013876843 | 0.9486695998323905 |
| Case1009 | CenterA | scar | nnunet_oof | 0.6048804535370964 | 0.7778275810548334 |
| Case1009 | CenterA | lesion_union | nnunet_oof | 0.6048804535370964 | 0.855623950755456 |
| Case1010 | CenterA | scar | nnunet_oof | 0.48279378027020137 | 0.7890460427324707 |
| Case1010 | CenterA | lesion_union | nnunet_oof | 0.48279378027020137 | 0.9465968586387434 |


\newpage

# 附录 E2：case oracle 和 voxel oracle 分块（续 2）

| case_id | center | metric_name | best_case_model | case_oracle_dice | voxel_tp_oracle_dice |
| --- | --- | --- | --- | --- | --- |
| Case1021 | CenterA | scar | nnunet_oof | 0.5699192044748291 | 0.8075624577987845 |
| Case1021 | CenterA | lesion_union | nnunet_oof | 0.5699192044748291 | 0.8910518053375196 |
| Case1023 | CenterA | scar | nnunet_oof | 0.6466011466011466 | 0.809106830122592 |
| Case1023 | CenterA | lesion_union | nnunet_oof | 0.6466011466011466 | 0.9032258064516129 |
| Case1029 | CenterA | scar | nnunet_oof | 0.16436865021770683 | 0.8728323699421965 |
| Case1029 | CenterA | lesion_union | nnunet_oof | 0.16436865021770683 | 0.9024390243902439 |
| Case1033 | CenterA | scar | nnunet_oof | 0.671361030077457 | 0.9045765669037713 |
| Case1033 | CenterA | lesion_union | nnunet_oof | 0.671361030077457 | 0.9621057985757884 |


\newpage

# 附录 E2：case oracle 和 voxel oracle 分块（续 3）

| case_id | center | metric_name | best_case_model | case_oracle_dice | voxel_tp_oracle_dice |
| --- | --- | --- | --- | --- | --- |
| Case1040 | CenterA | scar | nnunet_oof | 0.4280078895463511 | 0.749494365790234 |
| Case1040 | CenterA | lesion_union | nnunet_oof | 0.4280078895463511 | 0.9095490047871 |
| Case1042 | CenterA | scar | nnunet_oof | 0.7573770491803279 | 0.8738346799254195 |
| Case1042 | CenterA | lesion_union | nnunet_oof | 0.7573770491803279 | 0.8984802431610942 |
| Case1045 | CenterA | scar | nnunet_oof | 0.09968847352024922 | 0.21903052064631956 |
| Case1045 | CenterA | lesion_union | mosaic_clean_oof | 0.09969824038876043 | 0.9229098805646037 |
| Case1047 | CenterA | scar | nnunet_oof | 0.6283120251991847 | 0.7999641994092902 |
| Case1047 | CenterA | lesion_union | nnunet_oof | 0.6283120251991847 | 0.9152981150392363 |


\newpage

# 附录 E2：case oracle 和 voxel oracle 分块（续 4）

| case_id | center | metric_name | best_case_model | case_oracle_dice | voxel_tp_oracle_dice |
| --- | --- | --- | --- | --- | --- |
| Case1053 | CenterA | scar | nnunet_oof | 0.5196241017136539 | 0.6927860696517413 |
| Case1053 | CenterA | lesion_union | nnunet_oof | 0.5196241017136539 | 0.7743440233236152 |
| Case1062 | CenterA | scar | nnunet_oof | 0.5070823546159869 | 0.8913910391742904 |
| Case1062 | CenterA | lesion_union | nnunet_oof | 0.5070823546159869 | 0.9570782301666115 |
| Case1070 | CenterA | scar | nnunet_oof | 0.5004500450045004 | 0.9154228855721394 |
| Case1070 | CenterA | lesion_union | nnunet_oof | 0.5004500450045004 | 0.9742225859247136 |
| Case1073 | CenterA | scar | nnunet_oof | 0.4282765737874097 | 0.605580215599239 |
| Case1073 | CenterA | lesion_union | nnunet_oof | 0.4282765737874097 | 0.8110300081103001 |


\newpage

# 附录 E2：case oracle 和 voxel oracle 分块（续 5）

| case_id | center | metric_name | best_case_model | case_oracle_dice | voxel_tp_oracle_dice |
| --- | --- | --- | --- | --- | --- |
| Case1080 | CenterA | scar | nnunet_oof | 0.6369426751592356 | 0.8048359240069085 |
| Case1080 | CenterA | lesion_union | nnunet_oof | 0.6369426751592356 | 0.8945686900958466 |
| Case2002 | CenterB | scar | mosaic_clean_oof | 0.7485981308411215 | 0.9008810572687225 |
| Case2002 | CenterB | pure_edema | nnunet_oof | 0.5376005596362364 | 0.8198004304441401 |
| Case2002 | CenterB | lesion_union | nnunet_oof | 0.6753080082135524 | 0.8740532959326788 |
| Case2007 | CenterB | scar | mosaic_clean_oof | 0.5997541990987301 | 0.7985246657445828 |
| Case2007 | CenterB | pure_edema | nnunet_oof | 0.5701357466063348 | 0.9036370453693289 |
| Case2007 | CenterB | lesion_union | mosaic_clean_oof | 0.7312165985539139 | 0.9472682276794213 |


\newpage

# 附录 E2：case oracle 和 voxel oracle 分块（续 6）

| case_id | center | metric_name | best_case_model | case_oracle_dice | voxel_tp_oracle_dice |
| --- | --- | --- | --- | --- | --- |
| Case2008 | CenterB | scar | mosaic_clean_oof | 0.7747178329571106 | 0.9579487179487179 |
| Case2008 | CenterB | pure_edema | nnunet_oof | 0.3485546711353163 | 0.4638669793221062 |
| Case2008 | CenterB | lesion_union | nnunet_oof | 0.5702576112412178 | 0.6719378953421506 |
| Case2017 | CenterB | scar | mosaic_clean_oof | 0.6924019607843137 | 0.8994565217391305 |
| Case2017 | CenterB | pure_edema | nnunet_oof | 0.6796246648793566 | 0.9097633136094675 |
| Case2017 | CenterB | lesion_union | nnunet_oof | 0.8161448741559238 | 0.9754112260471426 |
| Case2020 | CenterB | scar | nnunet_oof | 0.4196185286103542 | 0.4307692307692308 |
| Case2020 | CenterB | pure_edema | nnunet_oof | 0.5630676084762866 | 0.7018867924528301 |


\newpage

# 附录 E2：case oracle 和 voxel oracle 分块（续 7）

| case_id | center | metric_name | best_case_model | case_oracle_dice | voxel_tp_oracle_dice |
| --- | --- | --- | --- | --- | --- |
| Case2020 | CenterB | lesion_union | nnunet_oof | 0.7695139911634757 | 0.7922668688400303 |
| Case2031 | CenterB | scar | nnunet_oof | 0.8013937282229965 | 0.8972559029993619 |
| Case2031 | CenterB | pure_edema | nnunet_oof | 0.29880478087649404 | 0.7984344422700587 |
| Case2031 | CenterB | lesion_union | nnunet_oof | 0.8012589928057554 | 0.9197416974169742 |
| Case2033 | CenterB | scar | mosaic_clean_oof | 0.7440613026819923 | 0.9776951672862454 |
| Case2033 | CenterB | pure_edema | nnunet_oof | 0.523033309709426 | 0.9168008588298443 |
| Case2033 | CenterB | lesion_union | nnunet_oof | 0.7858133544680008 | 0.9875180028804609 |
| Case3004 | CenterC | scar | nnunet_oof | 0.6247040252565115 | 0.8873475245156661 |


\newpage

# 附录 E2：case oracle 和 voxel oracle 分块（续 8）

| case_id | center | metric_name | best_case_model | case_oracle_dice | voxel_tp_oracle_dice |
| --- | --- | --- | --- | --- | --- |
| Case3004 | CenterC | pure_edema | nnunet_oof | 0.4530451866404715 | 0.8063480741797432 |
| Case3004 | CenterC | lesion_union | nnunet_oof | 0.7493601102579248 | 0.9805929919137466 |
| Case3011 | CenterC | scar | mosaic_clean_oof | 0.7138450993831391 | 0.8494663231505337 |
| Case3011 | CenterC | pure_edema | nnunet_oof | 0.26666666666666666 | 0.5664739884393064 |
| Case3011 | CenterC | lesion_union | mosaic_clean_oof | 0.754122752634842 | 0.8860688885789988 |
| Case3012 | CenterC | scar | nnunet_oof | 0.8267066766691673 | 0.8777379530067703 |
| Case3012 | CenterC | pure_edema | nnunet_oof | 0.45068083693125205 | 0.5211420310805926 |
| Case3012 | CenterC | lesion_union | nnunet_oof | 0.703188303681522 | 0.7577528089887641 |


\newpage

# 附录 E2：case oracle 和 voxel oracle 分块（续 9）

| case_id | center | metric_name | best_case_model | case_oracle_dice | voxel_tp_oracle_dice |
| --- | --- | --- | --- | --- | --- |
| Case3023 | CenterC | scar | mosaic_clean_oof | 0.6629643814630409 | 0.9761904761904762 |
| Case3023 | CenterC | pure_edema | mosaic_clean_oof | 0.3463302752293578 | 0.5878003696857671 |
| Case3023 | CenterC | lesion_union | nnunet_oof | 0.7185840707964601 | 0.9637166442695335 |
| Case3026 | CenterC | scar | nnunet_oof | 0.8081740276862228 | 0.9205207687538748 |
| Case3026 | CenterC | pure_edema | nnunet_oof | 0.21919504643962848 | 0.4873810508895325 |
| Case3026 | CenterC | lesion_union | mosaic_clean_oof | 0.7943426179823928 | 0.9611764705882353 |
| Case3034 | CenterC | scar | nnunet_oof | 0.8293831423638361 | 0.9992917847025495 |
| Case3034 | CenterC | pure_edema | nnunet_oof | 0.6546035125066525 | 0.8521543227259927 |


\newpage

# 附录 E2：case oracle 和 voxel oracle 分块（续 10）

| case_id | center | metric_name | best_case_model | case_oracle_dice | voxel_tp_oracle_dice |
| --- | --- | --- | --- | --- | --- |
| Case3034 | CenterC | lesion_union | nnunet_oof | 0.8200217198143943 | 0.9770767613038907 |
| Case3038 | CenterC | scar | nnunet_oof | 0.75830144426614 | 0.8583495340886237 |
| Case3038 | CenterC | pure_edema | nnunet_oof | 0.16778761061946904 | 0.5391705069124424 |
| Case3038 | CenterC | lesion_union | nnunet_oof | 0.7429068277503204 | 0.9254175976167678 |
| Case3040 | CenterC | scar | mosaic_clean_oof | 0.896551724137931 | 0.9404626469472885 |
| Case3040 | CenterC | pure_edema | nnunet_oof | 0.24913093858632676 | 0.9072512647554806 |
| Case3040 | CenterC | lesion_union | nnunet_oof | 0.8685294117647059 | 0.9888114155991568 |
| Case3044 | CenterC | scar | nnunet_oof | 0.7844537386514332 | 0.8406698084829038 |


\newpage

# 附录 E2：case oracle 和 voxel oracle 分块（续 11）

| case_id | center | metric_name | best_case_model | case_oracle_dice | voxel_tp_oracle_dice |
| --- | --- | --- | --- | --- | --- |
| Case3044 | CenterC | pure_edema | nnunet_oof | 0.16612529002320187 | 0.849015317286652 |
| Case3044 | CenterC | lesion_union | mosaic_clean_oof | 0.8614214019750688 | 0.9557705597788528 |
| Case5005 | CenterE | scar | nnunet_oof | 0.5725747629467542 | 0.6074055604039397 |
| Case5005 | CenterE | lesion_union | nnunet_oof | 0.5725747629467542 | 0.6373063315847262 |
| Case6001 | CenterF | scar | nnunet_oof | 0.44598337950138506 | 0.7146321746160065 |
| Case6001 | CenterF | lesion_union | nnunet_oof | 0.44598337950138506 | 0.7445716541650217 |
| Case6010 | CenterF | scar | nnunet_oof | 0.49259110933119743 | 0.5942290351668169 |
| Case6010 | CenterF | lesion_union | nnunet_oof | 0.49259110933119743 | 0.8540977581771407 |


\newpage

# 附录 E2：case oracle 和 voxel oracle 分块（续 12）

| case_id | center | metric_name | best_case_model | case_oracle_dice | voxel_tp_oracle_dice |
| --- | --- | --- | --- | --- | --- |
| Case7005 | CenterG | scar | nnunet_oof | 0.0 | 1.0 |
| Case7005 | CenterG | lesion_union | nnunet_oof | 0.0 | 1.0 |
| Case8003 | CenterH | scar | mosaic_clean_oof | 0.7372156126069714 | 0.8894625674724244 |
| Case8003 | CenterH | lesion_union | nnunet_oof | 0.7172976649285876 | 0.9875909285408644 |
| Case8011 | CenterH | scar | mosaic_clean_oof | 0.2871452420701169 | 0.6880907372400756 |
| Case8011 | CenterH | lesion_union | nnunet_oof | 0.22406639004149378 | 0.8528925619834711 |
| Case8015 | CenterH | scar | nnunet_oof | 0.46925795053003533 | 0.608346709470305 |
| Case8015 | CenterH | lesion_union | nnunet_oof | 0.46925795053003533 | 0.9468569693288794 |


\newpage

# 附录 E3：PRISM 13 checkpoint corrected metrics 分块

| checkpoint_step | case_id | metric_name | dice | anchor_dice | dice_delta_vs_anchor |
| --- | --- | --- | --- | --- | --- |
| 500 | Case1004 | scar | 0.530063061 |  |  |
| 500 | Case1004 | pure_edema | 1.000000000 |  |  |
| 500 | Case1004 | edema_zone | 0.000000000 |  |  |
| 500 | Case1008 | scar | 0.351104376 |  |  |
| 500 | Case1008 | pure_edema | 1.000000000 |  |  |
| 500 | Case1008 | edema_zone | 0.000000000 |  |  |
| 500 | Case1020 | scar | 0.301903303 |  |  |
| 500 | Case1020 | pure_edema | 1.000000000 |  |  |


\newpage

# 附录 E3：PRISM 13 checkpoint corrected metrics 分块（续 2）

| checkpoint_step | case_id | metric_name | dice | anchor_dice | dice_delta_vs_anchor |
| --- | --- | --- | --- | --- | --- |
| 500 | Case1020 | edema_zone | 0.000000000 |  |  |
| 500 | Case1026 | scar | 0.308909785 |  |  |
| 500 | Case1026 | pure_edema | 1.000000000 |  |  |
| 500 | Case1026 | edema_zone | 0.000000000 |  |  |
| 500 | Case1032 | scar | 0.313862475 |  |  |
| 500 | Case1032 | pure_edema | 1.000000000 |  |  |
| 500 | Case1032 | edema_zone | 0.000000000 |  |  |
| 500 | Case1035 | scar | 0.373240645 |  |  |


\newpage

# 附录 E3：PRISM 13 checkpoint corrected metrics 分块（续 3）

| checkpoint_step | case_id | metric_name | dice | anchor_dice | dice_delta_vs_anchor |
| --- | --- | --- | --- | --- | --- |
| 500 | Case1035 | pure_edema | 1.000000000 |  |  |
| 500 | Case1035 | edema_zone | 0.000000000 |  |  |
| 500 | Case1039 | scar | 0.354683374 |  |  |
| 500 | Case1039 | pure_edema | 1.000000000 |  |  |
| 500 | Case1039 | edema_zone | 0.000000000 |  |  |
| 500 | Case1043 | scar | 0.340329835 |  |  |
| 500 | Case1043 | pure_edema | 1.000000000 |  |  |
| 500 | Case1043 | edema_zone | 0.000000000 |  |  |


\newpage

# 附录 E3：PRISM 13 checkpoint corrected metrics 分块（续 4）

| checkpoint_step | case_id | metric_name | dice | anchor_dice | dice_delta_vs_anchor |
| --- | --- | --- | --- | --- | --- |
| 500 | Case1056 | scar | 0.297742319 |  |  |
| 500 | Case1056 | pure_edema | 1.000000000 |  |  |
| 500 | Case1056 | edema_zone | 0.000000000 |  |  |
| 500 | Case1058 | scar | 0.400374550 |  |  |
| 500 | Case1058 | pure_edema | 1.000000000 |  |  |
| 500 | Case1058 | edema_zone | 0.000000000 |  |  |
| 500 | Case1071 | scar | 0.265054471 |  |  |
| 500 | Case1071 | pure_edema | 1.000000000 |  |  |


\newpage

# 附录 E3：PRISM 13 checkpoint corrected metrics 分块（续 5）

| checkpoint_step | case_id | metric_name | dice | anchor_dice | dice_delta_vs_anchor |
| --- | --- | --- | --- | --- | --- |
| 500 | Case1071 | edema_zone | 0.000000000 |  |  |
| 500 | Case1074 | scar | 0.274797723 |  |  |
| 500 | Case1074 | pure_edema | 1.000000000 |  |  |
| 500 | Case1074 | edema_zone | 0.000000000 |  |  |
| 500 | Case1077 | scar | 0.160764612 |  |  |
| 500 | Case1077 | pure_edema | 1.000000000 |  |  |
| 500 | Case1077 | edema_zone | 0.000000000 |  |  |
| 500 | Case2009 | scar | 0.297890659 |  |  |


\newpage

# 附录 E3：PRISM 13 checkpoint corrected metrics 分块（续 6）

| checkpoint_step | case_id | metric_name | dice | anchor_dice | dice_delta_vs_anchor |
| --- | --- | --- | --- | --- | --- |
| 500 | Case2009 | pure_edema | 0.236245037 |  |  |
| 500 | Case2009 | edema_zone | 0.578436965 |  |  |
| 500 | Case2011 | scar | 0.450949894 |  |  |
| 500 | Case2011 | pure_edema | 0.254467582 |  |  |
| 500 | Case2011 | edema_zone | 0.725151311 |  |  |
| 500 | Case2012 | scar | 0.088264300 |  |  |
| 500 | Case2012 | pure_edema | 0.230547550 |  |  |
| 500 | Case2012 | edema_zone | 0.237605913 |  |  |


\newpage

# 附录 E3：PRISM 13 checkpoint corrected metrics 分块（续 7）

| checkpoint_step | case_id | metric_name | dice | anchor_dice | dice_delta_vs_anchor |
| --- | --- | --- | --- | --- | --- |
| 500 | Case2016 | scar | 0.359180649 |  |  |
| 500 | Case2016 | pure_edema | 0.217131669 |  |  |
| 500 | Case2016 | edema_zone | 0.574229180 |  |  |
| 500 | Case2018 | scar | 0.195901920 |  |  |
| 500 | Case2018 | pure_edema | 0.137720096 |  |  |
| 500 | Case2018 | edema_zone | 0.450291095 |  |  |
| 500 | Case2019 | scar | 0.302401890 |  |  |
| 500 | Case2019 | pure_edema | 0.167984934 |  |  |


\newpage

# 附录 E3：PRISM 13 checkpoint corrected metrics 分块（续 8）

| checkpoint_step | case_id | metric_name | dice | anchor_dice | dice_delta_vs_anchor |
| --- | --- | --- | --- | --- | --- |
| 500 | Case2019 | edema_zone | 0.641064946 |  |  |
| 500 | Case2021 | scar | 0.531396648 |  |  |
| 500 | Case2021 | pure_edema | 0.184663132 |  |  |
| 500 | Case2021 | edema_zone | 0.595887650 |  |  |
| 500 | Case2023 | scar | 0.413302614 |  |  |
| 500 | Case2023 | pure_edema | 0.355800092 |  |  |
| 500 | Case2023 | edema_zone | 0.640534583 |  |  |
| 500 | Case2034 | scar | 0.383697505 |  |  |


\newpage

# 附录 E3：PRISM 13 checkpoint corrected metrics 分块（续 9）

| checkpoint_step | case_id | metric_name | dice | anchor_dice | dice_delta_vs_anchor |
| --- | --- | --- | --- | --- | --- |
| 500 | Case2034 | pure_edema | 0.219345455 |  |  |
| 500 | Case2034 | edema_zone | 0.483364428 |  |  |
| 500 | Case3009 | scar | 0.231240876 |  |  |
| 500 | Case3009 | pure_edema | 0.087815326 |  |  |
| 500 | Case3009 | edema_zone | 0.223065476 |  |  |
| 500 | Case3014 | scar | 0.473822656 |  |  |
| 500 | Case3014 | pure_edema | 0.147459529 |  |  |
| 500 | Case3014 | edema_zone | 0.609071545 |  |  |


\newpage

# 附录 E3：PRISM 13 checkpoint corrected metrics 分块（续 10）

| checkpoint_step | case_id | metric_name | dice | anchor_dice | dice_delta_vs_anchor |
| --- | --- | --- | --- | --- | --- |
| 500 | Case3017 | scar | 0.559992978 |  |  |
| 500 | Case3017 | pure_edema | 0.085812357 |  |  |
| 500 | Case3017 | edema_zone | 0.550992958 |  |  |
| 500 | Case3028 | scar | 0.364503554 |  |  |
| 500 | Case3028 | pure_edema | 0.274458874 |  |  |
| 500 | Case3028 | edema_zone | 0.491357091 |  |  |
| 500 | Case3032 | scar | 0.000000000 |  |  |
| 500 | Case3032 | pure_edema | 0.061583578 |  |  |


\newpage

# 附录 E3：PRISM 13 checkpoint corrected metrics 分块（续 11）

| checkpoint_step | case_id | metric_name | dice | anchor_dice | dice_delta_vs_anchor |
| --- | --- | --- | --- | --- | --- |
| 500 | Case3032 | edema_zone | 0.483450895 |  |  |
| 500 | Case3036 | scar | 0.689690198 |  |  |
| 500 | Case3036 | pure_edema | 0.167058824 |  |  |
| 500 | Case3036 | edema_zone | 0.643038322 |  |  |
| 500 | Case3042 | scar | 0.547086765 |  |  |
| 500 | Case3042 | pure_edema | 0.070341362 |  |  |
| 500 | Case3042 | edema_zone | 0.693790961 |  |  |
| 500 | Case7006 | scar | 0.000000000 |  |  |


\newpage

# 附录 E3：PRISM 13 checkpoint corrected metrics 分块（续 12）

| checkpoint_step | case_id | metric_name | dice | anchor_dice | dice_delta_vs_anchor |
| --- | --- | --- | --- | --- | --- |
| 500 | Case7006 | pure_edema | 1.000000000 |  |  |
| 500 | Case7006 | edema_zone | 1.000000000 |  |  |
| 500 | Case8009 | scar | 0.216859325 |  |  |
| 500 | Case8009 | pure_edema | 1.000000000 |  |  |
| 500 | Case8009 | edema_zone | 0.000000000 |  |  |
| 500 | Case8012 | scar | 0.124890760 |  |  |
| 500 | Case8012 | pure_edema | 1.000000000 |  |  |
| 500 | Case8012 | edema_zone | 0.000000000 |  |  |


\newpage

# 附录 E4：Batch0-7 / SRR casewise metrics 分块

| case_id | pathology | anchor_dice | srr_dice | dice_delta_srr_minus_anchor | srr_hd95 |
| --- | --- | --- | --- | --- | --- |
| Case1002 | edema |  |  |  | 0.0 |
| Case1002 | scar | 0.6167400881057269 | 0.6167400881057269 | 0.0 | 4.323466070663145 |
| Case1007 | edema |  |  |  | 0.0 |
| Case1007 | scar | 0.5810928013876843 | 0.5810928013876843 | 0.0 | 6.836000084877014 |
| Case1009 | edema |  |  |  | 0.0 |
| Case1009 | scar | 0.6048804535370964 | 0.6048804535370964 | 0.0 | 8.496820117260281 |
| Case1010 | edema |  |  |  | 0.0 |
| Case1010 | scar | 0.48279378027020137 | 0.48279378027020137 | 0.0 | 9.103254137198277 |


\newpage

# 附录 E4：Batch0-7 / SRR casewise metrics 分块（续 2）

| case_id | pathology | anchor_dice | srr_dice | dice_delta_srr_minus_anchor | srr_hd95 |
| --- | --- | --- | --- | --- | --- |
| Case1021 | edema |  |  |  | 0.0 |
| Case1021 | scar | 0.5699192044748291 | 0.5699192044748291 | 0.0 | 7.972077529615252 |
| Case1023 | edema |  |  |  | 0.0 |
| Case1023 | scar | 0.6466011466011466 | 0.6466011466011466 | 0.0 | 5.0 |
| Case1029 | edema |  |  |  | 0.0 |
| Case1029 | scar | 0.16436865021770683 | 0.16436865021770683 | 0.0 | 51.395270620488255 |
| Case1033 | edema |  |  |  | 0.0 |
| Case1033 | scar | 0.671361030077457 | 0.671361030077457 | 0.0 | 7.152037197524651 |


\newpage

# 附录 E4：Batch0-7 / SRR casewise metrics 分块（续 3）

| case_id | pathology | anchor_dice | srr_dice | dice_delta_srr_minus_anchor | srr_hd95 |
| --- | --- | --- | --- | --- | --- |
| Case1040 | edema |  |  |  | 0.0 |
| Case1040 | scar | 0.4280078895463511 | 0.4280078895463511 | 0.0 | 8.5 |
| Case1042 | edema |  |  |  | 0.0 |
| Case1042 | scar | 0.7573770491803279 | 0.7573770491803279 | 0.0 | 3.057152176795867 |
| Case1045 | edema |  |  |  | 0.0 |
| Case1045 | scar | 0.09968847352024922 | 0.09968847352024922 | 0.0 | 58.23937490442107 |
| Case1047 | edema |  |  |  | 0.0 |
| Case1047 | scar | 0.6283120251991847 | 0.6283120251991847 | 0.0 | 5.781199932098389 |


\newpage

# 附录 E4：Batch0-7 / SRR casewise metrics 分块（续 4）

| case_id | pathology | anchor_dice | srr_dice | dice_delta_srr_minus_anchor | srr_hd95 |
| --- | --- | --- | --- | --- | --- |
| Case1053 | edema |  |  |  | 0.0 |
| Case1053 | scar | 0.5196241017136539 | 0.5196241017136539 | 0.0 | 27.536782421660927 |
| Case1062 | edema |  |  |  | 0.0 |
| Case1062 | scar | 0.5070823546159869 | 0.5070823546159869 | 0.0 | 15.291149322372709 |
| Case1070 | edema |  |  |  | 0.0 |
| Case1070 | scar | 0.5004500450045004 | 0.5004500450045004 | 0.0 | 34.297412438841505 |
| Case1073 | edema |  |  |  | 0.0 |
| Case1073 | scar | 0.4282765737874097 | 0.4282765737874097 | 0.0 | 10.678173489481713 |


\newpage

# 附录 E4：Batch0-7 / SRR casewise metrics 分块（续 5）

| case_id | pathology | anchor_dice | srr_dice | dice_delta_srr_minus_anchor | srr_hd95 |
| --- | --- | --- | --- | --- | --- |
| Case1080 | edema |  |  |  | 0.0 |
| Case1080 | scar | 0.6369426751592356 | 0.6369426751592356 | 0.0 | 11.0 |
| Case2002 | edema | 0.5376005596362364 | 0.5376005596362364 | 0.0 | 17.453201935819685 |
| Case2002 | scar | 0.5602700096432015 | 0.5602700096432015 | 0.0 | 21.415372143918024 |
| Case2007 | edema | 0.5701357466063348 | 0.5701357466063348 | 0.0 | 7.5130097186944615 |
| Case2007 | scar | 0.4898728214790391 | 0.4898728214790391 | 0.0 | 11.682996338833703 |
| Case2008 | edema | 0.3485546711353163 | 0.3485546711353163 | 0.0 | 33.237885822186755 |
| Case2008 | scar | 0.7531584062196307 | 0.7531584062196307 | 0.0 | 6.640625 |


\newpage

# 附录 E4：Batch0-7 / SRR casewise metrics 分块（续 6）

| case_id | pathology | anchor_dice | srr_dice | dice_delta_srr_minus_anchor | srr_hd95 |
| --- | --- | --- | --- | --- | --- |
| Case2017 | edema | 0.6796246648793566 | 0.6793211255024565 | -0.00030353937690008603 | 10.0 |
| Case2017 | scar | 0.5470588235294118 | 0.5470588235294118 | 0.0 | 11.338866091557966 |
| Case2020 | edema | 0.5630676084762866 | 0.5630676084762866 | 0.0 | 7.5130097186944615 |
| Case2020 | scar | 0.4196185286103542 | 0.4196185286103542 | 0.0 | 20.994429281533453 |
| Case2031 | edema | 0.29880478087649404 | 0.29880478087649404 | 0.0 | 25.052956799932126 |
| Case2031 | scar | 0.8013937282229965 | 0.8013937282229965 | 0.0 | 5.008673145796307 |
| Case2033 | edema | 0.523033309709426 | 0.5228480340063762 | -0.0001852757030497143 | 10.76453641085509 |
| Case2033 | scar | 0.7208988764044943 | 0.7208988764044943 | 0.0 | 10.0 |


\newpage

# 附录 E4：Batch0-7 / SRR casewise metrics 分块（续 7）

| case_id | pathology | anchor_dice | srr_dice | dice_delta_srr_minus_anchor | srr_hd95 |
| --- | --- | --- | --- | --- | --- |
| Case3004 | edema | 0.4530451866404715 | 0.4530451866404715 | 0.0 | 9.222044972510458 |
| Case3004 | scar | 0.6247040252565115 | 0.6247040252565115 | 0.0 | 24.000003814697266 |
| Case3011 | edema | 0.26666666666666666 | 0.26666666666666666 | 0.0 | 34.26613348722458 |
| Case3011 | scar | 0.6389535925461387 | 0.6389535925461387 | 0.0 | 10.960275328815657 |
| Case3012 | edema | 0.45068083693125205 | 0.4506060102938735 | -7.482663737856665e-05 | 22.41143161325818 |
| Case3012 | scar | 0.8267066766691673 | 0.8267066766691673 | 0.0 | 2.916266679763794 |
| Case3023 | edema | 0.16291793313069908 | 0.16291793313069908 | 0.0 | 41.324851944191856 |
| Case3023 | scar | 0.6612691466083152 | 0.6612691466083152 | 0.0 | 4.124789669313123 |


\newpage

# 附录 E4：Batch0-7 / SRR casewise metrics 分块（续 8）

| case_id | pathology | anchor_dice | srr_dice | dice_delta_srr_minus_anchor | srr_hd95 |
| --- | --- | --- | --- | --- | --- |
| Case3026 | edema | 0.21919504643962848 | 0.21919504643962848 | 0.0 | 17.325748731744103 |
| Case3026 | scar | 0.8081740276862228 | 0.8081740276862228 | 0.0 | 2.916266679763794 |
| Case3034 | edema | 0.6546035125066525 | 0.6544293695131684 | -0.00017414299348406104 | 9.135179190762985 |
| Case3034 | scar | 0.8293831423638361 | 0.8293831423638361 | 0.0 | 1.6302426341173635 |
| Case3038 | edema | 0.16778761061946904 | 0.16778761061946904 | 0.0 | 28.21288893486063 |
| Case3038 | scar | 0.75830144426614 | 0.75830144426614 | 0.0 | 8.297908510253126 |
| Case3040 | edema | 0.24913093858632676 | 0.24913093858632676 | 0.0 | 24.13887469193756 |
| Case3040 | scar | 0.8691367757193535 | 0.8691367757193535 | 0.0 | 1.458133339881897 |


\newpage

# 附录 E4：Batch0-7 / SRR casewise metrics 分块（续 9）

| case_id | pathology | anchor_dice | srr_dice | dice_delta_srr_minus_anchor | srr_hd95 |
| --- | --- | --- | --- | --- | --- |
| Case3044 | edema | 0.16612529002320187 | 0.16612529002320187 | 0.0 | 22.61223504639135 |
| Case3044 | scar | 0.7844537386514332 | 0.7844537386514332 | 0.0 | 4.89072790235209 |
| Case5005 | edema |  |  |  | 0.0 |
| Case5005 | scar | 0.5725747629467542 | 0.5725747629467542 | 0.0 | 11.148974014770653 |
| Case6001 | edema |  |  |  | 0.0 |
| Case6001 | scar | 0.44598337950138506 | 0.44598337950138506 | 0.0 | 10.606601717798213 |
| Case6010 | edema |  |  |  | 0.0 |
| Case6010 | scar | 0.49259110933119743 | 0.49259110933119743 | 0.0 | 13.050383136138187 |


\newpage

# 附录 E4：Batch0-7 / SRR casewise metrics 分块（续 10）

| case_id | pathology | anchor_dice | srr_dice | dice_delta_srr_minus_anchor | srr_hd95 |
| --- | --- | --- | --- | --- | --- |
| Case7005 | edema |  |  |  | 0.0 |
| Case7005 | scar | 0.0 | 0.0 | 0.0 |  |
| Case8003 | edema |  |  |  | 0.0 |
| Case8003 | scar | 0.7172976649285876 | 0.7172976649285876 | 0.0 | 8.754271418365223 |
| Case8011 | edema |  |  |  | 0.0 |
| Case8011 | scar | 0.22406639004149378 | 0.22406639004149378 | 0.0 | 31.32764229603699 |
| Case8015 | edema |  |  |  | 0.0 |
| Case8015 | scar | 0.46925795053003533 | 0.46925795053003533 | 0.0 | 20.046675576268406 |


\newpage

# 附录 E4：Batch0-7 / SRR casewise metrics 分块（续 11）

| case_id | pathology | anchor_dice | srr_dice | dice_delta_srr_minus_anchor | srr_hd95 |
| --- | --- | --- | --- | --- | --- |
| Case8019 | edema |  |  |  | 0.0 |
| Case8019 | scar | 0.6588021778584392 | 0.6588021778584392 | 0.0 | 11.25 |
| Case8021 | edema |  |  |  | 0.0 |
| Case8021 | scar | 0.0 | 0.0 | 0.0 |  |
| Case8022 | edema |  |  |  | 0.0 |
| Case8022 | scar | 0.6748560460652591 | 0.6748560460652591 | 0.0 | 10.093025488583056 |
| Case8023 | edema |  |  |  | 0.0 |
| Case8023 | scar | 0.45514445007602633 | 0.45514445007602633 | 0.0 | 32.0090827611819 |


\newpage

# 附录 E5：ARC casewise metrics 分块

| case_id | variant | pathology | dice | hd95 | changed_mask_ratio_vs_nnunet |
| --- | --- | --- | --- | --- | --- |
| Case1002 | raw_direct_enabled | scar | 0.3811576354679803 | 15.316167399909908 | 0.7589718719689622 |
| Case1002 | raw_direct_enabled | edema_zone | 0.3811576354679803 | 15.316167399909908 | 0.7589718719689622 |
| Case1002 | raw_direct_enabled | pure_edema |  | 0.0 | 0.0 |
| Case1002 | postprocessed_enabled | scar | 0.4097646033129904 | 16.08990523109105 | 0.8098933074684772 |
| Case1002 | postprocessed_enabled | edema_zone | 0.4097646033129904 | 16.08990523109105 | 0.8098933074684772 |
| Case1002 | postprocessed_enabled | pure_edema |  | 0.0 | 0.0 |
| Case1002 | nnunet_anchor | scar | 0.6167400881057269 | 4.323466070663145 | 0.0 |
| Case1002 | nnunet_anchor | edema_zone | 0.6167400881057269 | 4.323466070663145 | 0.0 |


\newpage

# 附录 E5：ARC casewise metrics 分块（续 2）

| case_id | variant | pathology | dice | hd95 | changed_mask_ratio_vs_nnunet |
| --- | --- | --- | --- | --- | --- |
| Case1002 | nnunet_anchor | pure_edema |  | 0.0 | 0.0 |
| Case1002 | raw_direct_identity | scar | 0.3811576354679803 | 15.316167399909908 | 0.7589718719689622 |
| Case1002 | raw_direct_identity | edema_zone | 0.3811576354679803 | 15.316167399909908 | 0.7589718719689622 |
| Case1002 | raw_direct_identity | pure_edema |  | 0.0 | 0.0 |
| Case1002 | postprocessed_identity | scar | 0.4097646033129904 | 16.08990523109105 | 0.8098933074684772 |
| Case1002 | postprocessed_identity | edema_zone | 0.4097646033129904 | 16.08990523109105 | 0.8098933074684772 |
| Case1002 | postprocessed_identity | pure_edema |  | 0.0 | 0.0 |
| Case1007 | raw_direct_enabled | scar | 0.5335622853574774 | 5.890021974846564 | 1.1359107214029494 |


\newpage

# 附录 E5：ARC casewise metrics 分块（续 3）

| case_id | variant | pathology | dice | hd95 | changed_mask_ratio_vs_nnunet |
| --- | --- | --- | --- | --- | --- |
| Case1007 | raw_direct_enabled | edema_zone | 0.5335622853574774 | 5.890021974846564 | 1.1359107214029494 |
| Case1007 | raw_direct_enabled | pure_edema |  | 0.0 | 0.0 |
| Case1007 | postprocessed_enabled | scar | 0.5289711053355756 | 6.348233338766624 | 1.1992825827022717 |
| Case1007 | postprocessed_enabled | edema_zone | 0.5289711053355756 | 6.348233338766624 | 1.1992825827022717 |
| Case1007 | postprocessed_enabled | pure_edema |  | 0.0 | 0.0 |
| Case1007 | nnunet_anchor | scar | 0.5810928013876843 | 6.836000084877014 | 0.0 |
| Case1007 | nnunet_anchor | edema_zone | 0.5810928013876843 | 6.836000084877014 | 0.0 |
| Case1007 | nnunet_anchor | pure_edema |  | 0.0 | 0.0 |


\newpage

# 附录 E5：ARC casewise metrics 分块（续 4）

| case_id | variant | pathology | dice | hd95 | changed_mask_ratio_vs_nnunet |
| --- | --- | --- | --- | --- | --- |
| Case1007 | raw_direct_identity | scar | 0.5335622853574774 | 5.890021974846564 | 1.1359107214029494 |
| Case1007 | raw_direct_identity | edema_zone | 0.5335622853574774 | 5.890021974846564 | 1.1359107214029494 |
| Case1007 | raw_direct_identity | pure_edema |  | 0.0 | 0.0 |
| Case1007 | postprocessed_identity | scar | 0.5289711053355756 | 6.348233338766624 | 1.1992825827022717 |
| Case1007 | postprocessed_identity | edema_zone | 0.5289711053355756 | 6.348233338766624 | 1.1992825827022717 |
| Case1007 | postprocessed_identity | pure_edema |  | 0.0 | 0.0 |
| Case1009 | raw_direct_enabled | scar | 0.5536579736902839 | 10.890367585526468 | 0.49926650366748165 |
| Case1009 | raw_direct_enabled | edema_zone | 0.5536579736902839 | 10.890367585526468 | 0.49926650366748165 |


\newpage

# 附录 E5：ARC casewise metrics 分块（续 5）

| case_id | variant | pathology | dice | hd95 | changed_mask_ratio_vs_nnunet |
| --- | --- | --- | --- | --- | --- |
| Case1009 | raw_direct_enabled | pure_edema |  | 0.0 | 0.0 |
| Case1009 | postprocessed_enabled | scar | 0.5547378104875805 | 10.884015542109314 | 0.5232273838630807 |
| Case1009 | postprocessed_enabled | edema_zone | 0.5547378104875805 | 10.884015542109314 | 0.5232273838630807 |
| Case1009 | postprocessed_enabled | pure_edema |  | 0.0 | 0.0 |
| Case1009 | nnunet_anchor | scar | 0.6048804535370964 | 8.496820117260281 | 0.0 |
| Case1009 | nnunet_anchor | edema_zone | 0.6048804535370964 | 8.496820117260281 | 0.0 |
| Case1009 | nnunet_anchor | pure_edema |  | 0.0 | 0.0 |
| Case1009 | raw_direct_identity | scar | 0.5536579736902839 | 10.890367585526468 | 0.49926650366748165 |


\newpage

# 附录 E5：ARC casewise metrics 分块（续 6）

| case_id | variant | pathology | dice | hd95 | changed_mask_ratio_vs_nnunet |
| --- | --- | --- | --- | --- | --- |
| Case1009 | raw_direct_identity | edema_zone | 0.5536579736902839 | 10.890367585526468 | 0.49926650366748165 |
| Case1009 | raw_direct_identity | pure_edema |  | 0.0 | 0.0 |
| Case1009 | postprocessed_identity | scar | 0.5547378104875805 | 10.884015542109314 | 0.5232273838630807 |
| Case1009 | postprocessed_identity | edema_zone | 0.5547378104875805 | 10.884015542109314 | 0.5232273838630807 |
| Case1009 | postprocessed_identity | pure_edema |  | 0.0 | 0.0 |
| Case1010 | raw_direct_enabled | scar | 0.3667673716012085 | 14.003965359377354 | 1.1158051689860835 |
| Case1010 | raw_direct_enabled | edema_zone | 0.3667673716012085 | 14.003965359377354 | 1.1158051689860835 |
| Case1010 | raw_direct_enabled | pure_edema |  | 0.0 | 0.0 |


\newpage

# 附录 E5：ARC casewise metrics 分块（续 7）

| case_id | variant | pathology | dice | hd95 | changed_mask_ratio_vs_nnunet |
| --- | --- | --- | --- | --- | --- |
| Case1010 | postprocessed_enabled | scar | 0.4023602135431301 | 13.96507748175677 | 1.166003976143141 |
| Case1010 | postprocessed_enabled | edema_zone | 0.4023602135431301 | 13.96507748175677 | 1.166003976143141 |
| Case1010 | postprocessed_enabled | pure_edema |  | 0.0 | 0.0 |
| Case1010 | nnunet_anchor | scar | 0.48279378027020137 | 9.103254137198277 | 0.0 |
| Case1010 | nnunet_anchor | edema_zone | 0.48279378027020137 | 9.103254137198277 | 0.0 |
| Case1010 | nnunet_anchor | pure_edema |  | 0.0 | 0.0 |
| Case1010 | raw_direct_identity | scar | 0.3667673716012085 | 14.003965359377354 | 1.1158051689860835 |
| Case1010 | raw_direct_identity | edema_zone | 0.3667673716012085 | 14.003965359377354 | 1.1158051689860835 |


\newpage

# 附录 E5：ARC casewise metrics 分块（续 8）

| case_id | variant | pathology | dice | hd95 | changed_mask_ratio_vs_nnunet |
| --- | --- | --- | --- | --- | --- |
| Case1010 | raw_direct_identity | pure_edema |  | 0.0 | 0.0 |
| Case1010 | postprocessed_identity | scar | 0.4023602135431301 | 13.96507748175677 | 1.166003976143141 |
| Case1010 | postprocessed_identity | edema_zone | 0.4023602135431301 | 13.96507748175677 | 1.166003976143141 |
| Case1010 | postprocessed_identity | pure_edema |  | 0.0 | 0.0 |
| Case1021 | raw_direct_enabled | scar | 0.523430028689831 | 9.57040011882782 | 0.5996602491506229 |
| Case1021 | raw_direct_enabled | edema_zone | 0.523430028689831 | 9.57040011882782 | 0.5996602491506229 |
| Case1021 | raw_direct_enabled | pure_edema |  | 0.0 | 0.0 |
| Case1021 | postprocessed_enabled | scar | 0.5278200060808756 | 9.965796328325363 | 0.6540203850509626 |


\newpage

# 附录 E5：ARC casewise metrics 分块（续 9）

| case_id | variant | pathology | dice | hd95 | changed_mask_ratio_vs_nnunet |
| --- | --- | --- | --- | --- | --- |
| Case1021 | postprocessed_enabled | edema_zone | 0.5278200060808756 | 9.965796328325363 | 0.6540203850509626 |
| Case1021 | postprocessed_enabled | pure_edema |  | 0.0 | 0.0 |
| Case1021 | nnunet_anchor | scar | 0.5699192044748291 | 7.972077529615252 | 0.0 |
| Case1021 | nnunet_anchor | edema_zone | 0.5699192044748291 | 7.972077529615252 | 0.0 |
| Case1021 | nnunet_anchor | pure_edema |  | 0.0 | 0.0 |
| Case1021 | raw_direct_identity | scar | 0.523430028689831 | 9.57040011882782 | 0.5996602491506229 |
| Case1021 | raw_direct_identity | edema_zone | 0.523430028689831 | 9.57040011882782 | 0.5996602491506229 |
| Case1021 | raw_direct_identity | pure_edema |  | 0.0 | 0.0 |


\newpage

# 附录 E6：历史 prediction binding 分块

| model_id | artifact_type | path | binding_status |
| --- | --- | --- | --- |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |


\newpage

# 附录 E6：历史 prediction binding 分块（续 2）

| model_id | artifact_type | path | binding_status |
| --- | --- | --- | --- |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |


\newpage

# 附录 E6：历史 prediction binding 分块（续 3）

| model_id | artifact_type | path | binding_status |
| --- | --- | --- | --- |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |


\newpage

# 附录 E6：历史 prediction binding 分块（续 4）

| model_id | artifact_type | path | binding_status |
| --- | --- | --- | --- |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |


\newpage

# 附录 E6：历史 prediction binding 分块（续 5）

| model_id | artifact_type | path | binding_status |
| --- | --- | --- | --- |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |


\newpage

# 附录 E6：历史 prediction binding 分块（续 6）

| model_id | artifact_type | path | binding_status |
| --- | --- | --- | --- |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_bounded_srr_correction/predictions/Ca... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1002... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1007... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1009... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1010... | BOUND |


\newpage

# 附录 E6：历史 prediction binding 分块（续 7）

| model_id | artifact_type | path | binding_status |
| --- | --- | --- | --- |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1021... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1023... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1029... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1033... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1040... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1042... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1045... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1047... | BOUND |


\newpage

# 附录 E6：历史 prediction binding 分块（续 8）

| model_id | artifact_type | path | binding_status |
| --- | --- | --- | --- |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1053... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1062... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1070... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1073... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case1080... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case2002... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case2007... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case2008... | BOUND |


\newpage

# 附录 E6：历史 prediction binding 分块（续 9）

| model_id | artifact_type | path | binding_status |
| --- | --- | --- | --- |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case2017... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case2020... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case2031... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case2033... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case3004... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case3011... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case3012... | BOUND |
| BATCH0_3_SRR_V2_ANCHOR_CONTROL | prediction | results/srr_production/inference/anchor_identity_control/predictions/Case3023... | BOUND |


\newpage

# 附录 E7：组件生存清单分块

| source_model | component | casewise_signal | failure_mode | future_status |
| --- | --- | --- | --- | --- |
| Batch7 | availability-aware evidence | some | implementation complexity | RETAIN_AS_DATA_OR_SUPERVISION_RULE |
| Batch7 | pathology-specific retrieval | weak | not deployable | RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST |
| Batch7 | negative-space | unproven | not independently validated | RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST |
| Batch7 | complex router/SIP | harmful | scar degradation | DO_NOT_REUSE_CURRENT_IMPLEMENTATION |
| MMRD | reliable-label supervision | supportive | not model-gain alone | RETAIN_AS_DATA_OR_SUPERVISION_RULE |
| MMRD | no-T2 edema hygiene | supportive | not model-gain alone | RETAIN_AS_DATA_OR_SUPERVISION_RULE |
| MMRD | simple residual pathology head | weak | underpowered head | DO_NOT_REUSE_CURRENT_IMPLEMENTATION |
| Cascade | strong baseline fallback | protective | gain near zero | RETAIN_WITH_STRONG_EVIDENCE |


\newpage

# 附录 E7：组件生存清单分块（续 2）

| source_model | component | casewise_signal | failure_mode | future_status |
| --- | --- | --- | --- | --- |
| Cascade | bounded correction | small | ceiling too low | RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST |
| Cascade | prototype input | unresolved | control shared inputs | UNRESOLVED |
| ARC | direct reconstruction | mixed | decoder/final-mask mismatch | RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST |
| ARC | decoder reset | harmful | random decoder loses strong baseline | DO_NOT_REUSE_CURRENT_IDEA |
| DG/DR/DPR | pathology-specific arbitration | unresolved | stopped/partial gates | RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST |
| PRISM | private pyramids/routing | weak | decoder/training schedule loss | DO_NOT_REUSE_CURRENT_IMPLEMENTATION |
| PRISM | stage schedule | declines late | selected checkpoint not best for V2 edema-zone | RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST |


\newpage

# 附录 E：代码、配置、split 和预测 hash

当前 hash manifest 是启动级定位清单。大型 checkpoint 和 prediction 在 V2 中保留 path/size 绑定；关键 source 和小文件保留 SHA。缺 exact replay 条件的模型在对应 binding 表中标注。

| path | hash_status | size_bytes |
| --- | --- | --- |
| results/20260729_care_prism_fold0_fold1_v2/finalizer_state.json | FULL | 1260 |
| results/20260729_care_prism_v2_backbone_repair_and_resume/checkpoint_resume_r... | FULL | 594 |
| results/20260729_care_prism_v2_backbone_repair_and_resume/controller_context.... | FULL | 2190 |
| results/20260729_care_prism_v2_backbone_repair_and_resume/w3_training_summary... | FULL | 2759 |
| results/20260729_care_prism_fold0_fold1_v2/controller_context.json | PREFIX_8192_BYTES | 8289 |
| results/20260729_care_prism_fold0_fold1_v2/controller_bootstrap_snapshot.md | FULL | 894 |
| results/20260729_care_prism_fold0_fold1_v2/architecture_delta_final.md | FULL | 4306 |
| results/20260729_care_prism_fold0_fold1_v2/known_bad_report.json | FULL | 443 |
| results/20260729_care_prism_fold0_fold1_v2/unit_test_report.json | FULL | 327 |
| results/20260729_care_prism_fold0_fold1_v2/controller_report.md | FULL | 1976 |
| results/20260729_care_prism_fold0_fold1_v2/mapper_report_final.md | PREFIX_8192_BYTES | 9056 |
| results/20260729_care_prism_fold0_fold1_v2/adoption_receipt.json | FULL | 1524 |


\newpage

# 附录 F：证据缺口

V2 的缺口不再是 REQUIRED GPU 未运行，而是后续科学设计前的边界：不能把 oracle 写成可部署性能，不能把 full-data MoSAIC 写成 clean 架构优势，不能复制历史失败实现。


\newpage

# 附录 G：PDF 渲染验收记录

最终 PDF 采用 `pandoc_xelatex_named_fonts`，不是 Chromium fallback。验收重点是 `pdfinfo` 不含 HeadlessChrome/Skia，`pdffonts` 出现 TeXGyreTermes 与 `/users` render bundle 的 NotoSerifSC/NotoSansSC，`pdftotext -layout` 中文可抽取，第 1、3、10、19 页 PNG 中中文和表格可见。
