# One-Batch Overfit

| formal_variant | script_alias | pre_submit_stage0 | formal_stage0 | steps | first_loss | last_loss | loss_decrease | case_id |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `anchored_srr_v25_full` | `srr_propref_shared_dual_dict` | `PASS` | `PASS` | 40 | 4.28929328918457 | 1.5355852842330933 | 2.753708004951477 | `Case1037` |
| `anchored_scar_precision_edema_safe` | `srr_propref_scar_precision` | `PASS` | `PASS` | 40 | 4.717623710632324 | 1.7456912994384766 | 2.9719324111938477 | `Case1037` |
| `anchored_conservative_cascade_no_proto_or_frozen_proto` | `srr_propref_no_proto_cascade` | `PASS` | `PASS` | 40 | 4.102067470550537 | 1.414960503578186 | 2.687106966972351 | `Case1037` |

Pre-submit Stage 0 used a bounded CPU sanity config. Formal jobs rerun Stage 0 with the formal GPU config before optimizer training.
