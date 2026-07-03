# Train OOF Protocol

task_key: `20260703_nnunet_oof_component`
scorer_variant: `oof_scar_component_score`

## Split Contract

- Dataset: `Dataset501_CAREMyoPS`.
- Fold0 validation cases: `44` cases from `data/benchmarks/protocol/splits_MyoPS.json`.
- Train-side OOF evidence: `176` fold0-training cases, read from existing nnU-Net validation outputs for folds `1,2,3,4`.
- Fold0 validation ground truth use: evaluation only after scorer threshold was frozen.
- Fold0 validation ground truth leakage into threshold selection: not used.

## Feature Contract

- Decision features are prefixed with `decision_`.
- GT-derived/evaluation annotations are prefixed with `evaluation_`.
- Threshold selection used the decision score and train-side OOF metrics only.
- Selected scar score threshold: `1.30`.

## Forbidden Actions

- No network.
- No validation upload.
- No upload-ready package.
- No new fold training or new fold inference.
- No label/evaluator/fold split change.
