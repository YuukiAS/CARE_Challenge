# Controller Report

这轮已经把“四个模型到底跑没跑、哪里不行”说清楚了：四条 lane 都完成了正式训练，M0R/M1/M2/M3 都经过 checkpoint 审计和 inner full-volume 评价；最后不是全失败，而是 M0R 明显赢下 scar 和 edema 的 inner source selection。outer 复放后，scar 有本地候选价值，edema 仍在 CenterC sentinel 上漏检明显，所以终态应写 `SCAR_ONLY_CANDIDATE_READY`，不能写完整 target-domain candidate。

## Model Status

| model | status | key evidence | interpretation |
|---|---|---|---|
| M0R faithful control | trained/evaluated complete | `m0r_faithful_control/*_training_receipt.json`, `inner_evaluation/m0r_faithful_control/*` | 修复了旧 M0 的 SGD/PolyLR/16epoch 问题；AdamW warmup-cosine 4000 steps/fold；inner scar/edema 均最强。 |
| M1 MyoPS-Net-L CARE | trained/evaluated complete | `m1_myopsnet_l_care/*_training_receipt.json`, `inner_evaluation/m1_myopsnet_l_care/*` | 真实 C0/LGE/T2 adapter 跑完，但 inner scar/edema 明显弱于 M0R/M2。 |
| M2 I-MMSeg CARE | trained/evaluated complete | `m2_i_mmseg_care/asset_download_receipt.json`, `inner_evaluation/global_summary_metrics.csv` | 官方 source/assets 已落地并训练；不是 lite 替代。inner 表现次于 M0R，强于 M1/M3。 |
| M3 CARE-TDS | trained/evaluated complete | `m3_care_tds/*_training_receipt.json`, `inner_evaluation/m3_care_tds/*` | 训练完成但 pathology 输出很弱；不能作为候选。 |

## Frozen Sources

- scar: `m0r_faithful_control`, checkpoint step `3500`
- pure edema: `m0r_faithful_control`, checkpoint step `4000`
- freeze evidence: `inner_evaluation/global_source_selection.json`
- outer-driven source selection: `false`

## Outer Replay Result

| pathology | Dice mean | sensitivity mean | practical conclusion |
|---|---:|---:|---|
| scar | 0.6500 | 0.7264 | 可作为本地 scar candidate 继续给 Planner 判断是否扩展。 |
| pure edema | 0.4340 | 0.4124 | 不足以声明完整 target-domain candidate。 |

Sentinel cases:

- `Case2019`: scar `0.7651`, edema `0.6764`; 远端假阳性没有爆炸。
- `Case2034`: scar `0.7747`, edema `0.5533`; edema 有检出但体积偏大。
- `Case2021`: scar `0.7912`, edema `0.5838`; 原本较好病例没有被破坏。
- `Case3009`: scar `0.6840`, edema `0.3173`; CenterC edema 仍弱。
- `Case3008`: scar `0.6170`, edema `0.1581`; edema sensitivity `0.0885`，这是拒绝 full candidate 的关键证据。

## Boundary

No official validation, Docker upload, or hosted metric claim was performed or authorized. Final remaining operational work is validator, commit, push, remote SHA verification, then a valid completion notification through the existing notifier.
