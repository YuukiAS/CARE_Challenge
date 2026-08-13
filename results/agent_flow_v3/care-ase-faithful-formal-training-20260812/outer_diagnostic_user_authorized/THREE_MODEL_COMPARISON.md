# CARE-ASE 三模型 outer diagnostic 对照

结论需要分两层读：all-scar headline 下当前 faithful CARE-ASE 仍低于 matched nnU-Net，但这个 headline 混合了 complete tri-modal 和 partial-modality 病例，不能单独解释为目标域 scar 失败。重新分层后，当前 faithful CARE-ASE 在 complete tri-modal scar 上已经接近并轻微超过 matched nnU-Net；partial-modality scar 明显退化，pure edema 仍有真实负差，尤其 fold3。

这张三模型表仍然保留旧错误实现的 outer diagnostic 参考，但它不是同病例 A/B test：当前 faithful 是 fold2+fold3，旧错误实现是 fold1+fold4。更稳妥的比较方式是看各自相对 matched nnU-Net 的差值和失败形态。

## Current Faithful vs Matched nnU-Net

| 指标/人群 | Folds / checkpoint | Cases | CARE-ASE Dice | Matched nnU-Net Dice | Delta |
|---|---|---:|---:|---:|---:|
| all outer scar | fold2 step5000 + fold3 step4000 | 88 | 0.450878 | 0.556272 | -0.105394 |
| complete tri-modal scar | fold2 step5000 + fold3 step4000 | 32 | 0.679285 | 0.672510 | 0.006775 |
| partial-modality scar | fold2 step5000 + fold3 step4000 | 56 | 0.320360 | 0.489851 | -0.169491 |
| pure edema on T2-present | fold2 step5000 + fold3 step4000 | 32 | 0.450331 | 0.475196 | -0.024865 |

## Three-Model Headline Table

| 模型/基线 | 口径 | Folds / checkpoint | all scar Dice | complete scar Dice | partial scar Dice | pure edema Dice | matched nnU-Net all scar | matched nnU-Net edema | all scar delta | edema delta |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| nnU-Net matched baseline | current formal outer | fold2+fold3, matched to current checkpoints | 0.556272 | 0.672510 | 0.489851 | 0.475196 | NA | NA | NA | NA |
| CARE-ASE faithful current | user-authorized outer diagnostic, old ASE logic | fold2 step5000 + fold3 step4000 | 0.450878 | 0.679285 | 0.320360 | 0.450331 | 0.556272 | 0.475196 | -0.105394 | -0.024865 |
| CARE-ASE previous erroneous/weak implementation | user-authorized outer diagnostic, old ASE logic | fold1+fold4 step6000 final | 0.441313 | NA | NA | 0.400175 | 0.567296 | 0.403762 | -0.125983 | -0.003587 |

## 旧错误实现的 best-checkpoint 参考

旧错误实现不是每个 step 都更差。按旧 outer diagnostic 记录：

| 旧错误实现参考点 | Folds / checkpoint | CARE-ASE scar | Matched nnU-Net scar | Scar delta | CARE-ASE edema | Matched nnU-Net edema | Edema delta |
|---|---|---:|---:|---:|---:|---:|---:|
| best scar point | fold1+fold4 step1000 | 0.547311 | 0.567306 | -0.019995 | 0.393025 | 0.403811 | -0.010786 |
| best edema point | fold1+fold4 step3000 | 0.517100 | 0.567277 | -0.050177 | 0.414737 | 0.403807 | 0.010930 |
| final stop point | fold1+fold4 step6000 | 0.441313 | 0.567296 | -0.125983 | 0.400175 | 0.403762 | -0.003587 |

## 可比性边界

- 当前 faithful 结果来自 fold2+fold3；旧错误实现结果来自 fold1+fold4。两者都使用 user-authorized outer diagnostic，但不是同一病例面板。
- 旧错误实现的 historical summaries 没有当前新建的 complete/partial subgroup breakdown，因此三模型表不能给它补填 subgroup Dice。
- 当前 faithful 的 all-scar delta 为 -0.105394，但 complete tri-modal scar delta 为 +0.006775；不能把 mixed all-scar headline 直接写成目标域 complete tri-modal scar 失败。
- 当前 faithful 的 partial-modality scar delta 为 -0.169491，是 all-scar headline 被拉低的主要来源。
- pure edema combined delta 为 -0.024865，不能因为 scar 被分层解释后就声称模型整体已经胜过 nnU-Net。
- inner/same-exposure 接近 0.9 的旧表仍然只能作为 diagnostic-only，不是 fair held-out comparison。

## 证据路径

- Current faithful subgroup summary: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_subgroup_summary.json`
- Current faithful subgroup report: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/OUTER_DIAGNOSTIC_SUBGROUP_REPORT.md`
- Current faithful combined summary: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_latest_combined_summary.json`
- Current faithful report: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/REPORT_FOR_GPT.md`
- Old erroneous final step6000 summary: `results/20260804_care_ase_r2_deadline_recovery_training_docker/outer_diagnostic_step06000_combined_summary.json`
- Old erroneous step1000 summary: `results/20260804_care_ase_r2_deadline_recovery_training_docker/outer_diagnostic_step01000_combined_summary.json`
- Old erroneous step3000 summary: `results/20260804_care_ase_r2_deadline_recovery_training_docker/outer_diagnostic_step03000_combined_summary.json`
