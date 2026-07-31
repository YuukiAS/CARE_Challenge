# Controller report

此前混在一起的数字主要是四类：12 例 inner-select 上的 D0-D3 诊断 Dice、220/80 例 clean OOF 本地公平比较、80 例 full-data train-on-case 的 MoSAIC 机制 probe、以及隐藏病例的 hosted leaderboard。D0 的 0.922379592 scar 和 0.923082832 pure edema 明确是 stock fold0 nnU-Net 在 frozen 12-case inner-select 上对 GT 的 Dice，不是 prediction parity，也不是 clean OOF 或 hosted validation。当前可公平比较的 clean 指标只有 nnU-Net vs MoSAIC clean OOF：scar 为 0.5610470930146593 vs 0.3781679456697728，pure edema 为 0.43081230355478206 vs 0.05275611807880284（T2-present denominator=80）。hosted 指标只能作为 leaderboard 参考：MoSAIC-family scar 0.6965、official edema 0.5983、CineMyoPS 0.2058，hosted rows 作为 leaderboard reference 通过；exact uploaded ZIP 未本地保存，因此不能本地重算或与 clean OOF 直接比较。以后禁止把 D0 inner-select、clean OOF、outer once、full-data probe、hosted hidden validation、official pure edema 和 internal edema-zone 互相直接比较。A0-A3 机制实验本任务不允许进入正式训练；按并行总览，Lane B formal training 需要 Lane A `metric_contract_status: PASS`，而本包已修订为 `PASS`。

controller_verification_decision: VERIFIED_COMPLETE
metric_contract_status: PASS
contract_execution_status: COMPLETED_PASS_WITH_HOSTED_REFERENCE_BOUNDARY

## Required outputs

- source_inventory.csv: complete
- score_occurrence_inventory.csv: complete
- decoder_reset_score_semantics.json: complete
- decoder_reset_score_lineage.csv: complete
- metric_truth_table.csv: complete
- metric_semantics_contract.json: complete
- metric_truth_receipt.json: complete
- score_lineage_report.md: complete
- deep_research_score_corrections.md: complete
- scripts/forensics/metric_truth/validate_metric_truth.py: complete
- tests/forensics/metric_truth/test_metric_truth_known_bad.py: complete
- controller_report.md: complete
- completion_check.md: complete
- MANIFEST.md: complete

## Validator and runtime state

Strict validator: PASS; report written to `strict_validator_report.json`.
Known-bad tests: PASS, 15/15.
Slurm: no new Slurm job submitted for this reconciliation. Historical source job `61220581` is read only.
Git: local commit required after validator; push not authorized.
Upload/training: no validation upload, no Docker upload, no new architecture training, no checkpoint selection, no threshold search, no post-processing tuning.

## Evidence boundaries

Metric truth can now be read from `metric_truth_table.csv` and `metric_semantics_contract.json`. The receipt now reports `PASS`: hosted MoSAIC rows are accepted as provenance-bound leaderboard references using the recorded leaderboard row, user attestation, MoSAIC source commit, downloaded weight hashes, and recipe binding. Exact ZIP bytes remain unavailable, so these rows are not locally recomputable and cannot be used outside the hosted-reference comparison group.

## Late user-supplied Deep Research draft handling

The file `/users/a/e/aereinh/CARE/CARE Myocardium 下一代模型深度研究与设计裁决.md` was added by the user after packet generation began and was read only. It is not moved by this task because the frozen write scope is limited. Its prose includes D0 0.922x in an official-validation/hosted context; this packet rejects that wording and records the occurrence as non-claim-allowed. The corrected machine truth remains: D0 0.922x is inner-select prediction-vs-GT Dice on 12 frozen cases. The draft also contains a hosted nnU-Net anchor prose claim around 0.92/0.923; this packet does not promote that prose claim and instead uses locally bound leaderboard alignment rows as hosted references.
