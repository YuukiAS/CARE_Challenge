# V2 Controller Report

V1 不足以进入 Deep Research，因为它仍混有 Chromium PDF、占位状态、未绑定旧模型、未完成 GPU 诊断和视觉 pending。V2 已把 G1-G10 变成终态证据：能跑的诊断给出真实指标，缺 exact checkpoint/prediction/activation 的项目给出 `BLOCKED_BY_MISSING_BOUND_ASSET`，不再把缺失资产写成科学负结果。

Batch0-7 的真实结论是：availability-aware evidence、病理特异候选和安全 fallback 有保留价值，但复杂 router/SIP 当前实现不能复用。MMRD 可保留 reliable-label、no-T2 edema hygiene 和 modality dropout 作为数据/监督规则，不能复用简单 residual head。Cascade 可保留强基线 fallback、bounded correction 和 help/harm gate，但 prototype input 的历史 control 语义不干净。ARC 可保留 direct reconstruction 和 train/deploy parity 纪律，但不能复用 decoder reset/未进入 final mask 的分支。

PRISM 的主要失败根因是只继承 encoder 不足以恢复 nnU-Net：D1 decoder reset 大幅损伤 pure edema 和 scar，D3 完整短 finetune 才接近恢复。MoSAIC hosted 优势主要不能由 clean architecture 解释；本地证据更支持 full-data、checkpoint 组合、recipe/TTA/threshold/postprocess 和目标域因素。nnU-Net/MoSAIC 存在 scar 互补，但 case-level oracle 只给 modest gain；pure edema 的 clean 互补很弱。Cine temporal 和 alignment 当前都不是主要可用增益来源。

约 0.1 Dice 级别现实上限没有被 clean case-level evidence 直接证明：voxel oracle 很乐观但不可部署，selector 只在 scar 上有信号。V2 已足够进入外部 Deep Research，但后续必须把大增益当作假设验证，不能把 oracle/full-data probe 当成承诺。

controller_verification_decision: VERIFIED_COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: ADEQUATE_FOR_DEEP_RESEARCH_EVIDENCE_PACKET_NOT_FOR_MODEL_CLAIM
required_gpu_tasks_complete: true
historical_evidence_complete: true
mosaic_evidence_complete: true
standardized_metrics_complete: true
case_montages_complete: true
oracle_complete: true
feature_probe_complete: true_with_missing_asset_boundaries
decoder_reset_complete: true
alignment_complete: true
cine_complete: true
component_survival_complete: true
large_gain_feasibility_complete: true
pdf_complete: true
pdf_searchable: true
pdf_visual_validation_complete: true
validators_passed: true
all_jobs_terminal: true
aggregation_complete: true
git_commit_decision: local_commit_required
git_push_decision: forbidden_by_contract_not_attempted
next_required_action: external Deep Research design using V2 constraints
