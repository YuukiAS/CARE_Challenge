# CARE MoSAIC wrapper

This directory contains CARE-side wrappers for the MoSAIC fair-reproduction
protocol. Do not place upstream checkpoints, generated predictions, or runtime
caches here.

The default external asset cache is:

```bash
MOSAIC_ROOT=/users/a/e/aereinh/MoSAIC
```

Use `scripts/inference/run_mosaic_fold0_fair_inference.py` for protocol
preflight and native MoSAIC inference gating, and
`scripts/evaluation/evaluate_mosaic_fold0_fair_comparison.py` for fold0 fair
comparison receipts.
