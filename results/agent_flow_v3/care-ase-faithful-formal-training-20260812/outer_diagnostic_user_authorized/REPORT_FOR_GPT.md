# CARE-ASE 当前 outer diagnostic 结果解释修正

当前 `scar -0.105394` headline 本身来自原始 casewise CSV 的均值，但它不能作为唯一科学解释，因为它把 complete tri-modal 目标域病例和 no-T2 partial-modality 病例混在一起。重新从 fold2 step5000 与 fold3 step4000 的 outer casewise CSV 分层计算后，complete tri-modal scar 已经接近并轻微超过 matched nnU-Net；真正把 mixed scar headline 拉低的是 partial-modality scar。

这不等于 CARE-ASE 已经整体超过 nnU-Net。pure edema 的评价分母本来就是 T2-present 病例，combined delta 仍为负，尤其 fold3 暴露了真实的 edema 欠激活或校准问题。当前证据支持继续 frozen 14000-step formal training，同时修正 diagnostic reporting；没有发现足以停止训练的实现性阻断。

## 运行口径

| 项目 | 内容 |
|---|---|
| comparison contract | `USER_AUTHORIZED_OUTER_DIAGNOSTIC_OLD_ASE_LOGIC` |
| outer 授权 | 用户在 2026-08-13 当前对话中明确授权 |
| CARE fold/checkpoint | fold2 step5000；fold3 step4000 |
| baseline | same-fold stock nnU-Net `checkpoint_final.pth` |
| 病例数 | 88 个 outer scar cases；其中 T2-present edema 计分病例 32 个 |
| 推理设置 | patch `20,256,256`；tile step `0.5`；Gaussian；mirroring；fp32 |
| 执行 job | A100 `63501304`，`COMPLETED 0:0`，耗时 `00:10:31` |

## 主分层结果

| 指标/人群 | Split | Cases | CARE-ASE Dice | nnU-Net Dice | CARE-ASE - nnU-Net |
|---|---:|---:|---:|---:|---:|
| all outer scar | fold2 | 44 | 0.529509 | 0.590782 | -0.061272 |
| all outer scar | fold3 | 44 | 0.372246 | 0.521763 | -0.149516 |
| all outer scar | combined | 88 | 0.450878 | 0.556272 | -0.105394 |
| complete tri-modal scar | fold2 | 16 | 0.704129 | 0.697969 | 0.006160 |
| complete tri-modal scar | fold3 | 16 | 0.654441 | 0.647050 | 0.007391 |
| complete tri-modal scar | combined | 32 | 0.679285 | 0.672510 | 0.006775 |
| partial-modality scar | fold2 | 28 | 0.429727 | 0.529531 | -0.099805 |
| partial-modality scar | fold3 | 28 | 0.210992 | 0.450170 | -0.239177 |
| partial-modality scar | combined | 56 | 0.320360 | 0.489851 | -0.169491 |
| pure edema on T2-present | fold2 | 16 | 0.507419 | 0.506598 | 0.000822 |
| pure edema on T2-present | fold3 | 16 | 0.393242 | 0.443793 | -0.050551 |
| pure edema on T2-present | combined | 32 | 0.450331 | 0.475196 | -0.024865 |

## Center Complete Tri-Modal Breakdown

| 指标/人群 | Split | Cases | CARE-ASE Dice | nnU-Net Dice | CARE-ASE - nnU-Net |
|---|---:|---:|---:|---:|---:|
| CenterB complete scar | fold2 | 7 | 0.719907 | 0.702761 | 0.017146 |
| CenterB complete scar | fold3 | 7 | 0.617510 | 0.715274 | -0.097764 |
| CenterB complete scar | combined | 14 | 0.668708 | 0.709017 | -0.040309 |
| CenterB complete edema | fold2 | 7 | 0.608713 | 0.617819 | -0.009105 |
| CenterB complete edema | fold3 | 7 | 0.438806 | 0.524348 | -0.085542 |
| CenterB complete edema | combined | 14 | 0.523760 | 0.571083 | -0.047324 |
| CenterC complete scar | fold2 | 9 | 0.691857 | 0.694243 | -0.002385 |
| CenterC complete scar | fold3 | 9 | 0.683165 | 0.593987 | 0.089178 |
| CenterC complete scar | combined | 18 | 0.687511 | 0.644115 | 0.043396 |
| CenterC complete edema | fold2 | 9 | 0.428635 | 0.420093 | 0.008543 |
| CenterC complete edema | fold3 | 9 | 0.357803 | 0.381140 | -0.023336 |
| CenterC complete edema | combined | 18 | 0.393219 | 0.400616 | -0.007397 |

## Help/Harm 和形状诊断

| 指标/人群 | Split | Help | Harm | Tie | CARE sens | nnU-Net sens | CARE prec | nnU-Net prec | CARE HD95 | nnU-Net HD95 | CARE vol ratio | nnU-Net vol ratio | CARE empty pred | nnU-Net empty pred |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| complete tri-modal scar | fold2 | 11 | 5 | 0 | 0.737107 | 0.750335 | 0.705321 | 0.687565 | 29.271 | 31.193 | 1.176592 | 1.293962 | 0 | 0 |
| complete tri-modal scar | fold3 | 8 | 8 | 0 | 0.663391 | 0.757766 | 0.738881 | 0.665278 | 62508.375 | 62511.311 | 1.177537 | 1.429508 | 2 | 0 |
| complete tri-modal scar | combined | 19 | 13 | 0 | 0.701438 | 0.753930 | 0.720983 | 0.676421 | 31268.823 | 31271.252 | 1.177049 | 1.359549 | 2 | 0 |
| partial-modality scar | fold2 | 5 | 20 | 3 | 0.381458 | 0.574013 | 0.642905 | 0.540004 | 71451.329 | 71444.858 | 0.712842 | 1.198026 | 1 | 1 |
| partial-modality scar | fold3 | 2 | 24 | 2 | 0.154877 | 0.422540 | 0.713931 | 0.566834 | 285736.829 | 35738.950 | 0.224688 | 0.743806 | 8 | 1 |
| partial-modality scar | combined | 7 | 44 | 5 | 0.261755 | 0.493989 | 0.673129 | 0.553419 | 178594.079 | 53591.904 | 0.454950 | 0.958061 | 9 | 2 |
| pure edema on T2-present | fold2 | 6 | 10 | 0 | 0.482059 | 0.489780 | 0.634697 | 0.636976 | 25.208 | 24.374 | 0.815729 | 0.851508 | 0 | 0 |
| pure edema on T2-present | fold3 | 6 | 10 | 0 | 0.342850 | 0.401968 | 0.634391 | 0.591657 | 62528.738 | 26.047 | 0.585583 | 0.736394 | 1 | 0 |
| pure edema on T2-present | combined | 12 | 20 | 0 | 0.412455 | 0.445874 | 0.634549 | 0.614317 | 31276.973 | 25.211 | 0.700656 | 0.793951 | 1 | 0 |

## 诊断边界

- `Case2012` 是 fold3 complete/T2-present 灾难性空预测病例，CARE scar Dice 和 edema Dice 都为 0；它只作为诊断说明，仍保留在正式均值中。
- 原始 casewise CSV 没有 prediction/GT voxel-count 字段，因此 Dice 分层仍以原始 CSV 为准；volume ratio 只从后续只读 no-T2 matched diagnostic CSV 补充，属于 diagnostic-only，不覆盖原始 outer headline，也不得用于 checkpoint selection。
- CARE no-T2 decode 使用 class set `0,1,2,3,5`，当前 nnU-Net baseline runner 原始口径使用六类 logits 直接 argmax。这是 comparison asymmetry；已完成 diagnostic no-T2 matched class-set rerun。结果显示 partial-modality scar 上 matched no-T2 class-set nnU-Net Dice 与 direct six-class nnU-Net Dice 完全相同，combined `matched_minus_direct = 0.000000`，因此该 asymmetry 不是本次 partial scar deficit 的来源。该结果仍是 diagnostic-only，不覆盖原始报告，也不得用于 checkpoint selection。
- `automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json` 是 implementation-fidelity control-plane 状态，不是 formal-training live step state；当前 formal-training live state 应看 `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/CURRENT_LIVE_MONITOR.json`。

## Provenance 判断

fold2 step5000 与 fold3 step4000 checkpoint payload 均记录：

- `training_source_commit_sha = fdd45b5ee1c1abea352c318c66951910e565262f`
- `formal_execution_checkout_commit_sha = fdd45b5ee1c1abea352c318c66951910e565262f`
- `critical_source_manifest_sha256 = implementation_source_manifest_sha256 = code_hash = 33ec5151957f652467a18787e7f068abb368ab575697ba27dcef0cfc1a8c5831`
- `split_hash = 9c3e9f3b7e4565a5c3c2589ddbb913c78c0ad423f4265370585841c93c6f880a`
- `plans_hash = 06492f8fc75b5de383a28006f76b7f1099f305422953cf9d4f89ae1ec38d3e2f`
- `frozen_contract_sha256 = a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d`

Diff audit from Planner/Critic PASS to training source commit shows formal runtime/path/cache namespace, authorization, fold selection, checkpoint cadence, and monitoring/evidence wiring changes. No model, loss, sampler scientific semantics, inference decode semantics, Stage A/B/C, or 14000-step schedule redesign was found.

`NO_NEW_FAITHFULNESS_REGRESSION_EVIDENCE`

## 证据路径

- Subgroup summary JSON: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_subgroup_summary.json`
- Subgroup table CSV: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_subgroup_table.csv`
- Subgroup report: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/OUTER_DIAGNOSTIC_SUBGROUP_REPORT.md`
- Subgroup verification receipt: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_subgroup_verification_receipt.json`
- no-T2 matched subgroup summary: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_no_t2_matched_subgroup_summary.json`
- no-T2 matched subgroup report: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_no_t2_matched_subgroup_report.md`
- Combined summary: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_latest_combined_summary.json`
- Fold2 casewise CSV: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/fold_2/step05000/outer_casewise_metrics.csv`
- Fold3 casewise CSV: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/fold_3/step04000/outer_casewise_metrics.csv`
- no-T2 matched diagnostic job status: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/no_t2_matched_diagnostic_job_status.json`
- State sync receipt: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/formal_training_state_sync_receipt.json`
- Runner: `scripts/evaluation/care_ase/run_current_user_authorized_outer_diagnostic.py`
- Subgroup summarizer: `scripts/evaluation/care_ase/summarize_outer_diagnostic_subgroups.py`
- Subgroup verifier: `scripts/evaluation/care_ase/verify_outer_diagnostic_subgroup_summary.py`
