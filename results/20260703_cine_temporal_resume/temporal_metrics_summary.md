# Cine Motion Hardmode Temporal Metrics

## Setup

- safe cases evaluated: `59`
- mismatch cases held out: `5`
- runtime seconds: `102.25`
- hosted `myocardium_cinemyops`: `evidence not found`; no validation upload/package was authorized.
- class_3 scar sanity remains a negative control because the source anatomy prior has no scar head.

## Local Proxy Metrics

| variant | metric | n | Dice | HD95 mean | HD95 median | components | volume ratio | empty rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cine_deformable_or_feature_warp | class_1_myocardium | 59 | 0.6032 | 10.3834 | 6.0000 | 2.1525 | 1.1260 | 0.0000 |
| cine_deformable_or_feature_warp | class_2_lv | 59 | 0.8163 | 10.5923 | 6.0000 | 1.0678 | 0.8562 | 0.0000 |
| cine_deformable_or_feature_warp | class_3_scar_sanity | 59 | 0.0000 | NA | NA | 0.0000 | 0.0000 | 1.0000 |
| cine_motion_descriptor_temporal_refiner | class_1_myocardium | 59 | 0.5624 | 11.3331 | 6.0000 | 1.4746 | 1.0167 | 0.0000 |
| cine_motion_descriptor_temporal_refiner | class_2_lv | 59 | 0.7708 | 11.0440 | 6.0000 | 1.0847 | 0.7731 | 0.0169 |
| cine_motion_descriptor_temporal_refiner | class_3_scar_sanity | 59 | 0.0000 | NA | NA | 0.0000 | 0.0000 | 1.0000 |
| cine_reference_control_recheck | class_1_myocardium | 59 | 0.5626 | 11.3331 | 6.0000 | 1.4746 | 1.0168 | 0.0000 |
| cine_reference_control_recheck | class_2_lv | 59 | 0.7709 | 11.0440 | 6.0000 | 1.0847 | 0.7733 | 0.0169 |
| cine_reference_control_recheck | class_3_scar_sanity | 59 | 0.0000 | NA | NA | 0.0000 | 0.0000 | 1.0000 |

## Temporal Diagnostics

- mean descriptor reference weight: `0.7414`
- descriptor reference dominance rate: `0.3559`
- optical-flow warp runtime mean seconds: `0.3915`
- optical-flow folding proxy mean pixels: `5335.4068`
- optical-flow smoothness proxy mean: `0.2203`

## Delta Versus Reference Control

- optical-flow/feature-warp myocardium Dice delta: `0.0406`
- optical-flow/feature-warp LV Dice delta: `0.0454`
- descriptor temporal refiner myocardium Dice delta: `-0.0002`
- descriptor temporal refiner LV Dice delta: `-0.0001`

route_decision: `TEMPORAL_PROXY_SIGNAL_DIAGNOSTIC`
self_assessed_status: `EXECUTED_UNAUDITED`
experiment_adequacy_decision: `PARTIAL`
route_promotion_decision: `NO_PROMOTION`
route_negative_decision: `STOP_NOT_SUPPORTED`
scientific_resolution_status: `SCIENTIFIC_UNRESOLVED`
