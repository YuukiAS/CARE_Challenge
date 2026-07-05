---
task_key: "20260705_srr_v3_milestone_plan_index"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "planning_index"
risk_level: "medium"
allow_code_change: false
allow_shell_command: false
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "SRR-v3 milestone task graph / hard-gated planning"
expected_result_dir: "results/20260705_srr_v3_milestone_plan_index/"
blocking: false
---

# SRR-v3 / SRR-ProposeRefine Milestone Plan Index

This file replaces the previous all-in-one SRR-v2.5 goal pattern with small hard-gated milestones. Each milestone has an exact `results/<task_key>/` directory, required outputs, completion check, and a separate read-only review expectation. MyoPS is the primary line. Cine is secondary. No milestone below authorizes validation packaging, validation upload, route promotion, fold expansion, or hosted metric claims.

## Hard-Gate Rule

Before executing the scientific task, enforce the hard-gate policy: exact task graph, strict validator, completion-check-before-final-audit, minimum effective training, and current-bad-packet regression. If any hard gate fails, stop with NEEDS_REVISION or NEEDS_EVIDENCE; do not continue to final audit.

## Ordered Milestone Graph

| order | task_key | path | expected result directory | blocking for next | purpose |
| ---: | --- | --- | --- | --- | --- |
| 0 | `20260705_srr_v3_m0_architecture_master_contract` | `prompts/tasks/20260705_srr_v3_m0_architecture_master_contract.md` | `results/20260705_srr_v3_m0_architecture_master_contract/` | yes | lock the SRR-v3 architecture story, interfaces, metrics, and hard gates before code |
| 1 | `20260705_srr_v3_m1_runtime_instrumentation_gate` | `prompts/tasks/20260705_srr_v3_m1_runtime_instrumentation_gate.md` | `results/20260705_srr_v3_m1_runtime_instrumentation_gate/` | yes | export missing gate/residual/prototype/context evidence without training |
| 2 | `20260705_srr_v3_m2_myops_bounded_runtime_repair` | `prompts/tasks/20260705_srr_v3_m2_myops_bounded_runtime_repair.md` | `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/` | yes | repair MyoPS runtime architecture gaps with small smoke only |
| 3 | `20260705_srr_v3_m3_myops_min_effective_pilot_training` | `prompts/tasks/20260705_srr_v3_m3_myops_min_effective_pilot_training.md` | `results/20260705_srr_v3_m3_myops_min_effective_pilot_training/` | yes | run a minimum-effective pilot, not full folds, after M0-M2 pass |
| 4 | `20260705_srr_v3_m4_myops_mechanism_ablation_readiness` | `prompts/tasks/20260705_srr_v3_m4_myops_mechanism_ablation_readiness.md` | `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/` | yes | isolate which SRR-v3 mechanisms open the gate and help/harm nnU-Net |
| 5 | `20260705_srr_v3_m5_cine_secondary_contract` | `prompts/tasks/20260705_srr_v3_m5_cine_secondary_contract.md` | `results/20260705_srr_v3_m5_cine_secondary_contract/` | no for MyoPS | keep Cine as a secondary registration/temporal evidence line |

## Execution Policy

Execute only one milestone at a time. The executor/controller session writes
required outputs, `completion_check.md`, `review_request.md`, and
`MANIFEST.md`, then stops. It must not write `review.md`, must not approve
itself, and must not start the next milestone. Do not start a later blocking
milestone until a separate read-only `review.md` supports continuation with the
exact audited-go token. A diagnostic result may be useful, but it must not be
promoted as a full implementation.

## First Task To Execute

Start with `prompts/tasks/20260705_srr_v3_m0_architecture_master_contract.md`.
