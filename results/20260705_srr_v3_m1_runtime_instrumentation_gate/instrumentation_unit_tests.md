# Instrumentation Unit Tests

## Commands

- `python -m py_compile scripts/evaluation/export_srr_v3_m1_runtime_instrumentation.py`: PASS.
- `python scripts/evaluation/export_srr_v3_m1_runtime_instrumentation.py --known-bad-validator-smoke`: PASS; the synthetic claim-only packet failed closed.
- `python scripts/evaluation/export_srr_v3_m1_runtime_instrumentation.py --device cpu`: PASS; regenerated M1 continued runtime CSVs from an existing checkpoint and selected prototype summary.
- `python scripts/evaluation/export_srr_v3_m1_runtime_instrumentation.py --strict-validate`: PASS; no issues.

## Validator Behavior

The known-bad smoke generated claim-only CSVs and was rejected with `claim_only_rows`, missing runtime gate evidence, and missing selected prototype source checks. The continued real packet passes only because `prototype_coverage_export.csv` contains a `selected_nonempty_t2_source` row with non-zero edema positive, edema negative, and T2-present edema positive counts.
