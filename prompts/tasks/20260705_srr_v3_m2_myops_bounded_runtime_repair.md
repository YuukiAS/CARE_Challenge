---
task_key: "20260705_srr_v3_m2_myops_bounded_runtime_repair"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "milestone"
milestone_id: "M2"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "MyoPS bounded SRR-v3 runtime repair / no full-fold training"
expected_result_dir: "results/20260705_srr_v3_m2_myops_bounded_runtime_repair/"
prerequisite_review: "results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md:M1_AUDITED_GO"
required_outputs:
  - "result.md"
  - "code_diff_summary.md"
  - "runtime_gap_closure_table.csv"
  - "strong_encoder_context_sanity.csv"
  - "prototype_t2_coverage_sanity.csv"
  - "proposal_refinement_sanity.csv"
  - "baseline_gate_safety_sanity.csv"
  - "no_t2_safety_sanity.csv"
  - "unit_test_report.md"
  - "completion_check.md"
  - "review_request.md"
  - "MANIFEST.md"
forbidden_substitutes:
  - "formal full fold training"
  - "6-step bounded checkpoint as scientific evidence"
  - "edema prototype bank with zero T2-present positives"
  - "gate closed by default with no correction-positive sanity"
  - "full-volume residual called local refinement"
  - "plain nnU-Net copy as SRR"
  - "route promotion"
---

# Milestone M2: MyoPS Bounded Runtime Repair

## Milestone Review Gate

This is an executor/controller milestone only. Execute M2 and stop after writing
all required outputs, `completion_check.md`, `review_request.md`, and
`MANIFEST.md`. Do not write `review.md`, do not mark `M2_AUDITED_GO`, do not
approve yourself, and do not start M3.

M2 may start only after
`results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md` contains
`M1_AUDITED_GO`. `review_request.md` must request a separate read-only review of
the M2 result directory and must state that M3 remains blocked until
`M2_AUDITED_GO`.

## Goal

Repair the MyoPS runtime architecture so that the next pilot can train a real SRR-v3 correction instead of a near-identity diagnostic packet. This is the first bounded implementation milestone. It may modify model/training/evaluation code and run toy or small-case smoke tests, but it must not run full folds, package validation, upload, or claim route promotion.

## Prerequisite Gate

Before starting, verify that `results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md` exists and contains `M1_AUDITED_GO`. If not, stop with `M2_BLOCKED_BY_M1`.

## Required Runtime Repairs

Close these gaps with code and small runtime evidence:

1. Baseline-preserving anchor/residual safety: closed gate exactly reproduces nnU-Net, but the model also has a correction-positive sanity path where the gate can open on uncertain or known-error regions.
2. Strong encoder/context path: `strong_4scale` must be callable with realistic channel settings or a documented memory-safe alternative; tiny `base_channels=4` smoke cannot be the only evidence.
3. Pathology proposal/refinement path: scar and edema proposals must feed bounded local ROI refinement and emit proposal/refinement diagnostics by class.
4. Real prototype/dictionary runtime evidence: prototype fitting must include T2-present edema-positive and edema-safe-negative cases when such cases exist in the selected train subset; if none exist, the sampler must select a T2-present edema subset or stop with `NEEDS_EVIDENCE`.
5. No-T2 edema safety: loss, proposal, ROI, final logits, decode, and export must remain blocked or safely inert for no-T2 cases.
6. Cache/provenance isolation: every smoke output must record checkpoint path, prototype source, selected case ids, encoder profile, optimizer steps, and eval case ids.

## Smoke Scale Only

Allowed smoke tests:

- one-batch overfit on a selected scar-positive case;
- one-batch overfit on a selected T2-present edema-positive case;
- explicit hard-subgroup eval on a small case list;
- CPU or single-GPU smoke under a strict runtime limit.

Disallowed:

- full fold training;
- validation package or upload;
- route-promotion claim;
- final audit.

## Strict Validation

- Unit tests must cover closed-gate identity, correction-positive gate opening on synthetic error, T2-present prototype selection, no-T2 edema blocking, and bounded local crop behavior.
- `runtime_gap_closure_table.csv` must mark each required runtime gap as `CLOSED`, `PARTIAL`, or `NEEDS_EVIDENCE` with an exact artifact path.
- The default strict validator must be run and documented.

## Required Outputs

Write all required outputs under `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/`.

`completion_check.md` must contain one of:

- `M2_READY_FOR_REVIEW`
- `M2_NEEDS_REVISION`
- `M2_NEEDS_EVIDENCE`

`review_request.md` must state that `review.md` is intentionally absent at
executor stop and that M3 remains blocked until a separate read-only reviewer
writes `M2_AUDITED_GO`.

A separate read-only reviewer should later write `review.md` with one of:

- `M2_AUDITED_GO`
- `M2_AUDITED_NEEDS_REVISION`
- `M2_AUDITED_NEEDS_EVIDENCE`

## Completion Gate

Do not mark ready if the T2-present edema prototype bank is empty, if gate statistics remain unavailable, if local refinement is not bounded-crop evidence, or if no-T2 edema safety is not end-to-end exported.
