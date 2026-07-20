# Route B Round03 Implementation Snapshot

created_at_utc: `2026-07-18T10:39:46Z`

Implemented route-local Round03 surfaces:

- `src/care_myocardium/route_B_round03/`: SRR-v3 MyoPS modules, official CineMA adapter/provenance surface, SVF registration, temporal evidence consumer, and known-bad fixtures.
- `scripts/route_B_round03/`: manifest builder, B2 gate, preflight, checkpoint selector, packet aggregator, and shared runtime helpers.
- `scripts/training/route_B_round03/`: MyoPS staged training, CineMA matched-control training, registration training, and temporal training entrypoints.
- `scripts/validation/route_B_round03/`: B0, B2, B3-B9, and B10 packet validators.
- `jobs/route_B_round03/`: htzhulab/a100/volta/l40 wrappers with route-local logs, isolated attempt outputs, and atomic B3 winner-lock behavior.

Verified local gates:

- B0 manifest freeze passed and wrote the required manifest receipts.
- B1 static tests passed: `tests/route_B_round03/test_static_contract.py` and `tests/route_B_round03/test_known_bad_static.py`.
- B2 strict implementation gate passed with official CineMA source, exact weight SHA `c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f`, exact state-dict load, and real official ConvUNetR forward.

Current runtime state:

- B3 is submitted but not started.
- `results/route_B/runtime/round03/B3/selected.pt` does not exist yet.
- B4-B10 must not run until B3 terminal evidence and selected checkpoint exist.

This snapshot is a controller draft, not a completion packet.
