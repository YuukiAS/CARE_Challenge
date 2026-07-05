# Manifest

task: `prompts/tasks/20260705_srr_v3_m0_architecture_master_contract.md`
result_dir: `results/20260705_srr_v3_m0_architecture_master_contract/`
status: `EXECUTED_UNAUDITED`
self_assessed_status: `M0_READY_FOR_REVIEW`

## Files

- `result.md`: executor summary, inputs read, command evidence, and stop boundary.
- `architecture_contract.md`: binding SRR-v3 architecture story and component evidence requirements.
- `interface_contract.md`: exact model input/output and runtime-active module contract.
- `metric_contract.md`: metric, help/harm, adequacy, and no-T2 edema reporting contract.
- `hard_gate_mapping.md`: M0 hard-gate evidence and known-bad-packet validator rerun.
- `downstream_milestone_graph.md`: exact M1-M5 paths, result dirs, prerequisites, and continuation tokens.
- `completion_check.md`: executor completion check; contains `M0_READY_FOR_REVIEW`.
- `review_request.md`: request for separate read-only M0 review.
- `MANIFEST.md`: this file.

## Intentionally Absent

- `review.md`: intentionally absent. A separate read-only reviewer must write it.

## Forbidden Actions Not Performed

- model/training source edits
- training
- validation packaging
- external upload
- route promotion
- M1 execution
