---
task_key: "20260705_srr_v3_m5_cine_secondary_contract"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "milestone"
milestone_id: "M5"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "Cine secondary registration/temporal contract / diagnostic only"
expected_result_dir: "results/20260705_srr_v3_m5_cine_secondary_contract/"
prerequisite_review: "results/20260705_srr_v3_m0_architecture_master_contract/review.md:M0_AUDITED_GO"
required_outputs:
  - "result.md"
  - "cine_scope_contract.md"
  - "registration_safe_subset_matrix.csv"
  - "temporal_dictionary_readiness.md"
  - "frame_quality_router_probe.csv"
  - "cine_missing_evidence.md"
  - "completion_check.md"
  - "review_request.md"
  - "MANIFEST.md"
forbidden_substitutes:
  - "frame0 only as temporal retrieval"
  - "untrained VoxelMorph adapter as successful registration"
  - "SyN one-case smoke as full matrix"
  - "temporal dictionary claim without runtime evidence"
  - "hosted Cine metric claim"
  - "blocking MyoPS milestones"
---

# Milestone M5: Cine Secondary Contract

## Goal

Keep Cine as a secondary diagnostic line while MyoPS remains primary. This milestone does not attempt route promotion. It should define and, if lightweight, probe the missing Cine evidence needed before any future temporal dictionary integration: same-safe-subset registration matrix, frame-quality/motion-saliency routing evidence, and temporal aggregation readiness.

## Prerequisite Gate

Before starting, verify that `results/20260705_srr_v3_m0_architecture_master_contract/review.md` exists and contains `M0_AUDITED_GO`. If not, stop with `M5_BLOCKED_BY_M0`. This milestone does not block M1-M4 unless the user explicitly chooses to prioritize Cine.

## Required Work

Audit and, if lightweight, extend Cine evidence for:

- CineMA or equivalent anatomy-prior source status;
- ANTsPy SyN beyond one-case smoke, ideally a small same-safe-subset matrix;
- VoxelMorph status, distinguishing runnable adapter from trained/usable registration;
- SimpleITK/Demons/optical flow as fallback/proxy only;
- frame0 and ED-anchor controls;
- temporal dictionary readiness, including frame-quality/motion-saliency router inputs;
- explicit missing evidence before any Cine temporal integration task can run.

## Strict Validation

- One-case SyN or untrained VoxelMorph cannot pass full registration.
- If no same-safe-subset matrix is available, write `CINE_REGISTRATION_GAP_REMAINS`.
- If no temporal dictionary runtime exists, write `TEMPORAL_DICTIONARY_NOT_READY`.
- Do not claim hosted `myocardium_cinemyops` metric improvement.

## Required Outputs

Write all required outputs under `results/20260705_srr_v3_m5_cine_secondary_contract/`.

`completion_check.md` must contain one of:

- `M5_DIAGNOSTIC_READY_FOR_REVIEW`
- `M5_NEEDS_REVISION`
- `M5_NEEDS_EVIDENCE`

A separate read-only reviewer should later write `review.md` with one of:

- `M5_AUDITED_DIAGNOSTIC_GO`
- `M5_AUDITED_NEEDS_REVISION`
- `M5_AUDITED_NEEDS_EVIDENCE`

## Completion Gate

Do not mark full pass unless a same-safe-subset registration matrix and temporal dictionary readiness evidence exist. Diagnostic completion is acceptable, but it must not block MyoPS.
