# CARE-ASE 当前 outer diagnostic 结果

这次结果说明：按用户在 2026-08-13 明确授权的 outer diagnostic，对当前 CARE-ASE 正式训练 checkpoint 做旧 ASE 逻辑的 held-out 比较后，当前 CARE-ASE 仍然没有超过 nnU-Net。两个 fold 汇总后，scar Dice 低 0.1054，pure edema Dice 低 0.0249。

此前同暴露或 inner in-sample 口径下接近 0.9 的表不能作为 primary fair comparison。旧 ASE thread 已经证明，这类表会受到 stock nnU-Net 同训练暴露影响，只能作为诊断趋势，不能拿来判断 held-out 泛化。

## 运行口径

| 项目 | 内容 |
|---|---|
| comparison contract | `USER_AUTHORIZED_OUTER_DIAGNOSTIC_OLD_ASE_LOGIC` |
| outer 授权 | 用户在 2026-08-13 当前对话中明确授权 |
| CARE fold/checkpoint | fold2 step5000；fold3 step4000 |
| baseline | same-fold stock nnU-Net `checkpoint_final.pth` |
| 病例数 | 88 个 outer cases；其中 T2 edema 计分病例 32 个 |
| 推理设置 | patch `20,256,256`；tile step `0.5`；Gaussian；mirroring；fp32 |
| 执行 job | A100 `63501304`，`COMPLETED 0:0`，耗时 `00:10:31` |

## 汇总结果

| 指标 | CARE-ASE | nnU-Net | CARE-ASE - nnU-Net |
|---|---:|---:|---:|
| scar Dice | 0.450878 | 0.556272 | -0.105394 |
| pure edema Dice | 0.450331 | 0.475196 | -0.024865 |

## 分 fold 结果

| Fold | Checkpoint | Cases | T2 edema cases | CARE scar | nnU-Net scar | Scar delta | CARE edema | nnU-Net edema | Edema delta |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | step5000 | 44 | 16 | 0.529509 | 0.590782 | -0.061272 | 0.507419 | 0.506598 | 0.000822 |
| 3 | step4000 | 44 | 16 | 0.372246 | 0.521763 | -0.149516 | 0.393242 | 0.443793 | -0.050551 |

## 证据路径

- Combined summary: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_latest_combined_summary.json`
- Job status receipt: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_job_status.json`
- Fold2 summary: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/fold_2/step05000/outer_diagnostic_summary.json`
- Fold2 casewise CSV: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/fold_2/step05000/outer_casewise_metrics.csv`
- Fold3 summary: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/fold_3/step04000/outer_diagnostic_summary.json`
- Fold3 casewise CSV: `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/fold_3/step04000/outer_casewise_metrics.csv`
- Runner: `scripts/evaluation/care_ase/run_current_user_authorized_outer_diagnostic.py`
- A100 sbatch: `jobs/care_ase_r2/run_current_outer_diagnostic_a100.sh`
- htzhulab mirror sbatch: `jobs/care_ase_r2/run_current_outer_diagnostic_htzhulab.sh`

## 注意

这不是 14000-step 的最终结果，只是当前已完成 checkpoint 的 outer diagnostic：fold2 到 step5000，fold3 到 step4000。正式训练仍需继续到目标步数；后续 checkpoint 应继续用同一 outer diagnostic 口径，不能再用 inner/same-exposure 0.9 表替代 fair comparison。
