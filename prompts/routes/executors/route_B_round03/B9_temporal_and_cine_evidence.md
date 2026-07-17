---
route_id: route_B
portfolio_round: round03
executor_id: B9_TEMPORAL_AND_CINE_EVIDENCE
lane: cine
wave: 10
role: executor
status: BLOCKED_UNTIL_B8_REGISTRATION_GATE
---

# B9 — registered temporal training and Cine evidence

Temporal work starts only after the selected B8 registration checkpoint is clean-reloaded and the case-level aggregate gate passes. An abstract `temporal_z`, frame0 fallback, unregistered aggregation, missing field, or partial registration denominator is a hard failure.

Run:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/training/route_B_round03/train_temporal.py --targets 4000 8000 12000 16000 20000 --registration results/route_B/runtime/round03/B8/selected.pt --config configs/route_B_round03/temporal.yaml --out results/route_B/runtime/round03/B9
```

The named input structure must contain reference logits/features/uncertainty; registered non-reference logits/features/uncertainty; velocity; integrated displacement; true Jacobian; motion magnitude; texture residual; frame quality; sinusoidal temporal position; and valid-frame mask. Record tensor-consumption gradients and feature ablations.

Formal requirements: cumulative targets 4000/8000/12000/16000/20000, 20,000 credited steps, at least 7200 seconds, ten validations, four full-case events, 12 cases, AdamW `2e-4`, weight decay `1e-4`, batch one case, clip 5, seed `26071833`. Each chunk is estimated <=6.5 hours, saves atomically at most every 500 steps and on signals, and binds parent checkpoint/config/data hashes. Gap, overlap, reset, duplicate, timeout, preemption, or partial checkpoint receives zero credit.

Run reference-only, unregistered multi-frame, registered temporal, temporal-off, motion-off, anatomy-off, and pretrained-vs-random controls. Temporal on/off must alter actual final logits, labels, voxels, and components on at least eight cases. Report myocardium Dice/HD95 and case-wise help/harm.

Full temporal training defaults to a100 or htzhulab. V100 is not credited for the full registered-sequence training until unchanged-config memory compatibility is proven; it is assigned independent checkpoint evaluation, selected reload, and GPU validator work. A two-way identical race is allowed under the single-critical-job rule.

Success token `ROUTE_B_ROUND03_B9_CINE_EVIDENCE_TERMINAL` requires terminal accounting, cumulative continuity, selected reload, all controls, and final-output interventions. Adequate negative is permitted; monitor, undertrained, partial, or needs-evidence state cannot masquerade as terminal completion.