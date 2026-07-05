# Instrumentation Unit Tests

## Commands

- `python -m py_compile scripts/evaluation/export_srr_v3_m1_runtime_instrumentation.py`: PASS.
- `python scripts/evaluation/export_srr_v3_m1_runtime_instrumentation.py --known-bad-validator-smoke`: PASS; the synthetic claim-only packet failed closed.
- `python scripts/evaluation/export_srr_v3_m1_runtime_instrumentation.py --strict-validate`: FAIL as expected for readiness because `prototype_coverage_export.csv: edema_prototypes_empty`.

## Validator Behavior

The known-bad smoke generated CSVs with `CLAIM_WITHOUT_RUNTIME_EVIDENCE`; strict validation rejected them with `claim_only_rows` and `no_runtime_instrumented_row`. The real packet contains runtime rows, but is not M1-ready because the actual bounded source summary has zero edema positive and zero edema negative prototype counts.
