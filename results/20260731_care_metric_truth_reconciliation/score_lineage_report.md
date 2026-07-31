# CARE metric truth and score lineage reconciliation

这次核对的核心结论是：此前被混写的不是一个分数的小数位，而是不同病例人群和不同用途的指标被放进了同一比较语境。D0 的 0.922x 是 frozen inner-select 12 例上的 nnU-Net stock checkpoint 对 GT 的 Dice；clean OOF 是 220 例/80 T2-present 的本地 held-out OOF；PRISM W3 是 fold0 outer once 44 例诊断；MoSAIC M2-M10 是 full-data train-on-case 机制 probe；hosted validation 是隐藏病例的 leaderboard 结果。它们不能直接互相替代。

## Corrected score groups

| group | allowed use | key scores |
|---|---|---|
| Clean local OOF | fair local comparison within same source/evaluator population | nnU-Net scar 0.5610470930146593, pure edema 0.43081230355478206; MoSAIC scar 0.3781679456697728, pure edema 0.05275611807880284 |
| Decoder-reset inner-select | D0-D3 mechanism diagnosis only | D0 scar 0.922379592, pure edema 0.923082832; D1-D3 in `decoder_reset_score_lineage.csv` |
| PRISM fold0 outer once | one-time fold0 diagnostic after inner selection | PRISM scar 0.419644177598268, edema-zone 0.247154384798841; same-fold nnU-Net scar 0.534091153005157, edema-zone 0.559227769916473 |
| MoSAIC full-data probe | mechanism decomposition only, not fair validation | M2-M10 rows in `metric_truth_table.csv`; train-on-case=true |
| Hosted leaderboard | external hidden validation reference only | MoSAIC scar 0.6965, edema 0.5983, CineMyoPS 0.2058 with partial hosted bind |

## D0 reconstruction

D0 uses checkpoint SHA `8bceb20cae8920e87d43b14665a0db9dfd4f1204533d25a3cd6e40ad9de74111`, historical Slurm job `61220581`, nnU-Net v2 trainer/plans validation, and the prediction manifest recorded in `/users/a/e/aereinh/CARE/results/20260730_care_failure_forensics_deep_research_packet/nnunet_decoder_reset_prediction_manifest.csv`. Its 0.922379592 scar and 0.923082832 pure edema scores come from prediction-vs-GT Dice on 12 frozen inner-select cases. They are not prediction parity, not training-case performance, not clean OOF, and not hosted validation.

## Why metric_contract_status is PASS

The reconciliation packet satisfies the task contract: all core score regimes are separated, label semantics are frozen, T2-present denominator is bound to 80, required forbidden comparisons are explicit, and the strict validator passes. Hosted MoSAIC rows are provenance-bound leaderboard references, not locally recomputable prediction rows; exact ZIP bytes remain unavailable but are recorded as a boundary rather than a blocker.

## Forbidden direct comparisons

- D0 inner-select GT Dice vs clean OOF 220-case Dice
- MoSAIC M2-M10 full-data train-on-case probe vs hosted validation
- PRISM fold0 outer once vs future fold1 or validation selection
- internal edema-zone vs official pure edema leaderboard
- D0/D1/D2/D3 inner-select diagnostics vs hosted validation leaderboard
- MoSAIC M2-M10 full-data train-on-case probe vs clean OOF held-out Dice
- hosted hidden validation rows vs local clean OOF rows as if same denominator
- official pure edema label 4 vs internal edema-zone labels 4 or 5

## Late user-supplied Deep Research draft handling

The file `/users/a/e/aereinh/CARE/CARE Myocardium 下一代模型深度研究与设计裁决.md` was added by the user after packet generation began and was read only. It is not moved by this task because the frozen write scope is limited. Its prose includes D0 0.922x in an official-validation/hosted context; this packet rejects that wording and records the occurrence as non-claim-allowed. The corrected machine truth remains: D0 0.922x is inner-select prediction-vs-GT Dice on 12 frozen cases. The draft also contains a hosted nnU-Net anchor prose claim around 0.92/0.923; this packet does not promote that prose claim and instead uses locally bound leaderboard alignment rows as hosted references.
