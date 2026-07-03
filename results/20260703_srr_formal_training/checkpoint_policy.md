# Checkpoint Policy

policy_status: `BEST_AND_FINAL_EXPORTED`

| variant | best_step | final_step | best_val_patch_loss | validation_events | checkpoint_best | checkpoint_final |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `srr_propref_shared_dual_dict` | 1800 | 1800 | 1.3569 | 9 | `/users/a/e/aereinh/CARE/results/20260703_srr_formal_training/variants/srr_propref_shared_dual_dict/checkpoints/fold_0/propref_config/checkpoint_best.pt` | `/users/a/e/aereinh/CARE/results/20260703_srr_formal_training/variants/srr_propref_shared_dual_dict/checkpoints/fold_0/propref_config/checkpoint_final.pt` |
| `srr_propref_scar_precision` | 1800 | 1800 | 1.5820 | 9 | `/users/a/e/aereinh/CARE/results/20260703_srr_formal_training/variants/srr_propref_scar_precision/checkpoints/fold_0/propref_config/checkpoint_best.pt` | `/users/a/e/aereinh/CARE/results/20260703_srr_formal_training/variants/srr_propref_scar_precision/checkpoints/fold_0/propref_config/checkpoint_final.pt` |
| `srr_propref_no_proto_cascade` | 1800 | 1800 | 1.2471 | 9 | `/users/a/e/aereinh/CARE/results/20260703_srr_formal_training/variants/srr_propref_no_proto_cascade/checkpoints/fold_0/propref_config/checkpoint_best.pt` | `/users/a/e/aereinh/CARE/results/20260703_srr_formal_training/variants/srr_propref_no_proto_cascade/checkpoints/fold_0/propref_config/checkpoint_final.pt` |

Best checkpoint selection was eligible after the warmup fraction. In these runs, best and final both point to step 1800 for all three variants. Both checkpoint-specific prediction and metric files were exported.
