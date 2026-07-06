# Cine Registration Repair Report

status: `EXECUTED_UNAUDITED`
cine_decision: `CINE_REGISTRATION_BLOCKED_AFTER_REPAIR_ATTEMPT`

- safe cases selected: `Case1001,Case1002,Case1003`
- non-reference pairs attempted: `6`
- SimpleITK Demons iterations: `10`
- ANTsPy available: `True`; SyNOnly attempted: `True`; iterations: `5`
- VoxelMorph module available: `True`; trained usable weights: `false`
- temporal dictionary status: `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP_AFTER_REPAIR_ATTEMPT`

Evidence files: `registration_same_subset_matrix.csv`, `cine_metrics_summary.csv`, and `temporal_dictionary_evidence.csv`.

This report does not copy M5 as a conclusion. It records a bounded M7 continued repair attempt and keeps Cine blocked unless a usable non-reference registration row is actually present.
