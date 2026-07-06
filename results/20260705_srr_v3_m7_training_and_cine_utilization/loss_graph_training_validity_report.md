# Loss Graph Training Validity Report

status: `ORIGINAL_TRAINING_GRAPH_CONNECTED_LOGGING_METRICS_DETACHED`

- original total loss function: `src/care_myocardium/losses/srr_losses.py::srr_m6_expanded_total_loss` via `scripts/training/run_srr_propref_myops_fold0.py::propref_loss`.
- original optimizer backward path: `loss.backward()` was called on the `total` tensor returned by `srr_m6_expanded_total_loss`; the total is the weighted sum of expanded component tensors before metrics detachment.
- original blocker cause: metrics in `srr_m6_expanded_total_loss` were detached for logging, so the old `loss_component_gradient_sanity.csv` tried to backward detached metrics and produced 75/75 `BACKWARD_FAILED` rows.
- code repair: `detach_metrics=True` remains the default logging behavior; M7 continued gradient sanity uses `detach_metrics=False` to return graph-connected component tensors.
- rerun training required: `false`; continued evidence proves the original training backward path used graph-connected `total`, while only the gradient-sanity logging path was detached.
- continued gradient sanity runtime seconds: `2263.636`
