# Lane A Round09 Next Baseline-Initialized Edema Adaptation Execution Plan

Plan metadata:
- Type: next/planned round execution
- Lane: Lane A, MyoPS scar/edema
- Round scope: Round09
- Status: next goal-mode controller, planning-only artifact
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: `docs/plans/laneA_round08_next_t2_present_edema_expert_separated_head_execution.md`
- Function: define a staged, gated Round9 route that preserves the nnU-Net501 fold0 baseline representation while testing modality-aware / T2-present edema adaptation
- Do not: execute experiments from this plan-writing pass; do not train; do not submit Slurm; do not create validation zip; do not upload; do not download weights; do not clone or train external repos; do not modify production code while creating this plan

## 1. 当前证据链和阶段判断

Lane A 的结论必须按 Round2-Round8 的连续证据来解释，不能只看某一轮单表。

1. **Round2: edema inference postprocess route fail.** 小连通域删除和 ROI 阈值不能作为主线。删除 1-voxel edema 小岛后 component count 下降，但 GT-positive edema Dice 略降、HD95 略恶化，说明真实瓶颈不在简单 inference cleanup。
2. **Round3: loss wiring / gradient / tiny-overfit smoke pass, not performance proof.** `edema_focal_tversky`、`no_t2_edema_loss_downweighting` 等能跑通，只证明工程链路和 loss 梯度可用。
3. **Round4: `edema_focal_tversky + no_t2_edema_loss_downweighting` fold0 short train fail.** 真实 fold0 short train 出现 remote FP、no-T2 FP、HD95 恶化和 scar guardrail 不干净，因此不能继续围绕单一 Focal Tversky / scalar downweighting 微调。
4. **Round5: mechanism audit.** Alignment 为 `watch`，boundary/distance 为 `watch`，anatomy soft prior 进入 bounded diagnostic；这提供机制方向，但没有支持 hard ROI 或 postprocess 主线。
5. **Round6: anatomy soft attenuation fail; missing-modality route go/watch.** 当前 anatomy soft prior 不能扩展；missing-modality audit 指出 no-T2 empty-GT 不能当强 negative，explicit modality presence 和 uncertainty-aware supervision 是下一步信号。
6. **Round7: 6-channel modality-presence pipeline 可行，但简单 presence channels + scalar no-T2 weighting 不过 tiny gate。** U1 太弱，没有 T2-positive edema signal；U2 有 edema signal，但引入 no-T2 empty-GT FP。Round7 不能进入 fold0 training。
7. **Round8: T2-present edema expert / separated edema supervision tiny gate 有信号，但 scratch / near-scratch very-short fold0 train 全面崩溃。** Round8 复用了 6-channel pipeline，tiny-overfit 通过，并在用户明确批准后完成单个 bounded `htzhulab` fold0 very-short job。该 job 只跑了极短预算，验证链路成功导出 44/44 fold0 validation predictions，但 gate 为 `fail_stop_no_longer_train`：T2-present edema、CenterC edema、HD95/component/remote FP 和 scar guardrail 均大幅差于已有完整 nnU-Net501 fold0 baseline。

Round8 的准确解释：

- Round8 **没有证明** “T2-present edema expert / separated edema route 最终失败”。
- Round8 证明的是：**从 scratch 或 near-scratch 用极短预算训练一个改结构模型，不能保留 nnU-Net501 已学到的 anatomy/scar 表征，也不能公平地和完整 nnU-Net501 baseline 比最终性能。**
- 因此不应继续直接把当前 Round8 scratch candidate 扩到 fold0 short/longer、fold1-4、5-fold 或 validation submission。

Round9 的核心战略切换：

```text
baseline-preserving adaptation
```

也就是从已有 nnU-Net501 fold0 checkpoint 初始化，尽量保留 backbone / decoder / scar / anatomy 表征，只在 edema route、modality conditioning、no-T2 supervision policy 或轻量 refiner 上做增量适配。

Round9 要回答的问题不是“一个从零训练的新模型能不能超过完整 nnU-Net”，而是：

```text
在不丢掉 nnU-Net 已学到的表征和 scar guardrail 的前提下，Round7/Round8 的 modality-aware / T2-present edema expert 思想是否能改善 edema？
```

## 2. 明确停止和继续的路线

停止或不得作为 Round9 主线：

- 不继续 Round8 scratch / near-scratch candidate 直接增大 epoch。
- 不继续 U1/U2 scalar no-T2 weighting 周边微调。
- 不回到 Focal Tversky 主导训练。
- 不回到 small-component deletion、ROI threshold、hard ROI deletion、hard anatomy attenuation。
- 不直接接入完整 AdaMM、UniME、CoPeDiT、MoE、I-MMSeg、BiomedParse 或 diffusion/harmonization。
- 不创建 validation zip、不上传、不跑 fold1-4 或 5-fold，除非后续 fold0 longer gate 通过且用户另行授权。

Round9 可以继续的机制：

- 复用 Round7/Round8 的 6-channel modality presence 基础设施。
- 复用 Round8 的 class_4 edema supervision 分离思想，但必须从 baseline checkpoint 初始化或以 baseline refiner 形式实现。
- no-T2 cases 继续避免被当成 class_4 dense hard negative。
- class_5 scar 必须作为硬 guardrail；任何 adaptation 不得破坏 scar。

## 3. 输出根目录和必须隔离的实验名

Round9 所有输出统一放在：

```text
results/diagnostics/care_myocardium/laneA_myops/round09_baseline_initialized_adaptation/
```

建议输出文件至少包括：

- `round9_goal_execution_readme.md`
- `round9_failure_audit.md`
- `round9_failure_audit_case_table.csv`
- `round9_checkpoint_loader_audit.md`
- `round9_checkpoint_key_report.csv`
- `round9_initial_inference_baseline_reproduction.csv`
- `round9_train_config_checkpoint_initialized.yaml`
- `round9_train_config_edema_refiner.yaml`
- `round9_train_commands.txt`
- `round9_unit_gradient_smoke.csv`
- `round9_tiny_overfit_metrics.csv`
- `round9_fold0_very_short_metrics.csv`
- `round9_fold0_short_train_metrics.csv`
- `round9_fold0_longer_train_metrics.csv`
- `baseline_vs_candidate_by_subset.csv`
- `no_t2_empty_gt_fp_table.csv`
- `centerB_centerC_edema_table.csv`
- `scar_guardrail_table.csv`
- `case_level_failure_flags.csv`
- `round9_decision_table.md`
- `round9_next_actions.md`

Optional overlays:

```text
results/diagnostics/care_myocardium/laneA_myops/round09_baseline_initialized_adaptation/failure_overlays/
```

Suggested isolated experiment names:

- Checkpoint-initialized 6-channel fine-tune:

```text
laneA_r9_ckptinit_6ch_edema_adapt_fold0_<budget>
```

- Edema-only residual refiner:

```text
laneA_r9_edema_residual_refiner_fold0_<budget>
```

These names must not overwrite:

- `nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres`
- `nnUNetTrainer__nnUNetPlans__3d_fullres`
- `laneA_edema_focal_tversky_t2down_fold0_short__nnUNetPlans__3d_fullres`
- `laneA_t2_edema_expert_sephead_fold0_short__nnUNetPlans__3d_fullres`
- any Round7/Round8 diagnostic outputs

## 4. 主路线 1: `nnUNet501_checkpoint_initialized_6channel_finetune`

### Goal

把 Round7/Round8 的 6-channel modality-presence input 和 separated edema supervision 迁移到一个由 nnU-Net501 fold0 checkpoint 初始化的模型上，而不是从 scratch 训练。这个路线的关键 gate 是：**初始化后必须尽可能复现 baseline，不得先把 baseline 表征打碎再指望训练修回来。**

### Baseline Assets

Current known candidate baseline checkpoint paths include:

```text
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth
```

Preferred initial source:

```text
checkpoint_best.pth
```

The exact checkpoint used must be recorded in `round9_train_config_checkpoint_initialized.yaml` and `round9_checkpoint_loader_audit.md`.

### 3-Channel To 6-Channel Weight Migration

The existing nnU-Net501 baseline was trained on the original image channels. Round7/Round8 use 6 input channels:

```text
original image channels + C0_present + LGE_present + T2_present
```

The loader must:

1. Build the Round9 6-channel network using the same plans/configuration as Round7/Round8.
2. Locate the first convolution weight in the checkpoint and in the 6-channel model.
3. Copy the original image-channel weights from the baseline checkpoint into the corresponding original image channels of the Round9 model.
4. Initialize the added modality-presence channel weights to `0` or a very small value.
5. Load all other compatible backbone / decoder / segmentation head weights from nnU-Net501 checkpoint.
6. Record missing keys, unexpected keys, shape-mismatch keys, loaded key ratio, and strict/non-strict loading rules.

The plan does not assume the first conv key name. The implementation must discover it by shape and module traversal, then record it explicitly.

### Initial Inference Reproduction Requirement

Before training, the checkpoint-initialized 6-channel model must run validation/export smoke on a tiny fixed case set and compare against baseline predictions. Candidate predictions should be close to baseline when modality-presence channels are constant and extra-channel weights are zero.

Minimum cases:

- one CenterB complete T2-present GT-positive edema case
- one CenterC complete T2-present GT-positive edema case
- one CenterA or CenterH LGE-only no-T2 empty-GT case
- one C0+LGE no-T2 empty-GT case if available in fold0

Baseline reproduction must report:

- per-class volume delta for classes 1-5
- edema component count and FP voxels
- scar Dice / HD95 versus baseline prediction
- case-level label histogram
- whether affine/spacing/origin match

If initial predictions are not baseline-like, do not train. Fix loader/channel order first.

### Training Policy

After loader and initial inference gates pass:

- Use low learning rate relative to scratch Round8.
- Consider freezing or partial-freezing early encoder for the first smoke.
- Keep class_5 scar supervised and monitored.
- Keep no-T2 class_4 from becoming dense hard negative.
- Do not alter label semantics or evaluator.

Suggested first candidate:

```text
ckptinit_6ch_A1_lowlr_separated_edema
```

Candidate behavior:

- T2-present / complete cases: strong class_4 edema supervision plus standard non-edema classes.
- no-T2 cases: non-edema classes and class_5 scar remain supervised; class_4 receives no dense hard negative or only very weak calibration.
- Extra modality channels initialized inertly, so initial state is baseline-preserving.

## 5. 主路线 2: `edema_only_residual_refinement_module`

### Goal

训练一个轻量 edema correction / refinement module，而不是直接改动 nnU-Net501 主 segmentation backbone。该路线优先保护 scar 和 baseline anatomy：scar 始终来自 baseline 或不被 refiner 修改。

### Input Options

Refiner 输入可以包括：

- baseline nnU-Net501 class probabilities or logits
- baseline class_4 edema probability/logit
- T2 image and LGE image
- modality presence mask
- optional myocardium probability, LV/RV probability, or soft distance support
- optional center/modality metadata only for reporting or conditioning, not as hidden shortcut without audit

### Output And Fusion

The refiner output should be restricted to class_4 edema:

- binary edema residual correction
- edema probability calibration
- conservative edema mask refinement

Inference fallback must be explicit:

- if refiner gate fails, export baseline edema unchanged;
- scar class_5 remains baseline scar;
- anatomy classes remain baseline anatomy unless a specific audited fusion rule says otherwise.

### Risk Comparison

Compared with checkpoint-initialized 6-channel fine-tune:

- **Refiner is safer** because it can preserve scar and most anatomy by construction.
- **Refiner may have lower upside** because it corrects baseline output rather than learning a fully integrated representation.
- Refiner is the preferred promotion route if it shows clean edema gains without scar risk.

### Required Smoke

Before any fold0 training:

- one-case forward
- gradient smoke
- baseline fallback smoke
- export/label mapping smoke
- fusion smoke confirming class_5 prediction is bitwise unchanged when refiner is class_4-only

If a refiner changes class_5 or class labels unexpectedly, stop and fix before training.

## 6. 预备路线: `catastrophic_failure_audit_and_engineering_sanity`

### Goal

解释 Round8 全面崩溃的直接原因，避免把工程/初始化/预算问题误判为机制失败。This audit must run before any Round9 training.

### Required Audit Items

Use existing Round8 predictions, baseline predictions, logs, configs, and evaluator outputs to check:

- prediction label histogram by case
- per-class predicted volume and pred/GT volume ratio
- class_4/class_5 component count, small FP, remote FP
- spacing/origin/affine consistency between GT, baseline prediction, Round8 prediction
- class_4/class_5 logits or probability summary if available
- baseline-vs-Round8 overlays for selected severe failures
- checkpoint initialization status for Round8: confirm whether it was scratch/near-scratch
- loss curve and epoch/iteration budget
- train/export channel order
- validation channel injection
- evaluator class mapping: `edema=4`, `scar=5`
- cache/output path isolation

### Interpretation Rules

- If label mapping, channel order, affine/spacing, export, evaluator, or cache bug is found, fix engineering and rerun sanity before any model conclusion.
- If no obvious engineering bug is found, treat Round8 as evidence that scratch very-short training destroyed baseline representation, and proceed to baseline-initialized adaptation.

## 7. Phase 1: `round9_failure_audit_and_baseline_reproducibility_gate`

### Goal

Run Round8 catastrophic failure audit and confirm nnU-Net501 fold0 baseline, fold split, label semantics, evaluator, cache, and prediction export are reproducible.

### Allowed

- Create Round9 diagnostic scripts under `scripts/diagnostics/`.
- Read existing baseline/Round8 predictions and existing fold0 GT.
- Read nnU-Net501 fold0 checkpoint and validation predictions.
- Generate CSV/MD audit tables and optional overlays.
- Confirm fold0 split and modality/center metadata.

### Forbidden

- No training.
- No Slurm submission.
- No validation zip/upload.
- No fold1-4.
- No external repo/weight download.
- No label/evaluator/preprocessing silent change.

### Outputs

- `round9_goal_execution_readme.md`
- `round9_failure_audit.md`
- `round9_failure_audit_case_table.csv`
- optional `failure_overlays/*.png`

### Pass Criteria

- Baseline prediction path and checkpoint path are identified.
- Existing baseline metrics and Round8 metrics are reproducible or explainably matched.
- Label semantics are confirmed: `edema=4`, `scar=5`.
- Round8 failure is not explained by obvious evaluator/export/affine/channel-order/cache bug.
- Fold0 split and 44 validation cases are confirmed.

### Fail Criteria

- Baseline path is missing or stale.
- Round8 predictions have affine/spacing/label/export bug.
- Evaluator mapping differs from expected labels.
- Cache contamination is detected.
- Round8 failure is an engineering bug requiring repair before any adaptation.

### Next Stage

If pass, proceed to Phase 2. If fail due engineering, fix the specific engineering issue and rerun this phase; do not train.

## 8. Phase 2: `checkpoint_initialized_6channel_loader_gate`

### Goal

Implement and verify nnU-Net501 checkpoint to 6-channel Round9 model migration.

### Allowed

- Add first-party Round9 trainer/loader code under `src/care_myocardium/nnunet/`.
- Reuse Round7/Round8 modality channel injection helpers.
- Add checkpoint loader smoke in `scripts/diagnostics/`.
- Generate one or more no-training initial inference predictions in an isolated diagnostic directory.

### Forbidden

- No training until loader and initial inference pass.
- Do not overwrite baseline checkpoint or baseline validation predictions.
- Do not alter nnU-Net501 baseline plans/preprocessed cache.
- Do not use external pretrained weights other than existing CARE-trained nnU-Net501 checkpoint.

### Outputs

- `round9_checkpoint_loader_audit.md`
- `round9_checkpoint_key_report.csv`
- `round9_initial_inference_baseline_reproduction.csv`
- `round9_train_config_checkpoint_initialized.yaml`

### Required Report Fields

`round9_checkpoint_key_report.csv` should include:

- `key`
- `checkpoint_shape`
- `model_shape`
- `status`: `loaded`, `missing`, `unexpected`, `shape_mismatch`, `expanded_first_conv`
- `notes`

`round9_checkpoint_loader_audit.md` should include:

- source checkpoint path
- first conv key name
- old channel count
- new channel count
- original image-channel copy rule
- modality channel initialization rule
- total keys loaded / total model keys
- strict or non-strict loading mode
- any skipped keys and why

### Pass Criteria

- 6-channel model initializes.
- First convolution uses copied baseline weights for original image channels.
- Added modality presence channel weights are zero or near-zero initialized.
- All non-input compatible weights load from nnU-Net501 checkpoint.
- Initial inference is baseline-like:
  - class_5 scar does not collapse;
  - major anatomy volumes are close to baseline;
  - class_4 no-T2 FP does not explode;
  - label histogram is plausible.

### Fail Criteria

- First conv migration cannot be verified.
- Loaded key ratio is low for non-input layers.
- Initial predictions differ massively from baseline before training.
- class_5 scar collapses in initial inference.
- Channel order cannot be proven.

### Next Stage

If pass, proceed to Phase 3 and/or Phase 4. If fail, repair loader before any training.

## 9. Phase 3: `edema_refiner_baseline_preserving_gate`

### Goal

Design and smoke-test an edema-only residual refiner as a lower-risk alternative to whole-network fine-tuning.

### Allowed

- Add small first-party refiner module under `src/care_myocardium/` or `src/care_myocardium/nnunet/`.
- Add diagnostic/refiner smoke scripts.
- Use existing baseline predictions/logits/probabilities if available.
- If logits are unavailable, use prediction masks plus images only for initial compatibility smoke and record the limitation.

### Forbidden

- Do not modify class_5 scar prediction.
- Do not alter baseline predictions in place.
- Do not use validation pseudo-label supervised training.
- Do not train refiner on external data.
- Do not add heavy foundation model dependencies.

### Outputs

- `round9_train_config_edema_refiner.yaml`
- `round9_unit_gradient_smoke.csv`
- optional refiner compatibility rows in `round9_failure_audit_case_table.csv`

### Pass Criteria

- One-case forward/backward works.
- Refiner fusion changes only class_4 edema or a documented edema probability field.
- class_5 scar output is unchanged by construction.
- Fallback-to-baseline path is implemented and tested.
- Exported labels remain valid.

### Fail Criteria

- Refiner changes class_5 or labels 1/2/3 unexpectedly.
- Fusion rule introduces invalid labels.
- Refiner cannot consume baseline outputs without brittle assumptions.
- Refiner requires external data or validation pseudo-label training.

### Next Stage

If pass, refiner may enter the training ladder as a second candidate. If both Phase 2 and Phase 3 pass, prioritize the safer candidate first unless the implementation burden is clearly lower for checkpoint-initialized fine-tune.

## 10. Phase 4: `bounded_training_ladder`

### Goal

Allow goal-mode to make meaningful progress, including training, but only through staged, baseline-preserving gates.

### Resource Stance

User token、Slurm、GPU 资源充足，goal-mode 可以尽可能多往前推进。但推进方式必须是:

```text
staged, gated, and baseline-preserving
```

Do not skip gates because resources are available.

### Training Ladder

1. **import / py_compile / config smoke**
   - no training
   - verify scripts import and configs are written
2. **checkpoint loader smoke**
   - no training
   - verify key migration and initial model state
3. **initial inference baseline-reproduction smoke**
   - no training or only exact checkpoint inference
   - compare candidate initial predictions to baseline
4. **one-batch forward + backward**
   - tiny runtime
   - record loss values, gradient norm, NaN/Inf, class_4/class_5 gradient signals
5. **tiny-overfit**
   - selected T2-present CenterB/CenterC edema-positive cases plus selected no-T2 empty-GT cases
   - confirm edema signal without no-T2 FP explosion or scar collapse
6. **fold0 very-short train**
   - one bounded job, htzhulab preferred
   - very small epoch/iteration budget
   - export 44/44 fold0 validation predictions only if training completes cleanly
7. **fold0 short train**
   - only if very-short gate passes
   - still bounded, unique experiment name
8. **fold0 longer train**
   - only if short train shows clean signal and baseline preservation
   - still no fold1-4 unless explicitly authorized later
9. **fold1-4 expansion plan**
   - only if fold0 longer is clean
   - prepare plan; do not submit folds or validation without explicit user authorization

### Allowed

- In one goal-mode run, continue through multiple stages if each preceding gate passes.
- Submit bounded `htzhulab` jobs only after non-training gates pass and only for the current candidate.
- Use a single candidate at a time unless the user explicitly asks for parallel candidates.

### Forbidden

- Do not jump from loader smoke directly to fold0 long train.
- Do not train multiple candidates at once by default.
- Do not run fold1-4, 5-fold, validation zip, or submission.
- Do not use foreground mean as the success criterion.
- Do not use external data or validation pseudo-label supervised training.

### Outputs

- `round9_train_commands.txt`
- `round9_unit_gradient_smoke.csv`
- `round9_tiny_overfit_metrics.csv`
- `round9_fold0_very_short_metrics.csv`
- `round9_fold0_short_train_metrics.csv`
- `round9_fold0_longer_train_metrics.csv`

### Pass Criteria

For any candidate to advance:

- No NaN/Inf.
- No cache/output collision.
- Initial state preserves baseline if candidate is checkpoint-initialized.
- Tiny-overfit shows T2-present edema signal.
- no-T2 empty-GT class_4 FP remains bounded.
- scar class_5 does not collapse.
- Fold0 metrics show clean positive signal in T2-present GT-positive edema or CenterC complete-case edema.

### Fail Criteria

- Any training instability.
- Initial baseline reproduction fails.
- Dice improves but HD95/component/remote FP clearly worsen.
- scar guardrail degrades.
- no-T2 edema FP becomes uncontrolled.
- gains come only from empty-GT artifacts.
- evaluator/label/cache changes silently.

### Next Stage

If a candidate passes its current training stage, proceed to Phase 5 evaluation for promotion decision. If it fails, stop that candidate and record `stop` or `watch`; do not automatically enlarge.

## 11. Phase 5: `evaluation_and_non_regression_gate`

### Goal

Evaluate candidates with “do not lose baseline” as a first-class requirement.

### Required Subsets

Report all metrics separately for:

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

For `myops_scar` class_5:

- Dice
- HD
- HD95
- component count as guardrail when available
- pred/GT volume ratio as guardrail when available

For baseline preservation:

- baseline reproduction delta
- candidate-vs-baseline per-class volume delta
- candidate-vs-baseline overlay summary
- case-level failure flags

### Outputs

- `baseline_vs_candidate_by_subset.csv`
- `no_t2_empty_gt_fp_table.csv`
- `centerB_centerC_edema_table.csv`
- `scar_guardrail_table.csv`
- `case_level_failure_flags.csv`
- `round9_decision_table.md`
- `round9_next_actions.md`

### Pass Criteria

A candidate may be promoted only if:

- Initial baseline reproduction gate passed.
- class_5 scar Dice/HD95 does not clearly regress.
- major anatomy / prediction volume does not collapse.
- T2-present GT-positive edema or CenterC complete-case edema has a clean positive signal.
- Dice and HD95 are not in a severe trade-off.
- component count and remote FP do not clearly worsen.
- no-T2 empty-GT edema FP remains under a strict low ceiling.
- improvement is not driven by empty-GT artifact.
- conclusions are not based on foreground mean or all-case aggregate alone.

Suggested no-T2 FP ceiling for Round9 smoke:

- no-T2 empty-GT FP case count should be `0` for very-short / tiny gates where possible.
- If not zero, it must be lower than or equal to the baseline-compatible ceiling defined in the evaluator and must not include large remote components.
- Any no-T2 FP increase must be explicitly justified by a much stronger T2-present edema gain and marked `watch`, not `go`, unless a later gate cleans it.

### Fail Criteria

- Initial candidate cannot reproduce baseline-like outputs.
- class_5 scar Dice/HD95 clearly regresses.
- T2-present GT-positive edema and CenterC do not improve.
- HD95/component/remote FP worsen even if Dice improves.
- no-T2 empty-GT FP becomes uncontrolled.
- result only looks good in all-case aggregate.
- label/evaluator/cache/preprocessing changes are required to explain the result.

## 12. Phase 6: `promotion_and_next_route_decision`

### Goal

Decide whether Round9 should promote, watch, postpone, or stop each route.

### Decision Logic

Use this decision table:

| route | gate result | decision | next action |
| --- | --- | --- | --- |
| checkpoint-initialized 6-channel fine-tune | baseline reproduction pass + clean edema signal + scar guardrail clean | `go` | proceed to fold0 longer train, then prepare fold1-4 expansion plan only after another clean gate |
| checkpoint-initialized 6-channel fine-tune | baseline reproduction pass + mixed edema/scar signal | `watch` | adjust minimal policy or LR/freeze schedule once; do not expand |
| checkpoint-initialized 6-channel fine-tune | baseline reproduction fail | `stop_engineering` | fix loader/channel/init; no training conclusion |
| edema-only residual refiner | class_4 improvement + class_5 unchanged | `go` | prioritize refiner as safer route |
| edema-only residual refiner | edema signal weak but scar protected | `watch` | consider limited refiner tuning |
| edema-only residual refiner | label/fusion/scar risk | `stop` | do not expand |
| both first-party baseline-preserving routes fail with clean engineering | no clean positive signal | `postpone_first_party_route` | move to controlled external method readiness |

### Promotion Constraints

Even if a candidate gets `go`, Round9 by itself does not authorize:

- validation zip
- upload
- fold1-4
- 5-fold
- external repo full training

Those require a new user authorization or a later plan.

## 13. Controlled External Method Readiness

External methods are not Round9 first-pass targets. They become relevant only if:

- baseline-preserving first-party adaptation has a positive signal and needs a stronger implementation, or
- first-party baseline-preserving adaptation fails with clean engineering and the mechanism needs an external method slot.

Mechanism slots:

| method family | mechanism slot | Round9 status |
| --- | --- | --- |
| AdaMM / UniME / CoPeDiT / MoE / MMPL-Seg | missing-modality routing, student-teacher, modality-conditioned representation | watch / future metadata audit only |
| I-MMSeg | modality/intensity prior for edema/scar | watch / future metadata audit only |
| CAA-Seg / SSA | multi-sequence alignment | watch |
| Cascaded FSN / PT-Net | anatomy-guided prior | watch |
| InverseForm / surface loss / HD loss | boundary / HD objective | watch |
| BiomedParse / MedNeXt / nnU-Net Task114/M&Ms | pretrained backbone | watch |

Before any external repo enters training, it must pass:

- license/compliance audit
- pretrained data source audit
- external data risk audit under CARE rule: pretrained weights may be usable, external training datasets are not
- input-output shape audit
- label mapping audit: `edema=4`, `scar=5`
- one-case smoke
- fold0 smoke

Do not clone/train all repos indiscriminately. Do not use external data training or validation pseudo-label supervised training.

## 14. Implementation Files For Next Goal-Mode

Suggested files to create or update in the next execution pass:

- `src/care_myocardium/nnunet/laneA_round9_trainer.py`
- `src/care_myocardium/nnunet/laneA_round9_checkpoint_loader.py`
- `src/care_myocardium/nnunet/laneA_round9_refiner.py` if refiner route is implemented
- `scripts/diagnostics/laneA_round9_failure_audit.py`
- `scripts/diagnostics/laneA_round9_checkpoint_loader_smoke.py`
- `scripts/diagnostics/laneA_round9_initial_inference_eval.py`
- `scripts/diagnostics/laneA_round9_fold0_eval.py`
- `scripts/training/run_laneA_round9_nnunet_train.py`
- `jobs/nnUNet/laneA_round9_fold0_very_short_train.sh` only after non-training gates pass
- `jobs/nnUNet/laneA_round9_fold0_short_train.sh` only after very-short gate passes

Use `htzhulab` by default for bounded GPU jobs. Keep the Slurm logging style used by existing CARE jobs.

## 15. Next Goal Execution Prompt Draft

```text
你现在在 `/overflow/htzhu/CARE` 中工作。请执行 Lane A Round9：

`docs/plans/laneA_round09_next_baseline_initialized_edema_adaptation_execution.md`

目标是尽可能推进 baseline-preserving edema adaptation，但必须 staged/gated。不要创建 validation zip，不要上传，不要跑 fold1-4 或 5-fold，除非 fold0 gates 全部通过且我另行授权。不要下载权重，不要拉取外部 repo，不要使用 external data training，不要用 validation pseudo-label supervised training。

请先执行 Phase 1：Round8 catastrophic failure audit 和 baseline reproducibility gate。确认 Round8 崩溃不是 label/export/evaluator/cache/channel-order bug，确认 nnU-Net501 fold0 baseline checkpoint/predictions、fold split、label semantics、evaluator 和输出路径都正确。输出到：

`results/diagnostics/care_myocardium/laneA_myops/round09_baseline_initialized_adaptation/`

若 Phase 1 通过，请执行 Phase 2：实现 nnU-Net501 checkpoint 到 6-channel Round9 model 的 loader。要求原始图像通道权重从 baseline checkpoint 复制，新增 `C0_present/LGE_present/T2_present` 通道权重初始化为 0 或极小值，其余兼容 backbone/decoder/head 权重尽量加载。生成 key report、loader audit 和 initial inference baseline reproduction table。若 initial predictions 不能接近 baseline，停止并修 loader，不训练。

若 loader gate 通过，请实现或 smoke Phase 3 的 edema-only residual refiner，至少确认 one-case forward/backward、fallback-to-baseline、class_5 scar bitwise unchanged 或不受影响。如果 refiner 风险更低且能通过 smoke，可作为第二候选。

训练只允许通过 Phase 4 ladder 自动推进：import/py_compile/config smoke -> checkpoint loader smoke -> initial inference reproduction -> one-batch forward/backward -> tiny-overfit -> fold0 very-short train -> fold0 short train -> fold0 longer train。每一阶段必须写 command、config、random seed、experiment name、output dir、epoch/iteration budget、metrics 和 gate decision。任一 gate fail 即停止该 candidate，不得自动扩大训练。

评估必须按 Phase 5 报告 `myops_edema` class_4 和 `myops_scar` class_5，包含 all-case、T2-present GT-positive、complete-modality、CenterB、CenterC、no-T2 empty-GT、C0+LGE no-T2、LGE-only、center/modality subsets。必须报告 Dice、HD、HD95、component count、small/remote FP、pred/GT volume ratio、no-T2 edema FP voxel/case count、scar guardrail、baseline reproduction delta 和 case-level failure flags。不要使用 foreground mean 或 all-case aggregate 掩盖失败。

资源充足时可以在一个 goal-mode run 中尽可能推进多个阶段，但推进方式必须 staged, gated, and baseline-preserving。最终更新 `round9_decision_table.md` 和 `round9_next_actions.md`，给出 checkpoint-initialized finetune 和 edema-only refiner 的 `go/watch/postpone/stop` 结论。
```
