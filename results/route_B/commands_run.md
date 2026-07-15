# Route B Commands Run Continuation

- `python scripts/route_B/run_implementation_gate.py --strict`
- `python scripts/validation/route_B/validate_route_b_implementation.py --strict --write-report results/route_B/validator_implementation_report.json`
- `python scripts/validation/route_B/validate_route_b_packet.py --strict --write-report results/route_B/validator_packet_report.json`
- `pytest -q tests/route_B src/care_myocardium/tests/test_route_b_implementation.py`
- `git diff --check`

No `sbatch`, `srun`, validation upload, push, or M11 command was run.
