# Gate B-R2 Scale-Grid Diagnostic Report

created_at_utc: `2026-07-28T03:15:18Z`

## Decision

`GATE_B_R2_NO_TRAIN_SIDE_SAFE_INFERENCE_SELECTION_REPAIR_FOUND`

No fold expansion is authorized. The R2 no-retraining checkpoint/scale-grid search used only fixed train-side complete inner cases and did not find any eligible candidate. Outer fold0 was not used for selection and was not re-evaluated.

## Best Train-Side Recipe

- checkpoint step: `4000`
- checkpoint: `results/20260727_care_dg_dual_pathology_validation/runtime/repaired_formal_scar_priority/fold0/checkpoints/checkpoint_step04000.pt`
- scar scale: `1.0`
- edema scale: `0.25`
- status: `FAIL`
- failure: `no_pathology_improves_by_more_than_0.005`
- help/harm on inner: `25` / `7`

| pathology | Dice delta vs inner anchor | HD95 ok | remote FP ok | component ok |
|---|---:|---:|---:|---:|
| scar | 0.004258 | True | True | True |
| edema_zone | 0.000630 | True | True | True |
| pure_edema | 0.000607 | True | True | True |

## Interpretation

The inference/selection repair space is exhausted for this fold under the current frozen model family: eight checkpoints times 64 scar/edema scale pairs produced zero train-side candidates satisfying the same expansion gate. The best recipe is safe but too weak: scar reaches only `+0.004258`, and edema-zone/pure-edema are far below the required `+0.005` improvement. This means the remaining failure is learned correction efficacy, not just checkpoint selection, Gaussian blending, scar-priority composition, or scalar inference gain.

## Boundary

Do not start folds 1-4, all-data fit, validation packaging, validation upload, Docker upload, a new Slurm job, or runtime push from this evidence. The allocation remains preserved for authorized same-scope work.

## Evidence

- scale grid: `results/20260727_care_dg_dual_pathology_validation/runtime/repaired_formal_scar_priority/fold0/gate_b_r2_scale_diagnostic/gate_b_r2_scale_grid_selection.csv`
- root summary: `results/20260727_care_dg_dual_pathology_validation/gate_b_r2_summary.json`
- validator: `results/20260727_care_dg_dual_pathology_validation/gate_b_r2_validator_report.json`
