---
task_key: "20260704_srr_v25_failure_analysis_overlay"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "failure analysis / overlay diagnostics / hard subgroup triage"
required_evidence: ["case_overlays", "component_error_taxonomy", "proposal_vs_refiner_breakdown", "dictionary_gate_trace", "nnunet_context_trace"]
forbidden_substitutes: ["table-only metrics", "no visual or spatial evidence", "case-id-based fix", "minor threshold-only explanation"]
---

# Task: Failure Analysis, Overlays, And Mechanism Triage

## Goal

Find the true causes of low Dice and high remote false positives. This task must produce spatial and mechanism-level evidence, not only summary tables.

## Required Work

For hard cases and subgroups, produce compact overlays and trace files that show original modalities, nnU-Net context, SRR proposal, dictionary gates, crop region, final prediction, and ground truth. Focus on CenterC edema, T2-present GT-positive edema, scar CenterC, no-T2 safety, and cases where scar was harmed compared with nnU-Net.

## Required Taxonomy

Classify errors into categories such as missed lesion, remote island, fragmented component, wrong crop seed, weak T2 support, anchor misleading, dictionary misroute, prototype mismatch, refiner overcorrection, and label/spacing/alignment issue.

## Required Outputs

Write `results/20260704_srr_v25_failure_analysis_overlay/` with `result.md`, `case_error_taxonomy.csv`, `overlay_manifest.md`, `proposal_vs_refiner_breakdown.csv`, `dictionary_gate_trace.csv`, `nnunet_context_trace.csv`, `hard_case_summary.md`, and `MANIFEST.md`.

## Completion Gate

Do not propose new training until this task identifies which mechanism fails most often in the hard subgroups.
