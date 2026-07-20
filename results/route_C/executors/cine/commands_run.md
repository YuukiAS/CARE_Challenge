# Route C Cine Commands Run

- `python scripts/ops/validate_executor_plan.py prompts/routes/route_C_executor_plan.yaml` -> exit `0`; executor plan validation passed.
- `python -m pytest tests/route_C/cine/test_fidelity_adapters.py` -> exit `0`; 3 tests passed.
- `python scripts/validation/route_C/cine/known_bad_selftest.py` -> exit `0`; fake provenance, identical pretrained/random, frame0-only, proxy registration, and temporal-without-registered-evidence fixtures all exited nonzero.
- `python scripts/route_C/cine/preflight.py --strict --print-contract` -> exit `0`; concrete preflight executed; formal runtime remains blocked by incomplete gate
- `python scripts/validation/route_C/cine/strict_validator.py --packet-dir results/route_C/executors/cine --write-report results/route_C/executors/cine/strict_validator_report.md` -> exit `0`; honest non-completion packet passed strict validation.
- `python scripts/diagnostics/route_C/cine/summarize_packet.py --packet-dir results/route_C/executors/cine --out results/route_C/executors/cine/diagnostic_summary.json` -> exit `0`; diagnostic summary written.
