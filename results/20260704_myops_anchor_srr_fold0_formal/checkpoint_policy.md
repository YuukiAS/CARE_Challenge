# Checkpoint Policy

| formal_variant | script_alias | best_step | final_step | validation_events | checkpoint_best | checkpoint_final |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `anchored_srr_v25_full` | `srr_propref_shared_dual_dict` | 22200 | 24000 | 40 | `/users/a/e/aereinh/CARE/results/20260704_myops_anchor_srr_fold0_formal/variants/srr_propref_shared_dual_dict/checkpoints/fold_0/propref_config/checkpoint_best.pt` | `/users/a/e/aereinh/CARE/results/20260704_myops_anchor_srr_fold0_formal/variants/srr_propref_shared_dual_dict/checkpoints/fold_0/propref_config/checkpoint_final.pt` |
| `anchored_scar_precision_edema_safe` | `srr_propref_scar_precision` | 18000 | 22800 | 38 | `/users/a/e/aereinh/CARE/results/20260704_myops_anchor_srr_fold0_formal/variants/srr_propref_scar_precision/checkpoints/fold_0/propref_config/checkpoint_best.pt` | `/users/a/e/aereinh/CARE/results/20260704_myops_anchor_srr_fold0_formal/variants/srr_propref_scar_precision/checkpoints/fold_0/propref_config/checkpoint_final.pt` |
| `anchored_conservative_cascade_no_proto_or_frozen_proto` | `srr_propref_no_proto_cascade` | 18000 | 22800 | 38 | `/users/a/e/aereinh/CARE/results/20260704_myops_anchor_srr_fold0_formal/variants/srr_propref_no_proto_cascade/checkpoints/fold_0/propref_config/checkpoint_best.pt` | `/users/a/e/aereinh/CARE/results/20260704_myops_anchor_srr_fold0_formal/variants/srr_propref_no_proto_cascade/checkpoints/fold_0/propref_config/checkpoint_final.pt` |

Formal best checkpoint selection is validation-loss based after warmup eligibility. Final checkpoint is retained for comparison.
