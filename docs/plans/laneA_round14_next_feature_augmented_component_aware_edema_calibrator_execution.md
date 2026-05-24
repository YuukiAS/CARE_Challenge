# Lane A Round14 Next Feature-Augmented Component-Aware Edema Calibrator Execution Plan

Plan metadata:

- Type: next execution controller
- Lane: Lane A / MyoPS scar-edema
- Round scope: Round14
- Status: planned, not executed
- Parent roadmap: `TODO.md`, `README.md`, Lane A Round2-Round13 evidence chain
- Parent plan: `docs/plans/laneA_round13_next_t2_lge_intensity_prior_anatomy_consistency_execution.md`
- Function: controller document for a future goal-mode run focused on a feature-augmented, component-aware, baseline-preserving class-4 edema calibrator
- Do not: train during this planning pass, submit Slurm, download weights, pull external repos, create validation zip, upload, modify production code, or overwrite existing predictions/results

## 1. 当前证据链和阶段判断

Lane A 已经连续排除了多条 shallow/local tweak route。Round14 不应再把“更多 epoch”或“再调一个阈值”作为主线，而应把 Round13 的弱但真实 feature signal 转化为一个 learned、可部署、component-aware 的 class-4 edema calibrator。

- Round2: edema inference postprocess route fail。小组件/ROI 删除不能作为主线。
- Round3: loss wiring / gradient / tiny-overfit 可跑，但不代表性能。
- Round4: `edema_focal_tversky + no_t2_edema_loss_downweighting` 在真实 fold0 short train 中 fail，原因包括 remote FP、no-T2 FP、HD95 恶化和 scar guardrail 不干净。
- Round5: alignment 为 `watch`，boundary/distance 为 `watch`，anatomy soft prior 进入 bounded diagnostic。
- Round6: 当前 anatomy soft attenuation fail；missing-modality audit 指出 no-T2 empty-GT 不能作为强 negative，explicit modality presence 和 uncertainty-weighted supervision 是后续信号。
- Round7: first-party 6-channel modality-presence pipeline 工程可行，但简单 presence channels + scalar no-T2 weighting 没有通过 tiny gate。
- Round8: T2-present edema expert / separated edema supervision tiny gate 有信号，但 scratch / near-scratch very-short fold0 train 全面崩溃。
- Round9: nnU-Net501 checkpoint 可以成功迁移到 6-channel model，初始 logits 与 baseline 可做到完全一致；whole-network checkpoint-initialized fine-tune 只有极弱 edema signal，component / HD95 / scar guardrail 不干净。
- Round10: add-only edema residual refiner 安全性较好，scar unchanged，no-T2 clean，但只有极小 Dice gain，HD95/component 不 clean。
- Round11: component-safe bidirectional refiner 仍然 fail。scar unchanged、no-T2 clean，但 CenterC、remote FP 和 component guardrail 不干净。
- Round12: deployable fallback salvage 只能作为 optional calibration，不能回到主线。
- Round13: T2/LGE intensity prior 和 anatomy-lesion consistency 有信号，但 feature-only rule 收益很弱。`strict_support_filter` 可以消除 hard failure flags，却不能真正解决 CenterC/T2-present edema。Feature-augmented tiny calibrator smoke 稳定，loss 从 `0.6598` 降到 `0.4678`，无 NaN/Inf。

Round13 关键证据：

- `strict_support_filter`: all-case edema Dice `+0.0008`，T2-present GT-positive edema Dice `+0.0008`，T2-present GT-positive HD95 improvement `+0.0026`，CenterC edema Dice `-0.0002`，CenterC HD95 improvement `-0.0329`，CenterC remote FP improvement `+0.1111`，scar unchanged，no-T2 component unchanged。
- Round13 gate: `watch_feature_augmented_calibrator_smoke`，即只允许 bounded learned calibrator smoke，不允许 fold expansion 或 validation submission。
- Round13 tiny smoke: `pass`，`n_samples=8071`，`n_positive=4096`，`n_negative=3975`，`loss_delta=0.1920`，`nan_or_inf=False`。

最新结论：

Lane A 下一阶段不应继续普通 add/remove refiner 训练，不应直接加 epoch，不应扩 fold1-4，不应提交 validation，不应回到 Focal Tversky、小组件、hard ROI、anatomy attenuation 或 whole-network fine-tune。当前 refiner substrate 可以复用，但 Round14 主线应升级为：

```text
feature-augmented component-aware edema calibrator
```

核心思想：

- nnU-Net501 baseline 继续负责 scar/anatomy/main segmentation。
- class_5 scar 必须保持 unchanged。
- no-T2 empty-GT 必须保持 clean。
- calibrator/refiner 只允许修改 class_4 edema。
- Round13 已经证明 T2/LGE intensity prior 和 anatomy-lesion consistency 有弱信号；下一步应让轻量 learned calibrator 在这些 feature 上学习可部署的 accept/reject/correct rule，而不是继续手写固定阈值 rule。
- 重点 failure zone 是 CenterC/T2-present edema、remote/edge activation、component safety 和 baseline-preserving correction。

## 2. Output Root

所有 Round14 输出必须放在：

```text
results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator/
```

建议输出文件：

- `round14_goal_execution_readme.md`
- `round14_reproducibility_gate.md`
- `round14_component_dataset_manifest.csv`
- `round14_component_feature_summary.csv`
- `round14_component_rule_smoke.csv`
- `round14_component_model_smoke.csv`
- `round14_voxel_patch_dataset_manifest.csv`
- `round14_feature_calibrator_config.yaml`
- `round14_train_commands.txt`
- `round14_unit_gradient_smoke.csv`
- `round14_tiny_overfit_metrics.csv`
- `round14_fold0_very_short_metrics.csv`
- `round14_fold0_short_metrics.csv`
- `round14_fold0_longer_metrics.csv`
- `round14_fusion_policy_grid.csv`
- `baseline_vs_candidate_by_subset.csv`
- `centerC_edema_table.csv`
- `no_t2_empty_gt_fp_table.csv`
- `scar_unchanged_guardrail_table.csv`
- `case2031_3011_3012_3040_table.csv`
- `component_accept_reject_summary.csv`
- `case_level_failure_flags.csv`
- `round14_decision_table.md`
- `round14_round15_recommendation.md`

如果生成 overlays 或 feature visualizations，放在：

```text
results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator/overlays/
```

## 3. 主路线 A: `component_level_support_calibrator`

目标：从 Round13 的 intensity/anatomy feature 中构建 component-level samples，训练或评估一个轻量 component accept/reject/calibration model。该路线优先解决 `Case3011` / `Case3040` 类似的 remote/edge activation。

### 3.1 Component Sample 来源

候选 component 必须覆盖：

- nnU-Net501 baseline class_4 edema components。
- Round10 add-only refiner新增/改变 components。
- Round11 bidirectional refiner新增/改变 components。
- Round12 deployable fallback / proxy rule components。
- Round13 `strict_support_filter` 接受/拒绝的 components。
- remote/edge activation components，尤其 `Case3011`、`Case3040` 风格。
- GT-overlapping true edema components。
- CenterB/CenterC complete-modality T2-present cases。
- no-T2 empty-GT cases，用于 stability audit，但不能作为强 dense edema negative。

### 3.2 Component Feature Columns

每个 candidate edema component 至少包含：

- `baseline_edema_prob_mean/p25/p50/p75/max`
- `baseline_edema_margin_mean`
- `baseline_entropy_mean`
- `T2_present`
- `normalized_T2_support_mean/p50/p75/max`
- `LGE_support_mean/p50/p75`
- `LGE_T2_contrast_mean/p50`
- `within_myocardium_T2_percentile`
- `within_myocardium_LGE_percentile`
- `anatomy_support_mean/max`
- `distance_to_myocardium_or_anatomy_mm`
- `distance_to_baseline_edema_mm`
- `distance_to_high_T2_support_mm`
- `component_voxels`
- `component_volume_mm3`
- `largest_component_fraction`
- `shape_compactness`
- `bbox_size_zyx`
- `remote_distance_mm`
- `center`
- `modality_group`
- `C0_present/LGE_present/T2_present`
- `source_model_or_rule`
- `fold0_split`

Optional but useful:

- `added_vs_baseline_voxels`
- `removed_vs_baseline_voxels`
- `component_touches_baseline_edema`
- `component_overlaps_round13_strict_rule`
- `component_support_score`

### 3.3 Component Labels

Label definitions must be explicit and leakage-safe:

- For fold0 train cases only: label by GT overlap and HD/component plausibility, e.g. `keep_component` if component overlaps GT edema or is near GT edema boundary; `reject_component` if it is remote FP with no GT overlap and weak support.
- For fold0 validation cases: labels may be used only for evaluation, failure analysis, and gate decisions, not for fitting model parameters.
- Do not use hosted validation feedback, case IDs, or oracle per-case fallback decisions as deployable model features.

### 3.4 Candidate Component Models

Start from interpretable, lightweight candidates:

1. `component_rule_score`: no-training score using support features; baseline comparator only.
2. `component_logistic_regression`: sklearn or small first-party torch linear model, trained on fold0 train component samples only.
3. `component_shallow_mlp`: one hidden layer MLP only if logistic/rule smoke has a clean signal.

Forbidden in Round14 first pass:

- random forest/boosting as opaque mainline unless logistic is clearly insufficient and leakage is audited.
- any model trained using fold0 validation labels.
- center-only shortcut model.
- external repo model.

### 3.5 Component Route Gate

Pass only if the component-level route:

- reduces remote/edge activation compared with Round11/Round13;
- is at least as safe as `strict_support_filter`;
- keeps no-T2 empty-GT edema FP unchanged or lower;
- keeps scar unchanged by construction;
- does not reject true GT-positive edema components in T2-present cases;
- gives a clean signal in CenterC, not only all-case aggregate.

Fail if:

- the model relies on center/modality shortcut without intensity/anatomy support;
- CenterC true edema components are rejected;
- no-T2 FP increases;
- component count improves only by over-pruning;
- validation labels are used to choose case-specific fallback;
- `strict_support_filter` remains safer and equally effective.

## 4. 主路线 B: `voxel_patch_feature_augmented_edema_calibrator`

目标：训练一个轻量 voxel/patch-level edema calibrator 或 residual calibrator。输入来自 cached CARE features 和 baseline probabilities；输出只修改 class_4 edema，必须有 residual magnitude bound 和 fallback-to-baseline。

### 4.1 Candidate Inputs

Required input channels/features:

- baseline logits/probabilities, especially class_4 edema probability。
- baseline entropy and edema margin。
- raw C0/LGE/T2 normalized image channels where present。
- modality presence constants: `C0_present/LGE_present/T2_present`。
- Round13 `normalized_T2_support`。
- Round13 `LGE_T2_contrast_feature`。
- Round13 `baseline_uncertainty_intensity_feature`。
- anatomy-lesion consistency feature。
- component support score or per-component accept probability。

no-T2 handling:

- no-T2 cases must preserve explicit missing state.
- no-T2 empty-GT should provide weak stability/calibration signal, not dense hard-negative edema supervision.
- no-T2 feature channels must not fake low T2 support as pathology evidence.

### 4.2 Candidate Outputs

候选按保守程度排序：

1. `component_accept_reject_calibrator`: per-component score only; if component unsafe, fallback to baseline on that component。
2. `bounded_edema_probability_calibrator`: outputs small delta to class_4 probability/logit; non-edema classes unchanged。
3. `support_gated_residual_refiner`: reuse Round10/Round11 substrate but add feature channels and component-level support gating。

All candidates must:

- preserve class_5 scar exactly;
- avoid changes to classes 1/2/3 except where class_4 edema is explicitly accepted;
- record changed voxels, added voxels, removed voxels, residual magnitude, component accept/reject counts;
- support fallback-to-baseline when safety rules fail.

### 4.3 Training Objective

Use bounded, conservative objective:

- T2-present GT-positive: supervised edema correction with BCE/Dice or small focal component only if stable。
- no-T2 empty-GT: weak calibration penalty only; no dense hard negative。
- residual regularization: penalize large probability/logit deltas。
- component safety regularization: weak penalty for unsupported remote additions。
- optional boundary/HD auxiliary: watch only; small weight and only after support features are clean。

Do not:

- train whole nnU-Net;
- update class_5 scar logic;
- use external data;
- use validation pseudo-label supervised training;
- allow component growth without a support/fallback check.

## 5. 辅助路线 A: `strict_support_filter_as_safety_baseline`

Round13 `strict_support_filter` 是 safety baseline and fallback comparator，不是主线。

Role:

- minimum safety reference for learned calibrators;
- sanity comparator for remote FP and component safety;
- fallback option when learned candidate is unsafe.

Required comparisons:

- baseline nnU-Net501 fold0;
- Round11 bidirectional refiner;
- Round13 `strict_support_filter`;
- Round14 component-level calibrator;
- Round14 voxel/patch calibrator。

Hard rule:

Any learned calibrator that is less safe than `strict_support_filter` on scar unchanged, no-T2 clean, remote FP, or component guardrails must fail, even if Dice improves slightly.

## 6. 辅助路线 B: `external_method_bridge_for_round15`

Round14 不直接训练外部 repo。Deep Research methods should be mapped into the feature-calibrator framework and held for Round15 readiness.

| mechanism slot | Deep Research methods | Round14 interpretation | Round15 trigger |
| --- | --- | --- | --- |
| intensity prior | I-MMSeg | use as inspiration for CARE-first T2/LGE support and contrast features | if Round14 feature-calibrator has signal but needs richer intensity prior |
| anatomy-lesion consistency | Cascaded FSN / PT-Net | use as soft consistency feature/penalty, not hard ROI deletion | if component model shows anatomy support is predictive but current features are too crude |
| boundary/component auxiliary | InverseForm / surface loss / HD loss | watch; small auxiliary only after support features pass | if HD95/component remains main blocker after support-calibrator is safe |
| missing-modality representation | UniME / AdaMM / CoPeDiT / MoE / MMPL-Seg | postpone; metadata/readiness only | if no-T2/T2-present supervision conflict remains after first-party calibrator |
| alignment | CAA-Seg / SSA | watch | if overlays show sequence mismatch or intensity support is inconsistent spatially |
| pretrained backbone/features | BiomedParse / MedNeXt / nnU-Net Task114/M&Ms | future feature/backbone watch | if first-party feature substrate fails or needs external representation |

Any external repo entering Round15 must first pass:

- license/compliance check;
- pretrained data source check;
- external-data risk check;
- input-output shape check;
- label mapping check;
- one-case smoke;
- fold0 smoke;
- one-zip submission semantics review.

## 7. Stage 1: `round14_reproducibility_and_feature_cache_gate`

目标：复核 Round13 outputs、feature cache、baseline predictions/probabilities、raw modalities、GT、modality metadata、center metadata、spacing/origin、label semantics、refiner cache。

Allowed:

- Read Round11-Round13 outputs and scripts。
- Create Round14 output root。
- Write `round14_goal_execution_readme.md` and `round14_reproducibility_gate.md`。
- Create new diagnostic/calibrator scripts only if needed in a future execution pass。

Forbidden:

- training;
- Slurm submission;
- validation zip/upload;
- external repo/weights;
- production nnU-Net cache changes;
- modifying existing Round10-Round13 outputs.

Outputs:

- `round14_goal_execution_readme.md`
- `round14_reproducibility_gate.md`

Pass criteria:

- Round13 feature-only rule grid, tiny calibrator smoke, overlays, T2/LGE features, anatomy consistency features are locatable。
- Round11/Round13 predictions and nnU-Net501 baseline probabilities are locatable。
- Fold0 split and out-of-fold baseline source folds are clear。
- Label semantics remain background, myocardium, LV, RV, edema=4, scar=5。

Fail criteria:

- feature cache missing or incompatible;
- fold0 split ambiguous;
- baseline predictions/probabilities unavailable;
- label/evaluator mismatch;
- any required artifact would require re-running training to reconstruct.

Next stage: if pass, enter Stage 2.

## 8. Stage 2: `component_sample_dataset_construction`

目标：构建 component-level sample dataset。

Allowed:

- Read fold0 train and fold0 validation existing OOF baseline predictions/probabilities。
- Read Round10/Round11/Round13 refiner/fusion predictions。
- Extract component-level features from existing feature cache and image/probability files。
- Use fold0 train labels to build training labels; use fold0 validation labels only for evaluation。

Forbidden:

- training a model before leakage check passes;
- using validation labels to fit thresholds/model parameters;
- case-ID specific rules;
- hosted feedback;
- changing existing predictions.

Outputs:

- `round14_component_dataset_manifest.csv`
- `round14_component_feature_summary.csv`
- leakage audit section in `round14_reproducibility_gate.md`

Pass criteria:

- component samples cover baseline, Round11/Round13, remote FP, GT-overlap, CenterB, CenterC, and no-T2 empty-GT groups。
- feature columns are stable and documented。
- train/eval split is leakage-safe。
- center/modality distribution is reported。

Fail criteria:

- component labels require fold0 validation labels for fitting;
- too few T2-present GT-positive train components for any meaningful smoke;
- CenterC components absent or unusable;
- feature values show geometry mismatch or missing modality misencoding.

Next stage: if pass, enter Stage 3.

## 9. Stage 3: `component_level_rule_and_model_smoke`

目标：先做 no-training component-level rule smoke，再在通过时做轻量 model smoke。

Allowed:

- Evaluate deployable rules using component features。
- Train/evaluate logistic regression or one-layer torch model on fold0 train components only。
- Use fold0 validation only for gate evaluation。
- Compare against `strict_support_filter`。

Forbidden:

- fitting on fold0 validation;
- opaque high-capacity model as first pass;
- external repo;
- case-specific fallback using GT;
- treating center as the only decision feature.

Outputs:

- `round14_component_rule_smoke.csv`
- `round14_component_model_smoke.csv`
- `component_accept_reject_summary.csv`
- `case2031_3011_3012_3040_table.csv`

Pass criteria:

- component model/rule reduces remote/edge activation, especially `Case3011`/`Case3040` style components。
- no-T2 empty-GT remains clean。
- true GT-positive edema components are not systematically rejected。
- CenterC has clean or at least watch-positive signal。
- safety is no worse than `strict_support_filter`。

Fail criteria:

- weaker safety than `strict_support_filter`;
- rejects true edema to improve HD/component;
- no-T2 FP increases;
- only all-case aggregate improves;
- CenterC worsens;
- signal comes from center shortcut rather than support features.

Next stage: if pass or watch-positive, enter Stage 4. If fail, skip trainable calibrator and write stop/watch decision in Stage 8.

## 10. Stage 4: `voxel_patch_feature_calibrator_dataset_construction`

目标：构建 voxel/patch-level feature dataset。

Required samples:

- T2-present GT-positive edema voxels。
- edema boundary voxels。
- baseline FP/FN/TP voxels。
- Round11/Round13 remote FP voxels。
- no-T2 empty-GT stability samples。
- CenterB and CenterC complete-modality samples。

Allowed:

- cached feature extraction;
- balanced sampling;
- hard negative sampling only from reliable T2-present contexts;
- weak no-T2 stability sampling.

Forbidden:

- no-T2 dense hard negative policy;
- using fold0 validation patches for training;
- whole-volume brute-force training before unit/tiny gate;
- silent normalization changes.

Outputs:

- `round14_voxel_patch_dataset_manifest.csv`
- feature normalization summary in `round14_feature_calibrator_config.yaml`

Pass criteria:

- sample counts are sufficient and documented。
- no-T2 cases are represented as weak stability/control, not strong negatives。
- CenterB/CenterC and T2-present GT-positive cases are included。
- feature ranges are finite and stable。

Fail criteria:

- NaN/Inf features;
- severe class imbalance without sampling control;
- no-T2 negative samples dominate the loss;
- fold0 validation leakage.

Next stage: if pass, enter Stage 5.

## 11. Stage 5: `feature_augmented_edema_calibrator_implementation`

目标：实现最小 first-party feature-augmented edema-only calibrator。

Preferred first implementation:

- `src/care_myocardium/calibrator/laneA_round14_component_dataset.py`
- `src/care_myocardium/calibrator/laneA_round14_model.py`
- `scripts/diagnostics/laneA_round14_feature_augmented_calibrator.py`
- `scripts/training/run_laneA_round14_feature_calibrator_train.py`
- optional after gates: `jobs/nnUNet/laneA_round14_feature_calibrator_fold0_very_short.sh`

候选实现顺序：

1. component accept/reject calibrator。
2. bounded voxel/patch edema probability calibrator。
3. support-gated residual refiner with component fallback。

Allowed:

- small first-party modules under `src/care_myocardium/calibrator/`;
- scripts under `scripts/diagnostics/` and `scripts/training/`;
- new isolated output directories;
- import/py_compile/unit/gradient tests.

Forbidden:

- modifying class label semantics;
- modifying evaluator;
- modifying nnU-Net trainer or dataloader unless a later plan explicitly authorizes it;
- training whole nnU-Net;
- touching class_5 scar predictions;
- overwriting Round10-Round13 outputs.

Outputs:

- `round14_feature_calibrator_config.yaml`
- `round14_train_commands.txt`
- `round14_unit_gradient_smoke.csv`

Pass criteria:

- import and py_compile pass。
- one-batch forward/backward pass。
- no NaN/Inf。
- finite gradient norm。
- class_5 scar unchanged by fusion construction。
- no-T2 additions disabled or bounded by explicit safety policy。
- baseline fallback path works.

Fail criteria:

- scar can change;
- no fallback path;
- NaN/Inf;
- feature shape/channel mismatch;
- residual magnitude unbounded;
- model requires changing evaluator/labels/cache semantics.

Next stage: if pass, enter Stage 6.

## 12. Stage 6: `bounded_training_ladder`

目标：允许 future goal-mode 积极推进训练，但必须 staged/gated。

Training ladder:

1. `import / py_compile / config smoke`
2. `one-batch forward + backward`
3. `tiny-overfit` on selected T2-present CenterB/CenterC and no-T2 empty-GT stability cases
4. `fold0 very-short train`
5. `fold0 short train`
6. `fold0 longer train` only if short train passes and user later accepts expansion risk

Allowed:

- bounded local/GPU execution in future goal-mode;
- one candidate at a time;
- isolated experiment name, e.g. `laneA_round14_feature_augmented_component_calibrator_fold0_very_short`;
- htzhulab Slurm only after smoke gates pass.

Forbidden:

- direct fold1-4 / 5-fold;
- validation zip/upload;
- multiple candidates in parallel without gate;
- direct jump from unit smoke to long train;
- continuing after safety fail.

Outputs:

- `round14_tiny_overfit_metrics.csv`
- `round14_fold0_very_short_metrics.csv`
- `round14_fold0_short_metrics.csv`
- `round14_fold0_longer_metrics.csv`
- `round14_train_commands.txt`

Pass criteria for each rung:

- loss decreases without NaN/Inf。
- scar unchanged。
- no-T2 empty-GT FP unchanged or lower。
- T2-present GT-positive or CenterC edema has clean signal。
- component count / remote FP no worse than `strict_support_filter`。
- Dice and HD95 do not trade off badly。

Fail criteria:

- Dice improves but HD95/component/remote FP worsen。
- CenterC worsens。
- no-T2 FP appears。
- scar guardrail not clean。
- improvement only from empty-GT artifact。
- training instability or cache pollution。

Next stage: if a rung passes, continue to next rung within resource limits; if any rung fails, stop that candidate and enter Stage 8.

## 13. Stage 7: `fusion_policy_and_evaluation_gate`

目标：统一评估 candidate and fusion policies，决定 promote/watch/postpone/stop。

Required subsets:

- all-case
- T2-present
- T2-present GT-positive
- complete-modality
- CenterB
- CenterC
- C0+LGE+T2
- C0+LGE no-T2
- LGE-only
- no-T2 empty-GT
- focus cases: `Case2031`, `Case3011`, `Case3012`, `Case3040`

Required metrics:

- `myops_edema` class_4 Dice, HD, HD95
- component count
- small FP
- remote FP
- pred/GT volume ratio
- no-T2 edema FP voxel count
- no-T2 edema FP case count
- component accept/reject counts
- changed/added/removed voxels
- residual/probability delta magnitude
- `myops_scar` class_5 Dice, HD, HD95 guardrail
- scar changed voxels
- case-level failure flags

Fusion policy grid:

- baseline fallback
- strict_support_filter fallback
- component accept/reject
- residual magnitude bound
- support-score threshold
- no-T2 disabled addition
- component-count fallback
- remote-distance fallback
- hybrid component + voxel calibrator

Outputs:

- `round14_fusion_policy_grid.csv`
- `baseline_vs_candidate_by_subset.csv`
- `centerC_edema_table.csv`
- `no_t2_empty_gt_fp_table.csv`
- `scar_unchanged_guardrail_table.csv`
- `case2031_3011_3012_3040_table.csv`
- `case_level_failure_flags.csv`

Pass criteria:

- T2-present GT-positive edema or CenterC complete-case edema has clean positive signal。
- HD95/component/remote FP no worse than `strict_support_filter` and preferably better than baseline。
- no-T2 empty-GT FP does not increase。
- class_5 scar Dice/HD95 unchanged or numerically identical by construction。
- gains do not come from empty-GT artifact。
- case-level focus table does not show new `Case3011/3040` style remote activation。

Fail criteria:

- only all-case aggregate improves。
- CenterC does not improve or worsens。
- no-T2 FP increases。
- scar changes。
- stricter safety baseline is better or equal but safer。
- component accept/reject relies on GT/case IDs。

Next stage: enter Stage 8 for final decision.

## 14. Stage 8: `round14_decision_and_round15_bridge`

目标：记录 final decision and next action。

Decision labels:

- `go_fold0_short_or_longer`: only if very-short/short gates cleanly pass。
- `watch_feature_calibrator`: weak but safe signal; no expansion without explicit user authorization。
- `optional_safety_calibration_only`: safe but tiny benefit, comparable to strict_support_filter。
- `stop_feature_calibrator`: unsafe or no positive signal。
- `postpone_external_bridge`: external method not yet justified。
- `go_round15_external_metadata_smoke`: first-party calibrator fails or shows a specific missing mechanism requiring external method readiness。

Outputs:

- `round14_decision_table.md`
- `round14_round15_recommendation.md`

Promotion criteria:

- candidate beats baseline and `strict_support_filter` on the relevant edema gate, not just all-case aggregate。
- T2-present GT-positive or CenterC signal is clean。
- no-T2 and scar guardrails are clean。
- component/remote FP are clean。
- deployable policy uses no GT/case-ID oracle。

Stop criteria:

- no positive CenterC/T2-present signal。
- remote/edge activation persists。
- learned calibrator is no safer than a fixed rule。
- no-T2 FP or scar guardrail fails。
- required solution becomes external data training or validation pseudo-label supervised training。

Round15 bridge:

- If Round14 fails because features are insufficient, prioritize external method metadata / one-case smoke by mechanism slot.
- If intensity support is the main missing signal, start with I-MMSeg-inspired first-party or metadata audit.
- If anatomy consistency is predictive but crude, start Cascaded FSN/PT-Net-style soft feature audit.
- If HD95 remains bad after support is safe, start InverseForm/surface/HD auxiliary smoke.
- If no-T2/T2-present supervision conflict remains, start UniME/AdaMM/CoPeDiT/MoE metadata audit only.
- Do not clone/train all repos indiscriminately.

## 15. Resource Stance

用户 token、Slurm、GPU 资源充足，后续 goal-mode 可以尽可能多往前推进；但推进方式必须 staged, gated, feature-driven, baseline-preserving, and component-safe。

Allowed in a future goal-mode run if gates pass:

- component dataset construction;
- voxel/patch feature dataset construction;
- rule smoke;
- lightweight model smoke;
- feature-augmented calibrator implementation;
- unit tests;
- tiny-overfit;
- fold0 very-short train;
- fold0 short train;
- evaluation and decision table;
- fold0 longer train only if previous gates pass and the plan/user permits it.

Forbidden regardless of resources:

- skipping feature/component diagnostics and jumping directly to training;
- fold1-4 / 5-fold without explicit later authorization;
- validation zip or submission;
- external data training;
- validation pseudo-label supervised training;
- large external repo integration in Round14 first pass;
- foreground_mean success criteria.

## 16. Next Goal Execution Prompt Draft

```text
你现在在 `/overflow/htzhu/CARE` 中工作。请执行 Lane A Round14：

`docs/plans/laneA_round14_next_feature_augmented_component_aware_edema_calibrator_execution.md`

目标是尽可能推进 feature-augmented component-aware edema calibrator，但必须 staged/gated, feature-driven, baseline-preserving, and component-safe。不要创建 validation zip，不要上传，不要扩 fold1-4/5-fold，不要下载权重，不要拉取外部 repo，不要训练 whole nnU-Net。

请先复核 Round13 输出和 feature cache，输出 `round14_reproducibility_gate.md`。然后构建 component-level support dataset 和 voxel/patch feature dataset，明确 fold0 train/validation leakage audit。先做 component-level rule smoke，再做轻量 component model smoke；必须与 Round13 `strict_support_filter` 比较。若 component signal 通过或 watch-positive，再实现最小 first-party feature-augmented edema-only calibrator，执行 import/py_compile、one-batch forward/backward、unit/gradient smoke、tiny-overfit。只有这些 gate 通过后，才允许提交或运行单个 bounded fold0 very-short job；fold0 short/longer 也必须逐级 gate。

所有输出放在：

`results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator/`

必须输出 metrics、overlays、component accept/reject summary、scar unchanged guardrail、no-T2 empty-GT FP table、CenterC table、case2031/3011/3012/3040 focus table、failure flags、`round14_decision_table.md` 和 `round14_round15_recommendation.md`。

通过标准：T2-present GT-positive edema 或 CenterC complete-case edema 有 clean positive signal；HD95/component/remote FP 不比 `strict_support_filter` 差；no-T2 empty-GT FP 不增加；class_5 scar unchanged；不能靠 empty-GT artifact 或 all-case aggregate 过 gate。任一 gate fail 必须停止该 candidate，记录原因，不得自动扩大训练或提交。
```
