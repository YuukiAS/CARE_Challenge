# srr_v2_light_refine_extras Selection

status: `STOP_NO_SRR_V2_SIGNAL`
selected_variant: `none`

## Evidence Roots

- `srr_v2_light_refine_lowmix`: `results/20260629_srr_v2_unet_core/light_refine_extras/variants/srr_v2_light_refine_lowmix`
- `srr_v2_light_refine_hardneg`: `results/20260629_srr_v2_unet_core/light_refine_extras/variants/srr_v2_light_refine_hardneg`

## Decision Basis

- nnU-Net scar all-case reference: `0.5602`
- nnU-Net edema GT-positive reference used for this gate: `0.3944`
- Conservative selection rule: select only if a target metric reaches at least 80% of the corresponding nnU-Net reference.

## Reasons

- best_edema_gt_positive=srr_v2_light_refine_lowmix:0.1879; selection_floor_80pct_nnunet=0.3155
- best_scar_all_cases=srr_v2_light_refine_lowmix:0.2431; selection_floor_80pct_nnunet=0.4481
- no SRR-v2 variant approached nnU-Net enough for selection

No validation upload, fold expansion, split change, label mapping change, or evaluator change was performed.
