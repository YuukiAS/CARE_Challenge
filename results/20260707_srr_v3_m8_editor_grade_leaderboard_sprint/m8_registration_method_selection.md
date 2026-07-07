# Cine Registration Repair Report

status: `EXECUTED_UNAUDITED`
cine_decision: `CINE_REGISTRATION_BLOCKED_AFTER_MATURE_M8_ATTEMPT`

- safe cases selected: `Case1001,Case1002,Case1003,Case1004,Case1005,Case1006,Case1007,Case1008,Case1010,Case1011,Case1012,Case1013`
- non-reference pairs attempted: `24`
- SimpleITK Demons iterations: `40`
- ANTsPy available: `True`; SyNOnly attempted: `True`; iterations: `25`
- VoxelMorph module available: `True`; trained usable weights: `false`
- temporal dictionary status: `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP_AFTER_REPAIR_ATTEMPT`

Evidence files: `registration_same_subset_matrix.csv`, `cine_metrics_summary.csv`, and `temporal_dictionary_evidence.csv`.

This report records an M8 mature Cine registration attempt and keeps Cine blocked unless a usable non-reference registration row is actually present.
