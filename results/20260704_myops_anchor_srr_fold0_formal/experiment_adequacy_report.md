# Experiment Adequacy Report

minimum_optimizer_steps: 1500
minimum_train_loop_seconds: 1800

| formal_variant | script_alias | decision | optimizer_steps | train_loop_seconds | validation_events | loss_decrease | missing_or_failed_evidence |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `anchored_srr_v25_full` | `srr_propref_shared_dual_dict` | `PASS` | 24000 | 3665.815591425984 | 40 | 2.6257859468460083 | none |
| `anchored_scar_precision_edema_safe` | `srr_propref_scar_precision` | `PASS` | 22800 | 3514.2873339329963 | 38 | 3.537801504135132 | none |
| `anchored_conservative_cascade_no_proto_or_frozen_proto` | `srr_propref_no_proto_cascade` | `PASS` | 22800 | 9873.30117172096 | 38 | 3.27606925368309 | none |

Pending/running jobs are not formal evidence complete. Budget exhaustion while curves still move remains `SCIENTIFIC_UNDERTRAINED` or `NEEDS_MONITOR`, not route failure.
