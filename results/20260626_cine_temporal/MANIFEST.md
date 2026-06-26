# Manifest 20260626 Cine Temporal

## Task

- `prompts/tasks/20260626_cine_temporal.md`

## Result Files

- `results/20260626_cine_temporal/result.md`
- `results/20260626_cine_temporal/decision.md`
- `results/20260626_cine_temporal/safe_split.md`
- `results/20260626_cine_temporal/metrics_summary.md`
- `results/20260626_cine_temporal/failure_interpretation.md`
- `results/20260626_cine_temporal/case_metrics.csv`
- `results/20260626_cine_temporal/frame_retrieval.csv`
- `results/20260626_cine_temporal/summary_metrics.csv`

## Code

- `scripts/evaluation/cinemyops_temporal_preflight.py`

## Inputs

- `results/20260625_cine_geometry/safe_cases.csv`
- `results/20260625_cine_geometry/mismatch_cases.csv`
- `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics.csv`
- Existing CineMA adapter prediction files referenced by that metrics CSV.

## Notes

- No validation upload was performed.
- No external data, external weights, network download, or hosted submission was used.
- No prediction directory, checkpoint directory, `.nii.gz`, `.pt`, `.pth`, or `.ckpt` artifact is part of this result manifest.
