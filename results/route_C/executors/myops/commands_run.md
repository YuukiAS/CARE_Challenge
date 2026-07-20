# Commands Run

- `python scripts/route_C/myops/replay_intervention_selector.py --preflight --strict --print-contract`
- `python scripts/route_C/myops/replay_intervention_selector.py --evaluate --force --phase d2_hierarchical_psip --checkpoint checkpoint_best.pt --max-cases 1 --device cpu`
- `python -B -m pytest -q tests/route_C/myops/test_lane_validator.py -o cache_dir=/tmp/route_C_myops_pytest_cache`
- `python scripts/validation/route_C/myops/validate_lane_packet.py --known-bad-selftest --strict`
- `python scripts/validation/route_C/myops/validate_lane_packet.py --strict`
- `git diff --check`
