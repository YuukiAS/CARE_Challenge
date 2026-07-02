# SRR-v2 Capacity-Targeted CPU Preflight

Date: 2026-07-02 02:24 EDT

This directory contains CPU-only two-step preflights for an additional
capacity-targeted SRR-v2 rescue probe. It is executability evidence only, not
route-quality evidence, because export/evaluation was skipped and no formal
Dice metrics were produced.

## Variants

- `srr_v2_capacity12_edema_t2_focus`
  - base variant: `srr_v2_multiscale_private_proposal`
  - intent: combine the stronger `base_channels=12` capacity setting with the
    T2/edema-focused sampling and loss emphasis used by the targeted edema
    probe.
  - CPU preflight status: `OK`
  - stop reason: `max_steps`
  - best step: `2`
  - best validation patch loss: `2.3302699526151023`

- `srr_v2_capacity12_scar_precision_nointeract`
  - base variant: `srr_v2_proposal_uncertainty_hardneg`
  - intent: combine the strongest first-party scar capacity result with a more
    precision-oriented hard-negative setting and disabled SRR-v2 interactions.
  - CPU preflight status: `OK`
  - stop reason: `max_steps`
  - best step: `2`
  - best validation patch loss: `2.902617414792379`

## Formal GPU Status

The corresponding formal wrapper is
`jobs/src/run_srr_v2_capacity_targeted_extra.sh`, with output root
`results/20260629_srr_v2_unet_core/capacity_targeted_extras/`.

Two attempts to submit the formal `--array=0-1` job to the preferred
`htzhulab` partition failed with:

```text
sbatch: error: Batch job submission failed: Unable to contact slurm controller (connect failure)
```

This was a Slurm controller contact failure, not a completed formal run and not
evidence that the route is weak. The existing `57334792_[0-1]` targeted
SRR-v2 jobs were still running on `htzhulab` at this checkpoint.
