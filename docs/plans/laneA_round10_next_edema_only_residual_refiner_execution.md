# Lane A Round10 Next Edema-Only Residual Refiner Execution Plan

Plan metadata:
- Type: next/planned round execution
- Lane: Lane A, MyoPS scar/edema
- Round scope: Round10
- Status: next goal-mode controller, planning-only artifact
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: `docs/plans/laneA_round09_next_baseline_initialized_edema_adaptation_execution.md`
- Function: define a staged, gated Round10 route for a baseline-preserving class_4 edema-only residual refiner after Round9 stopped whole-network adaptation
- Do not: execute experiments from this plan-writing pass; do not train; do not submit Slurm; do not create validation zip; do not upload; do not download weights; do not clone or train external repos; do not modify production code while creating this plan

## 1. 当前证据链和阶段判断

Lane A 现在不是一个单轮调参问题。Round2 到 Round9 已经把多个低收益方向排除，并留下了一个更窄、更安全的下一步。

1. **Round2: edema inference postprocess route fail.** 小组件删除和 ROI 阈值不能作为主线。删除 1-voxel edema 小岛后 component count 下降，但 GT-positive edema Dice 略降、HD95 略恶化，说明真实瓶颈不是简单 inference cleanup。
2. **Round3: loss wiring / gradient / tiny-overfit 可跑，但不是性能证明。** `edema_focal_tversky`、`no_t2_edema_loss_downweighting` 等候选能跑通，只说明工程链路和梯度可用。
3. **Round4: `edema_focal_tversky + no_t2_edema_loss_downweighting` fold0 short train fail。** 失败原因包括 remote FP、no-T2 FP、HD95 恶化和 scar guardrail 不干净。因此不继续围绕单一 Focal Tversky、loss weight 或 scalar no-T2 downweighting 微调。
4. **Round5: controlled mechanism audit。** Alignment 是 `watch`，boundary/distance 是 `watch`，anatomy soft prior 进入 bounded diagnostic。该轮把 Deep Research 转成机制槽位，但不支持 hard ROI deletion。
5. **Round6: current anatomy soft attenuation fail。** Anatomy soft prior 的当前实现不能扩展；missing-modality audit 指出 no-T2 empty-GT 不能作为 class_4 edema 强 negative，explicit modality presence 和 uncertainty-aware supervision 是后续信号。
6. **Round7: first-party 6-channel modality-presence pipeline 工程上可行，但简单 presence channels + scalar no-T2 weighting 没有通过 tiny gate。** U1 太弱，没有 T2-positive edema signal；U2 有 edema signal，但引入 no-T2 empty-GT FP。
7. **Round8: T2-present edema expert / separated edema supervision tiny gate 有信号，但 scratch / near-scratch very-short fold0 train 全面崩溃。** Round8 不能被解释为机制最终失败，但证明了不能拿 scratch 3 epoch 改结构模型去和完整 nnU-Net501 baseline 硬比，也不能直接扩训练。
8. **Round9: baseline-initialized 6-channel whole-network route stop, refiner safety gate pass。** Round9 证明 nnU-Net501 fold0 checkpoint 可以迁移到 6-channel model，初始 crop logits 与 baseline 完全一致；但 whole-network checkpoint-initialized fine-tune 只有极弱 edema signal，component / HD95 / scar guardrail 不干净，不应继续 longer train。与此同时，Round9 的 edema-only residual refiner safety gate 通过：class_5 scar unchanged，no-T2 crop FP unchanged，class_4-only fusion works。

Round9 关键证据：

- `results/diagnostics/phase0_phase1/laneA_myops/round9_baseline_initialized_adaptation/round9_next_actions.md`
- `results/diagnostics/phase0_phase1/laneA_myops/round9_baseline_initialized_adaptation/round9_decision_table.md`
- `results/diagnostics/phase0_phase1/laneA_myops/round9_baseline_initialized_adaptation/round9_refiner_smoke.csv`
- `src/care_myocardium/nnunet/laneA_round9_refiner.py`

Round10 新结论：

```text
Lane A 下一阶段应切换到 edema-only residual refiner / baseline-preserving correction。
```

不要继续：

- whole-network fine-tune；
- scratch 复杂新结构训练；
- U1/U2 scalar no-T2 weight 微调；
- 小组件删除、ROI threshold、hard ROI deletion；
- Focal Tversky 主导训练；
- anatomy attenuation；
- 无差别外部 repo integration。

核心思想：

- nnU-Net501 baseline 继续负责整体 anatomy、scar 和主要 segmentation structure。
- Refiner 只对 class_4 edema 做局部 residual correction。
- class_5 scar 必须完全保持 baseline，或在导出层面逐 case 证明不被修改。
- 如果 refiner 不通过 gate，必须 fallback 到 baseline。

Round10 要回答的问题：

```text
在完全保护 nnU-Net baseline scar/anatomy 表征的前提下，能不能用轻量 class_4 edema refiner 改善 T2-present / CenterC edema Dice、HD95、component 和 remote FP？
```

## 2. 输出根目录

Round10 所有输出必须隔离到：

```text
results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner/
```

建议输出文件：

- `round10_goal_execution_readme.md`
- `round10_cache_manifest.csv`
- `round10_cache_sanity.md`
- `round10_refiner_config.yaml`
- `round10_train_commands.txt`
- `round10_unit_gradient_smoke.csv`
- `round10_tiny_overfit_metrics.csv`
- `round10_fold0_very_short_metrics.csv`
- `round10_fold0_short_train_metrics.csv`
- `round10_fold0_longer_train_metrics.csv`
- `baseline_vs_refiner_by_subset.csv`
- `no_t2_empty_gt_fp_table.csv`
- `centerB_centerC_edema_table.csv`
- `scar_unchanged_guardrail_table.csv`
- `residual_magnitude_summary.csv`
- `case_level_failure_flags.csv`
- `round10_decision_table.md`
- `round10_next_actions.md`

Optional overlays:

```text
results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner/failure_overlays/
```

Suggested experiment/cache names:

```text
laneA_r10_edema_residual_refiner_fold0_very_short
laneA_r10_edema_residual_refiner_fold0_short
laneA_r10_edema_residual_refiner_fold0_longer
```

Do not overwrite any nnU-Net501 baseline, Round8, Round9, or previous diagnostic outputs.

## 3. 主路线 1: `cached_baseline_edema_refiner_dataset`

### Goal

构建一个 Round10 专用 cached refiner dataset，用于训练 class_4 edema-only residual refiner。这个 cache 的目的不是替代 nnU-Net preprocessing，而是避免每次 refiner 训练都重复运行完整 nnU-Net，同时把 baseline prediction、image features、metadata 和 GT 对齐记录下来。

### Inputs

Preferred inputs, ordered by information value:

1. nnU-Net501 fold0 baseline logits/probabilities if available.
2. If logits/probabilities are unavailable, use compact baseline prediction labels and record information loss.
3. Baseline class_4 edema probability or binary mask.
4. Baseline class_5 scar probability or binary mask, for guardrail only.
5. Baseline myocardium/LV/RV probability or binary mask as anatomy support.
6. C0/LGE/T2 image channels, with missing modalities filled with zeros and presence channels recorded.
7. Modality presence channels: `C0_present`, `LGE_present`, `T2_present`.
8. Optional myocardium distance/support feature, derived only from baseline anatomy or GT anatomy in training diagnostics. If GT anatomy is used, it must be marked oracle/training-only and never assumed available at validation/test inference.

### Targets

The supervised target is class_4 edema only:

```text
target_edema = GT == 4
```

Other labels are used only for:

- scar unchanged guardrail;
- anatomy support features;
- case-level diagnostics;
- optional safety masks.

### Cache Requirements

Each cached case must record:

- `case_id`
- `fold`
- `split`: train/val
- `center`
- `modality_group`
- `C0_present`
- `LGE_present`
- `T2_present`
- `edema_gt_positive`
- `scar_gt_positive`
- `no_t2_empty_gt`
- baseline prediction path
- baseline logits/probability path if available
- GT path
- raw/preprocessed image paths used
- spacing, origin, direction, shape
- label set in GT and baseline prediction
- cache feature tensor path
- cache target tensor path
- feature channel order
- whether logits/probs or hard labels were used

Cache must live under:

```text
results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner/cache/
```

Do not write into `data/nnUNet/nnUNet_preprocessed`, `data/nnUNet/nnUNet_results`, or any baseline prediction directory.

### Safety Rules

- Refiner training must never modify baseline predictions in place.
- Refiner export must create a separate prediction directory.
- Label mapping must remain compact Dataset501 semantics: `edema=4`, `scar=5`.
- Spacing/origin/direction must be copied from baseline/GT and checked before any metric.
- If logits/probs are missing and only hard labels are used, `round10_cache_sanity.md` must explicitly say the route is lower-information and may have limited upside.

## 4. 主路线 2: `edema_only_residual_refiner_trainable_smoke`

### Goal

Train a lightweight residual module that only changes class_4 edema. It must not change class_5 scar, myocardium, LV, RV, or background except through a documented class_4 replacement/fusion rule.

### Candidate A: Conservative Logit Residual Refiner

Most conservative first candidate.

Input:

- baseline edema logit/probability or binary edema channel;
- baseline class one-hot/probability channels for labels 0-5;
- T2/LGE/C0 image features;
- modality presence channels;
- optional anatomy support channel from baseline myocardium/LV/RV;
- optional baseline uncertainty channel if probabilities/logits exist.

Output:

```text
delta_edema_logit
```

Fusion:

```text
new_edema_logit = baseline_edema_logit + clip(delta_edema_logit, -delta_max, +delta_max)
```

Constraints:

- `delta_max` must be recorded, with a conservative first value such as `1.0` or `2.0`.
- If only hard baseline labels are available, emulate baseline edema logit with fixed low/high logits and record this approximation.
- class_5 scar logits/prediction are unchanged.
- final compact segmentation can only differ from baseline where the edema refiner changes class_4.
- residual magnitude regularization is required.

Expected benefit:

- small but controlled correction near baseline edema mistakes;
- lower risk of large remote FP;
- easiest to measure residual magnitude and fallback.

Fail-fast:

- residual saturates over large regions;
- class_5 changes after fusion;
- no-T2 empty-GT FP increases;
- CenterC component/HD95 worsens.

### Candidate B: Binary Edema Correction Refiner

Second candidate, still conservative.

Input:

- baseline prediction/probabilities;
- C0/LGE/T2 image features;
- modality mask;
- baseline anatomy support;
- optional distance/support channels.

Output:

```text
binary edema correction probability
```

Training:

- T2-present / complete cases receive strong edema supervision.
- no-T2 empty-GT cases are used only for weak calibration or FP control, not as dense hard negative that dominates the edema learner.
- Scar and anatomy classes are not supervised as outputs because the module does not predict them.

Fusion:

- class_4 can be added or removed only by a documented conservative threshold rule.
- class_5 scar and baseline anatomy are copied from baseline.
- fallback to baseline must be a one-line switch.

Expected benefit:

- easier implementation when baseline logits are unavailable;
- safer than whole-network fine-tune.

Risk:

- probability calibration may be weak if only hard labels are used;
- binary output can still create component/remote FP if thresholding is not constrained.

### Candidate C: T2-Focused CenterC Refiner

Optional only after A or B has a clean safety signal.

Goal:

- target CenterC complete-case edema weakness with local T2 intensity, baseline uncertainty, and myocardium support.

Constraints:

- not a CenterC-only overfit model;
- report CenterB and CenterC separately;
- no hidden center shortcut unless explicitly used as a diagnostic feature;
- do not promote if CenterB or no-T2 guardrails degrade.

Round10 first goal-mode should prioritize Candidate A and/or Candidate B minimal implementation. Do not implement complex external repo methods in the first pass.

## 5. 预备路线: `controlled_external_feature_readiness`

Deep Research should be used as mechanism source for refiner feature/loss slots, not as a target for wholesale repo reproduction.

| Deep Research method | Round10 refiner slot | Round10 status |
| --- | --- | --- |
| I-MMSeg | T2/LGE intensity prior feature or intensity-prompt-inspired channel | future feature, no repo integration first |
| Cascaded FSN / PT-Net | anatomy support feature from baseline myocardium/LV/RV or soft distance map | feature slot, first-party only |
| InverseForm / surface loss / HD loss | small-weight boundary auxiliary for refiner after safety passes | watch, not first loss |
| AdaMM / UniME / CoPeDiT / MoE / MMPL-Seg | future missing-modality representation or teacher/student route | postpone |
| CAA-Seg / SSA | alignment watch for multi-sequence feature reliability | watch |
| BiomedParse / MedNeXt / nnU-Net Task114/M&Ms | future backbone/pretrained route | watch |

External repo rules:

- no Round10 first-pass clone/train of external repos;
- no external training data;
- no validation pseudo-label supervised training;
- any future external method must first pass license/compliance, pretrained data source, input-output shape, label mapping, one-case smoke, and fold0 smoke.

## 6. Phase 1: `round10_reproducibility_and_cache_gate`

### Goal

复核 nnU-Net501 fold0 baseline predictions、fold split、label semantics、evaluator、spacing/origin、modality metadata 和 Round9 refiner safety gate。

### Allowed

- Read current README/TODO/plans and Round9 outputs.
- Create Round10 diagnostic/cache scripts.
- Inspect baseline predictions, GT, image files, metadata, and existing evaluator code.
- Generate cache sanity tables.

### Forbidden

- No training.
- No Slurm.
- No validation zip/upload.
- No fold1-4.
- No external repo or weight download.
- No modification of nnU-Net baseline cache.

### Outputs

- `round10_goal_execution_readme.md`
- `round10_cache_sanity.md`
- initial rows of `round10_cache_manifest.csv`

### Pass Criteria

- Baseline prediction files are located for fold0 validation and training-compatible cache construction.
- Fold0 split is confirmed.
- GT labels and compact label semantics are confirmed: `edema=4`, `scar=5`.
- Image channels and modality metadata are locatable.
- Round9 refiner safety gate is found and summarized.
- Baseline metrics are reproducible or linked to existing Round9/Round1 outputs.

### Fail Criteria

- Baseline predictions missing or stale.
- Case IDs cannot be matched across prediction/GT/image/metadata.
- Spacing/origin/direction mismatch cannot be handled.
- Label mapping ambiguity.
- Any cache construction would overwrite baseline paths.

### Next Stage

If pass, proceed to Phase 2. If fail, fix cache/reproducibility only; do not train.

## 7. Phase 2: `cached_refiner_dataset_construction`

### Goal

Generate the Round10 cached refiner dataset and manifest.

### Allowed

- Cache features and targets under the Round10 output root.
- Use existing baseline predictions/logits/probabilities if available.
- If logits/probabilities are unavailable, cache hard-label derived features and record information loss.
- Generate case-level sanity summaries and channel-order metadata.

### Forbidden

- Do not modify baseline predictions.
- Do not use official validation labels or validation pseudo-label supervised training.
- Do not write to nnU-Net preprocessed/results baseline folders.
- Do not silently resample without recording source/target geometry.

### Outputs

- `round10_cache_manifest.csv`
- `round10_cache_sanity.md`
- optional per-case cache files under `cache/`

### Pass Criteria

- Cache includes fold0 train/val rows with complete metadata.
- Feature channel order is documented.
- Target edema mask has expected values `{0,1}`.
- Scar/anatomy guardrail channels are present or explicitly marked unavailable.
- no-T2 empty-GT cases are correctly flagged.
- Cache sanity checks show no invalid labels or unresolved geometry mismatch.

### Fail Criteria

- Missing cases in train/val split.
- Feature/target shape mismatch.
- Unknown label values.
- Lost modality metadata.
- Baseline prediction modification risk.

### Next Stage

If pass, proceed to Phase 3.

## 8. Phase 3: `refiner_architecture_and_loss_gate`

### Goal

Implement a minimal refiner architecture and loss that can train class_4 correction while preserving baseline outputs.

### Allowed

- Create first-party refiner code under `src/care_myocardium/`.
- Create refiner diagnostics/training scripts under `scripts/diagnostics/` and `scripts/training/`.
- Use Candidate A or B first.
- Use residual clipping, fallback switch, and scar unchanged assertions.

### Forbidden

- Do not train whole nnU-Net.
- Do not modify class_5 scar output.
- Do not output full multiclass segmentation from the refiner.
- Do not use no-T2 empty-GT as dominant dense hard negative.
- Do not use external data or external repo modules.

### Loss Requirements

The loss should include:

- primary edema loss on T2-present GT-positive cases;
- weak no-T2 FP calibration or penalty;
- residual magnitude regularization;
- optional small boundary auxiliary only after initial safety passes;
- no class_5 loss because class_5 is not a refiner output.

### Outputs

- `round10_refiner_config.yaml`
- `round10_unit_gradient_smoke.csv`
- `round10_train_commands.txt`

### Pass Criteria

- import / py_compile pass.
- one-batch forward/backward pass.
- no NaN/Inf.
- residual clipping active and measured.
- fallback to baseline active and tested.
- class_5 scar unchanged after fusion.
- no-T2 empty-GT FP does not increase in smoke.

### Fail Criteria

- class_5 or anatomy labels change.
- residual magnitude saturates immediately.
- no-T2 FP appears in smoke.
- loss is unstable.
- label mapping or cache assumptions are ambiguous.

### Next Stage

If pass, proceed to Phase 4.

## 9. Phase 4: `tiny_overfit_and_safety_screen`

### Goal

Use a small selected set to verify that the refiner can learn edema correction without violating safety constraints.

### Required Tiny Set

Include at minimum:

- one CenterB complete T2-present GT-positive edema case;
- one CenterC complete T2-present GT-positive edema case;
- one LGE-only no-T2 empty-GT case;
- one C0+LGE no-T2 empty-GT case if available.

### Allowed

- Tiny crop/patch training.
- Several conservative candidate settings if cheap, but one selected candidate must be named before fold0 training.
- Generate overlays if lightweight.

### Forbidden

- No fold0 training if tiny gate fails.
- No full nnU-Net training.
- No fold1-4.
- No validation zip/upload.

### Outputs

- `round10_tiny_overfit_metrics.csv`
- `residual_magnitude_summary.csv`
- optional `failure_overlays/*.png`

### Pass Criteria

- T2-present edema has nonzero learning signal.
- CenterC selected case does not worsen component/remote FP in tiny screen.
- no-T2 empty-GT FP does not increase or remains below an explicitly tiny threshold.
- class_5 scar is exactly unchanged after fusion.
- residual magnitude remains within configured bounds.
- fallback baseline export works.

### Fail Criteria

- Dice improves but component/remote FP worsens in tiny cases.
- residual makes widespread class_4 changes.
- no-T2 cases gain edema FP.
- scar changes by any voxel.
- result depends only on empty-GT artifacts.

### Next Stage

If pass, proceed to Phase 5.

## 10. Phase 5: `bounded_fold0_refiner_training_ladder`

### Goal

Allow goal-mode to train the small refiner through staged fold0 gates. Because the refiner is smaller and baseline-preserving, it can move more aggressively than whole-network routes, but it still must not skip gates.

### Resource Stance

User token、Slurm、GPU 资源充足，goal-mode 可以尽可能多往前推进。但推进必须是：

```text
staged, gated, refiner-only, and baseline-preserving
```

Do not skip gates because resources are available.

### Training Ladder

1. fold0 very-short refiner train
2. fold0 short refiner train
3. fold0 longer refiner train
4. only if fold0 longer clean: prepare fold1-4 expansion plan, but do not execute fold1-4 without explicit user authorization

### Allowed

- Submit bounded `htzhulab` Slurm jobs after earlier gates pass.
- Train only the refiner.
- Use unique Round10 experiment/cache names.
- In one goal-mode run, continue to the next ladder rung only if the previous gate passes.

### Forbidden

- Do not train or fine-tune nnU-Net backbone.
- Do not modify baseline scar/anatomy predictions.
- Do not run fold1-4 or 5-fold.
- Do not create validation zip or upload.
- Do not train external repos.

### Outputs

- `round10_fold0_very_short_metrics.csv`
- `round10_fold0_short_train_metrics.csv`
- `round10_fold0_longer_train_metrics.csv`
- `round10_train_commands.txt`

### Pass Criteria

- Refiner exports predictions for all 44 fold0 validation cases at each rung.
- class_5 scar unchanged for every case.
- no-T2 empty-GT edema FP does not increase or stays below a strict tiny ceiling.
- T2-present GT-positive or CenterC complete-case edema has clean positive signal.
- HD95/component/remote FP do not regress.
- residual magnitude distribution remains bounded.

### Fail Criteria

- Any scar voxel changes.
- no-T2 FP increases materially.
- component/remote FP worsens.
- Dice-only gain with HD95 regression.
- residual magnitude saturates.
- cache/label/evaluator silent change.

### Next Stage

If fold0 very-short fails, stop candidate. If very-short passes, proceed to short. If short passes, proceed to longer. If longer passes, move to Phase 7 promotion decision.

## 11. Phase 6: `evaluation_and_refiner_decision_gate`

### Goal

Evaluate refiner outputs with baseline preservation as a hard gate.

### Required Subsets

Report separately:

- all-case
- T2-present GT-positive
- complete-modality
- CenterB
- CenterC
- no-T2 empty-GT
- C0+LGE no-T2
- LGE-only
- center groups
- modality groups

### Required Metrics

For `myops_edema` class_4:

- Dice
- HD
- HD95
- component count
- small FP
- remote FP
- pred/GT volume ratio
- no-T2 edema FP voxel count
- no-T2 edema FP case count
- baseline-vs-refiner edema delta

For `myops_scar` class_5:

- exact unchanged check by case;
- Dice/HD/HD95 can be copied or reported as unchanged guardrail, but any voxel change is fail.

Refiner-specific:

- residual magnitude distribution;
- clipped residual fraction;
- changed voxel count;
- changed component count;
- overlay summary;
- case-level failure flags.

### Outputs

- `baseline_vs_refiner_by_subset.csv`
- `no_t2_empty_gt_fp_table.csv`
- `centerB_centerC_edema_table.csv`
- `scar_unchanged_guardrail_table.csv`
- `residual_magnitude_summary.csv`
- `case_level_failure_flags.csv`
- `round10_decision_table.md`
- `round10_next_actions.md`

### Pass Criteria

- class_5 scar unchanged for every case.
- no-T2 empty-GT edema FP does not increase or remains below a predeclared tiny threshold.
- T2-present GT-positive edema or CenterC complete-case edema has clean positive signal.
- HD95/component/remote FP do not clearly worsen.
- improvement is not from empty-GT artifact or all-case aggregate only.
- residual does not rewrite baseline over large regions.

### Fail Criteria

- Any scar change.
- Dice improves but HD95/component worsens.
- no-T2 FP increases.
- CenterC does not improve or becomes less clean.
- residual saturates or creates remote components.
- result depends only on empty-GT behavior.

### Watch Criteria

- CenterB improves but CenterC is flat or mixed.
- Dice improves but HD95 is exactly flat and components are neutral.
- no-T2 guardrail is clean but positive edema gain is too small.

Watch candidates may get one conservative feature/loss adjustment but must not expand to fold1-4.

## 12. Phase 7: `promotion_and_next_route_decision`

### Decision Table

| route outcome | decision | next action |
| --- | --- | --- |
| refiner cleanly improves T2-present or CenterC edema and all guardrails pass | `go` | proceed to fold0 longer or prepare fold1-4 expansion plan |
| refiner improves CenterB only but CenterC is mixed | `watch` | add feature/loss audit, no expansion |
| refiner is safe but weak | `watch_refine_features` | try T2 intensity prior, anatomy support feature, or small boundary auxiliary |
| refiner improves Dice but worsens HD95/component/remote FP | `fail_stop_candidate` | stop current refiner |
| refiner changes scar or baseline anatomy | `fail_safety` | stop refiner route until fusion is fixed |
| first-party refiner is unsafe after repair attempts | `postpone_refiner_route` | consider controlled external method readiness |

### Promotion Constraints

Even with a `go`, Round10 does not authorize:

- validation zip;
- upload;
- fold1-4 execution;
- 5-fold training;
- full external repo training.

These require explicit user authorization or a later plan.

### Future Positive-Signal Path

If refiner has strong signal:

- keep it as a final package postprocess/refinement branch only after validation-packaging authorization;
- consider distilling the refiner correction back into a future nnU-Net-like model;
- prepare fold1-4 expansion plan with cache isolation and scar unchanged QA.

If refiner has no clean signal but remains safe:

- add T2 intensity prior feature inspired by I-MMSeg;
- add anatomy support feature inspired by Cascaded FSN/PT-Net;
- add small boundary auxiliary inspired by InverseForm/surface loss;
- still keep all implementation first-party and CARE-only.

## 13. Implementation Targets For Next Goal-Mode

Suggested files for execution pass:

- `src/care_myocardium/refiner/laneA_round10_dataset.py`
- `src/care_myocardium/refiner/laneA_round10_model.py`
- `src/care_myocardium/refiner/laneA_round10_fusion.py`
- `scripts/diagnostics/laneA_round10_cache_refiner_dataset.py`
- `scripts/diagnostics/laneA_round10_refiner_smoke.py`
- `scripts/diagnostics/laneA_round10_refiner_eval.py`
- `scripts/training/run_laneA_round10_refiner_train.py`
- `jobs/nnUNet/laneA_round10_refiner_fold0_very_short.sh`
- `jobs/nnUNet/laneA_round10_refiner_fold0_short.sh` only if very-short passes

If reusing Round9 `EdemaResidualRefiner`, keep imports explicit and do not mutate Round9 output directories.

## 14. Next Goal Execution Prompt Draft

```text
你现在在 `/overflow/htzhu/CARE` 中工作。请执行 Lane A Round10：

`docs/plans/laneA_round10_next_edema_only_residual_refiner_execution.md`

目标是尽可能推进 edema-only residual refiner / baseline-preserving correction。不要创建 validation zip，不要上传，不要跑 fold1-4 或 5-fold，除非 fold0 gates 全部通过且我另行授权。不要下载权重，不要拉取外部 repo，不要使用 external data training，不要用 validation pseudo-label supervised training。不要训练或 fine-tune whole nnU-Net backbone。

请先执行 Phase 1：复核 nnU-Net501 fold0 baseline predictions、fold split、label semantics、evaluator、spacing/origin、modality metadata 和 Round9 refiner safety gate。若路径或 label mapping 不一致，只修 cache/reproducibility，不进入训练。

若 Phase 1 通过，请执行 Phase 2：在

`results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner/`

下构建 cached baseline refiner dataset。缓存必须记录 baseline prediction/logit/prob source、image modalities、GT edema mask、scar/anatomy guardrail labels、center、modality group、T2-present flag、no-T2 empty-GT flag、spacing/origin/direction、feature channel order 和 label set。不得污染 nnU-Net baseline cache。

若 cache gate 通过，请实现 Candidate A conservative logit residual refiner 和/或 Candidate B binary edema correction refiner。Refiner 只能输出 class_4 edema correction；class_5 scar 和 baseline anatomy 必须 unchanged。必须有 residual clipping、fallback-to-baseline、scar unchanged assertion、no-T2 FP safety check。

然后按 staged ladder 推进：unit/gradient smoke -> tiny-overfit safety screen -> fold0 very-short refiner train -> fold0 short refiner train -> fold0 longer refiner train。资源充足，可以在一个 goal-mode run 中尽可能推进，但每一阶段必须 gate；任一 gate fail 即停止该 candidate，不得自动扩大规模。

评估必须报告 `myops_edema` class_4 和 `myops_scar` class_5 guardrail，包含 all-case、T2-present GT-positive、complete-modality、CenterB、CenterC、no-T2 empty-GT、C0+LGE no-T2、LGE-only、center/modality subsets。必须报告 Dice、HD、HD95、component count、small/remote FP、pred/GT volume ratio、no-T2 edema FP voxel/case count、scar unchanged check、baseline-vs-refiner delta、residual magnitude distribution、case-level failure flags 和 overlay summary。不要用 foreground mean 或 all-case aggregate 掩盖失败。

最终更新 `round10_decision_table.md` 和 `round10_next_actions.md`，给出 `go/watch/fail/stop/postpone` 结论。仍禁止 validation submission、fold1-4、5-fold、外部 repo full training，除非用户另行授权。
```
