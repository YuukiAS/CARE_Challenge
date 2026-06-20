# Artifact Manifest 20260620 T2 Edema Pilot

task: `prompts/tasks/20260620_t2_edema_pilot.md`
result: `results/20260620_t2_edema_pilot/result.md`
review: `results/20260620_t2_edema_pilot/review.md`

## Summary

Migrated manifest for the MyoPS T2-present edema expert/routing pilot. The original execution artifacts remain in CARE's experiment result roots; this manifest provides the task-scoped index required by the current AI bridge protocol.

## Primary Artifacts

- `results/20260620_t2_edema_pilot/result.md`: migrated execution report.
- `results/20260620_t2_edema_pilot/review.md`: migration-time review.
- `docs/notes/t2_present_edema_pilot_20260620.md`: durable note from the pilot.

## Generated Scripts And Jobs

- `scripts/experiments/t2_present_edema_pilot.py`: feature/routing pilot script.
- `jobs/experiments/run_t2_present_edema_pilot.sh`: optional Slurm entrypoint.

## Existing Output Roots

- `results/experiments/t2_present_edema_20260619_131434/summary.md`: summary report.
- `results/experiments/t2_present_edema_20260619_131434/manifest.json`: original output manifest.
- `results/experiments/t2_present_edema_20260619_131434/myops_case_metadata.csv`: train case metadata.
- `results/experiments/t2_present_edema_20260619_131434/myops_group_summary.csv`: modality group summary.
- `results/experiments/t2_present_edema_20260619_131434/myops_validation_modality_metadata.csv`: validation metadata.
- `results/experiments/t2_present_edema_20260619_131434/feature_baseline_threshold_grid.csv`: threshold grid results.
- `results/experiments/t2_present_edema_20260619_131434/feature_baseline_case_metrics.csv`: case metrics.
- `results/experiments/t2_present_edema_20260619_131434/feature_baseline_summary.json`: selected baseline summary.
- `results/experiments/t2_present_edema_20260619_131434/feature_baseline_predictions/all_complete/`: prediction outputs.

## Reproduction

See `results/20260620_t2_edema_pilot/result.md` for the exact commands, interpreter, output paths, and failure/retry notes.

## Notes

This migration did not move large existing output directories, so existing CARE paths and downstream references remain valid.
