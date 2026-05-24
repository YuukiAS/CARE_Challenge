# Lane B Round2 Topology Execution Addendum

Date: 2026-05-20

Plan metadata:
- Type: round addendum
- Lane: B, CineMyoPS / `myocardium_cinemyops`
- Round scope: Round2 topology diagnostic smoke
- Status: completed/evidence addendum; use as Round3 hosted-calibration input, not as active controller
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: `docs/plans/laneB_round03plus_controller_cinemyops_hosted_topology_motion_plan.md`
- Function: document Round2 topology/LCC smoke design and the positive signal for Cine hosted calibration
- Do not: continue adding large-backbone or motion-model planning here; create `laneB_round03_next_<topic>_execution.md` for Round3

This is a focused addendum to the frozen Lane B controller plan. It does not replace `docs/plans/laneB_round03plus_controller_cinemyops_hosted_topology_motion_plan.md`.

Round2 objective: turn the existing LCC repair from a one-off trick into a formal topology-aware Cine postprocess module. Do not prioritize large temporal backbones in this round. Do not train, submit, upload, or download weights in this planning pass.

All future Round2 outputs must live under:

- `results/diagnostics/care_myocardium/laneB_cine/round02_topology_lcc/`

## Current Evidence

CARE diagnostics before/after diagnostics show:

| variant | cases | class_3 Dice | class_3 HD95 | scar components |
| --- | ---: | ---: | ---: | ---: |
| pathology_direct | 13 | 0.4378 | 26.6533 | 5.5385 |
| lcc | 13 | 0.4441 | 18.7983 | 1.0000 |

LCC improves class_3 HD95 and component count without Dice loss on the smoke set. That makes topology stabilization the highest-signal near-term mechanism.

## Why Disconnected Pathology Can Cause Hosted/Local Mismatch

Local Dice can tolerate disconnected small scar/pathology islands because they contribute little volume. Hosted HD-sensitive scoring can punish the same islands strongly when a tiny remote component is far from GT or anatomy. A local class_1 myocardium proxy can also miss this failure because scar topology may not substantially alter myocardium Dice.

Potential mismatch mechanisms:

- raw `2221` components create large surface distances even with stable compact class_1.
- one-voxel or small fallback pathology can satisfy format requirements but worsen topology metrics.
- disconnected scar outside anatomy can inflate HD while preserving class_3 overlap.
- hosted `myocardium_cinemyops` may score scar/pathology, composite foreground topology, or raw-label validity differently than local class_1.

## Dangerous Topology Failures

Most dangerous for Round2:

- remote tiny false-positive pathology islands,
- multiple disconnected scar components with low largest-component fraction,
- scar bbox far from myocardium/LV anatomy bbox,
- excessive scar volume compared with train distribution,
- repair output that deletes plausible multi-focal true lesions,
- repair output that makes pathology empty and triggers fallback artifacts,
- local improvement that depends on empty-GT cases rather than GT-positive scar cases.

## How Topology Module Should Use Anatomy Prior

The topology module should use anatomy as a guardrail, not as an unconditional deletion mask.

Recommended structure:

1. Compute scar/pathology components on compact class_3 or raw `2221`.
2. Compute anatomy support from compact class_1/class_2 or raw `200/500`, optionally dilated.
3. For every scar component, record size, overlap with anatomy ROI, bbox gap, center distance, z-span, and volume fraction.
4. Keep components that pass at least one plausibility path:
   - largest component,
   - overlaps dilated anatomy ROI,
   - size above train-derived lower bound and bbox distance reasonable.
5. If all components would be deleted, fallback to original prediction and flag the case.

Do not hard-delete every component outside myocardium without a fallback path.

## DeepResearch-Derived CARE-Specific Topology Recipes

### DeepResearch-to-CARE mapping

Deep Research is used here only as mechanism inspiration. Topology-aware segmentation, HD-aware postprocess, anatomy-constrained segmentation, and CineMyoPS anatomy-motion coupling map to a CARE Cine topology module: generalized LCC, component guard, anatomy-overlap guard, bbox-distance guard, and raw `2221` topology QC. The original methods suggest that topology, surface distance, and anatomy consistency can dominate challenge robustness, but Round2 implements them as deterministic diagnostics on existing predictions. CineMA, ViTa, StrainNet, and MTI-MyoScarSeg remain watch candidates for later anatomy/motion features; they are not part of current immediate execution because LCC/topology already gives the first positive signal and no large temporal/foundation integration is needed now.

### 1. Generalized LCC

LCC is the first default topology rule, not the final method. It should become a named `topology_lcc` variant with auditable per-case outputs.

Required fields:

- removed components;
- removed voxels;
- largest component fraction;
- fallback flag;
- action reason;
- before/after class_3 Dice, HD, HD95, and component count.

LCC's value is reducing remote-island HD95 risk, not just improving Dice. Fail fast if LCC removes a GT-overlapping plausible lesion, makes pathology empty, increases fallback cases, or improves only class_1 while class_3 HD95/component behavior regresses.

### 2. Component-Size / Volume Guard

Thresholds must be estimated from CARE distributions:

- train scar volume distribution;
- raw `2221` voxel count distribution;
- scar/anatomy volume ratio;
- fold0 prediction component-size distribution.

Do not use hand-written magic thresholds. Small true scar may be clinically and metrically important, so size filtering should delete only components that are both small and implausible by another signal such as remote bbox distance or no anatomy overlap. Every deleted component must carry an `action_reason`, such as `small_remote_component`, `volume_outlier`, or `low_overlap_with_anatomy_roi`.

### 3. Myocardium-Overlap / Anatomy Guard

Anatomy is a plausibility guard, not a hard myocardium-only mask. Use dilated myocardium/LV ROI from compact class_1/class_2 or raw `200/500`. If anatomy segmentation is uncertain or the guard would delete all pathology, fallback to the original prediction and flag the case.

Required per-component logs:

- anatomy ROI overlap ratio;
- bbox distance to anatomy;
- center distance to anatomy;
- whether component was kept, removed, or forced to fallback.

The guard is valid only if it reduces remote topology failures without deleting plausible scar.

### 4. Bbox-Distance / Center-Distance Guard

Define scar component bbox gap as the shortest physical-space gap between a scar component bounding box and the anatomy bounding box. Define center distance as the physical-space distance from the component center to the anatomy center or nearest anatomy ROI.

Thresholds should come from train/fold0 distribution quantiles, not constants. This rule mainly identifies remote pathology islands and likely HD outliers. It should flag or remove only components that are distant and weakly supported by size/overlap/volume criteria.

### 5. HD-Aware Postprocess Selection

Do not use validation GT to choose the best postprocess per case. Selection must use proxy risk only:

- component count;
- largest component fraction;
- bbox gap;
- center distance;
- raw `2221` volume;
- scar/anatomy volume ratio.

Avoid overfitting local fold0. If the combined guard does not beat plain LCC on class_3 HD95/component behavior, keep LCC as the default and record why. A more complex rule is not promoted just because it is more elaborate.

### 6. Raw Label Topology QC

Compact class_3 to raw `2221` mapping must remain unchanged. Round2 raw-label QA is not zip creation.

Required QC:

- raw label subset remains legal: `{0,200,500,2221}`;
- every case records whether pathology is non-empty;
- raw `2221` component count;
- raw `2221` bbox and anatomy bbox;
- raw `2221` volume and scar/anatomy ratio;
- fallback and action reason.

This QC estimates hosted-metric risk before any packaging decision.

## Round2 Topology Candidate Table

| priority | candidate | mechanism | CARE Cine fit | current priority | smoke complexity | fail-fast criterion | hosted robustness impact |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | generalized LCC | Keep largest class_3/raw `2221` component, report removed components/voxels. | Already improves HD95 and components without Dice loss. | high | low | any GT-positive plausible lesion becomes empty or class_3 Dice drops materially. | strong: reduces remote HD outliers. |
| 2 | component-size filtering | Remove components below train-derived scar volume threshold; preserve main component. | Targets tiny FP islands that drive HD. | high | low | HD95 not improved or deleted voxels include plausible GT-overlapping lesion. | strong if hosted is HD/component sensitive. |
| 3 | myocardium-overlap filtering | Keep components overlapping dilated myocardium/LV ROI or near anatomy support. | Cine scar should be anatomically plausible; class_1/class_2 are available. | high | low-medium | true lesion outside imperfect anatomy mask is removed. | medium-high: reduces anatomy-incoherent raw `2221`. |
| 4 | bbox-distance filtering | Remove or flag scar components with bbox gap/center distance beyond train distribution. | Directly targets remote components and HD explosions. | high | low-medium | threshold deletes multi-focal plausible lesion or no threshold separates failures. | medium-high: improves HD robustness. |
| 5 | scar-volume sanity check | Guard against extreme raw `2221` volume using train p95/p99 and scar/anatomy ratio. | Existing round8 summary has train volume stats. | high | low | volume guard only improves empty-GT cases or clips true large scars. | medium: prevents hosted volume/topology penalty. |
| 6 | topology-aware ROI | Combine component size, anatomy overlap, bbox distance, and fallback into one module. | Formalizes LCC into auditable production rule. | high | medium | combined rule cannot explain per-case action or increases fallback cases. | strong if transparent and conservative. |
| 7 | HD-aware postprocess | Select repair variant per case by estimated HD risk proxies: remote component, bbox gap, largest fraction. | Directly aligned with observed local HD95 gain. | medium-high | medium | proxy reduces local HD95 but class_3 Dice drops or raw label validity worsens. | strong but must avoid overfitting local GT. |
| 8 | anatomy-constrained scar prediction | Combine anatomy logits and scar logits before compact export. | Better than postprocess long-term, but requires model/export changes. | watch | medium | class_3 recall drops or scar disappears in uncertain anatomy cases. | medium; not first topology-only smoke. |
| 9 | hard myocardium-only scar mask | Delete all scar outside myocardium. | Too aggressive because myocardium prediction can be imperfect. | postpone | low | any plausible lesion deletion. | may improve HD artifactually; unsafe. |
| 10 | large temporal foundation backbone | Replace CineMyoPS with temporal pretrained model. | Not the immediate failure mode after LCC evidence. | postpone | high | requires large weights or uncontrolled integration. | unclear; not Round2. |

## Recommended Topology Smoke Tests

1. `topology_module_lcc_plus_audit`
   - Formalize current LCC as `topology_lcc`.
   - Write before/after metrics, raw label counts, components, largest fraction, removed voxels/components, bbox distance, and fallback flag.
   - Output:
     - `results/diagnostics/care_myocardium/laneB_cine/round02_topology_lcc/topology_lcc_before_after.csv`
     - `results/diagnostics/care_myocardium/laneB_cine/round02_topology_lcc/topology_lcc_summary.md`
   - Gate: class_3 HD/HD95 and component count improve; class_3 Dice does not drop; no empty pathology fallback increase.

2. `component_anatomy_bbox_guard_grid`
   - Compare small-component, myocardium-overlap, bbox-distance, volume, and combined guards on the same fold0 smoke cases.
   - Output:
     - `results/diagnostics/care_myocardium/laneB_cine/round02_topology_lcc/topology_guard_grid.csv`
     - `results/diagnostics/care_myocardium/laneB_cine/round02_topology_lcc/topology_guard_grid.md`
   - Gate: every removed component has an explicit action reason; combined guard must beat plain LCC on HD95 or explain why LCC should remain the default.

3. `validation_style_raw_label_topology_qc`
   - No zip creation. Convert repaired compact predictions to raw-label QA tables only.
   - Check raw label subset `{0,200,500,2221}`, non-empty `2221`, raw `2221` component count, bbox, and volume.
   - Output:
     - `results/diagnostics/care_myocardium/laneB_cine/round02_topology_lcc/raw_label_topology_qc.csv`
   - Gate: raw mapping is unchanged and no repair creates unsafe empty pathology.

## Topology Failure Taxonomy Refinement

Add or refine these categories under `results/diagnostics/care_myocardium/failure_registry/`:

| category | definition | required evidence |
| --- | --- | --- |
| cine_remote_pathology_island | class_3/raw `2221` component far from anatomy bbox or GT. | component size, bbox gap, class_3 HD/HD95 contribution. |
| cine_fragmented_pathology | more than one class_3 component with low largest-component fraction. | component count, largest fraction, removed components. |
| cine_volume_outlier | scar volume above train p95/p99 or scar/anatomy ratio outlier. | raw_2221 voxels, train percentile, ratio. |
| cine_anatomy_guard_risk | component outside anatomy ROI but plausible by GT or adjacent anatomy. | overlap, bbox distance, Dice delta after deletion. |
| cine_empty_repair_risk | repair deletes all pathology or triggers fallback. | fallback flag, raw label histogram, before/after class_3 Dice. |
| hosted_local_metric_mismatch | local class_1 stable but class_3/raw topology changes materially. | class_1 vs class_3 metrics and raw topology QA. |

## Rules That May Delete True Lesions

Use these only with explicit fail-fast checks:

- Small-component filtering can remove small real scars.
- Myocardium-overlap filtering can remove true scar when myocardium segmentation is undersegmented.
- Bbox-distance filtering can remove multi-focal or unusual anatomy cases.
- Volume guard can clip true large pathology.
- LCC can remove true multi-component lesions.

Every future implementation must preserve the original prediction as fallback and record `action_reason`.

## Minimal CARE-First Extraction for Lane B

Round2 should remain a deterministic topology diagnostic. Only a topology module that passes smoke gates should later be extracted into first-party `src/` code. Candidate extraction targets are:

- `src/postprocess/topology_lcc.py`: generalized LCC with removed-component accounting and fallback handling.
- `src/postprocess/component_filter.py`: distribution-derived component-size and volume guard.
- `src/postprocess/anatomy_guard.py`: dilated myocardium/LV ROI overlap guard.
- `src/postprocess/bbox_guard.py`: bbox gap and center-distance guard based on distribution quantiles.
- `src/diagnostics/component_stats.py`: component count, largest fraction, removed voxels, and per-component action records.
- `src/diagnostics/raw_label_qc.py`: compact-to-raw topology QA for `{0,200,500,2221}`.

This round must not rewrite the Cine trainer, connect a large temporal backbone, integrate CineMA/ViTa/StrainNet/MTI-MyoScarSeg, or refactor the full pipeline. The implementation should prove topology value first using existing compact fold0 predictions.

## Required Metrics And Comparability

Every future Round2 Lane B implementation must report:

- compact class_1 and class_3 Dice, HD, HD95,
- raw `2221` voxels and component count,
- largest component fraction,
- bbox gap/center distance to anatomy,
- fallback cases and action reasons,
- raw label subset validation `{0,200,500,2221}`,
- no aggregate-only conclusions.

Do not accept:

- class_1-only gains,
- Dice gain with HD95/component regression,
- empty pathology fallback increase,
- silent compact/raw label changes,
- validation zip creation in this topology-only execution phase.

## Next Implementation Prompt Draft

Implement Lane B Round2 topology diagnostics only. Do not train, submit Slurm, download weights, create a validation zip, upload, modify label semantics, modify the evaluator, or change controller plans.

Create or extend a topology postprocess diagnostic under `scripts/diagnostics/` or `scripts/evaluation/` that reads existing compact CineMyoPS fold0 predictions and writes all outputs under `results/diagnostics/care_myocardium/laneB_cine/round02_topology_lcc/`.

Execute only:

1. `topology_module_lcc_plus_audit`
   - formalize current LCC as `topology_lcc`;
   - record removed components, removed voxels, largest component fraction, fallback flag, and action reason.

2. `component_anatomy_bbox_guard_grid`
   - compare component-size, volume, myocardium-overlap, bbox-distance, center-distance, and combined guards;
   - derive thresholds from train/fold0 distributions, not magic constants;
   - preserve original predictions as fallback.

3. `validation_style_raw_label_topology_qc`
   - convert compact predictions to raw-label QA tables only;
   - do not create a zip;
   - verify legal raw label subset, non-empty raw `2221`, component count, bbox, volume, and scar/anatomy ratio.

Required variants:

- `pathology_direct`
- `topology_lcc`
- `small_component_filter`
- `myocardium_overlap_guard`
- `bbox_distance_guard`
- `volume_guard`
- `combined_topology_guard`

Required outputs:

- `topology_lcc_before_after.csv/md`
- `topology_guard_grid.csv/md`
- `raw_label_topology_qc.csv`
- updated failure registry Markdown files for Cine topology categories.

Preserve compact labels (`1=myocardium`, `2=LV`, `3=scar`) and raw mapping (`3 -> 2221`). Evaluate class_1 and class_3 separately with Dice/HD/HD95. Do not accept aggregate-only success, empty-GT artifact improvement, or Dice gain with HD95/component regression. Fail fast if any rule deletes plausible GT-positive lesions, creates empty pathology fallback, improves only class_1, worsens class_3 HD95/component count, changes compact/raw label semantics, or changes evaluator/preprocessing behavior silently.
