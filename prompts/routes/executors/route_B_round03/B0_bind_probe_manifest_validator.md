---
route_id: route_B
portfolio_round: round03
executor_id: B0_BIND_PROBE_MANIFEST_VALIDATOR
lane: tooling
wave: 1
role: executor
status: BLOCKED_UNTIL_CURRENT_CRITIC_READY
---

# B0 — bind, source probe, manifests, and validator assets

Start only after the Controller supplies the exact `ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER` review bound by `CURRENT.md`. Read `prompts/routes/route_B.md`, `prompts/routes/route_B_executor_plan.yaml`, the current main hard matrix/anti-laziness rules, Slurm skill, mapper skill, and the bound Critic review.

Run exactly:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/route_B_round03/build_round03_assets.py --contract prompts/routes/route_B.md --out results/route_B/round03/executors/B0
```

The implementation created in this executor must deterministically:

1. inventory the exact first-party source symbols named in the contract and record their blobs;
2. enforce canonical `[LGE,T2,C0]` and reject the legacy Route B order;
3. generate and SHA-bind the 44-case MyoPS, T2-positive edema, disjoint sampler-strata, and 12-case Cine manifests;
4. require at least eight T2-present edema-positive evaluation cases and CenterB/CenterC representation;
5. write the executable known-bad fixture index with mutation, input schema, command, expected nonzero exit, and failure key;
6. write the three-partition static assignment/race matrix;
7. record official CineMA code/HF/weight/license/API/config blobs without downloading tracked heavy assets.

Required files are `source_probe.json`, `manifest_freeze_receipt.json`, `sampler_contract.json`, `validator_fixture_index.json`, `partition_static_matrix.json`, and `completion.json`. The completion token is exactly `ROUTE_B_ROUND03_B0_READY_FOR_CONTROLLER_MERGE`.

Any missing path, unresolved source symbol, inadequate positive-case manifest, wrong modality order, unknown external API, blank validator fixture, or partition field writes a non-ready token and stops. Do not implement the model, train, submit Slurm, edit shared source, push, write `review.md`, upload validation, promote a route, start M11, or make a scientific decision.