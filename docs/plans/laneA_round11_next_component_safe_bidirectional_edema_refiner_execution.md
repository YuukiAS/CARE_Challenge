# Lane A Round11 Next Component-Safe Bidirectional Edema Refiner Execution Plan

Plan metadata:
- Type: next/planned round execution
- Lane: Lane A, MyoPS scar/edema
- Round scope: Round11
- Status: next goal-mode controller, planning-only artifact
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: `docs/plans/laneA_round10_active_edema_only_residual_refiner_execution.md`
- Function: define a staged, gated Round11 route for explaining Round10 refiner component failures, calibrating fusion offline, and only then testing a component-safe bidirectional class_4 edema refiner
- Do not: execute experiments from this plan-writing pass; do not train; do not submit Slurm; do not create validation zip; do not upload; do not download weights; do not clone or train external repos; do not modify production code while creating this plan

## 1. Current Evidence Chain And Strategic Decision

Lane A has now accumulated enough negative evidence to avoid broad retuning. Round11 must be a targeted refiner-design round, not another whole-network or postprocess loop.

1. **Round2: edema inference postprocess route failed.** Small component deletion and ROI thresholding are not a viable mainline. Removing 1-voxel edema islands reduced component count but slightly worsened GT-positive edema Dice and HD95.
2. **Round3: loss wiring / gradient / tiny-overfit could run, but did not prove model quality.** `edema_focal_tversky` and `no_t2_edema_loss_downweighting` were engineering signals only.
3. **Round4: `edema_focal_tversky + no_t2_edema_loss_downweighting` failed real fold0 short train.** The candidate caused remote FP, no-T2 FP, HD95 regression, and unclean class_5 scar guardrails. Do not continue Focal Tversky / scalar downweighting as the main route.
4. **Round5: mechanism audit narrowed the routes.** Alignment remained `watch`, boundary/distance remained `watch`, and anatomy soft prior entered bounded diagnostic. This supported soft constraints, not hard ROI deletion.
5. **Round6: current anatomy soft attenuation failed.** Missing-modality audit showed no-T2 empty-GT cannot be treated as a strong class_4 negative; explicit modality presence and uncertainty-weighted supervision were promising mechanism signals.
6. **Round7: first-party 6-channel modality-presence pipeline was feasible, but simple presence channels plus scalar no-T2 weighting failed tiny gate.** U1 was too weak; U2 produced edema signal but introduced no-T2 empty-GT FP.
7. **Round8: T2-present edema expert / separated edema supervision had tiny-gate signal, but scratch / near-scratch fold0 very-short train collapsed.** This showed a new model cannot discard the nnU-Net501 baseline representation and expect a very-short budget to recover anatomy/scar structure.
8. **Round9: nnU-Net501 checkpoint could be migrated to 6-channel model, but whole-network fine-tune still failed.** Initial logits could reproduce baseline exactly, but the trained candidate showed only weak edema signal and unclean component / HD95 / scar guardrails. Whole-network adaptation should not continue longer.
9. **Round10: edema-only residual refiner was safer than whole-network adaptation but still failed the component gate.** The refiner preserved class_5 scar voxel-level exactly and did not create no-T2 empty-GT edema FP. However, the current add-only conservative refiner produced only tiny Dice gains, slightly worsened HD95 on T2-present/CenterC subsets, and flagged `Case2031` and `Case3012` with `edema_component_worse`.

Latest Round10 evidence:

- Plan/record: `docs/plans/laneA_round10_active_edema_only_residual_refiner_execution.md`
- Output root: `results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner/`
- Cache gate: `pass_cache_gate`
- Tiny gate: `pass_tiny_refiner_safety_gate`
- Fold0 very-short job: `52102044`, completed `0:0`, 44/44 validation predictions
- Final decision: `fail_stop_refiner_candidate`

Round10 subset deltas:

| subset | edema Dice delta | edema HD95 improvement | component improvement | remote FP improvement | scar delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| all-case | +0.0025 | -0.0189 | +0.1591 | +0.0227 | 0.0000 |
| T2-present GT-positive | +0.0025 | -0.0519 | +0.4375 | +0.0625 | 0.0000 |
| CenterB | +0.0051 | +0.0867 | +0.2857 | 0.0000 | 0.0000 |
| CenterC | +0.0005 | -0.1597 | +0.5556 | +0.1111 | 0.0000 |
| no-T2 empty-GT | NA | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

Current conclusion:

```text
Lane A should not continue whole-network fine-tuning, should not directly run add-only refiner longer, and should not return to small components, Focal Tversky, hard ROI, or anatomy attenuation.
```

Round11 should first explain the Round10 refiner failure and then upgrade only if justified:

```text
component-safe bidirectional but bounded edema-only refiner
```

Core principles:

- nnU-Net501 baseline remains responsible for anatomy, scar, and overall segmentation structure.
- Refiner may only modify class_4 edema.
- class_5 scar must remain voxel-level unchanged for every exported case.
- Refiner must be able to fallback to baseline per case or per component.
- Add and remove operations must be bounded, component-aware, T2/anatomy-supported, and audited separately.
- A fusion/post-fusion calibration that fixes Round10 without new training is preferred over adding a new trainable module.

## 2. Output Root And Required Files

All Round11 outputs must be isolated under:

```text
results/diagnostics/phase0_phase1/laneA_myops/round11_component_safe_refiner/
```

Required or recommended outputs:

- `round11_goal_execution_readme.md`
- `round11_round10_repro_gate.csv`
- `round11_failure_audit.csv`
- `round11_failure_audit.md`
- `round11_offline_fusion_grid.csv`
- `round11_offline_fusion_grid.md`
- `round11_train_config.yaml`
- `round11_train_commands.txt`
- `round11_unit_gradient_smoke.csv`
- `round11_tiny_overfit_metrics.csv`
- `round11_fold0_very_short_metrics.csv`
- `round11_fold0_short_train_metrics.csv`
- `round11_fold0_longer_train_metrics.csv`
- `baseline_vs_refiner_by_subset.csv`
- `case2031_case3012_component_audit.csv`
- `no_t2_empty_gt_fp_table.csv`
- `centerB_centerC_edema_table.csv`
- `scar_unchanged_guardrail_table.csv`
- `residual_magnitude_summary.csv`
- `component_safety_summary.csv`
- `case_level_failure_flags.csv`
- `round11_decision_table.md`
- `round11_next_actions.md`

Optional overlays and snapshots:

```text
results/diagnostics/phase0_phase1/laneA_myops/round11_component_safe_refiner/failure_overlays/
```

Suggested experiment names:

```text
laneA_r11_fusion_calibrated_round10_refiner
laneA_r11_bidirectional_edema_refiner_fold0_very_short
laneA_r11_bidirectional_edema_refiner_fold0_short
laneA_r11_bidirectional_edema_refiner_fold0_longer
```

Do not write into:

- `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/`
- Round8 / Round9 / Round10 output roots except read-only inputs
- validation submission workspaces

## 3. Main Route 1: `round10_failure_audit_and_offline_fusion_calibration`

### Goal

Before training anything, explain why Round10 worsened components in `Case2031` and `Case3012`, then test whether fusion/post-fusion calibration can remove those failures while preserving the small positive edema signal.

### Inputs

- nnU-Net501 fold0 baseline hard predictions and probabilities.
- Round10 refiner checkpoint and exported validation predictions.
- Round10 residual magnitude table and metrics.
- GT labels from Dataset501 compact labels.
- Raw C0/LGE/T2 images, resampled only for diagnostic overlays.
- Baseline anatomy support from myocardium/LV/RV probabilities or hard labels.
- Existing evaluator and component diagnostics.

### Required Failure Analysis

For `Case2031`, `Case3012`, and any other component-worse cases, analyze:

- baseline edema probability / logits;
- Round10 refiner residual map;
- fused edema prediction;
- GT edema mask;
- myocardium/LV/RV/anatomy support;
- T2/LGE/C0 image context;
- component count before/after;
- residual magnitude distribution;
- whether newly added edema voxels are near baseline edema boundary;
- whether new voxels are remote from myocardium/anatomy support;
- whether new voxels occur in low T2 support or ambiguous T2 intensity regions;
- whether component worsening comes from component splitting, isolated new islands, or thin bridges joining/splitting lesions;
- whether add-only fusion is the direct reason the error cannot be repaired.

Each audited case must get a `failure_reason_tag`, for example:

- `threshold_too_low`
- `residual_remote_addition`
- `component_split_from_edge_add`
- `baseline_probability_low_support`
- `outside_anatomy_support`
- `low_t2_support`
- `add_only_cannot_remove_baseline_fp`
- `training_signal_too_weak`
- `unclear_needs_overlay_review`

If the reason is `unclear_needs_overlay_review`, do not train. Add more diagnostics first.

### Offline Fusion / Threshold Grid

The grid must test at least:

- residual magnitude threshold;
- clipped residual range;
- baseline probability support threshold;
- anatomy / myocardium support gate;
- T2-present-only gate;
- minimum component size;
- keep-largest-or-near-baseline-component rule;
- add-only versus add-and-remove fusion;
- fallback-to-baseline per case;
- fallback-to-baseline per component;
- fallback-to-baseline if component count worsens;
- fallback-to-baseline if HD95 or remote FP worsens on training/diagnostic cases where GT is available.

Candidate offline rules:

| rule | description | expected use |
| --- | --- | --- |
| `r10_add_only_baseline` | current Round10 fusion | reference only |
| `residual_thresholded_add` | add only where residual magnitude exceeds threshold and baseline edema probability is near decision boundary | test threshold issue |
| `baseline_prob_supported_add` | require baseline class_4 probability or local edema neighborhood support | reduce isolated add components |
| `anatomy_supported_add` | require dilated myocardium/LV/RV support or distance-map threshold | reduce remote edema |
| `t2_supported_add` | require T2-present and local T2 intensity/support proxy | reduce low-support additions |
| `component_safe_add` | add candidates only if they touch or are near existing baseline edema/anatomy support | remove component splits/islands |
| `add_remove_prob_band` | allow addition above upper probability threshold and removal below lower threshold in bounded regions | test bidirectional need without training |
| `fallback_if_component_worse` | revert whole case or component to baseline if component count increases | safest guard |

### Promotion Rule

If any offline fusion rule:

- preserves class_5 scar exactly;
- does not increase no-T2 empty-GT edema FP;
- removes `Case2031` / `Case3012` component worsening;
- keeps or improves T2-present GT-positive edema Dice/HD95;
- keeps CenterC at least neutral on HD95/component;
- does not rely on empty-GT artifact;

then Round11 should promote `fusion_calibrated_refiner` and should not train a bidirectional refiner in the same branch unless the user explicitly asks.

If no offline rule fixes the component failures, but analysis shows removal is needed, proceed to the bidirectional trainable route.

## 4. Main Route 2: `component_safe_bidirectional_refiner_trainable_smoke`

### Goal

Design and test a bounded refiner that can both add missed edema and remove baseline/refiner edema errors, while still changing only class_4 and preserving scar exactly.

### Candidate A: Bounded Add-Remove Residual Refiner

Most conservative trainable upgrade after offline grid fails.

Architecture:

```text
shared small 3D refiner trunk -> two output channels:
  add_delta_edema
  remove_delta_edema
```

Fusion constraints:

- `add_delta` may only create class_4 in T2-present cases and only where baseline probability / local anatomy / T2 support is plausible.
- `remove_delta` may only remove class_4 where baseline predicted edema exists or where baseline edema probability is high enough to define an edema-support neighborhood.
- `add_delta` and `remove_delta` must be clipped separately, for example `delta_max_add <= 1.0`, `delta_max_remove <= 1.0`.
- class_5 scar voxels must be immutable.
- final output must support per-case fallback to baseline.
- final output must report changed voxels, added voxels, removed voxels, and changed components.

Loss:

- T2-present GT-positive cases: binary edema loss on final refined class_4 probability or logits.
- Baseline-edema false-positive regions: bounded remove loss only where GT has no edema and baseline/refiner support exists.
- no-T2 empty-GT cases: weak calibration only, not dense strong negative.
- Residual magnitude regularization for add and remove separately.
- Optional component-proxy penalty only as a small auxiliary after unit/tiny gates pass.

Expected benefit:

- can correct add-only limitation;
- may reduce component splits by removing bad baseline/refiner islands or bridges;
- preserves baseline scar/anatomy route.

Fail-fast:

- any scar voxel changes;
- no-T2 empty-GT edema FP increases;
- remove channel suppresses true GT-positive edema;
- add/remove residual saturates;
- component count worsens on `Case2031` or `Case3012`;
- Dice improves only by deleting true edema or exploiting empty-GT cases.

### Candidate B: Component-Aware Refiner Fusion

Second conservative route. It may reuse the Round10 one-channel residual model or Candidate A outputs, but fusion explicitly checks components.

Fusion checks:

- reject added components far from baseline edema support;
- reject added components far from myocardium/anatomy support;
- reject added components with low T2 support;
- reject components below minimum size unless they touch baseline edema;
- fallback to baseline if component count worsens;
- fallback to baseline if remote FP count worsens;
- keep largest or near-baseline components only when this is not hard ROI deletion of true GT-positive edema.

This route can be promoted from offline fusion without new training if it passes the full evaluation gate.

Risk:

- overly conservative component filtering can hide real small edema lesions;
- component rules may overfit `Case2031` / `Case3012`;
- must be reported as a refiner/fusion rule, not a new segmentation model.

### Candidate C: Boundary-Smoothing Residual Refiner

Optional only after A or B has a clean safety signal.

Goal:

- reduce boundary roughness and component split via small boundary/surface regularization.

Rules:

- boundary/surface loss cannot dominate Dice/CE;
- no Focal Tversky mainline;
- no InverseForm/HD repo integration in first pass;
- only first-party small auxiliary inspired by surface/HD mechanisms.

## 5. Preparatory Route: `external_method_escalation_criteria`

Round11 still does not authorize broad external repo integration. Deep Research remains a mechanism library.

| method family | potential Round12+ slot | Round11 stance |
| --- | --- | --- |
| I-MMSeg | T2/LGE intensity prior or intensity-prompt feature for T2-support estimation | watch; can inspire first-party T2-support proxy |
| Cascaded FSN / PT-Net | anatomy support feature or lesion-anatomy consistency for component-safe refiner | watch; use baseline anatomy first |
| InverseForm / surface loss / HD loss | small boundary auxiliary for component/boundary control | watch; only after component safety is clean |
| AdaMM / UniME / CoPeDiT / MoE | stronger missing-modality representation or teacher/student route | postpone until first-party refiner route is exhausted or gives positive signal |
| CAA-Seg / SSA | alignment preprocessing | watch; promote only if overlays show sequence mismatch |
| BiomedParse / MedNeXt / nnU-Net Task114/M&Ms | future backbone / feature extractor | watch; no weight download or training in Round11 |

External method escalation is allowed only if:

1. Round11 failure audit/offline grid cannot explain or fix component failures; and
2. bidirectional refiner smoke fails cleanly with documented mechanism reason; and
3. the next plan defines license/compliance, pretrained data source, external data risk, input/output shape, label mapping, one-case smoke, and fold0 smoke.

No external data training or validation pseudo-label supervised training is allowed.

## 6. Stage 1: `round11_reproducibility_and_round10_result_gate`

### Goal

Reproduce and locate the Round10 result that motivates Round11.

### Allowed

- Read Round10 cache, predictions, metrics, failure cases, baseline files, refiner outputs, fold split, label semantics, evaluator, spacing/origin, and modality metadata.
- Create diagnostic scripts under `scripts/diagnostics/` for Round11.
- Write Round11 output root and summary files.

### Forbidden

- No training.
- No Slurm.
- No validation zip or upload.
- No fold1-4.
- No external repo or weight download.
- No modification of nnU-Net baseline cache or Round10 outputs.

### Outputs

- `round11_goal_execution_readme.md`
- `round11_round10_repro_gate.csv`
- initial `round11_decision_table.md`

### Pass Criteria

- Round10 `fail_stop_refiner_candidate` can be reproduced or exactly linked.
- `Case2031` and `Case3012` baseline/refiner/GT/image files are locatable.
- Round10 metrics match `baseline_vs_refiner_by_subset.csv`.
- Compact label semantics remain `edema=4`, `scar=5`.
- Fold0 split and baseline out-of-fold probability logic are understood.
- Evaluation scripts and output roots are isolated.

### Fail Criteria

- Round10 outputs are missing or inconsistent.
- Candidate predictions do not contain 44/44 fold0 validation cases.
- GT/prediction geometry mismatch cannot be explained.
- Label semantics are ambiguous.
- Any planned diagnostic would overwrite baseline or Round10 artifacts.

### Next Stage

If pass, proceed to Stage 2. If fail, repair reproducibility documentation only; do not train.

## 7. Stage 2: `case_level_failure_audit_and_overlay`

### Goal

Produce a case-level explanation of Round10 component failures.

### Allowed

- Analyze `Case2031`, `Case3012`, and any case with component or HD95 regression.
- Generate CSV/MD audit tables.
- Generate lightweight overlay PNG or NIfTI snapshots if dependencies already exist.
- Use baseline probabilities, Round10 residual maps, baseline/refiner predictions, GT, and raw modalities.

### Forbidden

- No training.
- No threshold optimization that writes candidate predictions as promoted outputs before the audit table exists.
- No hard anatomy deletion claims.
- No external repo.

### Outputs

- `round11_failure_audit.csv`
- `round11_failure_audit.md`
- `case2031_case3012_component_audit.csv`
- optional `failure_overlays/Case2031_*.png`
- optional `failure_overlays/Case3012_*.png`

### Required Columns

- `case_id`
- `center`
- `modality_group`
- `baseline_dice`
- `round10_dice`
- `baseline_hd95`
- `round10_hd95`
- `baseline_component_count`
- `round10_component_count`
- `new_voxels`
- `removed_voxels`
- `new_component_count`
- `residual_abs_mean`
- `residual_abs_max`
- `residual_clip_fraction`
- `new_voxels_touch_baseline_edema`
- `new_voxels_distance_to_baseline_edema_mm`
- `new_voxels_distance_to_anatomy_mm`
- `new_voxels_t2_support_summary`
- `failure_reason_tag`

### Pass Criteria

- `Case2031` and `Case3012` each have a concrete failure reason tag.
- New voxel locations are classified as edge / remote / anatomy-supported / low-T2 / unclear.
- Component worsening mode is identified as split, island, bridge, or baseline-support issue.
- The audit can decide whether offline fusion is likely to fix the issue.

### Fail Criteria

- Failure reason remains unclear.
- Residual maps or baseline probabilities cannot be loaded.
- Overlay generation reveals geometry or orientation errors that invalidate Round10 metrics.

### Next Stage

If pass, proceed to Stage 3. If fail, stop and add diagnostics; do not train.

## 8. Stage 3: `offline_fusion_and_threshold_grid`

### Goal

Test whether Round10 can be made component-safe without retraining.

### Allowed

- Run offline fusion/threshold grid using existing Round10 outputs and baseline probabilities.
- Export temporary candidate predictions under Round11 output root only.
- Evaluate fold0 validation cases with existing evaluator.
- Compare add-only, gated-add, component-safe, fallback, and bounded add-remove fusion rules.

### Forbidden

- No training.
- No Slurm unless a purely diagnostic CPU/GPU job is later explicitly needed and recorded.
- No validation zip/upload.
- No external repo.
- No modification of Round10 predictions.

### Outputs

- `round11_offline_fusion_grid.csv`
- `round11_offline_fusion_grid.md`
- `component_safety_summary.csv`
- `baseline_vs_refiner_by_subset.csv` for best offline rule
- `case_level_failure_flags.csv`
- optional predictions under `predictions/offline_fusion_grid/<rule_name>/validation/`

### Pass Criteria

At least one offline rule:

- preserves class_5 scar exactly;
- does not increase no-T2 empty-GT edema FP;
- removes `Case2031` / `Case3012` component worsening;
- keeps component count and remote FP neutral or improved;
- keeps or improves T2-present GT-positive or CenterC edema Dice/HD95;
- does not rely on all-case aggregate or empty-GT artifact.

### Fail Criteria

- Every rule either loses the small Dice signal or keeps component failures.
- Any rule changes scar.
- Any rule creates no-T2 FP.
- Any rule fixes components only by hard deleting true GT-positive edema.
- Any result is only explainable through all-case aggregate.

### Next Stage

If pass, write decision `go_fusion_calibrated_refiner` and stop before training unless user asks for a separate training candidate. If fail and audit indicates remove correction is needed, proceed to Stage 4.

## 9. Stage 4: `bidirectional_refiner_architecture_gate`

### Goal

Implement the minimal bidirectional add/remove refiner only after offline fusion cannot solve the issue.

### Allowed

- Add Round11 first-party refiner code under `src/care_myocardium/refiner/`.
- Add Round11 diagnostics/training scripts under `scripts/diagnostics/` and `scripts/training/`.
- Reuse Round10 dataset/cache helpers.
- Run import, `py_compile`, one-batch forward/backward, and tiny safety smoke.

### Forbidden

- No whole nnU-Net training.
- No class_5 output head.
- No multiclass segmentation head.
- No fold0 train before unit/gradient/tiny gates.
- No external data or external repo modules.

### Outputs

- `round11_train_config.yaml`
- `round11_train_commands.txt`
- `round11_unit_gradient_smoke.csv`
- updated `component_safety_summary.csv`

### Pass Criteria

- import / py_compile pass;
- one-batch forward/backward finite;
- no NaN/Inf;
- add/remove outputs are clipped and measured separately;
- fallback-to-baseline works;
- scar unchanged assertion passes;
- no-T2 tiny FP does not increase;
- remove channel does not delete all GT-positive edema in the smoke cases.

### Fail Criteria

- scar changes by any voxel;
- add/remove residual saturates immediately;
- no-T2 FP appears;
- loss is unstable;
- label/cache/evaluator assumptions are ambiguous;
- implementation requires broad nnU-Net trainer rewrite.

### Next Stage

If pass, proceed to Stage 5. If fail, stop the bidirectional candidate and keep offline fusion results as the only Round11 evidence.

## 10. Stage 5: `tiny_overfit_component_safety_screen`

### Goal

Verify the bidirectional refiner can learn useful add/remove corrections without component or scar regressions before any fold0 training.

### Required Tiny Set

Include at minimum:

- `Case2031`;
- `Case3012`;
- one CenterB complete T2-present GT-positive case without Round10 failure;
- one CenterC complete T2-present GT-positive case without Round10 failure;
- one LGE-only no-T2 empty-GT case;
- one C0+LGE no-T2 empty-GT case if available.

### Allowed

- Tiny crop/patch training.
- One or two conservative candidate settings.
- Lightweight overlays.

### Forbidden

- No fold0 training if tiny gate fails.
- No whole nnU-Net training.
- No fold1-4.
- No validation zip/upload.

### Outputs

- `round11_tiny_overfit_metrics.csv`
- `residual_magnitude_summary.csv`
- `component_safety_summary.csv`
- optional overlays under `failure_overlays/`

### Pass Criteria

- `Case2031` and `Case3012` component count does not worsen in tiny screen.
- T2-present edema shows nonzero learning signal.
- no-T2 empty-GT FP does not increase.
- class_5 scar remains exactly unchanged.
- add and remove voxel counts are bounded.
- fallback-to-baseline restores baseline when component rule fails.

### Fail Criteria

- Dice improves but HD95/component worsens.
- remove channel suppresses true edema.
- add channel creates remote components.
- no-T2 cases gain edema FP.
- scar changes by any voxel.
- apparent improvement comes only from empty-GT behavior.

### Next Stage

If pass, proceed to Stage 6. If fail, stop candidate; do not increase epochs.

## 11. Stage 6: `bounded_fold0_component_safe_refiner_training_ladder`

### Goal

Allow the next goal-mode to train the small refiner through staged fold0 gates only.

### Training Ladder

1. fold0 very-short component-safe refiner train;
2. fold0 short refiner train only if very-short passes;
3. fold0 longer refiner train only if short passes;
4. prepare fold1-4 expansion plan only after longer fold0 passes, but do not execute fold1-4 without explicit user authorization.

### Allowed

- Submit bounded `htzhulab` Slurm jobs after earlier gates pass.
- Train only the refiner.
- Use unique Round11 experiment names and output roots.
- Continue to the next rung in one goal-mode run only if the previous rung passes.

### Forbidden

- Do not train or fine-tune nnU-Net backbone.
- Do not modify baseline scar/anatomy predictions.
- Do not run fold1-4 or 5-fold.
- Do not create validation zip or upload.
- Do not train external repos.

### Outputs

- `round11_fold0_very_short_metrics.csv`
- `round11_fold0_short_train_metrics.csv`
- `round11_fold0_longer_train_metrics.csv`
- `round11_train_commands.txt`
- prediction directories under Round11 output root

### Pass Criteria

- Refiner exports predictions for all 44 fold0 validation cases at each rung.
- class_5 scar unchanged for every case.
- no-T2 empty-GT edema FP does not increase.
- `Case2031` and `Case3012` component worsening is fixed or absent.
- T2-present GT-positive or CenterC edema has clean positive signal.
- HD95/component/remote FP do not regress.
- add/remove residual magnitude distribution remains bounded.

### Fail Criteria

- any scar voxel changes;
- no-T2 FP increases;
- component/remote FP worsens;
- Dice-only gain with HD95 regression;
- add/remove residual saturates;
- cache/label/evaluator silent change.

### Next Stage

If very-short fails, stop. If very-short passes, proceed to short. If short passes, proceed to longer. If longer passes, proceed to Stage 7.

## 12. Stage 7: `evaluation_and_round11_decision_gate`

### Goal

Decide whether Round11 should promote, watch, stop, or escalate.

### Required Subsets

Report separately:

- all-case;
- T2-present GT-positive;
- complete-modality;
- CenterB;
- CenterC;
- `Case2031`;
- `Case3012`;
- no-T2 empty-GT;
- C0+LGE no-T2;
- LGE-only;
- center groups;
- modality groups.

### Required Metrics

For `myops_edema` class_4:

- Dice;
- HD;
- HD95;
- component count;
- small FP;
- remote FP;
- pred/GT volume ratio;
- no-T2 edema FP voxel count;
- no-T2 edema FP case count;
- added voxel count;
- removed voxel count;
- changed component count;
- baseline-vs-refiner delta.

For `myops_scar` class_5:

- exact unchanged voxel check by case;
- Dice/HD/HD95 guardrail as unchanged or copied values.

Refiner-specific:

- add residual magnitude distribution;
- remove residual magnitude distribution;
- clipped residual fraction;
- changed voxel count;
- changed component count;
- fallback case count;
- fallback component count;
- overlay summary;
- case-level failure flags.

### Decision Labels

| decision | meaning | allowed next action |
| --- | --- | --- |
| `go_fusion_calibrated_refiner` | offline fusion fixes Round10 failures and preserves signal | consider fold0 longer packaging plan, no submission yet |
| `go_bidirectional_refiner` | bidirectional refiner cleanly improves T2/CenterC and fixes components | prepare fold0 longer or fold expansion plan |
| `watch_component_safe_refiner` | safety is clean but signal is small/mixed | one bounded feature/fusion adjustment only |
| `fail_stop_refiner_candidate` | component/HD/no-T2/scar gate fails | stop current candidate |
| `postpone_refiner_route` | first-party refiner route cannot explain or fix failures | prepare external-method metadata audit plan |

### Pass Criteria

- class_5 scar unchanged for every case;
- no-T2 empty-GT edema FP does not increase;
- `Case2031` and `Case3012` component worsening removed;
- T2-present GT-positive or CenterC edema has clean positive signal;
- HD95/component/remote FP do not clearly worsen;
- improvement is not from empty-GT artifact or all-case aggregate only;
- refiner does not rewrite baseline over large regions.

### Fail Criteria

- any scar change;
- Dice improves but HD95/component worsens;
- no-T2 FP increases;
- `Case2031` or `Case3012` still component-worse;
- CenterC remains flat or worse with HD95 regression;
- add/remove residual saturates;
- result depends only on empty-GT behavior.

### Next Stage

If `go`, write next plan for controlled fold expansion or final packaging audit. If `watch`, one targeted Round11-plus adjustment may be planned. If `fail` or `postpone`, stop this route and consider the external method readiness branch in a new plan.

## 13. Resource Stance For Next Goal-Mode

User token, Slurm, and GPU resources are assumed sufficient. The next goal-mode may push as far as possible in one run, but progression must be:

```text
staged, gated, refiner-only, component-safe, and baseline-preserving
```

Allowed in one goal-mode run if every gate passes:

1. failure audit;
2. offline fusion/threshold grid;
3. bidirectional refiner implementation if needed;
4. unit/gradient smoke;
5. tiny-overfit;
6. fold0 very-short train;
7. fold0 short train;
8. fold0 longer train;
9. evaluation and decision table.

Resource abundance does not permit skipping gates. If any gate fails, stop the candidate, write the reason, and do not automatically expand compute.

## 14. Next Goal Execution Prompt Draft

```text
你现在在 `/overflow/htzhu/CARE` 中工作。请执行 Lane A Round11：

`docs/plans/laneA_round11_next_component_safe_bidirectional_edema_refiner_execution.md`

目标是尽可能推进 `component-safe bidirectional but bounded edema-only refiner`，但必须先审计 Round10 failure cases。不要创建 validation zip，不要上传，不要跑 fold1-4 或 5-fold，除非 fold0 gates 全部通过且我另行授权。不要下载权重，不要拉取外部 repo，不要使用 external data training，不要用 validation pseudo-label supervised training。不要训练或 fine-tune whole nnU-Net backbone。

请先执行 Stage 1：复核 Round10 cache、predictions、metrics、failure cases、baseline files、refiner outputs、fold split、label semantics、evaluator、spacing/origin 和 modality metadata。必须确认 `Case2031`、`Case3012` 的 baseline/refiner/GT/image 文件都可定位，并且 Round10 metrics 与 summary 一致。若不一致，只修 reproducibility/diagnostics，不进入训练。

Stage 2：对 `Case2031`、`Case3012` 和所有 component-worse cases 做 case-level audit 和 overlay。必须分析 baseline edema probability/logits、Round10 residual map、fused edema prediction、GT edema mask、anatomy support、T2/LGE/C0 image context、component before/after、residual magnitude distribution、新增 voxels 与 baseline edema/anatomy/T2 support 的关系，并给每例 `failure_reason_tag`。

Stage 3：在不重训的情况下做 offline fusion/threshold grid。比较 residual threshold、clipped residual range、baseline probability support threshold、anatomy/myocardium support gate、T2-present-only gate、minimum component size、keep-largest-or-near-baseline-component rule、add-only vs add-and-remove fusion、fallback-to-baseline rule。若某个 fusion rule 能保持 Round10 微小 Dice gain，同时消除 `Case2031` / `Case3012` component worsening，且 scar unchanged、no-T2 FP 不增加、HD95/component/remote FP 不恶化，则 promote `fusion_calibrated_refiner`，不要训练新 bidirectional refiner，除非我另行要求。

只有当 offline fusion grid 不能解决问题，或明确显示需要 remove correction 时，才进入 Stage 4-6：实现 component-safe bidirectional edema refiner。候选优先级是 bounded add-remove residual refiner，然后 component-aware fusion/refiner，最后才考虑 boundary-smoothing residual auxiliary。Refiner 只能修改 class_4 edema；class_5 scar 必须 voxel-level unchanged；必须有 fallback-to-baseline、add/remove residual clipping、component safety summary 和 no-T2 FP guard。

训练推进必须按 gate：

1. import / py_compile / config smoke；
2. one-batch forward/backward；
3. tiny-overfit component safety screen，必须包含 `Case2031` 和 `Case3012`；
4. fold0 very-short refiner train；
5. fold0 short refiner train；
6. fold0 longer refiner train only if previous gates pass。

资源充足，可以在一个 goal-mode run 中尽可能推进，但每个阶段必须 gate；任一 gate fail 即停止当前 candidate，不得自动扩大规模。禁止 validation submission、禁止 fold1-4/5-fold、禁止 whole-network fine-tune、禁止外部 repo full training、禁止 external data 或 validation pseudo-label supervised training。

所有输出写入：

`results/diagnostics/phase0_phase1/laneA_myops/round11_component_safe_refiner/`

最终必须输出 `round11_decision_table.md` 和 `round11_next_actions.md`，并给出 `go_fusion_calibrated_refiner`、`go_bidirectional_refiner`、`watch_component_safe_refiner`、`fail_stop_refiner_candidate` 或 `postpone_refiner_route` 结论。评估必须分别报告 `myops_edema` class_4 与 `myops_scar` class_5 guardrail，包含 all-case、T2-present GT-positive、complete-modality、CenterB、CenterC、Case2031、Case3012、no-T2 empty-GT、C0+LGE no-T2、LGE-only、center/modality subsets。不要使用 foreground mean 或 all-case aggregate 掩盖失败。
```
