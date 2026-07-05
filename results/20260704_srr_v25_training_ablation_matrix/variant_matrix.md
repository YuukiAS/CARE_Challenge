# Variant Matrix

task_key: `20260704_srr_v25_training_ablation_matrix`

## Bounded Matrix Evidence

This is a bounded hard-subgroup matrix with identity rows, not the full required formal matrix.
All rows use fold0 and explicit eval cases `Case1002,Case2002,Case3004,Case3011`.

| matrix variant | model variant | steps | stop reason | eval cases | evidence status |
| --- | --- | ---: | --- | ---: | --- |
| `closed_gate_identity_fallback` | `closed_gate_identity_fallback` | 0 | `identity_export_only` | 4 | `IDENTITY_EXACT_NNUNET` |
| `nnunet_context_identity` | `nnunet_context_only_no_srr_correction` | 0 | `identity_export_only` | 4 | `IDENTITY_EXACT_NNUNET` |
| `srr_propref_no_proto_cascade` | `srr_propref_no_proto_cascade` | 6 | `max_steps` | 4 | `BOUNDED_HARD_SUBGROUP_MATRIX` |
| `srr_propref_scar_precision` | `srr_propref_scar_precision` | 6 | `max_steps` | 4 | `BOUNDED_HARD_SUBGROUP_MATRIX` |
| `srr_propref_shared_dual_dict` | `srr_propref_shared_dual_dict` | 6 | `max_steps` | 4 | `BOUNDED_HARD_SUBGROUP_MATRIX` |
| `srr_v25_no_anatomy_roi` | `srr_propref_shared_dual_dict` | 6 | `max_steps` | 4 | `BOUNDED_HARD_SUBGROUP_MATRIX` |
| `srr_v25_no_anchor` | `srr_propref_shared_dual_dict` | 6 | `max_steps` | 4 | `BOUNDED_HARD_SUBGROUP_MATRIX` |
| `srr_v25_no_local_refine` | `srr_propref_shared_dual_dict` | 6 | `max_steps` | 4 | `BOUNDED_HARD_SUBGROUP_MATRIX` |

## Required Variant Coverage

- current anchored PropRef packet is carried forward as a negative baseline but not rerun.
- full SRR-v2.5 without local refinement: `covered` via `srr_v25_no_local_refine`.
- full SRR-v2.5 without anatomy distance/ROI prior: `covered` via `srr_v25_no_anatomy_roi`.
- full SRR-v2.5 without nnU-Net anchor: `covered` via `srr_v25_no_anchor`.
- same-split nnU-Net only, nnU-Net context identity, and closed-gate identity fallback now exist for the hard-subgroup cases.

remaining_required_variant_rows: `none`

No route promotion, scientific stop, fold expansion, validation package, or upload is supported.
