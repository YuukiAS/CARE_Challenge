---
task_key: "20260705_srr_v3_m1_runtime_instrumentation_gate"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "milestone"
milestone_id: "M1"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "runtime instrumentation / gate-residual-prototype evidence export"
expected_result_dir: "results/20260705_srr_v3_m1_runtime_instrumentation_gate/"
prerequisite_review: "results/20260705_srr_v3_m0_architecture_master_contract/review.md:M0_AUDITED_GO"
required_outputs:
  - "result.md"
  - "instrumentation_contract.md"
  - "gate_residual_export.csv"
  - "prototype_coverage_export.csv"
  - "anchor_context_alignment_export.csv"
  - "no_t2_safety_export.csv"
  - "instrumentation_unit_tests.md"
  - "completion_check.md"
  - "review_request.md"
  - "MANIFEST.md"
forbidden_substitutes:
  - "new training run"
  - "full fold training"
  - "metrics without gate/residual distributions"
  - "prototype summary without T2-present edema coverage"
  - "diagnostic non-strict validator as completion pass"
---

# Milestone M1: Runtime Instrumentation Gate

## Milestone Review Gate

This is an executor/controller milestone only. Execute M1 and stop after writing
all required outputs, `completion_check.md`, `review_request.md`, and
`MANIFEST.md`. Do not write `review.md`, do not mark `M1_AUDITED_GO`, do not
approve yourself, and do not start M2.

M1 may start only after
`results/20260705_srr_v3_m0_architecture_master_contract/review.md` contains
`M0_AUDITED_GO`. `review_request.md` must request a separate read-only review of
the M1 result directory and must state that M2 remains blocked until
`M1_AUDITED_GO`.

## Goal

Close the evidence gaps identified by the SRR-v2.5 evidence supplement audit before changing scientific behavior. This milestone should add or run lightweight eval-only instrumentation so that future training can answer why a prediction is near-identity, harmful, or helpful. It must not run long training, package validation, upload, expand folds, or claim route promotion.

## Prerequisite Gate

Before starting, verify that `results/20260705_srr_v3_m0_architecture_master_contract/review.md` exists and contains `M0_AUDITED_GO`. If not, stop with `M1_BLOCKED_BY_M0`.

## Required Work

Instrument the current SRR-ProposeRefine path without changing training logic, except for minimal read-only/export helpers if needed. Export per-case and aggregate statistics for:

- baseline residual gate mean, p95, open-rate at thresholds `0.01,0.05,0.10,0.25,0.50`;
- bounded delta absolute mean, p95, max by class;
- actual correction magnitude `gate * bounded_delta` by class;
- decode label delta counts versus nnU-Net by class;
- anchor confidence/uncertainty distributions;
- prototype bank counts and T2-present edema coverage;
- anchor/component tensor alignment checks;
- no-T2 edema loss/logit/decode/export safety.

Use existing checkpoints and a small explicit eval set if needed. Full fold eval-only is allowed only if it reuses existing predictions/checkpoints and does not train; if full fold is too slow, write `EVIDENCE_NOT_FOUND` for the full-fold field and provide the explicit-case evidence.

## Strict Validation

- The default strict anti-laziness validator must fail the known bad packet.
- Instrumentation outputs must have non-empty headers and at least one data row or an explicit `EVIDENCE_NOT_FOUND` row.
- The result must distinguish `code_path_exists`, `runtime_instrumented`, and `formal_training_evidence`.
- Do not use a natural-language claim when a CSV/JSON field can be exported.

## Required Outputs

Write all required outputs under `results/20260705_srr_v3_m1_runtime_instrumentation_gate/`.

`completion_check.md` must contain one of:

- `M1_READY_FOR_REVIEW`
- `M1_NEEDS_REVISION`
- `M1_NEEDS_EVIDENCE`

`review_request.md` must state that `review.md` is intentionally absent at
executor stop and that M2 remains blocked until a separate read-only reviewer
writes `M1_AUDITED_GO`.

A separate read-only reviewer should later write `review.md` with one of:

- `M1_AUDITED_GO`
- `M1_AUDITED_NEEDS_REVISION`
- `M1_AUDITED_NEEDS_EVIDENCE`

## Completion Gate

Do not mark ready if gate/residual statistics are missing, if prototype coverage cannot identify T2-present edema positives/negatives, or if no-T2 safety is only asserted but not exported.
