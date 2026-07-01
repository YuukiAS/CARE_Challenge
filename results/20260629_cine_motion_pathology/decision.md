# Decision 20260626 Cine Temporal

status: `KEEP_REFERENCE_CONTROL`

## Reasons

- keyframe_context_retrieval.myocardium_delta=-0.0003
- keyframe_context_retrieval.lv_delta=-0.0000
- anatomy_consistency_temporal.myocardium_delta=-0.0964
- anatomy_consistency_temporal.lv_delta=-0.0753
- Temporal fusion did not beat the frame0 reference control on class_1/class_2 local proxies without tradeoff.
- class_3 scar sanity is not used as the sole failure reason because the source model has no scar head.
