# Same-Split Metrics

- matrix_root: `results/20260704_srr_v25_training_ablation_matrix/bounded_matrix`
- variants: `closed_gate_identity_fallback, nnunet_context_identity, srr_propref_no_proto_cascade, srr_propref_scar_precision, srr_propref_shared_dual_dict, srr_v25_no_anatomy_roi, srr_v25_no_anchor, srr_v25_no_local_refine`
- comparator: fold0 nnU-Net validation predictions
- output table: `help_harm_vs_nnunet.csv`

This file summarizes the bounded matrix source; detailed case/metric rows are in CSV.

Identity rows `nnunet_context_identity` and `closed_gate_identity_fallback` have zero delta versus nnU-Net for Dice, HD95, component count, and remote-FP metrics on the explicit hard-subgroup cases.

Isolated bounded rows now cover no-local-refine, no-ROI/anatomy, and no-anchor. `srr_v25_no_anchor` is strongly harmful on this packet: pathology-aware scar Dice delta `-0.608290`, edema Dice delta `-0.311185`, scar remote-FP delta `+801.0`, and edema remote-FP delta `+4635.5`. Anchor-enabled isolated rows remain near-neutral and show no remote-FP regression.
