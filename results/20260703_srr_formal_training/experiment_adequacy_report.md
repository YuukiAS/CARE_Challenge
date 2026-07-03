# Experiment Adequacy Report: 20260703 SRR Formal Training

experiment_adequacy_decision: `FAIL`
reason: all variants completed 1800 optimizer steps, but all failed `min_train_loop_seconds=1800` with train loops around 138-152 seconds.

min_optimizer_steps: `1500`
min_train_loop_seconds: `1800`

| variant | decision | optimizer_steps | train_loop_seconds | validation_events | loss_decrease | one_batch_overfit | prediction_files | failed_gate |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| `srr_propref_shared_dual_dict` | `FAIL` | 1800 | 138.168 | 9 | 2.0985 | `PASS` | 176 | train_loop_seconds below 1800 |
| `srr_propref_scar_precision` | `FAIL` | 1800 | 138.574 | 9 | 2.0580 | `PASS` | 176 | train_loop_seconds below 1800 |
| `srr_propref_no_proto_cascade` | `FAIL` | 1800 | 151.525 | 9 | 2.0215 | `PASS` | 176 | train_loop_seconds below 1800 |

Adequacy interpretation: this is not a smoke-only artifact because checkpoints, predictions, validation events, and metric CSVs exist for all variants. It is still inadequate for formal scientific conclusions because the task set an explicit 1800-second minimum train-loop budget. Therefore `STOP_NO_PROPREF_SIGNAL` is not supported.
