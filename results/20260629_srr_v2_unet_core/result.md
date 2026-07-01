# Result 20260629 srr_v2

Status: `STOP_NO_SRR_V2_SIGNAL`
Selected variant: `none`

## What Was Aggregated

This route aggregates canonical and isolated fallback outputs without moving or overwriting variant artifacts.

- `srr_v2_multiscale_private_basic` from `results/20260629_srr_v2_unet_core/variants/srr_v2_multiscale_private_basic`
- `srr_v2_multiscale_private_proposal` from `results/20260629_srr_v2_unet_core_htzhulab_fallback/variants/srr_v2_multiscale_private_proposal`
- `srr_v2_proposal_uncertainty_hardneg` from `results/20260629_srr_v2_unet_core_htzhulab_fallback/variants/srr_v2_proposal_uncertainty_hardneg`

## Interpretation

SRR-v2 is judged against the nnU-Net reference, not merely against the previous shallow SRR floor.
See `metrics_summary.md`, `subgroup_metrics.csv`, and `selection.md` for the complete evidence.

No validation upload, fold expansion, split change, label mapping change, or evaluator change was performed.
