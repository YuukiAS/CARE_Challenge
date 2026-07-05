# Downstream Milestone Graph

status: `M0_READY_FOR_REVIEW`

## Graph

| milestone | task path | expected result dir | prerequisite review | required executor stop files | continuation token |
| --- | --- | --- | --- | --- | --- |
| M0 | `prompts/tasks/20260705_srr_v3_m0_architecture_master_contract.md` | `results/20260705_srr_v3_m0_architecture_master_contract/` | hard-gate repair `AUDITED_GO` | `completion_check.md`, `review_request.md`, `MANIFEST.md` | `M0_AUDITED_GO` |
| M1 | `prompts/tasks/20260705_srr_v3_m1_runtime_instrumentation_gate.md` | `results/20260705_srr_v3_m1_runtime_instrumentation_gate/` | `results/20260705_srr_v3_m0_architecture_master_contract/review.md:M0_AUDITED_GO` | `completion_check.md`, `review_request.md`, `MANIFEST.md` | `M1_AUDITED_GO` |
| M2 | `prompts/tasks/20260705_srr_v3_m2_myops_bounded_runtime_repair.md` | `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/` | `results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md:M1_AUDITED_GO` | `completion_check.md`, `review_request.md`, `MANIFEST.md` | `M2_AUDITED_GO` |
| M3 | `prompts/tasks/20260705_srr_v3_m3_myops_min_effective_pilot_training.md` | `results/20260705_srr_v3_m3_myops_min_effective_pilot_training/` | `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md:M2_AUDITED_GO` | `completion_check.md`, `review_request.md`, `MANIFEST.md` | `M3_AUDITED_GO` |
| M4 | `prompts/tasks/20260705_srr_v3_m4_myops_mechanism_ablation_readiness.md` | `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/` | `results/20260705_srr_v3_m3_myops_min_effective_pilot_training/review.md:M3_AUDITED_GO` | `completion_check.md`, `review_request.md`, `MANIFEST.md` | `M4_AUDITED_GO` |
| M5 | `prompts/tasks/20260705_srr_v3_m5_cine_secondary_contract.md` | `results/20260705_srr_v3_m5_cine_secondary_contract/` | `results/20260705_srr_v3_m0_architecture_master_contract/review.md:M0_AUDITED_GO` | `completion_check.md`, `review_request.md`, `MANIFEST.md` | `M5_AUDITED_DIAGNOSTIC_GO` |

## Ordering Rules

- MyoPS primary chain: M0 -> M1 -> M2 -> M3 -> M4.
- Cine secondary chain: M0 -> M5.
- M5 does not block M1-M4 unless a later explicit user/GPT task changes priority.
- Every milestone requires a separate read-only `review.md` before the next milestone may start.
- Executor `completion_check.md` is readiness for review only; it is not continuation permission.

## Required Output Verification

Each downstream milestone task declares exact `required_outputs` in its frontmatter. A future executor must verify exact filenames, not similar replacements. Missing result directory or missing required file is a hard blocker.

## Forbidden Jump

Do not run M1 from this M0 executor session. Do not create `results/20260705_srr_v3_m1_runtime_instrumentation_gate/` from M0.
