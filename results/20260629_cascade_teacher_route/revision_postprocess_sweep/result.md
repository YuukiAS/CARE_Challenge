# Result Cascade Postprocess Sweep

Status: completed; no postprocess mode selected.

## What Was Done

- Added `scripts/evaluation/postprocess_cascade_revision_sweep.py`.
- Used signal-seek predictions as source inputs.
- Generated four baseline-support pruning modes for each of two source variants:
  - `pathology_overlap_dilate1`
  - `pathology_overlap_dilate2`
  - `edema_overlap_dilate2_keep_scar`
  - `top2_pathology_overlap_dilate2`
- Wrote postprocessed predictions under
  `results/20260629_cascade_teacher_route/revision_postprocess_sweep/variants/`.
- Evaluated each mode with the existing `laneA_round10_refiner_eval.py`.

## Result

All eight postprocessed candidates failed the evaluator as
`fail_stop_refiner_candidate`.

The sweep did show the expected mechanism: stricter component support can reduce
component burden. However, it did not remove remote false-positive regressions
or create a meaningful Dice/HD95 gain. The best coarse-to-fine top-2 mode still
had only `+0.0024` T2-positive edema Dice and remote FP worsening `-0.0625`.

Selection: `STOP_NO_POSTPROCESS_ROUTE`.

## Implication

The cascade family now has negative evidence from formal training, conservative
component guards, stronger signal-seeking residuals, and simple postprocessing.
The remaining active MyoPS route to resolve is SRR-v2 and its extra
light-refine probes.

No validation upload, upload-ready package, fold expansion, evaluator change, or
label mapping change was performed.
