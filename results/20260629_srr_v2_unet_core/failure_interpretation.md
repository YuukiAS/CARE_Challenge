# SRR-v2 Failure Interpretation

This file records the SRR-v2 failure and recovery state for the required formal
route, plus the later targeted-extra preflight status. It does not select a
route because the completed formal SRR-v2 metrics remain below the nnU-Net
reference gate, and the targeted extra full GPU runs have not started yet.

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

## Required Formal Route Outcome

The required SRR-v2 formal route is now fully aggregated:

- `srr_v2_multiscale_private_basic`
- `srr_v2_multiscale_private_proposal`
- `srr_v2_proposal_uncertainty_hardneg`

Selection status is `STOP_NO_SRR_V2_SIGNAL` in `selection.md`.

The nnU-Net-gated selection floor was:

- scar all-case floor: `0.4481` (80% of nnU-Net scar reference `0.5602`)
- edema GT-positive floor: `0.3155` (80% of nnU-Net edema reference `0.3944`)

The best formal SRR-v2 values were:

- best scar all-cases: `0.2474` from
  `srr_v2_proposal_uncertainty_hardneg`
- best edema GT-positive: `0.1855` from
  `srr_v2_multiscale_private_proposal`

The route therefore did not approach nnU-Net closely enough to justify fold
expansion, validation packaging, or replacing the current nnU-Net reference.

## Mechanistic Interpretation

The required SRR-v2 route fixed the shallow-capacity concern enough to train and
export, but the pathology signal remained weak:

- Proposal/hard-negative tuning helped scar signal relative to the weakest SRR
  variants, but not enough to close the nnU-Net gap.
- The edema-focused proposal variant remained far below the nnU-Net-derived
  edema floor, so the current SRR-v2 route still lacks a reliable T2/edema
  localization mechanism.
- The export bug was an implementation issue, not the main performance blocker,
  because the recovered/patched full-volume evaluation still selected no route.

## Targeted Extra Status

After weak formal SRR-v2/cascade results, two targeted SRR-v2 variants were
queued on all allowed GPU partitions:

- `srr_v2_edema_t2_focus`
- `srr_v2_scar_precision_nointeract`

They remain pending with `(PartitionDown)` on `htzhulab`, `a100-gpu`, and
`volta-gpu` as of the latest queue checks. While waiting, CPU-only two-step
preflights under `targeted_extras_cpu_preflight/` showed:

- `srr_v2_edema_t2_focus`: `budget_status=OK`, `best_val_patch_loss=2.0602`
- `srr_v2_scar_precision_nointeract`: `budget_status=OK`,
  `best_val_patch_loss=3.3605`

These preflights only prove the targeted configurations are executable. They do
not provide route-quality evidence because export/evaluation was skipped.

## Remaining Risk

The recovered export path produced full-volume predictions and subgroup metrics, but it did not recover detailed training-time retrieval usage. `dictionary_usage.csv` therefore records the missing usage logging caveat for this variant.

The route should not be stopped from the original export bug alone. The current
open question is narrower: whether either targeted extra can improve the best
first-party SRR-v2 scar/edema signal after a full GPU run and evaluation. If
they also remain below the nnU-Net gate, the evidence will continue to support
`STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL` for this rescue sprint.
