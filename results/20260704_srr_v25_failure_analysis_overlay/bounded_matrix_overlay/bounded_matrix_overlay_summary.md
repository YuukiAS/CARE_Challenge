# Bounded Matrix Overlay Summary

source_root: `results/20260704_srr_v25_failure_analysis_overlay/bounded_matrix_overlay`

## Generated Tables

- `bounded_matrix_overlay_taxonomy.csv`: 96 rows
- `bounded_matrix_overlay_proposal_refiner.csv`: 96 rows
- `bounded_matrix_overlay_dictionary_trace.csv`: 126 rows
- `bounded_matrix_overlay_residual_gate_trace.csv`: 6 rows

## Taxonomy Counts

| matrix_variant | metric_name | taxonomy | count |
| --- | --- | --- | ---: |
| `srr_propref_no_proto_cascade` | `myops_edema` | `boundary_or_extent_error;crop_or_roi_undercoverage` | 2 |
| `srr_propref_no_proto_cascade` | `myops_edema` | `neutral_or_minor` | 6 |
| `srr_propref_no_proto_cascade` | `myops_scar` | `neutral_or_minor` | 8 |
| `srr_propref_scar_precision` | `myops_edema` | `boundary_or_extent_error;crop_or_roi_undercoverage` | 2 |
| `srr_propref_scar_precision` | `myops_edema` | `neutral_or_minor` | 6 |
| `srr_propref_scar_precision` | `myops_scar` | `neutral_or_minor` | 8 |
| `srr_propref_shared_dual_dict` | `myops_edema` | `boundary_or_extent_error;crop_or_roi_undercoverage` | 2 |
| `srr_propref_shared_dual_dict` | `myops_edema` | `neutral_or_minor` | 6 |
| `srr_propref_shared_dual_dict` | `myops_scar` | `neutral_or_minor` | 8 |
| `srr_v25_no_anatomy_roi` | `myops_edema` | `boundary_or_extent_error;crop_or_roi_undercoverage` | 2 |
| `srr_v25_no_anatomy_roi` | `myops_edema` | `neutral_or_minor` | 6 |
| `srr_v25_no_anatomy_roi` | `myops_scar` | `neutral_or_minor` | 8 |
| `srr_v25_no_anchor` | `myops_edema` | `neutral_or_minor` | 2 |
| `srr_v25_no_anchor` | `myops_edema` | `remote_island;proposal_flooding_or_decode_export;refiner_overcorrection` | 6 |
| `srr_v25_no_anchor` | `myops_scar` | `remote_island;proposal_flooding_or_decode_export;refiner_overcorrection` | 8 |
| `srr_v25_no_local_refine` | `myops_edema` | `boundary_or_extent_error;crop_or_roi_undercoverage` | 2 |
| `srr_v25_no_local_refine` | `myops_edema` | `neutral_or_minor` | 6 |
| `srr_v25_no_local_refine` | `myops_scar` | `neutral_or_minor` | 8 |

## Interpretation

- Anchor-enabled rows mostly stay in `neutral_or_minor` or boundary/extent categories on this bounded packet.
- `srr_v25_no_anchor` concentrates failures in `remote_island;proposal_flooding_or_decode_export;refiner_overcorrection`, matching the help/harm remote-FP regression.
- This is bounded hard-subgroup evidence only; it does not replace full fold0 subgroup metrics or final read-only audit.
