# Code Diff Summary

## Source Changes

- `scripts/training/run_srr_propref_myops_fold0.py` adds `ensure_t2_edema_prototype_cases(...)` and wires it into `train_variant(...)`. This fixes the previous bounded-smoke failure mode where `--limit-train-cases 12` selected only LGE-only cases and produced an empty edema prototype bank. If prototype fitting is enabled and the limited subset has no T2-present edema-positive case, the code appends same-split T2 edema-positive cases for prototype fitting evidence.
- `scripts/evaluation/export_srr_v3_m2_runtime_repair_smoke.py` is the M2 smoke/instrumentation helper. This continued revision adds direct provenance/cache export and strict validation for the reviewer-flagged blocker. It runs synthetic unit checks and small real-case CPU forwards only; it does not train, package validation data, upload, write predictions, or start M3.

## Runtime Evidence Files

- `runtime_gap_closure_table.csv` records every required M2 runtime gap as `CLOSED` with exact artifact paths.
- `baseline_gate_safety_sanity.csv` covers closed-gate identity and correction-positive gate opening.
- `strong_encoder_context_sanity.csv` proves `strong_4scale` with `base_channels=8` runs on a real anchored patch.
- `prototype_t2_coverage_sanity.csv` proves the repair appends T2 edema cases and fits a non-empty edema prototype bank.
- `proposal_refinement_sanity.csv` proves scar/edema proposal seeds enter bounded crop ROI refinement rather than full-volume residual.
- `no_t2_safety_sanity.csv` proves no-T2 edema proposal/final/decode safety on Case1002.
- `provenance_cache_summary.json` records the no-training smoke checkpoint status, optimizer steps, encoder profile/channels, prototype source, selected/eval case ids, patch shape, smoke scope, command path, and artifact paths. `runtime_gap_closure_table.csv` points the cache/provenance gap row to this file.

## Scope Boundary

This is bounded runtime repair evidence. It is not full-fold training, formal training adequacy, route promotion, validation packaging/upload, hosted metric evidence, or challenge readiness.
