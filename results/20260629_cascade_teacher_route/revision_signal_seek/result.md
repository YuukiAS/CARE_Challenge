# Result Cascade Signal-Seek Revision

Status: completed; no signal-seek variant selected.

## What Was Done

- Submitted `jobs/src/run_cascade_oof_refiner_revision_signal_seek.sh` as Slurm
  job `57275246_[0-1]` on `htzhulab`.
- Ran two isolated variants under
  `results/20260629_cascade_teacher_route/revision_signal_seek/variants/`:
  - `nnunet_pathology_teacher_srr_refiner_signal_seek`
  - `coarse_to_fine_srr_roi_signal_seek`
- Both jobs completed with exit code `0:0` in `00:05:05`.
- Both variants exported `44/44` validation predictions and wrote summary,
  metrics, and decision tables.

## Result

The signal-seek revision did not rescue the cascade route.

- `nnunet_pathology_teacher_srr_refiner_signal_seek` produced T2-positive edema
  Dice delta `+0.0009` and all-case scar Dice delta `+0.0020`, but worsened
  T2-positive edema HD95 by `-0.0665`, edema component count by `-0.0625`, and
  all-case scar HD95 by `-0.3773`.
- `coarse_to_fine_srr_roi_signal_seek` produced T2-positive edema Dice delta
  `+0.0025` and all-case scar Dice delta `+0.0033`, but worsened T2-positive
  edema HD95 by `-0.0215`, component count by `-0.6875`, remote FP by
  `-0.3125`, and all-case scar HD95 by `-0.4362`.

Selection: `STOP_NO_SIGNAL_SEEK_ROUTE`.

## Implication

The cascade family has now failed in three ways:

- formal baseline variants: tiny deltas, no robust signal;
- component-guard revision: too conservative, near-zero deltas;
- signal-seek revision: slightly larger Dice deltas but worse HD95 and
  component/remote-FP behavior.

This points away from cascade threshold/capacity tuning as the main rescue path
for this sprint. Current mainline completion still depends on the SRR-v2 missing
variants and their aggregation.

No validation upload, upload-ready package, fold expansion, evaluator change, or
label mapping change was performed.
