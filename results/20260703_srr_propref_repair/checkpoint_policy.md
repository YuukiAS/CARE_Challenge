# Checkpoint Policy

| variant | best_step | final_step | validation_schedule | validation_events | checkpoint_best | checkpoint_final |
| --- | ---: | ---: | --- | ---: | --- | --- |
| `srr_propref_shared_dual_dict` | evidence not found | 0 | `evidence not found` | 0 | `evidence not found` | `evidence not found` |
| `srr_propref_scar_precision` | evidence not found | evidence not found | `evidence not found` | evidence not found | `evidence not found` | `evidence not found` |
| `srr_propref_no_proto_cascade` | evidence not found | evidence not found | `evidence not found` | evidence not found | `evidence not found` | `evidence not found` |

Policy: formal evidence must compare best and final checkpoints. Best checkpoint selection is ineligible before the warmup fraction and falls back to final when no eligible validation exists.
