# Batch7 Repair Implementation Snapshot

Wave0 implementation state:

- Current repair output root exists.
- No repair Slurm jobs have been submitted.
- No repair training optimizer steps have been run.
- The old Batch7 mechanism tables are marked superseded and retained in their historical result directory.
- `configs/srr_production/myops_batch7_repair.yaml` now parses as YAML while preserving the original superseded evidence file list and reason string.

Wave1/Wave2 code work started after bootstrap:

- Mode-isolated intervention runner and aggregator scripts are being added under `scripts/evaluation/`.
- The model discovery path is being split from anchor-conditioned confirmation.
- Semantic memory loading is being hardened so required `cross_fitted_memory.*` state cannot be silently absent under `strict=False`.
