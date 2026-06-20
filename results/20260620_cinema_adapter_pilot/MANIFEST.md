# Artifact Manifest 20260620 Cinema Adapter Pilot

task: `prompts/tasks/20260620_cinema_adapter_pilot.md`
result: `results/20260620_cinema_adapter_pilot/result.md`
review: `results/20260620_cinema_adapter_pilot/review.md`

## Summary

Migrated manifest for the CineMA -> CARE CineMyoPS adapter pilot. The original execution artifacts remain in the CARE domain-specific result roots; this manifest provides the task-scoped index required by the current AI bridge protocol.

## Primary Artifacts

- `results/20260620_cinema_adapter_pilot/result.md`: migrated execution report.
- `results/20260620_cinema_adapter_pilot/review.md`: migration-time review.
- `docs/notes/cinema_adapter_pilot_20260620.md`: durable note from the pilot.

## Generated Scripts And Jobs

- `scripts/diagnostics/cinemyops_raw_structure_audit.py`: raw CineMyoPS structure audit script.
- `scripts/external_adapters/cinema_care_adapter.py`: isolated CineMA -> CARE adapter.
- `jobs/experiments/run_cinema_adapter_pilot.sh`: Slurm pilot entrypoint.

## Existing Output Roots

- `results/diagnostics/cinemyops_raw_structure_audit_20260620/`: raw structure audit summary outputs.
- `results/cinema_adapter/external/CineMA/`: cloned CineMA code used by the pilot.
- `results/cinema_adapter/python_deps/`: isolated Python dependencies for the pilot.
- `results/cinema_adapter/metadata_check_20260620/`: metadata dry-run outputs.
- `results/cinema_adapter/smoke_cpu_1case_20260620/`: CPU smoke output area.
- `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/`: full pilot predictions and metrics.

## Reproduction

See `results/20260620_cinema_adapter_pilot/result.md` for the exact commands, Slurm job id, log path, and failure/retry notes.

## Notes

This migration did not move large existing output directories, so existing CARE paths and downstream references remain valid.
