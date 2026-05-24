# Lane A Round2 Targeted Execution Addendum

Date: 2026-05-20

Plan metadata:
- Type: round addendum
- Lane: A, MyoPS scar/edema
- Round scope: Round2 targeted diagnostic smoke
- Status: completed/evidence addendum; use as Round3 input, not as active controller
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: `docs/plans/laneA_round03plus_controller_myops_modality_aware_src_plan.md`
- Function: document Round2 edema-focused smoke design and the evidence that postprocess-only edema cleanup is not the mainline
- Do not: continue adding unrelated future mechanisms here; create `laneA_round03_next_<topic>_execution.md` for Round3

This is a focused addendum to the frozen Lane A controller plan. It does not replace `docs/plans/laneA_round03plus_controller_myops_modality_aware_src_plan.md`.

Round2 objective: edema-focused targeted smoke implementation under CARE-native constraints. Do not replace the backbone broadly, do not integrate external foundation models, do not train in this planning pass, and keep all future diagnostic outputs under:

- `results/diagnostics/care_myocardium/laneA_myops/round02_edema_postprocess_smoke/`

## Current Evidence

CARE diagnostics fixed the fold0 reference and failure landscape:

- `nnUNet501` fold0 anchor: `myops_scar` Dice `0.5602`, HD95 `13.6005`; `myops_edema` Dice `0.3944`, HD95 `7.2769`.
- Complete-modality `CenterC` cases show scar Dice `0.7557` but edema Dice `0.3100` and edema HD95 `23.1833`.
- This means edema remains weak even when T2 exists. The failure is not explained only by missing T2.
- The likely Round2 target is boundary/topology instability and T2-conditioned edema routing, not a large backbone replacement.

## Why Complete-Case Edema HD95 Remains High

Edema is diffuse, low-contrast, and boundary-ambiguous relative to scar. Even in C0+LGE+T2 cases, T2 signal can support edema but does not define a crisp closed object. A model can achieve tolerable overlap while leaving distant fragments, ragged boundaries, or disconnected overreach that dominate HD95.

The likely mechanisms are:

- Diffuse edema boundary: lesion edge is less anatomically crisp than scar, so Dice loss tolerates boundary spread that HD95 punishes.
- Topology fragmentation: small disconnected edema islands add little volume but can dominate HD95 and component counts.
- T2 dependence is conditional: T2-present cases should drive edema; T2-missing cases should not teach the model that edema is reliably absent.
- Anatomy support mismatch: edema should be near myocardium but hard ROI deletion can remove plausible pathology near uncertain myocardium boundaries.
- Scar/edema objective conflict: shared foreground loss may prioritize scar/anatomy stability while edema becomes a noisy minority target.

## DeepResearch-Derived CARE-Specific Implementation Recipes

### DeepResearch-to-CARE mapping

Deep Research is used here only as mechanism inspiration, not as a request to integrate external frameworks. InverseForm, boundary-aware loss, and ST-Loss map to a CARE class_4 edema boundary/HD95 smoke: first implement surface or distance-transform loss on edema masks and verify gradients before any fold0 training. Unified Focal and Focal Tversky map to class_4 small-lesion/imbalance auxiliary losses, not a wholesale replacement of the scar/anatomy objective. AdaMM, UniME, missing-modality segmentation, and MyoPS-Net-style routing map to T2-aware edema routing plus explicit modality-mask conditioning; the full teacher/student or missing-modality framework is postponed. I-MMSeg/intensity-prior ideas are reduced to CARE modality/intensity priors and subgroup diagnostics; no large intensity-prior model is connected in Round2.

### 1. Focal Tversky / Unified Focal Loss

Round2 should start with an edema-only auxiliary loss on class_4, added to the existing baseline loss, rather than replacing all foreground loss. The reason is practical: class_5 scar is the current anchor, and a global loss swap could degrade scar while hiding the regression behind a class_4 gain.

Initial rule:

- apply the auxiliary term only to class_4 edema logits/masks;
- keep class_5 scar loss unchanged and always report scar metrics as a guardrail;
- run unit/gradient/tiny-overfit smoke before any fold0 train smoke.

For Focal Tversky, start with a conservative FP penalty because edema is diffuse and recall-biased tuning can create remote false positives. Use an initial Tversky setting around `alpha_fp >= beta_fn` or balanced `alpha_fp ~= beta_fn`; only move toward recall emphasis if component count and remote FP stay controlled. Focal `gamma` should start in a small range such as `1.0-2.0`, with one value per smoke run and explicit logging.

For Unified Focal, use the same edema-only auxiliary pattern. Do not make it the default all-class objective until class_4 Dice, class_4 HD95, edema component count, and remote FP are all non-regressing.

Required logs:

- class_4 Dice, HD95, HD, component count, remote FP, small FP, pred/GT volume ratio;
- class_5 Dice/HD95 as an anchor;
- GT-positive-only and T2-present class_4 subsets;
- empty-GT cases separated from GT-positive cases.

Fail fast if Dice improves while HD95, component count, remote FP, or volume ratio worsens. That pattern means the loss increased recall by adding unstable edema islands, which is the exact Round2 failure mode.

### 2. Boundary / Distance / HD-Aware Loss

Round2 should not begin with a complex Hausdorff loss. Start with a surface loss or distance-transform loss on class_4 edema and run one-batch or tiny-overfit gradient smoke first. Only after gradient stability and sane per-class behavior are proven should it be eligible for a fold0 train smoke.

Implementation details for CARE:

- build the class_4 edema distance map from the binary GT edema mask in the same geometry as the training patch;
- respect image spacing and anisotropy when computing distance transforms, otherwise z-axis errors can dominate HD surrogates;
- handle empty-GT edema cases explicitly: either skip the distance term for empty GT or use a separate FP penalty, but do not let empty-GT cases define the main boundary signal;
- keep 3D masks as the default for 3D volumes; use 2D slice handling only if the existing training batch is slice-based and record that choice;
- keep class_5 scar out of the first boundary-loss smoke unless class_4 results pass.

Metrics after any boundary/distance smoke must include Dice, HD95, HD, component count, remote FP, small FP, and volume ratio. A boundary loss that improves Dice but increases component count or volume ratio is not a success.

### 3. T2-Aware Edema Routing

The first Round2 step is audit, not training. Report class_4 edema behavior by:

- T2-present vs no-T2;
- GT-positive vs empty-GT;
- center bucket;
- complete-modality vs C0+LGE vs LGE-only.

No-T2 cases cannot be treated as reliable edema negatives by default. If they are used as hard negatives, the edema head can learn that missing T2 means no edema, which contaminates class_4 behavior and can encode center shortcuts.

After audit, compare only these strategies:

- `report_only`: no behavior change, just subgroup metrics;
- `loss_masking`: omit class_4 loss on no-T2 cases while preserving scar/anatomy supervision;
- `loss_downweighting`: keep a small class_4 penalty on no-T2 cases to discourage obvious FP without claiming true negatives.

Routing must not become a center classifier. CenterA/H are mostly LGE-only while CenterB/C are complete cases, so any T2-aware result must be reported by both modality group and center. A gain that only follows center distribution is not enough.

### 4. Explicit Modality-Mask Conditioning

The minimal Round2-compatible implementation is input-level modality presence channels or a simple FiLM-like conditioning vector. Do not start with full AdaMM/UniME missing-modality distillation, teacher/student training, or a new missing-modality framework.

The modality mask should serve the T2-aware edema route:

- distinguish zero-filled missing T2 from a real low-intensity T2 image;
- allow loss/routing logic to know which modalities are present;
- support subgroup reporting and failure analysis.

It does not replace the CARE diagnostics failure landscape. Any future mask-conditioned smoke must report subgroup gain, especially T2-present class_4 and no-T2 FP behavior, not just all-case mean Dice.

### 5. Anatomy-Aware Edema ROI

Use anatomy as a soft, dilated plausibility guard for edema components. It must not be a default hard deletion rule.

Implementation guidance:

- derive myocardium/LV/RV support from existing compact anatomy labels or prediction labels;
- set dilation radius from voxel spacing or train/fold0 anatomy-edema distance distribution, not a hand-written magic number;
- compute edema component overlap with the dilated anatomy ROI, bbox gap, and center distance;
- keep original predictions as fallback when the guard would delete all edema.

The guard is meant to reduce remote components and HD95. It is not valid if it only improves Dice by deleting empty-GT artifacts or if it deletes GT-positive edema.

### 6. Small-Component Edema Suppression

Thresholds must come from train/fold0 prediction or GT edema component distribution, not fixed magic numbers. Candidate thresholds should be recorded as quantiles or explicit distribution-derived values.

Required reporting:

- GT-positive and empty-GT cases separately;
- removed components and removed voxels;
- component bbox distance to anatomy;
- before/after class_4 Dice, HD95, component count, volume ratio;
- `action_reason` for every removed component.

Reject the smoke if the main improvement comes from empty-GT artifact cases, if GT-positive edema Dice drops materially, or if HD95 improvement is paired with suspicious volume collapse.

## Round2 Prioritized Candidate Table

| priority | candidate | mechanism | CARE fit | current priority | smoke complexity | fail-fast criterion | expected signal |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | T2-aware edema gating | Apply edema supervision and/or inference routing conditional on T2 presence; report T2-present, GT-positive, and no-T2 subsets separately. | Directly addresses unreliable edema negatives in no-T2 groups while preserving scar routing. | high | low-medium | T2-present edema Dice/HD95 does not improve, or no-T2 false positives increase. | improves edema Dice and HD95 on T2-present/complete cases; reduces no-T2 artifact conclusions. |
| 2 | anatomy-aware edema ROI restriction | Restrict or score edema candidates by myocardium/LV/RV dilated ROI, with soft fallback rather than hard deletion. | Edema should be anatomically close to myocardium; CARE diagnostics show HD/component issues. | high | low | GT-positive edema lesions are deleted or edema Dice drops >1 point while HD95 improves. | reduces remote components and HD95; component count decreases. |
| 3 | small-component suppression for edema | Remove tiny edema islands below a fold0 train-derived voxel threshold, with GT-positive sanity checks. | Low-risk postprocess smoke against topology fragmentation. | high | low | HD95 does not decrease, or empty-GT artifact improvement is the only gain. | reduces component count and remote FP; HD95 improves with stable Dice. |
| 4 | edema-only weighting | Increase class_4 loss weight or sample weighting only for edema-positive/T2-present cases. | Direct response to edema bottleneck without architecture change. | high | low | edema recall gain creates remote FP/HD95 regression or scar Dice regresses. | improves edema Dice/recall; may not fix HD95 alone. |
| 5 | Focal Tversky | Penalize FN/FP asymmetrically for small/diffuse edema; tune beta to avoid overprediction. | Useful for imbalanced pathology, first-party implementation is small. | medium-high | low | recall gain causes component count or HD95 regression. | improves edema Dice/GT-positive recall; must be paired with topology metrics. |
| 6 | Unified Focal Loss | Combines CE/Tversky-style focal behavior for class imbalance. | Low implementation cost, but less targeted than edema-only Tversky. | medium | low | no edema-positive improvement over weighted Dice/CE, or remote FP increases. | possible Dice gain; HD95 uncertain. |
| 7 | boundary/distance/HD-aware loss | Add boundary or distance transform term for class_4 to reduce surface outliers. | Directly targets HD95, but gradient stability and spacing handling need care. | medium | medium | one-batch gradient unstable, Dice improves while HD95/component worsens. | improves HD95/boundary without major Dice gain. |
| 8 | explicit modality-mask embedding | Add modality presence vector to model blocks or input channels. | Necessary for first-party model maturity, but not a standalone edema fix. | medium | medium | no subgroup improvement or model learns center shortcuts. | improves no-T2 vs T2-present calibration; supports later routing. |
| 9 | hard anatomy deletion | Delete all edema outside myocardium ROI. | Tempting for HD95 but unsafe with anatomy uncertainty. | low/postpone | low | any plausible GT-positive edema is removed. | may reduce HD95 artificially; high false stop risk. |
| 10 | new large foundation/backbone replacement | Replace segmentation stack with large pretrained model. | Not justified by CARE diagnostics; edema topology is the immediate bottleneck. | postpone | high | requires large weights, external data, or uncontrolled integration. | unclear; not Round2. |

## First Smoke Tests To Execute

1. `edema_component_roi_postprocess_smoke`
   - Use existing nnUNet501 fold0 predictions as input.
   - Test edema small-component suppression plus soft anatomy ROI guard.
   - Output:
     - `results/diagnostics/care_myocardium/laneA_myops/round02_edema_postprocess_smoke/edema_component_roi_before_after.csv`
     - `results/diagnostics/care_myocardium/laneA_myops/round02_edema_postprocess_smoke/edema_component_roi_summary.md`
   - Gate: edema HD95 and component count decrease on T2-present/GT-positive subsets; edema Dice does not drop materially; no empty-GT artifact success.

2. `t2_aware_edema_routing_audit`
   - No training first. Audit current class_4 predictions by T2-present, no-T2, GT-positive, and center.
   - Test whether no-T2 cases need suppression, low-confidence routing, or loss masking in a later trainable smoke.
   - Output:
     - `results/diagnostics/care_myocardium/laneA_myops/round02_edema_postprocess_smoke/t2_aware_edema_routing_audit.csv`
     - `results/diagnostics/care_myocardium/laneA_myops/round02_edema_postprocess_smoke/t2_aware_edema_routing_audit.md`
   - Gate: the table must show actionable T2-present/no-T2 difference; otherwise keep routing as watch only.

3. `edema_loss_gradient_smoke`
   - Planning target for next implementation: implement first-party loss unit tests only, no fold training first.
   - Compare edema-only weighting, Focal Tversky, and Unified Focal on cached CARE tensors or a tiny overfit batch.
   - Output:
     - `results/diagnostics/care_myocardium/laneA_myops/round02_edema_postprocess_smoke/edema_loss_gradient_smoke.md`
   - Gate: stable gradients, no class_5/scar objective interference, and clear per-class logging.

## Candidates To Postpone

- Full first-party backbone replacement before postprocess/loss smoke proves the target mechanism.
- Heavy DA, diffusion harmonization, pseudo-label self-training, or foundation-model segmentation.
- Hard anatomy deletion as a default rule.
- Multi-module combinations such as modality mask + HD loss + ROI + routing in one first run.
- Fold1-4 expansion before fold0 smoke outputs isolate candidate-specific predictions and metrics.

## Minimal CARE-First Extraction for Lane A

Round2 should remain diagnostic. Only modules that pass smoke gates should later be extracted into first-party `src/` code. Candidate extraction targets are:

- `src/losses/edema_losses.py`: edema-only Focal Tversky, Unified Focal auxiliary term, and distance/surface loss after gradient smoke.
- `src/modules/modality_mask.py`: input-level modality presence channels or simple FiLM-like conditioning for T2-aware routing.
- `src/postprocess/component_filter.py`: distribution-derived small-component filtering with action reasons.
- `src/postprocess/anatomy_guard.py`: soft/dilated anatomy ROI guard with fallback behavior.
- `src/diagnostics/modality_center_eval.py`: subgroup reporting for modality group, T2 presence, GT-positive status, and center.
- `src/diagnostics/component_stats.py`: component count, removed voxels, bbox distance, remote FP, and volume-ratio utilities.

This round must not rewrite the trainer, rewrite the backbone, or refactor the whole repository. The implementation should prove mechanism value first using existing fold0 artifacts and small loss/unit smokes.

## Required Metrics And Comparability

Every future Round2 Lane A implementation must report:

- `myops_edema` and `myops_scar` separately.
- Dice, HD, HD95, component count, small/remote FP, pred/GT volume ratio.
- all-cases, GT-positive-only, T2-present, no-T2, complete-modality, and center subsets where applicable.
- identical compact label semantics: class_4 edema, class_5 scar.
- identical evaluator implementation unless explicitly documented.

Do not accept:

- aggregate foreground mean as a success criterion,
- Dice gain with HD95/component regression,
- empty-GT artifact improvement,
- stale prediction cache reuse,
- silent spacing/interpolation/preprocessing changes.

## Next Implementation Prompt Draft

Implement Lane A Round2 smoke diagnostics only. Do not train, submit Slurm, download weights, create a validation zip, upload, expand folds, modify label semantics, modify the evaluator, or change controller plans.

Create a first-party diagnostic script under `scripts/diagnostics/` that reads existing `nnUNet501` fold0 predictions and GT, then writes all outputs under `results/diagnostics/care_myocardium/laneA_myops/round02_edema_postprocess_smoke/`.

Execute only:

1. `edema_component_roi_postprocess_smoke`
   - test class_4 edema small-component suppression and soft/dilated anatomy ROI guard;
   - derive thresholds from train/fold0 distributions, not magic constants;
   - preserve class_5 scar predictions except for read-only guard metrics.

2. `t2_aware_edema_routing_audit`
   - report class_4 by T2-present, no-T2, GT-positive, empty-GT, center, and modality group;
   - compare `report_only`, future `loss_masking`, and future `loss_downweighting` as planning outputs only;
   - do not train a routing model in this pass.

3. Optional `edema_loss_gradient_smoke`
   - unit/gradient/tiny-overfit smoke only for edema-only Focal Tversky, Unified Focal auxiliary loss, and distance/surface loss;
   - no fold training;
   - keep class_5 scar loss unchanged and log scar guardrail metrics.

Required outputs under `results/diagnostics/care_myocardium/laneA_myops/round02_edema_postprocess_smoke/`:

- `edema_component_roi_before_after.csv/md`
- `t2_aware_edema_routing_audit.csv/md`
- optional `edema_case_flags.csv`
- optional `edema_loss_gradient_smoke.md`

The script must preserve Dataset501 compact labels (`4=edema`, `5=scar`), use the existing unified evaluator logic for Dice/HD/HD95, and report edema separately from scar. Do not accept aggregate-only success, empty-GT artifact improvement, or Dice gain with HD95/component regression. Fail fast if HD95 improvement comes from empty-GT artifact cases, if edema-positive Dice drops materially, if remote FP/component count worsens, if scar metrics regress through shared changes, or if any preprocessing/evaluator/label behavior changes silently.
