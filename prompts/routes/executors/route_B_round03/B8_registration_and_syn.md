---
route_id: route_B
portfolio_round: round03
executor_id: B8_REGISTRATION_AND_SYN
lane: cine
wave: 9
role: executor
status: BLOCKED_UNTIL_B7_MERGED
---

# B8 — first-party SVF registration and real SyN control

Consume only the clean-reloaded selected pretrained CineMA source. Direct use of velocity as displacement, one-step integration, proxy Jacobian/inverse, synthetic transforms, pair-as-case credit, or copied SyN outputs is forbidden.

Run:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/training/route_B_round03/train_registration.py --steps 25000 --source results/route_B/runtime/round03/B7/pretrained/selected.pt --config configs/route_B_round03/registration.yaml --out results/route_B/runtime/round03/B8
```

The first-party network outputs `v:[B,3,Z,H,W]`. Compute `exp(v)` and `exp(-v)` by exactly seven scaling-and-squaring steps under `align_corners=true`, border padding, trilinear image/feature/probability warps, and nearest label warps. Convert normalized displacement to voxel coordinates for Jacobian and inverse-composition receipts. Loss weights and ANTsPy `SyNOnly` parameters are exactly those in the contract.

Formal requirements: 25,000 steps, at least 7200 seconds, ten validations, four full-case events, 12 cases, at least 60 pairs, checkpoints 5000/10000/15000/20000/25000, AdamW `1e-4`, weight decay `1e-5`, batch one pair, clip 5, seed `26071832`. Clean-reload the selected checkpoint before full evaluation.

Every pair records velocity/displacement/forward/inverse/Jacobian/output hashes, folding, inverse error, anatomy and similarity change, and failure class. A case requires >=80% pair pass and >=4 passed non-reference frames; the full gate requires >=90% case pass. Real SyN uses identical pairs and complete denominators.

Prefer distinct work: learned training on htzhulab, SyN/evaluation on volta, other ready work on a100. Three-way race is allowed only when the exact critical job passes all three preflights and no independent work has priority.

Success token `ROUTE_B_ROUND03_B8_REGISTRATION_TERMINAL` is allowed for a faithful positive or adequate-negative registration result only after selected reload and full accounting. A failed implementation, partial denominator, pending state, or unreloaded checkpoint is non-ready and temporal cannot launch.