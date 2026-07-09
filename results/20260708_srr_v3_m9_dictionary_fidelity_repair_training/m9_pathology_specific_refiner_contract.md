# M9 Pathology-specific Refiner Contract

status: `RUNTIME_RECONCILED_FOR_M9_FOLLOWUP`

Scar refiner code path uses tighter/smaller ROI settings for focal scar precision. Edema refiner code path uses broader/larger ROI settings and T2-conditioned no-T2 blocking.

Runtime reconciliation evidence:

- Scar ROI stats: `m9_scar_refiner_roi_stats.csv`
- Edema ROI stats: `m9_edema_refiner_roi_stats.csv`
- Refiner asymmetry rows: `m9_refiner_asymmetry_ablation.csv`
- Final metric causal effect rows: `m9_refiner_causal_effect.csv`
- Same-split help/harm: `m9_same_split_help_harm.csv`

The evidence remains diagnostic and negative overall: ROI/refiner runtime rows exist, but selected formal candidates do not improve over the tracked M8 nnU-Net anchor.
