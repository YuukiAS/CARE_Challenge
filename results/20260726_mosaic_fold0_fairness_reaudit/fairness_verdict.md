本次复核显示，旧 MoSAIC fold0 结论的 checkpoint 选择部分失效：旧 scar 结果用了 epoch 75 的 `best.pt`，不是 upstream 风格的 pathology-specific checkpoint。修正后仍需看 clean fold0 与 nnU-Net 的同口径差距，full-data Google Drive 权重只能作为训练污染诊断。

final_verdict: CLEAN_MOSAIC_STILL_MATERIALLY_BELOW_NNUNET

| 问题 | 结论 |
| --- | --- |
| 旧 0.3392 scar 是否由错误 checkpoint 造成 | checkpoint routing 错误成立；epoch75->pathology checkpoint scar Dice 变化为 0.0209，旧结论至少不能作为最终 clean MoSAIC 结论 |
| 修正 clean MoSAIC scar 与 nnU-Net 差距 | nnU-Net 0.5602 vs clean_pathology_checkpoint 0.3601，差值 MoSAIC-nnU-Net -0.2001 |
| 修正 clean MoSAIC edema reliable T2 subset 与 nnU-Net 差距 | nnU-Net 0.3944 vs clean best-edema 0.2638 / terminal-edema merged 0.2413 |
| epoch 75 -> epoch 190 scar 增益 | 0.0209 |
| epoch 190 -> epoch 300 scar 差异 | -0.0123 |
| edema epoch 130 -> epoch 200 差异 | -0.0225 |
| full-data 污染版本比 clean fold0 高多少 | scar 0.1045；pure edema reliable 0.0692 |
| full-data 增益来自后处理多少 | scar final-raw -0.0021；edema final-raw-zone -0.2696；其余混有 all-train 权重、双 coarse、checkpoint 和 submission recipe |
| 三选一判断 | CLEAN_MOSAIC_STILL_MATERIALLY_BELOW_NNUNET |
| MoSAIC 是否适合做 primary backbone | 否，当前 clean 证据不足以替代 nnU-Net |
| MoSAIC 是否适合做 proposal source | 可以作为候选/互补性来源观察，但只能基于 clean fold0 help/harm 证据，不可用 full-data 污染结果背书 |
| 是否不值得进入 CARE final Docker | 当前不授权 Docker；若 clean 仍明显低于 nnU-Net，则不应作为 primary 进入 final Docker |
