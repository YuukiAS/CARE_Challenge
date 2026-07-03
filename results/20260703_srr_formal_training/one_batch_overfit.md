# One-Batch Overfit Sanity

| variant | status | steps | first_loss | last_loss | loss_decrease | case_id | elapsed_seconds |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |
| `srr_propref_shared_dual_dict` | `PASS` | 40 | 4.3328 | 2.9363 | 1.3965 | `Case1037` | 3.125 |
| `srr_propref_scar_precision` | `PASS` | 40 | 4.5757 | 3.2904 | 1.2853 | `Case1037` | 3.123 |
| `srr_propref_no_proto_cascade` | `PASS` | 40 | 3.8073 | 2.6861 | 1.1212 | `Case1037` | 3.172 |

Prototype gradient/update rows are in each variant `prototype_update_sanity.csv` and `prototype_update_sanity_formal.csv`.
