---
task_key: "20260704_cine_full_cinema_registration"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: true
allow_external_upload: false
review_required: true
mechanism_class: "CineMA / registration option matrix / CineMyoPS evidence"
required_evidence: ["asset_registry", "CineMA_attempt", "registration_matrix", "warp_sanity", "frame0_comparison", "resource_log"]
forbidden_substitutes: ["frame0 only", "descriptor-only route", "translation-only registration", "SimpleITK fallback as full registration", "skipping CineMA without blocker", "no ANTs-SyN or VoxelMorph attempt"]
---

# Task: CineMA And Full Registration Option Matrix

## Goal

Complete the Cine line at a serious registration level. Current Cine evidence remains diagnostic with a registration gap. This task must attempt CineMA or a documented equivalent and compare strong registration options.

## Required Attempts

Attempt or document blockers for:

- CineMA or equivalent cine anatomy prior;
- ANTs/SyN or installed classical deformable registration;
- TPS-style code from repo or public source if available;
- VoxelMorph or equivalent learning-based registration if code and weights are available;
- current optical-flow or SimpleITK fallback only as a lower baseline, not as the main registration completion.

Network may be used only to fetch public code or weights. Record source URL, version, local path, license status, and whether the asset was actually runnable. Do not upload CARE data.

## Required Metrics

Compare frame0 reference, moving-frame registered predictions, temporal consistency, myocardium proxy Dice, component count, warp sanity, folding or Jacobian proxy, and runtime. No hosted metric claim is allowed without hosted evidence.

## Required Outputs

Write `results/20260704_cine_full_cinema_registration/` with `result.md`, `asset_registry.md`, `cinema_status.md`, `registration_option_matrix.md`, `warp_sanity.csv`, `metrics_summary.md`, `resource_log.md`, and `MANIFEST.md`.

## Completion Gate

If ANTs/SyN and VoxelMorph do not run, mark `NEEDS_EVIDENCE` or `PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP`, not `PASS`. CineMA must be attempted or blocked with concrete evidence.
