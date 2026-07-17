---
route_id: route_B
portfolio_round: round03
executor_id: B3_MYOPS_EVIDENCE_WARMUP
lane: myops
wave: 4
role: executor
status: BLOCKED_UNTIL_B2_GATE_PASSED
---

# B3 — MyoPS evidence warmup

Use only the B2-gated commit, frozen manifests, canonical `[LGE,T2,C0]`, and exact formal config. No architecture, loss, sampler, batch, accumulation, or budget change is a retry.

Run the exact compute-node preflight, then:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/training/route_B_round03/train_myops.py --stage evidence_warmup --steps 6000 --config configs/route_B_round03/formal.yaml --out results/route_B/runtime/round03/B3
```

Formal semantics: AdamW `2e-4`, weight decay `1e-4`, batch 1, accumulation 2, AMP, clip 5, 500-step warmup then cosine; train stems/encoders/experts/routers/anatomy/evidence heads only. Checkpoints are exactly 2000/4000/6000. Record 6000 credited optimizer steps, at least 1800 train-loop seconds, three validation events, the 2:1:1 `E,E,S,R` sampler counts, cache isolation, loss decrease, one-batch overfit, per-family route mass/gradient, invalid weights, and the deterministic style-cluster freeze after step 2000.

Default assignment is `htzhulab`. A two-way identical race with `a100-gpu` is allowed immediately only when this is the sole critical pending job and no independent ready work can use the second partition. V100 is not compatible with this full formal stage absent an unchanged-config <=14.5 GiB preflight; it must run independent Route C replay/Cine extraction rather than a downscaled B3.

Required outputs and completion token are exactly those in the executor plan. Stage passage additionally requires finite losses, anatomy-union overfit Dice at least .70, gradients in every valid family, and frozen style centroids. `NEEDS_MONITOR`, `AWAITING_SACCT`, startup/preemption failure, or a scientific gate failure is not merge-ready. Same-scope operational retries receive zero failed-attempt credit.

Do not advance stages, reinterpret a failed gate, push, write `review.md`, upload, promote, start M11, or make a scientific decision.