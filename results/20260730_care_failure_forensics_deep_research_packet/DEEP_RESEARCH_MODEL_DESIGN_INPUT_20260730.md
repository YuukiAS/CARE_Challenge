# CARE Deep Research 模型设计输入 20260730

## A. 用户硬约束

1. 必须使用 Batch7、MMRD、Cascade、ARC 中至少一到两条有效经验。
2. 不得复制失败实现。
3. nnU-Net、MoSAIC 不得成为唯一主体。
4. 不得堆叠多个完整 backbone。
5. scar 和 edema 分别建模且同等重要。
6. 必须具有显著超过 nnU-Net 和 MoSAIC validation 的机制上限。
7. 不接受仅约 0.005-0.02 Dice 的收益。
8. 应评估约 0.1 Dice 级别的合理性。

## B. 本地已证实事实

- MyoPS training cases: 220。
- raw/meta T2-present cases: 80；V2 的 `t2_present=220` 是错误的 preprocessed slot 推断。
- scar = label 5。
- pure edema = label 4，official edema 只允许 raw/meta T2-present 且标签可靠病例。
- edema-zone = label 4 or 5，只能作为内部结构指标。
- myocardium union = label 1 or 4 or 5。

## C. 本地有效历史经验

- 数据 hygiene：no-T2 病例不得产生 edema 假阴性监督。
- final-output trace：任何新组件必须证明进入 final logits/final mask。
- decoder preservation：完整 decoder/recipe 对强基线至关重要。
- bounded correction 和 fallback safety 可作为安全规则保留。

## D. 本地禁止重复错误

- 用 Dataset501 三通道文件存在性推断 T2/C0 availability。
- 用 edema-zone 冒充 official pure edema。
- 把 full-data 或 hosted-near recipe 写成 clean architecture superiority。
- 把 control 与 SRR 同 prototype input 的结果解释为 prototype 无效。
- 使用未进入 final logits 的 router/dictionary/prototype/refiner 作为机制证据。

## E. scar evidence

scar 有病例级互补但 case-oracle gain 只在约 0.02 量级；simple selector/ensemble 不足以支撑约 0.1 Dice。未来机制必须直接减少 small-lesion FN、remote FP、blood-pool/normal-myocardium confusion 和 boundary undersegmentation。

## F. pure-edema evidence

pure edema 必须只在 raw/meta T2-present 病例评价。clean OOF 互补弱；任何 edema 专家必须证明不是 center shortcut、availability shortcut 或 no-T2 false-negative supervision。

## G. MoSAIC recipe evidence

M0-M10 需作为 recipe decomposition 使用：clean OOF、full-data diagnostic、hosted-near recipe 分开。可探索 coarse/fine、ensemble、TTA、threshold、postprocess 的贡献，但不能把 full-data 结果当 clean 验证。

## H. nnU-Net decoder/recipe evidence

完整 nnU-Net decoder 和 training recipe 是强基线核心。未来模型不能只迁移 encoder 后重置 decoder；必须证明 decoder capability 没有丢失。

## I. large-gain feasibility

当前本地结论：LOCAL_EVIDENCE_SUPPORTS_ONLY_MODEST_GAIN。约 0.1 Dice 需要新的空间或表征机制，并需要 patient-level feature probe、error-pool ablation 和 clean validation evidence。

## J. unresolved external research questions

- 哪类机制能真实恢复 small-lesion FN 且不引入 remote FP？
- 是否存在不依赖 center/availability shortcut 的 edema 表征？
- hosted validation 的 small-sample/domain shift 对 MoSAIC/nnU-Net 差距贡献多大？
- 如何在不堆多个完整 backbone 的情况下保持 decoder capacity？

## K. 允许 Deep Research 探索的机制类别

- 轻量 lesion-proposal + bounded correction。
- scar/edema 分离专家，但共享底座受限且必须有独立 loss/evidence。
- uncertainty/calibration 和 topology-safe postprocess。
- modality-aware supervision hygiene。
- decoder-preserving adaptation。

## L. 必须被拒绝的设计类别

- nnU-Net 或 MoSAIC 单独作为主体后只调 threshold。
- 多完整 backbone 堆叠。
- 无 final-logits 证据的 router/prototype/dictionary。
- 使用 no-T2 病例训练 edema 假阴性。
- 把 voxel oracle 当可部署上限。
