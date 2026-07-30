# CARE Myocardium 失败取证 Deep Research 证据包

版本：20260730 本地证据冻结版

这份 PDF 使用 `/users/a/e/aereinh/render_resources/chinese_math_pdf` 的本地 Chromium/Fandol 渲染路线生成。它不是新模型蓝图，不包含 validation upload，也不声明 hosted 指标。

## 一页执行摘要

当前最可靠的动作不是继续设计新 CARE 架构，而是先把评价语义、checkpoint/recipe 绑定、病例级统一重聚合、PRISM decoder-reset 对照、MoSAIC recipe decomposition 和 Cine temporal probe 做成可复现证据。已确认的硬边界是 pure edema 与 edema-zone 不能混写，full-data MoSAIC 不能冒充 clean fold0，pending 或未跑完的 GPU 诊断不能写成科学完成。

![证据等级计数](/users/a/e/aereinh/CARE/results/20260730_care_failure_forensics_deep_research_packet/figures/evidence_grade_counts.png)

## 1. 为什么现在必须做失败取证

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 2. CARE 数据、中心、模态和标签真值

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

![中心病例数](/users/a/e/aereinh/CARE/results/20260730_care_failure_forensics_deep_research_packet/figures/center_case_counts.png)

![病灶体积分布](/users/a/e/aereinh/CARE/results/20260730_care_failure_forensics_deep_research_packet/figures/pathology_volume_distribution.png)

| cases | scar_positive | pure_edema_positive | t2_present |
| --- | --- | --- | --- |
| 220 | 212 | 80 | 220 |

## 3. 官方与内部指标语义

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

| object | internal_labels | official_export | allowed_claim_scope |
| --- | --- | --- | --- |
| scar | 5 | scar | official |
| pure_edema | 4 | edema | T2-present official edema |
| edema_zone | 4|5 | none | internal only |

## 4. 当前评价代码中的已确认问题

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 5. nnU-Net 强基线到底强在哪里

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

| model_id | result_evidence_grade | current_scientific_conclusion |
| --- | --- | --- |
| NNUNET | A_VERIFIED_FAIR_FINAL_MASK | 强基线；需继续绑定五折和同口径病例级指标。 |
| SRR_V2 | E_STALE_OR_INCONSISTENT | 历史证据需绑定代码、checkpoint、split 和预测。 |
| SRR_V25 | E_STALE_OR_INCONSISTENT | 历史证据需绑定代码、checkpoint、split 和预测。 |
| SRR_V3 | E_STALE_OR_INCONSISTENT | 历史证据需绑定代码、checkpoint、split 和预测。 |
| BATCH0 | E_STALE_OR_INCONSISTENT | 历史证据需绑定代码、checkpoint、split 和预测。 |
| BATCH1 | E_STALE_OR_INCONSISTENT | 历史证据需绑定代码、checkpoint、split 和预测。 |
| BATCH2 | E_STALE_OR_INCONSISTENT | 历史证据需绑定代码、checkpoint、split 和预测。 |
| BATCH3 | E_STALE_OR_INCONSISTENT | 历史证据需绑定代码、checkpoint、split 和预测。 |

## 6. SRR v2-v3 的设计意图与落地差距

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 7. Batch 0-7 历史证据

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 8. MMRD 的设计、实现和失败

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 9. Cascade/DG 的设计、实现和失败

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 10. ARC 的设计、实现和失败

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 11. PRISM W1-W3 的完整复盘

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

PRISM 不能只看是否有强 encoder。D0-D3 未完成前，不能判断低分主要来自 representation、decoder reset 还是训练协议。

| diagnostic | status |
| --- | --- |
| D0_FULL_PRETRAINED_IDENTITY | NOT_RUN |

## 12. MoSAIC clean、full-data 和 hosted recipe

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

MoSAIC 必须拆成 clean fold0、full-data diagnostic 和 hosted-near recipe 三层。full-data 权重不能作为 clean architecture 比较。

| status |
| --- |
| NOT_RUN |

## 13. 所有模型统一病例级比较

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 14. 困难子组

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 15. case-wise help/harm

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 16. 失败病例视觉图册

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

病例 montage 的选择依赖 standardized casewise metrics。本包目前只生成 QA contact sheet，明确标注 `VISUAL_HUMAN_CONFIRMATION_PENDING`。

## 17. 错误重合和模型互补上限

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 18. selector feasibility

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 19. 冻结特征可分性 probe

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 20. decoder-reset 诊断对照

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 21. 多序列错位是否为主因

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 22. scar 的真实瓶颈

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 23. pure edema 的真实瓶颈

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 24. Cine 的真实瓶颈

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 25. 为什么过去多次充分设计仍然失败

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。

## 26. 根因排序与证据图

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

![决策状态](/users/a/e/aereinh/CARE/results/20260730_care_failure_forensics_deep_research_packet/figures/decision_state.png)

| root_cause | severity | confidence | confirmed | evidence |
| --- | --- | --- | --- | --- |
| METRIC_IMPLEMENTATION | HIGH | MODERATE | True | remote FP 和 pure-edema/edema-zone 语义已有 known-bad 保护；全量影响未重算。 |
| CHECKPOINT_OR_RECIPE | HIGH | MODERATE | True | MoSAIC clean/full-data/hosted recipe 未绑定完成，存在本地证据反转风险。 |
| DECODER_CAPABILITY_LOSS | MODERATE | LOW | False | PRISM decoder-reset 假说合理但 D0-D3 未运行。 |
| COMPONENT_NOT_WIRED | MODERATE | LOW | False | 多个路线需 forward/on-off 才能确认模块是否进入 final logits。 |
| INSUFFICIENT_PATHOLOGY_SIGNAL | MODERATE | UNRESOLVED | False | feature probe 未运行。 |
| MULTIMODAL_MISALIGNMENT | MODERATE | UNRESOLVED | False | alignment correlation 未运行。 |
| CINE_TASK_DEFINITION | MODERATE | UNRESOLVED | False | Cine P0/P1 未运行。 |

## 27. 当前能下的结论

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

# Local Evidence Conclusions

当前本地证据支持 A 和 I：先做评价/数据/recipe 绑定修复，并承认关键证据仍缺失。尚不能支持新的 CARE 架构蓝图。


## 28. 当前不能下的结论

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

当前不能下的结论：不能声称任何新架构已被支持；不能声称 MoSAIC clean 天然强于 nnU-Net；不能声称 alignment 或 Cine temporal 是主因。

## 29. 外部 Deep Research 必须回答的问题

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

- [DR-001] Small-lesion scar segmentation beyond nnU-Net requires which evidence standard?
- [DR-002] Can clean MoSAIC recipe gains be separated from full-data target-domain advantage?
- [DR-003] Do frozen encoder features contain patient-held-out scar FN/FP separability?
- [DR-004] When does cine temporal information improve pathology segmentation over ED-only?


## 30. 下一轮决策树

本章回答一个取证问题：现有本地证据能否支持对应科学判断。它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。

# Research Decision Tree

1. 先完成 evaluation/data repair。
2. 若 D0 不能复现 nnU-Net，停止 decoder-reset。
3. 若 selector nested CV 不超过 always-best-single-model，停止 deployable selector。
4. 若 feature probe control 不成立，停止 retrieval/prototype 叙事。


## 附录 A：模型和 checkpoint provenance

| model_id | path | size_bytes | hash_status | evidence_quality |
| --- | --- | --- | --- | --- |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset502_CARECineMyoPS/nnUNetTrainer__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth | 354608437 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset502_CARECineMyoPS/nnUNetTrainer__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth | 354266799 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset502_CARECineMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_4/checkpoint_final.pth | 354383029 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset502_CARECineMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_4/checkpoint_best.pth | 354382767 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset502_CARECineMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth | 354382965 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset502_CARECineMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth | 354201839 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset502_CARECineMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_2/checkpoint_final.pth | 354383093 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset502_CARECineMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_2/checkpoint_best.pth | 354242031 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset502_CARECineMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_1/checkpoint_final.pth | 354383349 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset502_CARECineMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_1/checkpoint_best.pth | 354270127 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset502_CARECineMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_3/checkpoint_final.pth | 354382965 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/Dataset502_CARECineMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_3/checkpoint_best.pth | 354369135 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/nnUNet/2d/Task025_Cine_Seg/nnUNetTrainerV2__nnUNetPlansv2.1/fold_0/model_final_checkpoint.model.pkl | 31579 | PREFIX_8192_BYTES | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/nnUNet/2d/Task025_Cine_Seg/nnUNetTrainerV2__nnUNetPlansv2.1/fold_0/model_final_checkpoint.model | 235538772 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/nnUNet/2d/Task026_Cine_4D_smoke/CARECineMyoPSTrainer__nnUNetPlansv2.1/fold_0/model_final_checkpoint.model.pkl | 4305 | FULL | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/nnUNet/2d/Task026_Cine_4D_smoke/CARECineMyoPSTrainer__nnUNetPlansv2.1/fold_0/model_final_checkpoint.model | 1669319383 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1/mosaic_oof_checkpoint_manifest.csv | 1985 | FULL | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1/mosaic_oof/fold0/oof_checkpoint_manifest.csv | 441 | FULL | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/nnUNet/2d/Task026_Cine_4D/CARECineMyoPSTrainer__nnUNetPlansv2.1/fold_0/model_final_checkpoint.model.pkl | 68222 | PREFIX_8192_BYTES | PARTIALLY_BOUND_BY_PATH |
| NNUNET | /users/a/e/aereinh/CARE/data/nnUNet/nnUNet_results/nnUNet/2d/Task026_Cine_4D/CARECineMyoPSTrainer__nnUNetPlansv2.1/fold_0/model_final_checkpoint.model | 1669390615 | LARGE_METADATA_ONLY | PARTIALLY_BOUND_BY_PATH |

## 附录 B：指标公式和 known-bad

| claim_id | claim_text | source_path | confidence | notes |
| --- | --- | --- | --- | --- |
| E-DATA-001 | 本包读取 Dataset501 labelsTr 的病例清单并统计标签体积。 | data_case_manifest.csv | MODERATE | geometry round-trip incomplete |
| E-METRIC-001 | reference metric known-bad fixtures pass for remote FP, spacing HD95, empty cases and lesion recall. | reference_metric_known_bad_report.json | HIGH | synthetic fixtures only |
| E-MOSAIC-001 | full-data MoSAIC evidence cannot be used as clean fold0 comparison. | mosaic_ablation_contract.json | HIGH | contract boundary |
| E-PRISM-001 | PRISM decoder-reset explanation remains unresolved until D0-D3 terminal diagnostics complete. | decoder_reset_diagnostic_report.md | LOW | diagnostics not run |
| E-GAP-005 | Required diagnostic evidence item 5 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-006 | Required diagnostic evidence item 6 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-007 | Required diagnostic evidence item 7 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-008 | Required diagnostic evidence item 8 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-009 | Required diagnostic evidence item 9 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-010 | Required diagnostic evidence item 10 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-011 | Required diagnostic evidence item 11 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-012 | Required diagnostic evidence item 12 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-013 | Required diagnostic evidence item 13 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-014 | Required diagnostic evidence item 14 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-015 | Required diagnostic evidence item 15 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-016 | Required diagnostic evidence item 16 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-017 | Required diagnostic evidence item 17 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-018 | Required diagnostic evidence item 18 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-019 | Required diagnostic evidence item 19 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |
| E-GAP-020 | Required diagnostic evidence item 20 remains incomplete and is not used as a performance claim. | strict_validator_report.json | HIGH | validator will fail until completed |

## 附录 F：证据缺口

strict validator 仍然要求 D0-D3、feature probe、MoSAIC recipe decomposition、Cine temporal probe 和 standardized casewise reaggregation。该状态防止后续误读为完成。
