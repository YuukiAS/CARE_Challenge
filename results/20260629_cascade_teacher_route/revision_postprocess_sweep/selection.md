# Cascade Postprocess Sweep Selection

status: `STOP_NO_POSTPROCESS_ROUTE`
selected_variant: `none`

## Reasons

- All eight postprocessed candidates were evaluated as
  `fail_stop_refiner_candidate`.
- The best postprocessed Dice deltas remained tiny.
- Some modes improved component count or HD95, but none removed both component
  and remote-FP failure modes while preserving a material scar/edema gain.
- This suggests the cascade signal is not recoverable by simple
  baseline-overlap or top-k component pruning.

No validation upload, upload-ready package, fold expansion, evaluator change, or
label mapping change was performed.
