# Route B Commands Run Continuation

- `python scripts/route_B/run_implementation_gate.py --strict`
- `python scripts/training/route_B/run_bounded_train_eval.py --steps 12 --myops-eval-cases 10 --cine-eval-cases 5`
- `python scripts/validation/route_B/validate_route_b_implementation.py --strict --write-report results/route_B/validator_implementation_report.json`
- `python scripts/validation/route_B/validate_route_b_packet.py --strict --write-report results/route_B/validator_packet_report.json`
- `pytest -q tests/route_B src/care_myocardium/tests/test_route_b_implementation.py`
- `git diff --check`

No validation upload, push, M11, or review command was run.
