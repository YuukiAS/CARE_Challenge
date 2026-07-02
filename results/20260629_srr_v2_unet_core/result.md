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

## Targeted Extra CPU Preflight

While the queued targeted extra GPU jobs were held by `PartitionDown`, two
CPU-only two-step preflights were run under
`results/20260629_srr_v2_unet_core/targeted_extras_cpu_preflight/`.

- `srr_v2_edema_t2_focus`: `budget_status=OK`, `stop_reason=max_steps`,
  `best_val_patch_loss=2.0601760347684226`.
- `srr_v2_scar_precision_nointeract`: `budget_status=OK`,
  `stop_reason=max_steps`, `best_val_patch_loss=3.3605021437009177`.

These preflights show that the targeted extra configurations load the current
fold0 data, mined hard-negative components, losses, and SRR-v2 options without
an argument/runtime failure. They do not change the route selection because
export/evaluation was skipped; the queued GPU full runs remain the authoritative
evidence for any improvement claim.
