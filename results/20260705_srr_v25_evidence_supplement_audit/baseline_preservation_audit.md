
# nnU-Net Anchor / Baseline Preservation Audit

Audit basis commit: `3f30e0ee4b8c951f700fe50de8810bac8e196c23`.

## Code Path Exists

- `src/care_myocardium/models/srr_propref.py:571`
- `src/care_myocardium/models/srr_propref.py:633`
- `src/care_myocardium/models/srr_propref.py:938`
- `src/care_myocardium/models/srr_propref.py:943`
- `scripts/training/run_srr_propref_myops_fold0.py:428`
- `scripts/training/run_srr_propref_myops_fold0.py:1523`
- `scripts/training/run_srr_propref_myops_fold0.py:681`

The source implements a baseline-preserving residual gate: final logits are computed as `anchor_logits + gate * bounded_delta`, with `bounded_delta` limited by `tanh`. Training code also adds `_baseline_preservation_loss` and logs gate/residual summaries.

## Runtime Scope

Closed-gate identity and nnU-Net context identity are demonstrated in toy/hard-subgroup/bounded rows, and the no-anchor full-fold0 ablation demonstrates why the anchor is necessary. There is no evidence that the closed-gate identity fallback was stress-tested as a full formal training recovery path beyond the bounded/eval-only packet.

## Metric Interpretation

The no-anchor row is strongly harmful: edema Dice delta `-0.142051`, scar Dice delta `-0.558659`, edema remote-FP `+2073.727`, and scar remote-FP `+856.932` on full fold0 argmax. This proves that removing the nnU-Net anchor is dangerous and that the baseline gate is necessary. It does **not** prove SRR beats nnU-Net; anchor-enabled rows remain near identity with Dice deltas much smaller than `0.005`.
