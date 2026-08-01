# nnU-Net / MoSAIC complementarity interpretation

这次证据闭合后的结论很直接：nnU-Net 仍是更稳的主线；MoSAIC clean OOF 在少数病例上能补一口，但补得不够多，也不够可靠，不能据此做病例级 selector、调阈值或恢复候选模型。

## Frozen Evidence Boundary

- 220 例 scar 使用 nnU-Net OOF 与 MoSAIC clean OOF 的同病例 Dice/component 证据。
- 80 例 pure edema 只使用 T2-present reliable-label 病例；no-T2 病例没有进入 pure-edema 分母。
- M10 只作为 80 例 full-data train-on-case 机制诊断，不作为泛化证据。
- 15 例 validation 只报告 fresh no-GT disagreement，不写帮助、伤害、优劣或性能结论。

## Oracle Bounds

| pathology | population | case_count | nnunet_mean_dice | mosaic_mean_dice | case_oracle_mean_dice | oracle_gain_over_nnunet | oracle_gain_over_mosaic | mosaic_rescues_count | mosaic_rescues_fraction | mosaic_rescues_mean_delta | selector_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pure_edema | all_cases | 80 | 0.430812 | 0.0527561 | 0.433105 | 0.00229265 | 0.380349 | 0 | 0 | 0 | CASE_ORACLE_UPPER_BOUND_ONLY_NOT_DEPLOYABLE |
| pure_edema | gt_positive_cases | 80 | 0.430812 | 0.0527561 | 0.433105 | 0.00229265 | 0.380349 | 0 | 0 | 0 | CASE_ORACLE_UPPER_BOUND_ONLY_NOT_DEPLOYABLE |
| scar | all_cases | 220 | 0.561047 | 0.378168 | 0.583001 | 0.0219541 | 0.204833 | 18 | 0.0818182 | 0.145685 | CASE_ORACLE_UPPER_BOUND_ONLY_NOT_DEPLOYABLE |
| scar | gt_positive_cases | 212 | 0.577502 | 0.392438 | 0.600284 | 0.0227825 | 0.207846 | 18 | 0.0849057 | 0.145685 | CASE_ORACLE_UPPER_BOUND_ONLY_NOT_DEPLOYABLE |

## Decision

- terminal_decision: `LIMITED_COMPLEMENTARITY_FOR_DIAGNOSTIC_REVIEW_ONLY`
- decision_reasons: `[]`

## Required Questions

1. MoSAIC 是否真能补 nnU-Net？只能说“少数病例局部能补”，不能说整体能替代或稳定补强。判断依据是 clean OOF 的 `MOSAIC_RESCUES` 桶和 case-oracle 上界。
2. nnU-Net 是否保护了大量病例？是。`NNUNET_PROTECTS` 桶直接记录了 nnU-Net Dice 至少高 0.05 的病例，这些病例不能被 MoSAIC 覆盖掉。
3. M10 为什么不能作为泛化主证据？M10 是 full-data/downloaded-weight 诊断，标记为 `trained_on_case_possible=true`，只能解释机制，不能证明 held-out 泛化。
4. validation 15 例能说明什么？只能说明 fresh 数据上两个预测彼此差异很大或很小；没有 GT，所以不能说谁更好。
5. 后续是否可以做病例级 selector？这轮证据不授权。case-oracle 只是上界，不是可部署 selector。
6. 现在给组会该怎么讲？讲成“nnU-Net 是底线，MoSAIC 提供少数可研究互补信号，但目前没有足够公平证据支持组合上线”。

## Validation Disagreement Buckets

| bucket | case_count |
| --- | --- |
| MOSAIC_ADDS_EDEMA | 13 |
| MIXED_NO_GT_DISAGREEMENT | 2 |
