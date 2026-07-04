---
task_key: "20260704_srr_v25_anti_laziness_acceptance_tests"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "anti-laziness acceptance tests / implementation claim validator"
required_evidence: ["validator_code", "claim_to_runtime_trace", "unused_utility_scan", "unit_test_report", "forbidden_substitute_report"]
forbidden_substitutes: ["implemented but not called", "utility-only completion", "file-exists pass", "diagnostic-only pass for implementation", "threshold tuning as architecture implementation", "single screenshot or table as proof"]
---

# Task: SRR-v2.5 Anti-Laziness Acceptance Tests

## Goal

Create repository-level acceptance tests that prevent Codex from satisfying SRR-v2.5 tasks with name-compatible stubs, unused utilities, deterministic fallbacks, or metrics-only reports. Every later implementation task must cite these tests and either pass them or explicitly mark `NEEDS_REVISION`.

## Required Work

Implement or update a lightweight validator under `scripts/validation/` that checks the following claims against source code and runtime outputs:

1. A module is not considered implemented unless it is both defined and called by the formal runner or model forward path.
2. A utility function is not considered evidence unless runtime summaries record it was invoked on train/OOF data.
3. A prototype bank is not considered real if its source is deterministic, random, default axis vectors, trainable parameters only, or post-hoc unused cache.
4. A dictionary is not considered semantic if only gates are logged. It needs slot groups, valid-slot masking, task routing, a loss or diagnostic tied to slot semantics, and an ablation.
5. nnU-Net context is not considered consumed if it is only summarized into global scalars or copied as final output. It must be spatially aligned, available to routing/proposal/refinement, and ablated.
6. A residual/gated SRR model is not considered meaningful if it always copies nnU-Net or always ignores nnU-Net. It must pass identity fallback tests and show nonzero bounded corrections in uncertain or error-prone regions.
7. Soft ROI refinement is not considered local if the residual branch sees the full volume without bounded crop evidence.
8. No-T2 edema safety is not considered complete unless train loss, inference logits, decode, export, and prediction sanity all block no-T2 edema.
9. A training task cannot pass from optimizer steps alone. It needs same-split metrics, hard subgroup metrics, proposal/component diagnostics, and a read-only audit.
10. A task cannot pass if required files listed by the controller do not exist or are silently replaced by similar names.

## Required Tests

Add tests or scripts that can be run on CPU with toy tensors and small fixture outputs. At minimum include:

- source-path call trace for model forward and training runner;
- identity fallback test for nnU-Net residual/gated path;
- no-T2 edema end-to-end toy decode/export test;
- prototype-source checker;
- local-crop evidence checker;
- required-file-name consistency checker between controller goal and subtask index.

## Required Outputs

Write `results/20260704_srr_v25_anti_laziness_acceptance_tests/` with:

- `result.md`
- `validator_manifest.md`
- `claim_to_runtime_trace.md`
- `unused_utility_scan.md`
- `unit_test_report.md`
- `forbidden_substitute_report.md`
- `MANIFEST.md`

## Completion Gate

Do not mark `PASS` unless the validator can detect at least three known failure modes from the current or previous SRR packets: unused prototype-bank utility, controller/index filename mismatch, and implementation claims unsupported by formal runtime evidence. Do not run training in this task.
