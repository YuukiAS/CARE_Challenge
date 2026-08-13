# CARE-ASE 三模型 outer diagnostic 对照

结论：按 held-out outer diagnostic 口径，当前 faithful CARE-ASE 仍然没有超过 nnU-Net。和之前那版错误/弱化 CARE-ASE 相比，当前 faithful 版本的 edema 明显更高；scar 只略高于旧错误实现 step6000 final 点，但低于旧错误实现早期 best-scar 点。下面的主表把 split/checkpoint 写清楚，避免把不同 fold 当成完全同一面板比较。

## 主表

| 模型/基线 | 口径 | Folds / checkpoint | Scar Dice | Pure edema Dice | Matched nnU-Net scar | Matched nnU-Net edema | Scar delta vs matched nnU-Net | Edema delta vs matched nnU-Net |
|---|---|---|---:|---:|---:|---:|---:|---:|
| nnU-Net matched baseline | current formal outer | fold2+fold3, matched to current checkpoints | 0.556272 | 0.475196 | NA | NA | NA | NA |
| CARE-ASE faithful current | user-authorized outer diagnostic, old ASE logic | fold2 step5000 + fold3 step4000 | 0.450878 | 0.450331 | 0.556272 | 0.475196 | -0.105394 | -0.024865 |
| CARE-ASE previous erroneous/weak implementation | user-authorized outer diagnostic, old ASE logic | fold1+fold4 step6000 final | 0.441313 | 0.400175 | 0.567296 | 0.403762 | -0.125983 | -0.003587 |

## 旧错误实现的 best-checkpoint 参考

旧错误实现不是每个 step 都更差。按旧 outer diagnostic 记录：

| 旧错误实现参考点 | Folds / checkpoint | CARE-ASE scar | Matched nnU-Net scar | Scar delta | CARE-ASE edema | Matched nnU-Net edema | Edema delta |
|---|---|---:|---:|---:|---:|---:|---:|
| best scar point | fold1+fold4 step1000 | 0.547311 | 0.567306 | -0.019995 | 0.393025 | 0.403811 | -0.010786 |
| best edema point | fold1+fold4 step3000 | 0.517100 | 0.567277 | -0.050177 | 0.414737 | 0.403807 | 0.010930 |
| final stop point | fold1+fold4 step6000 | 0.441313 | 0.567296 | -0.125983 | 0.400175 | 0.403762 | -0.003587 |

## 可比性边界

- 当前 faithful 结果来自 fold2+fold3；旧错误实现结果来自 fold1+fold4。它们都使用 outer held-out diagnostic 和同类 decode/inference 设置，但不是同一 fold 面板。
- 因为 split 不同，不能把旧错误实现和当前 faithful 的绝对 Dice 当作严格同病例 A/B test。更稳妥的读法是：分别看它们相对各自 matched nnU-Net 的差值。
- 当前 faithful 版本在当前 fold2+fold3 上仍低于 matched nnU-Net：scar 低 0.105394，pure edema 低 0.024865。
- 之前那些 inner/same-exposure 接近 0.9 的表仍然只能作为 diagnostic-only，不能作为这里的 fair comparison。

## 证据路径

- Current faithful combined summary: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_latest_combined_summary.json`
- Current faithful report: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/REPORT_FOR_GPT.md`
- Old erroneous final step6000 summary: `results/20260804_care_ase_r2_deadline_recovery_training_docker/outer_diagnostic_step06000_combined_summary.json`
- Old erroneous step1000 summary: `results/20260804_care_ase_r2_deadline_recovery_training_docker/outer_diagnostic_step01000_combined_summary.json`
- Old erroneous step3000 summary: `results/20260804_care_ase_r2_deadline_recovery_training_docker/outer_diagnostic_step03000_combined_summary.json`
