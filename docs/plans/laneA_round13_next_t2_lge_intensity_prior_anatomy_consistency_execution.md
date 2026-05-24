# Lane A Round13 Next T2/LGE Intensity Prior And Anatomy Consistency Execution Plan

Plan metadata:

- Type: next execution controller
- Lane: Lane A / MyoPS scar-edema
- Round scope: Round13
- Status: planned, not executed
- Parent roadmap: `TODO.md`, `README.md`, Lane A Round2-Round12 evidence chain
- Parent plan: `docs/plans/laneA_round12_next_refiner_salvage_and_high_upside_mechanism_transition_execution.md`
- Function: controller document for a future goal-mode run focused on CARE-first T2/LGE intensity prior features and soft anatomy-lesion consistency
- Do not: train during this planning pass, submit Slurm, download weights, pull external repos, create validation zip, upload, modify production code, or overwrite existing predictions/results

## 1. 当前证据链和阶段判断

Lane A 已经从 shallow tweak 进入 CARE-first mechanism testing。Round13 不应再把“多跑几轮 refiner”当成主线，而应把 refiner 降级为 baseline-preserving substrate，并构建更可靠的 edema support feature。

- Round2: edema inference postprocess route fail。小组件/ROI 删除不能作为主线。
- Round3: loss wiring / gradient / tiny-overfit 可跑，但不代表性能。
- Round4: `edema_focal_tversky + no_t2_edema_loss_downweighting` 在真实 fold0 short train 中 fail，原因包括 remote FP、no-T2 FP、HD95 恶化和 scar guardrail 不干净。
- Round5: alignment 为 `watch`，boundary/distance 为 `watch`，anatomy soft prior 进入 bounded diagnostic。
- Round6: 当前 anatomy soft attenuation fail；missing-modality audit 指出 no-T2 empty-GT 不能作为强 negative，explicit modality presence 和 uncertainty-weighted supervision 是后续信号。
- Round7: first-party 6-channel modality-presence pipeline 工程可行，但简单 presence channels + scalar no-T2 weighting 没有通过 tiny gate。
- Round8: T2-present edema expert / separated edema supervision tiny gate 有信号，但 scratch / near-scratch very-short fold0 train 全面崩溃。
- Round9: nnU-Net501 checkpoint 可以成功迁移到 6-channel model，初始 logits 与 baseline 可做到完全一致；whole-network checkpoint-initialized fine-tune 只有极弱 edema signal，component / HD95 / scar guardrail 不干净。
- Round10: add-only edema residual refiner 安全性较好，scar unchanged，no-T2 clean，但只有极小 Dice gain，HD95/component 不 clean。
- Round11: component-safe bidirectional refiner 仍然 fail。scar unchanged、no-T2 clean，但 CenterC、remote FP 和 component guardrail 不干净；failure-summary 显示 Case3011/3040 是 `add_residual_remote_island / edge activation / weak T2 support`。
- Round12: deployable fallback salvage 只能作为 optional calibration，不能回到主线。Round13 推荐主线是 `T2_LGE_intensity_prior_route` 和 `anatomy_lesion_consistency_route`；boundary/HD 仍为 `watch`；external missing-modality repos 暂时 postpone 到 readiness。

Round12 关键证据：

- `round12_decision_table.md`: `T2_LGE_intensity_prior` 为 `go`，`anatomy_lesion_consistency` 为 `go`，`boundary_HD_objective` 为 `watch`，external repo integration 为 `postpone`。
- T2-present intensity audit: GT edema mean normalized T2 support `0.5168`，Round11 added FP `0.4355`，gap about `0.0813`。
- Deployable fallback grid: `baseline_prob_weak_or_remote_proxy` 是 clean optional calibration，但收益极小；refiner 不能作为 mainline 继续加 epoch。
- Boundary audit: most cases are `no_clear_round11_boundary_signal`; true boundary/HD objective应放在 support features 之后。

最新结论：

Lane A 下一阶段不应继续普通 refiner 训练，不应直接加 epoch，不应扩 fold1-4，不应提交 validation，不应回到 Focal Tversky、小组件、hard ROI、anatomy attenuation 或 whole-network fine-tune。当前 refiner substrate 可以复用，但 refiner 不再是主线本身。

Round13 主线切换为：

```text
CARE-first T2/LGE intensity prior + soft anatomy-lesion consistency
```

核心思想：当前 refiner 失败不是因为 scar/no-T2 safety 不可控，而是 residual 在 CenterC/T2 弱支持区域发生 remote/edge activation，且 baseline probability 对 edema 支持不足。下一步需要构建更可靠的 edema support feature，让模型或 refiner 能区分真实 T2-supported edema、baseline false positives、refiner remote activation 和 weak/ambiguous regions。Intensity prior 和 anatomy-lesion consistency 应作为 feature / support / soft penalty，而不是 hard ROI deletion 或完整外部 repo 复现。

## 2. Output Root

所有 Round13 输出必须放在：

```text
results/diagnostics/phase0_phase1/laneA_myops/round13_t2_lge_intensity_anatomy_consistency/
```

建议输出文件：

- `round13_goal_execution_readme.md`
- `round13_reproducibility_gate.csv`
- `round13_feature_source_manifest.csv`
- `t2_lge_intensity_feature_config.yaml`
- `t2_lge_intensity_feature_cache_manifest.csv`
- `t2_lge_intensity_feature_summary.csv`
- `t2_lge_intensity_separability.csv`
- `centerB_centerC_intensity_comparison.csv`
- `centerB_centerC_intensity_comparison.md`
- `anatomy_lesion_consistency_feature_config.yaml`
- `anatomy_lesion_consistency_feature_manifest.csv`
- `component_support_consistency_table.csv`
- `feature_only_rule_grid.csv`
- `feature_only_rule_grid.md`
- `feature_augmented_refiner_config.yaml`
- `feature_augmented_refiner_commands.txt`
- `feature_augmented_unit_gradient_smoke.csv`
- `feature_augmented_tiny_overfit_metrics.csv`
- `feature_augmented_fold0_very_short_metrics.csv`
- `feature_augmented_fold0_short_metrics.csv`
- `baseline_vs_round13_by_subset.csv`
- `no_t2_empty_gt_fp_table.csv`
- `scar_guardrail_table.csv`
- `case_level_failure_flags.csv`
- `boundary_hd_auxiliary_watch.csv`
- `boundary_hd_auxiliary_watch.md`
- `round14_external_method_readiness_matrix.csv`
- `round14_external_method_readiness_matrix.md`
- `round13_decision_table.md`
- `round13_round14_recommendation.md`

若生成 overlays 或 feature visualizations，放在：

```text
results/diagnostics/phase0_phase1/laneA_myops/round13_t2_lge_intensity_anatomy_consistency/overlays/
```

## 3. 主路线 A: `care_first_t2_lge_intensity_prior_feature_smoke`

目标：基于 Round12 intensity audit 的正信号，构建 CARE-first intensity prior feature，而不是完整复现 I-MMSeg。第一轮 goal-mode 应先做 feature construction + diagnostic separability + small refiner feature smoke，不做 full external I-MMSeg。

### 3.1 Feature A: `normalized_T2_support`

定义：

- 对每个 T2-present case 生成 T2 support map。
- 支持至少两种 normalization：
  - per-case robust z-score: median/IQR or median/MAD。
  - myocardium-local percentile: 在 baseline myocardium/anatomy support 或 dilated myocardium support 内计算 percentile。
- 输出可截断到 `[0,1]` support 或保留 z-score raw feature。

生成方式：

- 从 `data/CARE_Challenge/MyoPS_train/<center>/<case>/<case>_T2.nii.gz` 读取 T2。
- 用 GT/reference geometry 或 nnU-Net fold prediction geometry resample。
- 复用 `src/care_myocardium/refiner/laneA_round10_dataset.py` 中的 raw modality loading、presence metadata、baseline probabilities。
- no-T2 cases 不伪造 T2 support；应写入 `T2_present=false`，T2 feature 为 neutral/missing state，并保留 explicit presence channel。

必须报告：

- GT edema vs baseline FP vs Round11/12 remote FP 的 T2 support distribution。
- CenterB vs CenterC 分层。
- T2-present GT-positive subset。
- no-T2 empty-GT stability：不把 missing T2 当作 low T2 pathology negative。

### 3.2 Feature B: `LGE_T2_contrast_feature`

定义：

- LGE 与 T2 的局部 contrast feature，例如 local z-score、within-myocardium percentile、T2-minus-local-background、LGE/T2 percentile pair。
- 目标是区分 scar/edema/false positive，而不是把 LGE-only cases当成 edema strong negative。

生成方式：

- 读取 LGE 和 T2；若 T2 缺失，只生成 LGE support 和 missing-state flag，不输出伪 T2 contrast。
- 使用 local neighborhood 或 dilated myocardium support 计算 local background。
- 记录 feature 是否依赖 T2-present。

必须报告：

- GT edema、baseline false positive、baseline missed GT、Round11 added FP、Round11 added GT-overlap 的 LGE/T2 contrast。
- CenterB vs CenterC 是否分布不同。
- scar class_5 guardrail risk：不要让 edema contrast feature 误惩罚 LGE-driven scar。

### 3.3 Feature C: `baseline_uncertainty_intensity_feature`

定义：

- 组合 baseline edema probability、probability entropy/margin、T2 support、LGE support、anatomy support。
- 用于判断 baseline edema prediction 或 refiner correction 是否可信。

候选：

- `edema_prob`: nnU-Net baseline class_4 probability。
- `edema_margin`: class_4 probability minus max non-edema/pathology competing probability。
- `entropy`: all-class probability entropy or local class uncertainty。
- `support_score`: weighted combination of normalized T2 support, LGE/T2 contrast, baseline edema probability, anatomy support。

接入方式：

- 作为 future feature-augmented refiner/calibrator channel。
- 作为 per-component accept/reject proxy。
- 作为 soft loss weight 或 confidence penalty in later trainable smoke。

禁止：

- 使用 external data。
- 使用 validation pseudo-label supervised training。
- 把 no-T2 missing state 当作确定无 edema。
- 完整复现 I-MMSeg 的 CLIP/GPT/text-prompt pipeline。

## 4. 主路线 B: `soft_anatomy_lesion_consistency_feature_smoke`

目标：重新使用 anatomy，但不能重复 Round6 的 simple myocardium-distance attenuation，也不能 hard deletion。Anatomy 只作为 consistency feature 和 soft constraint。

### 4.1 Feature A: `lesion_anatomy_overlap_consistency`

定义：

- edema candidate 与 myocardium/LV/RV support、baseline myocardium probability、scar/edema neighborhood 的 overlap / distance / plausibility。
- 使用 baseline anatomy probabilities 或 hard baseline anatomy labels；必须记录 uncertainty，不把 anatomy 当绝对真值。

候选统计：

- overlap with baseline myocardium/LV/RV probability support。
- distance to dilated myocardium support。
- distance to scar and baseline edema neighborhood。
- inside/outside plausible myocardial band flag。

### 4.2 Feature B: `component_support_consistency`

定义：

- 每个 edema component 的 support summary，用于识别 remote/edge activation。

必须包含：

- component size。
- distance to myocardium support。
- distance to baseline edema。
- distance to T2 support high region。
- largest-component fraction。
- shape compactness or bbox elongation。
- component-level T2/LGE support mean/percentile。
- component-level baseline edema probability mean/margin。

注意：该 feature 不能依赖 GT 做 deployable decision；GT 只能用于 diagnostic separability 和 gate 评估。

### 4.3 Feature C: `soft_penalty_or_feature_channel`

定义：

- 将 anatomy-lesion consistency 作为 refiner feature 或 loss 的小权重 soft penalty。
- 不做推理端 hard deletion。
- 不复用 Round6 simple distance attenuation。

候选接入：

- feature channel: component/anatomy support map appended to refiner input。
- soft penalty: weak penalty for high edema probability in unsupported/weak-T2/remote regions。
- per-component calibrator: accept/reject or downweight residual correction based on support score。

禁止：

- hard ROI deletion。
- hard myocardium mask deletion。
- single distance threshold as final rule。
- 用 anatomy prior 删除真实 GT-positive small lesions。

## 5. 辅助路线 A: `boundary_hd_auxiliary_watch`

目标：根据 Round12 boundary/HD audit 判断是否在 intensity/anatomy support 之后加入小权重 boundary/HD feature 或 auxiliary loss。

当前判断：

- Round12 显示 `boundary_hd_objective` 为 `watch`。
- boundary/component tags 包括 `boundary_hd95_worse_without_remote_flag`、`volume_overprediction`、`remote_component_or_edge_activation`，但多数为 `no_clear_round11_boundary_signal`。
- 因此 boundary/HD 不能替代 intensity/support 机制，只能作为后续小权重辅助。

可考虑：

- surface distance feature。
- component-aware penalty。
- residual smoothness。
- small island penalty。
- weak HD-aware auxiliary loss after support features pass。

禁止：

- 让 boundary/HD objective 主导 recall。
- 只优化 Dice 或 foreground mean。
- 用 HD95 改善掩盖 component/remote FP 或 scar regression。

## 6. 辅助路线 B: `external_method_readiness_for_round14`

目标：为后续外部方法做 readiness，不在 Round13 第一轮直接拉 repo 训练。

Deep Research 方法映射：

| mechanism slot | methods | Round13 stance |
| --- | --- | --- |
| intensity prior | I-MMSeg | Use as mechanism source only; first build CARE-first T2/LGE intensity features. |
| anatomy-lesion consistency | Cascaded FSN, PT-Net | Use as mechanism source for soft consistency/cascade; no hard ROI. |
| boundary/HD | InverseForm, surface loss, differentiable HD | Watch; small-weight auxiliary only after support features pass. |
| missing-modality representation | UniME, AdaMM, CoPeDiT, MoE, MMPL-Seg | Postpone to readiness; solve teacher reliability and compliance first. |
| alignment | CAA-Seg, SSA | Watch; escalate only if overlays/features show sequence mismatch. |
| pretrained backbone | BiomedParse, MedNeXt, nnU-Net Task114/M&Ms | Future watch; metadata/license/pretrained data audit before any use. |

进入 Round14 external method 的条件：

- Round13 CARE-first feature smoke 有明确正信号，需要 external repo/module scale-up；或
- Round13 CARE-first feature smoke 彻底失败，证明 first-party feature route insufficient。

任何 external method 后续必须先通过：

- license/compliance。
- pretrained data source audit。
- external data risk audit。
- input-output shape mapping。
- CARE label mapping。
- one-case smoke。
- fold0 smoke gate。

禁止无差别 clone/train 所有 repo。

## 7. 阶段化执行门控

### Stage 1: `round13_reproducibility_and_feature_source_gate`

目标：复核 Round12 outputs、baseline predictions/probabilities、raw modalities、GT、modality metadata、center metadata、spacing/origin、label semantics、refiner cache。

允许：

- 创建 Round13 output root。
- 读取 Round10/Round11/Round12 outputs。
- 创建 feature construction/diagnostic scripts under `scripts/diagnostics/`。
- 读取 existing baseline nnU-Net501 predictions/probabilities。
- 读取 raw C0/LGE/T2 and labels。

禁止：

- 训练。
- 提交 Slurm。
- 修改 production model/trainer。
- 覆盖 nnU-Net501 baseline cache。
- 创建 validation zip or upload。

输出：

- `round13_goal_execution_readme.md`
- `round13_reproducibility_gate.csv`
- `round13_feature_source_manifest.csv`

通过标准：

- T2/LGE/C0 image、baseline probabilities、GT edema、anatomy labels/probabilities、center/modality flags 都可定位且 geometry consistent。
- Round12 intensity/anatomy audit 可复现或关键数值可追踪。
- Fold0 validation case set 与 previous rounds 一致。
- label semantics unchanged: background, myocardium, LV, RV, edema=4, scar=5。

失败标准：

- baseline probability 或 raw modality 缺失不可定位。
- spacing/origin/direction mismatch 未被记录。
- Round12 audit 与 current files 对不上。
- label/evaluator/cache 发生 silent change。

下一阶段：通过后进入 Stage 2。

### Stage 2: `t2_lge_intensity_prior_feature_construction`

目标：生成 T2/LGE intensity-prior feature maps 和 per-case/per-voxel summary。

允许：

- 生成 feature cache under Round13 output root。
- 生成 per-case summary and voxel-level separability metrics。
- 生成 CenterB vs CenterC comparison。
- 统计 GT edema vs remote FP, baseline FP/FN/TP intensity。

禁止：

- external data。
- external pretrained weights。
- no-T2 fake T2 support。
- validation pseudo-label supervised training。

输出：

- `t2_lge_intensity_feature_config.yaml`
- `t2_lge_intensity_feature_cache_manifest.csv`
- `t2_lge_intensity_feature_summary.csv`
- `t2_lge_intensity_separability.csv`
- `centerB_centerC_intensity_comparison.csv`
- `centerB_centerC_intensity_comparison.md`
- optional overlays under `overlays/`

通过标准：

- 至少一个 intensity feature 对 GT edema 与 Round11/12 remote FP 或 baseline FP 有可分信号。
- CenterC 上不完全失效。
- no-T2 cases 被明确标记 missing/neutral，不作为强 negative。
- feature construction 不改变 labels/evaluator/cache。

失败标准：

- feature 只在 all-case aggregate 看起来有效。
- CenterC 无任何可分信号。
- feature 需要 GT 才能 deploy。
- no-T2 被误编码成 low-support hard negative。

下一阶段：通过或 watch 后进入 Stage 3；若完全失败，仍进入 Stage 6/8 做 readiness decision，不训练。

### Stage 3: `anatomy_lesion_consistency_feature_construction`

目标：生成 anatomy-lesion consistency feature maps 和 component-level summary。

允许：

- 统计每个 candidate edema component 的 anatomy support、distance、overlap、component size、distance-to-baseline edema、distance-to-T2 support、plausibility flags。
- 使用 baseline anatomy probability/support as uncertain feature。
- 生成 component-level tables and overlays。

禁止：

- hard ROI deletion。
- simple distance attenuation。
- GT-based deployable component selection。

输出：

- `anatomy_lesion_consistency_feature_config.yaml`
- `anatomy_lesion_consistency_feature_manifest.csv`
- `component_support_consistency_table.csv`
- optional overlays under `overlays/`

通过标准：

- anatomy consistency feature 能解释 Round11/12 remote/edge activation。
- 不依赖 GT 做选择。
- 不会明显压掉 T2-present GT-positive edema support。

失败标准：

- anatomy feature 与 failure 无关。
- 需要 hard deletion 才有效。
- feature 会删除真实 small edema。

下一阶段：通过或 watch 后进入 Stage 4。

### Stage 4: `feature_only_diagnostic_and_rule_smoke`

目标：不训练，用 intensity + anatomy consistency feature 做 rule-based diagnostic smoke。该阶段不是最终方法，只判断 support feature 是否足够强。

比较对象：

- nnU-Net501 baseline。
- Round11 refiner。
- Round12 deployable fallback。
- intensity-only support rule。
- anatomy-only consistency rule。
- combined intensity + anatomy support score。

允许：

- 使用 deployable support score 做 offline proxy grid。
- 使用 GT only for evaluation, not for rule selection。
- 输出 case-level and subset metrics。

禁止：

- 使用 case ID/GT/hosted feedback 选择 rule。
- 把 rule-based smoke 当最终 submission candidate。
- hard ROI deletion。

输出：

- `feature_only_rule_grid.csv`
- `feature_only_rule_grid.md`
- `baseline_vs_round13_by_subset.csv` for feature-only candidates
- `case_level_failure_flags.csv`

通过标准：

- 存在可部署 rule/score 能减少 remote/edge activation。
- 不显著损伤 T2-present GT edema Dice/HD95。
- no-T2 empty-GT 不新增 edema FP。
- scar unchanged。
- CenterC 有 clean signal or no regression。

失败标准：

- 只有 oracle rule 有效。
- Dice 提升但 HD95/component/remote FP 恶化。
- no-T2 FP 增加。
- scar changed。
- 只能靠 all-case aggregate 解释。

下一阶段：有正信号则进入 Stage 5；无正信号则跳到 Stage 8 做 Round14 recommendation。

### Stage 5: `feature_augmented_refiner_or_calibrator_smoke`

目标：在 feature 有信号时，将 intensity/anatomy consistency feature 接入安全的 refiner/calibrator substrate。

优先候选：

1. `feature_augmented_edema_only_calibrator`: 输入 baseline probabilities + T2/LGE support + anatomy consistency，输出 per-voxel or per-component class_4 calibration score。
2. `support_gated_residual_refiner`: 复用 Round10/Round11 edema-only refiner substrate，但新增 support feature channels，class_5 scar immutable，no-T2 additions disabled/strictly controlled。
3. `per_component_accept_reject_classifier`: 对 baseline/refiner candidate components 生成 deployable accept/reject score；训练前先做 feature-only and tiny smoke。

允许：

- 新增 small first-party diagnostic/training script。
- 新增 small first-party feature/calibrator module under `src/care_myocardium/` only if feature-only gate passes。
- unit/import/py_compile/one-batch forward/backward。
- tiny-overfit smoke。

禁止：

- whole nnU-Net training。
- changing class_5 scar。
- hard ROI deletion。
- external repo integration。
- fold1-4。
- validation zip/upload。

输出：

- `feature_augmented_refiner_config.yaml`
- `feature_augmented_refiner_commands.txt`
- `feature_augmented_unit_gradient_smoke.csv`
- `feature_augmented_tiny_overfit_metrics.csv`

通过标准：

- import/unit/gradient smoke pass。
- no NaN/Inf。
- class_5 scar unchanged by construction。
- no-T2 empty-GT remains clean in tiny smoke。
- T2-present/CenterC tiny cases show support-aware signal without remote activation.

失败标准：

- feature wiring changes label semantics/evaluator/cache。
- scar changes。
- no-T2 FP increases。
- remote/edge activation repeats immediately。
- feature model only learns case/center shortcut.

下一阶段：通过后进入 Stage 6。

### Stage 6: `bounded_fold0_training_ladder`

目标：如果 Stage 5 gate 通过，允许 future goal-mode staged training，但必须 bounded/gated。

训练阶梯：

1. py_compile/import/config smoke。
2. one-batch forward/backward。
3. tiny-overfit on selected CenterB/CenterC T2-present cases plus no-T2 empty-GT controls。
4. fold0 very-short train。
5. fold0 short train only if very-short gate passes。
6. fold0 longer train only if short gate passes and user later accepts expansion risk。

禁止：

- 直接 full schedule。
- 直接 fold1-4 / 5-fold。
- validation zip or upload。
- multiple candidates in parallel without gate。
- overwriting nnU-Net501 baseline cache。

输出：

- `feature_augmented_fold0_very_short_metrics.csv`
- `feature_augmented_fold0_short_metrics.csv`
- `baseline_vs_round13_by_subset.csv`
- `no_t2_empty_gt_fp_table.csv`
- `scar_guardrail_table.csv`
- `case_level_failure_flags.csv`

通过标准：

- T2-present GT-positive or CenterC edema has clean positive signal。
- Dice and HD95 cannot have a severe trade-off。
- component count and remote FP do not worsen。
- no-T2 empty-GT does not add edema FP。
- class_5 scar Dice/HD95 unchanged or not materially worse。
- gain is not empty-GT artifact。

失败标准：

- HD95/component/remote FP worsens.
- CenterC worsens or no clean signal.
- scar guardrail not clean.
- no-T2 FP increases.
- NaN/Inf or silent cache/label/evaluator change.
- result only supported by all-case aggregate.

下一阶段：pass 后进入 Stage 7；fail 时 stop candidate and write decision.

### Stage 7: `evaluation_and_decision_gate`

目标：统一评估并决定 promote/watch/postpone/stop。

必须报告：

- `myops_edema` class_4 Dice, HD, HD95, component count, small FP, remote FP, pred/GT volume ratio。
- `myops_scar` class_5 Dice, HD, HD95 as guardrail。
- all-case。
- T2-present。
- T2-present GT-positive。
- complete-modality。
- CenterB。
- CenterC。
- no-T2 empty-GT。
- C0+LGE no-T2。
- LGE-only。
- modality group and center subsets。
- case-level failure flags。

输出：

- `round13_decision_table.md`
- `round13_round14_recommendation.md`

判定：

- `go`: feature-only and/or feature-augmented candidate improves T2-present/CenterC edema without HD95/component/remote/scar/no-T2 regression。
- `watch`: feature separability is real, but trainable smoke is too weak or not clean enough。
- `postpone`: feature route requires external method or better data audit before training。
- `stop`: feature route fails deployable support or repeats remote/edge activation.

### Stage 8: `boundary_hd_auxiliary_watch`

目标：在 Stage 2-7 的证据基础上决定 boundary/HD 是否进入 Round14 auxiliary。

允许：

- Analyze surface distance feature、component-aware penalty、residual smoothness、small island penalty。
- Produce watch-only recommendation。

禁止：

- boundary/HD as primary route before intensity/anatomy support works。
- Focal Tversky or recall-heavy loss mainline。

输出：

- `boundary_hd_auxiliary_watch.csv`
- `boundary_hd_auxiliary_watch.md`

通过标准：

- boundary/HD failure has evidence not explained by support features。
- proposed objective is small-weight auxiliary and respects scar/no-T2/component gates。

### Stage 9: `external_method_readiness_for_round14`

目标：准备 Round14 external/high-upside mechanism integration，但本轮不 clone/train。

允许：

- Metadata-level readiness matrix。
- Link each method to mechanism slot and required smoke。

禁止：

- bulk clone/build/train external repos。
- download large weights。
- external data training。

输出：

- `round14_external_method_readiness_matrix.csv`
- `round14_external_method_readiness_matrix.md`

通过标准：

- Round14 top route is selected by evidence, not popularity。
- external method has compliance and one-case smoke requirements.

## 8. Resource Stance

用户 token、Slurm、GPU 资源充足，后续 goal-mode 可以尽可能多往前推进；但推进方式必须 staged, gated, evidence-driven。Round13 可以在一个 goal run 中完成 feature construction、feature-only diagnostic、unit/gradient/tiny smoke、bounded fold0 very-short/short train 和 decision table，前提是每个 gate 通过。任何 gate fail 后必须停止该 candidate 并记录原因，不能因为资源充足跳到 larger training、fold expansion 或 submission。

## 9. Next Goal Execution Prompt Draft

下面 prompt 可直接用于后续 goal-mode：

```text
你现在在 /overflow/htzhu/CARE 中工作。请执行 Lane A Round13：
docs/plans/laneA_round13_next_t2_lge_intensity_prior_anatomy_consistency_execution.md

目标是尽可能推进 Round13，但必须 staged, gated, evidence-driven。先复核 Round12 outputs、baseline predictions/probabilities、raw C0/LGE/T2、GT、center/modality metadata、spacing/origin、label semantics 和 refiner cache，输出 reproducibility gate。然后构建 CARE-first T2/LGE intensity prior features，包括 normalized_T2_support、LGE_T2_contrast_feature、baseline_uncertainty_intensity_feature；输出 feature cache manifest、case-level summary、voxel-level separability、CenterB vs CenterC comparison、GT edema vs remote FP/baseline FP/FN/TP stats。no-T2 cases 必须记录 missing/neutral state，不得伪造 T2 support 或当强 negative。

接着构建 soft anatomy-lesion consistency features，包括 lesion_anatomy_overlap_consistency、component_support_consistency、soft feature/penalty candidate；不要做 hard ROI，不要做 simple distance attenuation。随后执行 feature-only diagnostic rule smoke，比较 baseline、Round11 refiner、Round12 fallback、intensity/anatomy support rules。规则选择不得使用 GT、case ID 或 hosted feedback。

如果 feature-only gate 有正信号，再接入 feature-augmented edema-only refiner/calibrator substrate，先做 import/py_compile、unit/gradient、tiny-overfit；通过后才允许 fold0 very-short，进一步通过后才允许 fold0 short。禁止 whole nnU-Net training、禁止 class_5 scar 修改、禁止 no-T2 edema FP 增加、禁止 fold1-4/5-fold、禁止 validation zip/upload。输出全部 metrics、overlays、case-level failure flags、boundary/HD watch 和 Round14 external readiness matrix。

所有输出放在：
results/diagnostics/phase0_phase1/laneA_myops/round13_t2_lge_intensity_anatomy_consistency/

资源充足，可以尽可能推进多个阶段；但每个阶段必须 gate，失败即停，不得自动跳到更大训练或 submission。
```
