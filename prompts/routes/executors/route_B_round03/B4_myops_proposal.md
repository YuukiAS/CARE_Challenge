---
route_id: route_B
portfolio_round: round03
executor_id: B4_MYOPS_PROPOSAL
lane: myops
wave: 5
role: executor
status: BLOCKED_UNTIL_B3_MERGED
---

# B4 — pathology proposal and OOF memory

Start from the clean-reloaded selected B3 checkpoint and the deterministic B3 feature receipts. Fit the formal four-shard OOF banks exactly as contracted before proposal training. Online EMA, deterministic bootstrap, validation/test labels, current-case leakage, and no-T2 edema negatives are fatal errors.

Run:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/training/route_B_round03/train_myops.py --stage proposal --steps 8000 --parent results/route_B/runtime/round03/B3/selected.pt --config configs/route_B_round03/formal.yaml --out results/route_B/runtime/round03/B4
```

Formal semantics: AdamW `1e-4`, batch 1, accumulation 2, AMP, clip 5, cosine; 8000 steps, at least 2400 seconds, four validations, checkpoints 2000/4000/6000/8000. Train routers, upper experts, anatomy, and the exact 43/44-channel scar/edema proposals; refiners and gates remain frozen. Pattern-SIP coefficient is .05. The hard-negative queue is train-only, rank-synchronized, 256 entries per pathology/scale, max 16 insertions per batch, hardest-confidence ordering and FIFO eviction.

Default assignment is `a100-gpu`; an identical htzhulab mirror is allowed only under the plan’s single-critical-job rule. V100 cannot receive a semantically reduced formal model and is assigned independent Cine extraction, replay, or evaluation.

The gate requires scar proposal recall >=.85, T2-positive edema proposal recall >=.90, nonzero positive-minus-negative similarity contribution, exact bank provenance, safe-negative compliance, finite gradients, and clean bank serialization. Required files and token: `ROUTE_B_ROUND03_B4_PROPOSAL_GATE_PASSED`.

A missing/invalid OOF bank blocks formal Route B. The no-prototype control is diagnostic only and cannot substitute. Do not continue on a failed scientific gate or perform unauthorized writes/actions.