# Experiment Adequacy Report

minimum_optimizer_steps: 1500
minimum_train_loop_seconds: 1800

| variant | decision | actual_optimizer_steps | train_loop_seconds | validation_events | loss_decrease | overfit | missing_or_failed_evidence |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `srr_propref_shared_dual_dict` | `FAIL` | 0 | 0.0 | 0 | None | `PASS` | actual_optimizer_steps below minimum; train_loop_seconds below minimum; post-warmup validation events incomplete; loss decrease not demonstrated; prediction sanity/export evidence not found |
| `srr_propref_scar_precision` | `EVIDENCE_NOT_FOUND` | evidence not found | evidence not found | evidence not found | evidence not found | `evidence not found` | summary.json evidence not found |
| `srr_propref_no_proto_cascade` | `EVIDENCE_NOT_FOUND` | evidence not found | evidence not found | evidence not found | evidence not found | `evidence not found` | summary.json evidence not found |

Slurm elapsed time alone is not used as adequacy evidence. `STOP_NO_PROPREF_SIGNAL` remains unsupported unless this gate passes and a separate auditor supports the route-negative decision.
