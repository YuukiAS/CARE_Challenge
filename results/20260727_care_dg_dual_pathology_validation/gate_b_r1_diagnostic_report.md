# Gate B-R1 Diagnostic Report

created_at_utc: `2026-07-28T02:14:51Z`

Gate B-R1 fixed the overactive fragmented inference failure by replacing patch final-logit averaging with overlap=0.5 Gaussian blending of scar/edema deltas and one full-volume scar-priority composition. It did not satisfy the scientific expansion gate because no pathology improved by more than 0.005 Dice over the anchor on complete-trimodal fold0.

## Complete16 Metrics
| model | pathology | Dice | HD95 mm | remote FP mm3 | components |
|---|---:|---:|---:|---:|---:|
| A0_nnunet_anchor | scar | 0.693335 | 9.267 | 313.2 | 1.875 |
| A0_nnunet_anchor | edema_zone | 0.752194 | 11.697 | 1056.7 | 2.000 |
| A0_nnunet_anchor | pure_edema | 0.394436 | 20.012 | 2150.1 | 9.125 |
| A1_direct_residual_control | scar | 0.693970 | 9.315 | 298.3 | 1.750 |
| A1_direct_residual_control | edema_zone | 0.752998 | 11.722 | 1050.4 | 2.062 |
| A1_direct_residual_control | pure_edema | 0.393887 | 20.048 | 2153.7 | 8.750 |
| A2_care_dg_r1_selected | scar | 0.694740 | 9.309 | 311.8 | 1.812 |
| A2_care_dg_r1_selected | edema_zone | 0.753362 | 11.755 | 1053.9 | 2.188 |
| A2_care_dg_r1_selected | pure_edema | 0.392333 | 20.230 | 2167.0 | 8.688 |
| A3_no_stage_b_matched_control | scar | 0.695876 | 9.236 | 337.6 | 2.062 |
| A3_no_stage_b_matched_control | edema_zone | 0.754701 | 11.642 | 1000.8 | 2.625 |
| A3_no_stage_b_matched_control | pure_edema | 0.395067 | 19.827 | 2108.5 | 10.750 |

## Scientific Gate
status: `FAIL`
scientific_expansion_authorized: `false`
failures: `no_pathology_improves_by_more_than_0.005`
help_count: `28`, harm_count: `20`

## Interpretation
- Old Gate B complete16 A2 showed large fragmentation: scar components 11.5, edema-zone components 34.94, pure-edema components 80.19.
- R1 selected step8000 using train-side complete inner cases only; outer fold0 was not used for selection.
- R1 complete16 A2 safety is acceptable by the specified checks: HD95 within 1.05x anchor, remote FP within 10%, no component order-of-magnitude explosion, and help >= harm - 1.
- R1 complete16 A2 efficacy is too small for expansion: scar +0.001405, edema-zone +0.001168, pure-edema -0.002103 Dice versus anchor.
- A3 no-Stage-B matched control is slightly better than A2 on complete16 Dice, so Stage B calibration is not independently supported on fold0 under this R1 inference recipe.

## Current Decision
`GATE_B_R1_OPERATIONAL_PASS_SCIENTIFIC_FAIL_EXPANSION_PAUSED`: do not run folds 1-4 unless a later authorized same-scope repair satisfies the Gate B scientific expansion criteria.
