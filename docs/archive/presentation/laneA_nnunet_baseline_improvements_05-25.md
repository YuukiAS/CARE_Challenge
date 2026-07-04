# Lane A 汇报：基于 nnU-Net baseline 的 MyoPS edema 改进现状

时间戳：2026-05-25  
范围：Lane A / Dataset501 / `myops_edema` class 4；`myops_scar` class 5 作为 guardrail。

## 当前总判断

nnU-Net501 仍是 Lane A 的保守 baseline。过去多轮已经排除了若干“局部修补”路线：小组件/ROI 后处理、recall-heavy Focal Tversky、简单 no-T2 downweighting、hard/soft anatomy attenuation、scratch separated edema expert、whole-network fine-tune、普通 add/remove refiner、feature-only rule 和弱 feature-calibrator。

真正瓶颈不是某一个 loss 或阈值，而是 T2 presence、center confounding、edema supervision availability、HD/topology、以及 baseline edema representation 共同导致的 CenterC / T2-present edema localization 问题。no-T2 empty-GT 不能当强负样本；scar class 5 必须作为硬 guardrail。

## 已尝试路线与失败原因

| 阶段 | 主要想法 | 结果 | 失败/停止原因 |
| --- | --- | --- | --- |
| R2 | 推理小组件/ROI | component count 降，但 GT-positive Dice/HD95 不 clean | 小碎片不是主因；停止 postprocess-only。 |
| R3-R4 | loss smoke；Focal Tversky + no-T2 downweighting | wiring 可跑；fold0 short fail | remote FP、no-T2 FP、HD95、scar guardrail 不干净。 |
| R5-R6 | alignment/anatomy/boundary audit；anatomy attenuation | anatomy 有信号，但 oracle-style attenuation fail | anatomy 不能 hard delete 或简单 distance attenuation，只能做 future feature/regularizer。 |
| R7-R8 | 6-channel presence；T2-present separated expert | 工程可行，tiny 有信号；scratch very-short 崩 | presence+scalar weighting 不够；scratch 改结构不能硬比完整 baseline。 |
| R9 | baseline checkpoint 迁移；whole-network fine-tune | 初始 logits 可 baseline-identical；fine-tune fail | whole-network 更新破坏 component/HD95/scar guardrail。 |
| R10-R11 | edema-only refiner：add-only 到 bidirectional | scar unchanged、no-T2 clean；有效性弱 | CenterC/T2 weak support 下 edge/remote activation；Case3011/3040 remote FP worse。 |
| R12-R14 | fallback、T2/LGE+anatomy features、feature calibrator | intensity/anatomy 弱信号；tiny calibrator 可学习 | 收益太弱，不能解决 CenterC/T2-positive edema；不继续普通 epoch。 |
| R15 | DeepResearch portfolio first batch | A 有微弱 intensity-prior 信号，B/C 近似 fallback | A 引入 CenterC component safety 问题；B/C 无 clean T2-present/CenterC gain。 |

## 失败模式

- 数据结构限制：MyoPS train 中完整 C0+LGE+T2 只有 80/220；LGE-only 116/220。T2 是 edema 主 cue，但训练多数缺 T2。
- 关键 failure zone：CenterC complete-modality edema。问题不只是缺 T2，还包括 center style、edema boundary/topology、T2/LGE support 不稳定、baseline representation 不足。
- HD/topology：Dice 小幅提升经常伴随 HD95、component count 或 remote FP 变差；小 remote component 足以让 HD 不可接受。
- baseline-preserving 是必要条件但非充分条件：refiner 可保护 scar 和 no-T2 stability，但没学到可靠 edema correction。

## Round16 当前状态与下一步

Round16 目标是从普通 refiner/calibrator 转向 DeepResearch-guided controlled external mechanism integration，但仍保持 fold0 bounded、compliance-checked、no validation submission。

已完成：

- external live metadata/import/one-case smoke 已完成；未下载权重、未用外部训练数据。
- I-MMSeg：repo 可达但 license/dependency blocked。CascadedFSN/PTNet：未定位官方可用 repo。AdaMM：局部 UNet instantiate 可过但 package import blocked。MedNeXt：Apache-2.0 且 import/one-case instantiate 通过，是最干净的 pretrained/backbone readiness 候选。InverseForm：license unclear 且缺依赖。BiomedParse：依赖/权重 gate 未过。
- First-party A/C/E/F 已通过 unit/gradient/tiny smoke；已提交 fold0 very-short jobs。

当前队列：

- htzhulab jobs 因预计等待到 5/25-5/27 已 supersede，并加 manifest no-op gate 防止重复写结果。
- a100 replacement jobs pending：A=52278441，C=52278443，E=52278442，F=52278440。

决策规则：

- very-short 完成后运行 `scripts/diagnostics/laneA_round16_collect_results.py`。
- 只有 T2-present GT-positive 或 CenterC edema 有 clean signal，且 HD95/component/remote FP/no-T2/scar guardrail 不坏，才考虑 fold0 short。
- 否则停止该候选。仍禁止 validation zip、upload、fold1-4/5-fold。

## 后续建议

1. 短期：等 Round16 A/C/E/F very-short 结果。如果只有 tiny Dice gain 但 component/HD95 变差，直接 stop。
2. 若 Round16 有 clean signal：只对通过候选做 fold0 short，继续报告 CenterC、T2-present GT-positive、no-T2 empty-GT、scar guardrail、remote FP/component。
3. 若 Round16 全 fail：Round17 优先 MedNeXt/pretrained backbone readiness 或更窄的 T2/LGE intensity representation；同时保留 anatomy-lesion consistency 和 boundary/HD 为辅助，不再投入普通 refiner epoch。
4. 提交策略：Lane A 当前没有 submission candidate。CARE validation 仍是一个 zip 同时包含 MyoPS+CineMyoPS；不要拆成三个 metric 上传，也不要用 foreground mean 掩盖 edema 失败。

主要证据路径：`README.md`; `results/diagnostics/care_myocardium/laneA_myops/round10_edema_refiner/` 到 `round16_external_mechanism_integration/`; Round16 plan: `docs/plans/laneA_round16_next_external_mechanism_integration_large_smoke_execution.md`。
