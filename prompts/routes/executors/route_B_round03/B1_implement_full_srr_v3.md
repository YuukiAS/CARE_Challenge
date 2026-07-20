---
route_id: route_B
portfolio_round: round03
executor_id: B1_IMPLEMENT_FULL_SRR_V3
lane: shared
wave: 2
role: executor
status: BLOCKED_UNTIL_B0_MERGED
---

# B1 — implement the exact Route B Round03 model

Enter only after the Controller verifies the B0 merge receipt and all four frozen manifest hashes. Read the full Route B contract and executor plan. Scientific design is closed: do not choose alternate blocks, losses, modality order, bank fitting, CineMA hook, registration math, temporal inputs, budgets, or selectors.

All new code is confined to:

```text
src/care_myocardium/route_B_round03/**
scripts/route_B_round03/**
scripts/training/route_B_round03/**
scripts/validation/route_B_round03/**
tests/route_B_round03/**
configs/route_B_round03/**
jobs/route_B_round03/**
results/route_B/round03/executors/B1/**
```

Do not edit shared model, Cine, anchor, loss, or refiner files. A required shared edit is `ROUTE_B_ROUND03_B1_SHARED_SCOPE_REQUIRED` and returns to the Planner.

Implement exactly: four scales `[32,64,128,256]`; sixteen expert slots per scale; pathology-specific two-pass entmax routing; the numeric Pattern-SIP formula/schedule; deterministic four-shard OOF spherical-kmeans banks; training-only synchronized hard-negative queues; 43/44-channel scar/edema proposals; frozen soft-ROI equations; separate scar/edema refiners; bounded anchor correction; exact no-T2 zero semantics; official pinned CineMA adapter with 32-to-16 decoder projection; matched-random source interface; first-party seven-step SVF; true Jacobian/inverse composition; and the named registered temporal interface.

Implement every formal command and validator referenced by later prompts. The old `src/care_myocardium/route_B/**` wrapper, deterministic bootstrap formal memory, EMA formal memory, small CARE Cine adapter, direct velocity warp, and `temporal_z` interface must be executable known-bad fixtures, not fallback paths.

Run exactly:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python -m pytest tests/route_B_round03/test_static_contract.py tests/route_B_round03/test_known_bad_static.py -q
```

Produce `implementation_snapshot.md`, `symbol_inventory.json`, `tensor_contract.json`, `loss_contract.json`, `static_test_report.json`, and `completion.json`. Success token: `ROUTE_B_ROUND03_B1_READY_FOR_CONTROLLER_MERGE`.

Do not run formal training, claim implementation-gate passage, push, write runtime `review.md`, upload validation, promote, start M11, or alter another route.