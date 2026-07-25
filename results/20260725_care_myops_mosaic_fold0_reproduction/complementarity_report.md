# MoSAIC fold0 / nnU-Net 病例互补性

本报告只解释同一 fold0 验证集上的病例级互补性：如果某个病例某个病种由 MoSAIC 得分更高，oracle 会选择 MoSAIC；否则选择 nnU-Net。这不是新混合模型训练，也不是提交策略。

## Oracle Wins

- pure_edema::mosaic_fold0_random_init: 1
- pure_edema::nnunet_fold0: 15
- scar::mosaic_fold0_random_init: 9
- scar::nnunet_fold0: 35

## Help/Harm Counts

- pure_edema::harm: 15
- pure_edema::help: 1
- pure_edema::not_applicable_empty_gt: 28
- scar::harm: 33
- scar::help: 9
- scar::tie: 2

disagreement_row_count: 88

## Files

- Pairwise rows: `results/20260725_care_myops_mosaic_fold0_reproduction/pairwise_help_harm.csv`
- Canonical summary: `results/20260725_care_myops_mosaic_fold0_reproduction/canonical_model_summary.csv`
