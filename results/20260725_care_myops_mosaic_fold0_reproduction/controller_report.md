MoSAIC 的 fold0 公平复现已经完成本地同口径评价：新训练的 MoSAIC fold0、nnU-Net baseline、Batch10 MMRD、Batch7 minimal 和 SCR-R1 generic cascade control 都在 exact fold0 44 个验证病例上按同一 canonical evaluator 计算；Batch10/Batch7 来自现存预测复算，SCR-R1 已从现有 SCR cache 重新导出 raw-space NIfTI 后复算。当前不上传 validation、不构建 Docker、不 push；下一步应由 Planner 根据全量病例级 help/harm 和主指标差距决定是否继续做方法修复。

## Controller Decision
controller_verification_decision: VERIFIED_COMPLETE
operational_completion_status: TERMINAL_LOCAL_AGGREGATED
experiment_adequacy_decision: FOLD0_RANDOM_INIT_PUBLIC_CONFIG_REPRODUCTION
contract_compliance_status: PASS
required_outputs_complete: true
validators_passed: true
training_jobs_terminal_accounted: true
aggregation_complete: true
git_commit_decision: LOCAL_LIGHTWEIGHT_COMMIT_REQUIRED_AFTER_FINALIZER_SACCT
git_push_decision: NOT_AUTHORIZED_NOT_PERFORMED
next_required_action: RETURN_TO_PLANNER

## Key Evidence
- canonical casewise: `results/20260725_care_myops_mosaic_fold0_reproduction/canonical_casewise_metrics.csv`
- model summary: `results/20260725_care_myops_mosaic_fold0_reproduction/canonical_model_summary.csv`
- MoSAIC/nnU-Net complementarity: `results/20260725_care_myops_mosaic_fold0_reproduction/pairwise_help_harm.csv`
- all candidates vs nnU-Net: `results/20260725_care_myops_mosaic_fold0_reproduction/all_model_pairwise_vs_nnunet.csv`
- historical/export boundary: `results/20260725_care_myops_mosaic_fold0_reproduction/historical_attempt_summary.csv`
