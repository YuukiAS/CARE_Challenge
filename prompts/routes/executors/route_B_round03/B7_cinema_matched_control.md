---
route_id: route_B
portfolio_round: round03
executor_id: B7_CINEMA_MATCHED_CONTROL
lane: cine
wave: 8
role: executor
status: BLOCKED_UNTIL_B6_MERGED
---

# B7 — official CineMA pretrained/random matched control

Use only the pinned official source and twelve-case manifest. The CARE small `CineMAAdapter` is a known-bad historical control and cannot satisfy this executor.

Before training, atomically acquire the named weight to an untracked route-local asset path, verify SHA256 `c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f`, bind code commit/HF revision/license, and run a real CARE frame through `ConvUNetR`. Capture the 32-channel `decoder_dict["sax"]` output before `pred_head_dict["sax"]`, project to 16 channels, and emit four-class logits, probabilities, features, entropy, and complete affine/header/preprocessing provenance.

Create one serialized downstream initialization artifact with seed `26071831`. Verify that pretrained and random lanes have identical architecture, downstream parameter values, trainable/frozen masks, cases, frames, preprocessing, serialized augmentation draws, optimizer, schedule, budget, validation/checkpoint cadence, and selector. Only source initialization hashes may differ.

Run:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/training/route_B_round03/train_cinema_control.py --sources pretrained random --steps 8000 --config configs/route_B_round03/cine.yaml --out results/route_B/runtime/round03/B7
```

Each lane requires 8000 steps, 3600 seconds, four validations, 12 cases, checkpoints 2000/4000/6000/8000, AdamW `2e-4`, weight decay `1e-4`, batch one case, and clip 5. Select and clean-reload each source. Classify `PRETRAINED_BENEFIT`, `RANDOM_NONINFERIOR`, or `CINEMA_CONTROL_UNRESOLVED` exactly as contracted. Downstream always uses the reloaded pretrained source.

Independent work is preferred: pretrained may run on volta and random on a100 after common-init equality; htzhulab remains available. A three-way duplicate race is allowed only for one compatible critical logical run with identical hashes and an atomic winner lock. Losers get zero credit and pending losers are cancelled.

Success token `ROUTE_B_ROUND03_B7_CINEMA_CONTROL_TERMINAL` requires terminal accounting for both lanes, parameter equality, provenance, selections, and reload. Missing assets, fake/binary/frame0 output, unmatched controls, pending state, or undertraining is non-ready.