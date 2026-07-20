---
route_id: route_B
portfolio_round: round03
executor_id: B2_IMPLEMENTATION_GATE
lane: tooling
wave: 3
role: executor
status: BLOCKED_UNTIL_B1_MERGED
---

# B2 — implementation gate

This executor proves that the implemented graph is real before any formal training. It may run lightweight compute-node tests; it may not train a formal candidate.

Use the exact preflight, partition, retry, output, and race fields in `route_B_executor_plan.yaml`. `volta-gpu` is the preferred independent assignment because the gate is batch-1 and must prove peak memory below 14.5 GiB without semantic changes. A failed V100 preflight does not block identical htzhulab/A100 gates, but it must be recorded honestly.

Run exactly:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/route_B_round03/run_implementation_gate.py --config configs/route_B_round03/formal.yaml --strict --out results/route_B/round03/executors/B2
```

The strict gate requires real cases for LGE-only, LGE+C0, and LGE+T2+C0; finite nonzero losses; gradients into every valid stem/expert/router/proposal/refiner/gate; invalid-slot weight at most `1e-8`; Pattern-SIP non-alias gradients; OOF nonleakage; exact no-T2 edema zero; save/reload equality; wrong-order rejection; nonzero node-to-final interventions; official CineMA frame outputs with correct 4/16/1 shapes; matched source parameter inventory; `exp(v)`/`exp(-v)` with seven steps; true Jacobian and inverse composition; and temporal consumption of every named field.

Execute all known-bad fixtures, including the old wrapper, bootstrap/EMA formal memory, fake CineMA, direct velocity displacement, proxy Jacobian, pair-as-case, abstract `temporal_z`, frame0 fallback, and zero-MyoPS-plus-Cine-gain candidate fixture. Every known-bad command must exit nonzero with its expected failure key.

Required files: `implementation_gate.json`, `gradient_intervention_report.csv`, `save_reload_report.json`, `cinema_real_frame_smoke.json`, `registration_temporal_smoke.json`, `known_bad_selftest_report.md`, `completion.json`. Success token: `ROUTE_B_ROUND03_B2_IMPLEMENTATION_GATE_PASSED`.

Any disconnected module, mock/config-only implementation, missing asset/data, failed save/reload, or semantic known-bad pass is non-ready. Do not advance to B3. Do not push, write `review.md`, upload, promote, start M11, or make a final decision.