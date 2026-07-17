---
route_id: route_B
portfolio_round: round03
executor_id: B5_MYOPS_REFINER
lane: myops
wave: 6
role: executor
status: BLOCKED_UNTIL_B4_MERGED
---

# B5 — pathology-specific refinement

Use the clean-reloaded selected B4 checkpoint and its frozen OOF bank. Do not change proposal thresholds, ROI equations, crop sizes, refiner dilations, sampler, loss weights, or stage budget.

Run:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/training/route_B_round03/train_myops.py --stage refiner --steps 10000 --parent results/route_B/runtime/round03/B4/selected.pt --config configs/route_B_round03/formal.yaml --out results/route_B/runtime/round03/B5
```

Formal semantics: AdamW `1e-4`, batch 1, accumulation 2, AMP, clip 5, cosine; 10,000 steps, at least 3,000 seconds, five validations, checkpoints 2000/4000/6000/8000/10000. Stems/lower encoders and prototype banks are frozen. Train separate scar and edema refiners and permitted upper routed features. Scar uses the small precision-oriented ROI and dilations `[1,2,3]`; edema uses the larger T2-conditioned ROI and dilations `[1,2,4,6]`.

Record every case’s proposal support, ROI support, crop geometry, anatomy fallback, proposal-to-final retention, changed logits/voxels/components, Dice, HD95, remote-FP, components, and volume ratio. No hard deletion outside proposal support is allowed. Anatomy-only fallback above 5% is non-ready.

Default assignment is htzhulab with a100 eligible for identical two-way race under the single-critical-job rule. V100 receives independent evaluation/replay and cannot use a smaller architecture or input.

Pass requires positive proposal-to-final retention, nonzero changed components, no scar remote-FP increase on the gate set, finite losses/gradients, and exact no-T2 edema zero. Success token: `ROUTE_B_ROUND03_B5_REFINER_GATE_PASSED`. A gate failure stops progression and is not repaired by changing design inside the executor.