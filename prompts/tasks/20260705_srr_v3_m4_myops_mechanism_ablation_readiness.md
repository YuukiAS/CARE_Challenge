---
task_key: "20260705_srr_v3_m4_myops_mechanism_ablation_readiness"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "milestone"
milestone_id: "M4"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "MyoPS mechanism ablation readiness / bounded help-harm attribution"
expected_result_dir: "results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/"
prerequisite_review: "results/20260705_srr_v3_m3_myops_min_effective_pilot_training/review.md:M3_AUDITED_GO"
required_outputs:
  - "result.md"
  - "ablation_matrix_contract.md"
  - "ablation_config_table.csv"
  - "same_split_help_harm.csv"
  - "gate_residual_by_ablation.csv"
  - "prototype_dictionary_by_ablation.csv"
  - "proposal_refinement_by_ablation.csv"
  - "mechanism_decision.md"
  - "completion_check.md"
  - "review_request.md"
  - "MANIFEST.md"
forbidden_substitutes:
  - "single mixed model only"
  - "ablation without same-split nnU-Net help/harm"
  - "undertrained smoke rows as mechanism conclusion"
  - "threshold-only ablation"
  - "route promotion"
---

# Milestone M4: MyoPS Mechanism Ablation Readiness

## Milestone Review Gate

This is an executor/controller milestone only. Execute M4 and stop after writing
all required outputs, `completion_check.md`, `review_request.md`, and
`MANIFEST.md`. Do not write `review.md`, do not mark `M4_AUDITED_GO`, do not
approve yourself, and do not start any later milestone.

M4 may start only after
`results/20260705_srr_v3_m3_myops_min_effective_pilot_training/review.md`
contains `M3_AUDITED_GO`. `review_request.md` must request a separate read-only
review of the M4 result directory and must state that any later MyoPS milestone
remains blocked until `M4_AUDITED_GO`.

## Goal

After a minimum-effective pilot has passed review, isolate which SRR-v3 mechanisms are actually responsible for help, harm, or near-identity. This milestone prepares bounded ablations only; it does not train full folds or promote a route.

## Prerequisite Gate

Before starting, verify that `results/20260705_srr_v3_m3_myops_min_effective_pilot_training/review.md` exists and contains `M3_AUDITED_GO`. If not, stop with `M4_BLOCKED_BY_M3`.

## Required Ablation Axes

At minimum define and, if allowed by resources, run bounded ablations for:

- closed-gate identity fallback;
- no nnU-Net anchor;
- gate enabled but residual frozen;
- residual enabled but dictionary/prototypes disabled;
- real prototypes versus deterministic/no-prototype;
- semantic retrieval on/off;
- component proposal ranking on/off;
- anatomy distance/ROI prior on/off;
- local refinement on/off;
- no-T2 edema safety preserved in every row.

## Required Evidence

Each ablation row must report:

- same-split nnU-Net help/harm by class;
- gate open-rate and residual magnitude;
- prototype and dictionary diagnostics;
- proposal/refinement recall, component count, remote FP, and HD95;
- hard subgroup results for CenterC and T2-present edema;
- exact training/provenance budget.

If a row is not run, mark it `NOT_RUN_WITH_REASON`, not omitted.

## Required Outputs

Write all required outputs under `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/`.

`completion_check.md` must contain one of:

- `M4_READY_FOR_REVIEW`
- `M4_NEEDS_REVISION`
- `M4_NEEDS_EVIDENCE`
- `M4_RESOURCE_BLOCKED`

`review_request.md` must state that `review.md` is intentionally absent at
executor stop and that later MyoPS milestones remain blocked until a separate
read-only reviewer writes `M4_AUDITED_GO`.

A separate read-only reviewer should later write `review.md` with one of:

- `M4_AUDITED_GO`
- `M4_AUDITED_NEEDS_REVISION`
- `M4_AUDITED_NEEDS_EVIDENCE`

## Completion Gate

Do not mark ready unless the ablation matrix can identify whether SRR is near-identity because of gate closure, residual weakness, prototype failure, proposal failure, or decode behavior. Do not call any ablation a route candidate.
