# Required Revision Plan

task: `prompts/tasks/20260703_srr_failure_audit.md`

## Recommended Next State

next_recommended_state: NEEDS_REVISION
recommended_route: `20260703_srr_propref_repair`

Do not continue with validation packaging, upload, fold expansion, hosted metric claims, or next-stage training from the prior `STOP_NO_PROPREF_SIGNAL`. The next bounded task should repair evidence collection and run a minimum effective fold0 training/evaluation protocol.

## Minimum Repair Requirements

1. Add explicit counters to `summary.json`: `actual_steps`, `optimizer_steps`, `validation_events`, `best_step`, `best_metric`, `checkpoint_source`, and `train_loop_seconds`.
2. Make checkpoint policy valid for the budget: ensure `val_every <= max_steps`, require at least one validation after warmup/proposal/refinement stages, and evaluate `checkpoint_final` separately from `checkpoint_best`.
3. Run one-batch or one-case overfit sanity before formal fold0 evaluation.
4. Use a minimum effective training budget that is materially larger than `max_steps=120` and seconds-scale train loops, with early stopping or max-runtime guards.
5. Preserve nonempty logs or explicitly write a structured command transcript during the run.
6. Export checkpoint-specific predictions and metrics under isolated directories.
7. Report proposal PR/threshold sweeps, not only fixed threshold `0.50`.
8. Report decode sanity: compact labels, per-class volumes, foreground/pathology rates, empty rate, component counts, remote FP counts, and argmax-vs-pathology-aware decode comparison.
9. Preserve CARE T2-edema handling: no-T2 cases must not become dense edema hard negatives.
10. Compare against the same-split nnU-Net fold0 baseline using the same evaluator and compact label mapping.

## Stop Criteria For Repair

- If one-batch/one-case sanity cannot overfit, classify as `SCIENTIFIC_PIPELINE_BUG` or `SCIENTIFIC_NEEDS_REVISION`, not `STOP_NO_PROPREF_SIGNAL`.
- If post-warmup/final checkpoints remain near zero after adequate training and proposal/decode sanity passes, a future auditor may consider `STOP_SUPPORTED`.
- If proposal maps still flood the volume but threshold sweeps reveal a workable operating point, continue only with a bounded proposal/decode repair task.
- If adequate training cannot be run within the allowed compute budget, classify as `SCIENTIFIC_NEEDS_EVIDENCE`.

## Blocked Actions

- validation packaging
- validation upload
- fold expansion
- hosted metric claims
- label/evaluator/fold split changes
- git commit or push
- route promotion
