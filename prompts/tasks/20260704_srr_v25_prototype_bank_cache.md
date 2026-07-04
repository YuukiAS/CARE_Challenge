---
task_key: "20260704_srr_v25_prototype_bank_cache"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "data-derived prototype memory / train-OOF cache / safe negatives"
required_evidence: ["prototype_cache_files", "feature_source_manifest", "leakage_audit", "prototype_counts", "proposal_pr_delta", "unit_tests"]
forbidden_substitutes: ["deterministic_axis_bootstrap as final prototype bank", "random trainable prototype parameters as final bank", "prototype utility exists but not loaded", "no-T2 myocardium as edema negative", "validation-label tuned prototypes"]
---

# Task: Real Train/OOF Prototype Bank Cache

## Goal

Replace the current partial prototype implementation with real data-derived prototype memory. This is a high-impact task because current deterministic bootstrap prototypes and hard-negative replay are not enough to support the SRR-v2.5 proposal mechanism.

## Required Work

Build and commit source code that extracts feature prototypes from train or OOF evidence without validation leakage. Required banks:

- scar-positive prototypes from LGE-dominant scar features;
- scar-safe-negative prototypes from normal myocardium, blood pool, outside myocardium, LGE artifact, and mined hard false positives;
- edema-positive prototypes only from T2-present edema evidence;
- edema-safe-negative prototypes only from T2-present safe negatives, never no-T2 myocardium;
- center-aware summaries, especially CenterC T2-present edema.

The formal model must load these banks before training or before proposal evaluation. It is not enough to provide a utility function. `summary.json` must record prototype source, counts, feature stage, case count, and leakage policy.

## Required Tests

Add tests verifying no-T2 samples never contribute edema negatives, bank dimensions match model channels, missing categories fall back with explicit warning, and loaded banks change proposal similarity maps relative to deterministic bootstrap.

## Required Outputs

Write `results/20260704_srr_v25_prototype_bank_cache/` with `result.md`, `prototype_feature_source_manifest.md`, `prototype_bank_summary.json`, `leakage_audit.md`, `safe_negative_policy.md`, `proposal_pr_delta.csv`, `unit_test_report.md`, and `MANIFEST.md`.

## Completion Gate

Pass requires formal runtime evidence that the model loaded real prototype banks. If prototype banks remain deterministic bootstrap or post-hoc utilities only, mark `IMPLEMENTATION_INCOMPLETE`.
