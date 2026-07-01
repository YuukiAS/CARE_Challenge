# SRR-v2 Failure Interpretation

This file records the current SRR-v2 failure and recovery state. It is not a final route failure interpretation because two formal variants are still pending.

## Export Failure

Formal job `57094446_0` trained `srr_v2_multiscale_private_basic` on `htzhulab` for `06:37:38` and failed during full-volume export, not during training. The failure occurred when a validation volume with depth `1` reached a 3D pooling operation with a fixed kernel dimension of `2`.

The observed error was:

```text
RuntimeError: input image (T: 1 H: 249 W: 245) smaller than kernel size (kT: 2 kH: 2 kW: 2)
```

## Fix

`src/care_myocardium/models/srr_v2_unet.py` now uses safe per-dimension pooling in `ModalityEncoder._safe_pool`: dimensions smaller than `2` use kernel `1`, while larger dimensions use kernel `2`.

The patched model passed a depth-1 forward smoke test and the checkpoint was recovered by:

```bash
./envs/env_CARE/bin/python -u scripts/evaluation/export_srr_myops_checkpoint.py \
  --checkpoint results/20260629_srr_v2_unet_core/variants/srr_v2_multiscale_private_basic/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt \
  --out-root results/20260629_srr_v2_unet_core \
  --device cpu \
  --failure-note 'Recovered after SRR-v2 full-volume export failed on depth-1 validation case before safe pooling patch.'
```

## Remaining Risk

The recovered export path produced full-volume predictions and subgroup metrics, but it did not recover detailed training-time retrieval usage. `dictionary_usage.csv` therefore records the missing usage logging caveat for this variant.

The route should not be stopped from this bug alone. Variants `57095505_[1-2]` were still pending at the latest check and should use the patched code when they start.
