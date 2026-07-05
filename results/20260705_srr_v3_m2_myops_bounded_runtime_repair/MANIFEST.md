# MANIFEST

## Required Outputs

- `result.md`
- `code_diff_summary.md`
- `runtime_gap_closure_table.csv`
- `strong_encoder_context_sanity.csv`
- `prototype_t2_coverage_sanity.csv`
- `proposal_refinement_sanity.csv`
- `baseline_gate_safety_sanity.csv`
- `no_t2_safety_sanity.csv`
- `unit_test_report.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`

## Additional Small Evidence

- `runtime_smoke_summary.json`
- `runtime_smoke/prototype_bank_summary.json`

## Source Changes

- `scripts/training/run_srr_propref_myops_fold0.py`
- `scripts/evaluation/export_srr_v3_m2_runtime_repair_smoke.py`

## Publication Boundary

This packet contains small Markdown, CSV, and JSON evidence only. It does not contain checkpoints, NIfTI predictions, upload zips, raw data, secrets, environment dumps, or large logs.
