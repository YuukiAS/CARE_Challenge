# Full Fold0 Eval Summary

status: `FULL_FOLD0_EVAL_COMPLETE`

This packet evaluates existing bounded checkpoints only. It does not train,
rerun the current anchored packet, validation-package, or upload.

## Completion

- expected variants: `6`
- completed variants: `6`
- manifest status: `COMPLETE`
- eval cases: `44`
- fold: `0`

## Artifact Counts

| variant | predictions | case metric rows | subgroup rows |
| --- | ---: | ---: | ---: |
| `srr_propref_shared_dual_dict` | 88 | 176 | 36 |
| `srr_propref_no_proto_cascade` | 88 | 176 | 36 |
| `srr_propref_scar_precision` | 88 | 176 | 36 |
| `srr_v25_no_local_refine` | 88 | 176 | 36 |
| `srr_v25_no_anatomy_roi` | 88 | 176 | 36 |
| `srr_v25_no_anchor` | 88 | 176 | 36 |

## Pathology-Aware Help/Harm Vs Same-Split nnU-Net

| variant | metric_name | metric | n | delta_mean | help | harm | neutral |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `srr_propref_shared_dual_dict` | `myops_edema` | `dice` | 44 | -2.32481357e-05 | 4 | 5 | 35 |
| `srr_propref_shared_dual_dict` | `myops_edema` | `hd95` | 44 | 2.96331395e-05 | 0 | 2 | 42 |
| `srr_propref_shared_dual_dict` | `myops_edema` | `remote_fp_count` | 44 | 0 | 0 | 0 | 44 |
| `srr_propref_shared_dual_dict` | `myops_scar` | `dice` | 44 | 4.4082495e-05 | 16 | 6 | 22 |
| `srr_propref_shared_dual_dict` | `myops_scar` | `hd95` | 44 | 0.0018401074 | 2 | 2 | 38 |
| `srr_propref_shared_dual_dict` | `myops_scar` | `remote_fp_count` | 44 | 0 | 0 | 0 | 44 |
| `srr_propref_no_proto_cascade` | `myops_edema` | `dice` | 44 | 0.00147958845 | 11 | 5 | 28 |
| `srr_propref_no_proto_cascade` | `myops_edema` | `hd95` | 44 | -0.0163033302 | 9 | 5 | 30 |
| `srr_propref_no_proto_cascade` | `myops_edema` | `remote_fp_count` | 44 | 0.0454545455 | 0 | 1 | 43 |
| `srr_propref_no_proto_cascade` | `myops_scar` | `dice` | 44 | -0.000409858198 | 17 | 13 | 14 |
| `srr_propref_no_proto_cascade` | `myops_scar` | `hd95` | 44 | 0.00732865673 | 3 | 5 | 34 |
| `srr_propref_no_proto_cascade` | `myops_scar` | `remote_fp_count` | 44 | 0 | 0 | 0 | 44 |
| `srr_propref_scar_precision` | `myops_edema` | `dice` | 44 | -2.5997957e-05 | 3 | 5 | 36 |
| `srr_propref_scar_precision` | `myops_edema` | `hd95` | 44 | 2.96331395e-05 | 0 | 2 | 42 |
| `srr_propref_scar_precision` | `myops_edema` | `remote_fp_count` | 44 | 0 | 0 | 0 | 44 |
| `srr_propref_scar_precision` | `myops_scar` | `dice` | 44 | 3.7539275e-05 | 16 | 6 | 22 |
| `srr_propref_scar_precision` | `myops_scar` | `hd95` | 44 | 0.00395743505 | 0 | 3 | 39 |
| `srr_propref_scar_precision` | `myops_scar` | `remote_fp_count` | 44 | 0 | 0 | 0 | 44 |
| `srr_v25_no_local_refine` | `myops_edema` | `dice` | 44 | 0 | 0 | 0 | 44 |
| `srr_v25_no_local_refine` | `myops_edema` | `hd95` | 44 | 0 | 0 | 0 | 44 |
| `srr_v25_no_local_refine` | `myops_edema` | `remote_fp_count` | 44 | 0 | 0 | 0 | 44 |
| `srr_v25_no_local_refine` | `myops_scar` | `dice` | 44 | 1.54436902e-05 | 8 | 3 | 33 |
| `srr_v25_no_local_refine` | `myops_scar` | `hd95` | 44 | 0.0019611557 | 0 | 2 | 40 |
| `srr_v25_no_local_refine` | `myops_scar` | `remote_fp_count` | 44 | 0 | 0 | 0 | 44 |
| `srr_v25_no_anatomy_roi` | `myops_edema` | `dice` | 44 | -3.61419294e-05 | 6 | 6 | 32 |
| `srr_v25_no_anatomy_roi` | `myops_edema` | `hd95` | 44 | 0.000186300553 | 0 | 3 | 41 |
| `srr_v25_no_anatomy_roi` | `myops_edema` | `remote_fp_count` | 44 | 0 | 0 | 0 | 44 |
| `srr_v25_no_anatomy_roi` | `myops_scar` | `dice` | 44 | 3.18867704e-05 | 13 | 7 | 24 |
| `srr_v25_no_anatomy_roi` | `myops_scar` | `hd95` | 44 | 0.00392853591 | 1 | 3 | 38 |
| `srr_v25_no_anatomy_roi` | `myops_scar` | `remote_fp_count` | 44 | 0 | 0 | 0 | 44 |
| `srr_v25_no_anchor` | `myops_edema` | `dice` | 44 | -0.142050757 | 0 | 16 | 28 |
| `srr_v25_no_anchor` | `myops_edema` | `hd95` | 44 | 59.3779045 | 0 | 16 | 28 |
| `srr_v25_no_anchor` | `myops_edema` | `remote_fp_count` | 44 | 2073.72727 | 0 | 16 | 28 |
| `srr_v25_no_anchor` | `myops_scar` | `dice` | 44 | -0.558658776 | 1 | 42 | 1 |
| `srr_v25_no_anchor` | `myops_scar` | `hd95` | 44 | 142.906206 | 0 | 42 | 0 |
| `srr_v25_no_anchor` | `myops_scar` | `remote_fp_count` | 44 | 856.931818 | 0 | 44 | 0 |

## Decision

All expected full-fold0 rows are present. This enables a read-only audit, but does not itself authorize route promotion, validation packaging, upload, or scientific stop.
