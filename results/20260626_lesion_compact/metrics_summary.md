# Lesion Compact Metrics Summary

Status: `REVISE_COMPACTNESS_AND_REPEAT`

All four fold0 lesion compact variants completed with Slurm `ExitCode=0:0`, but all stopped by `max_steps` before the requested `min_effective_seconds`, so every variant has `budget_status=UNDER_BUDGET_MAX_STEPS`.

## Primary Comparison

| route | edema GT+ Dice | edema GT+ HD95 | scar all Dice | scar all HD95 | budget |
| --- | ---: | ---: | ---: | ---: | --- |
| previous best_srr_recovered | 0.1928 | 97.7248 | 0.0923 | 127.0317 | reference |
| D4 cross_modal_interaction_dictionary | 0.1599 | 114.0297 | 0.1054 | 129.2199 | OK |
| nnU-Net fold0 reference | 0.3944 | 7.2769 | 0.5602 | 13.6005 | reference |
| `soft_anatomy_containment` | 0.1873 | 128.7981 | 0.1091 | 134.8531 | `UNDER_BUDGET_MAX_STEPS` |
| `component_compactness_loss` | 0.1653 | 99.3085 | 0.0881 | 124.1339 | `UNDER_BUDGET_MAX_STEPS` |
| `scar_lge_fallback_boost` | 0.0907 | 133.7954 | 0.0800 | 147.4159 | `UNDER_BUDGET_MAX_STEPS` |
| `edema_t2_center_balance` | 0.0004 | 41.0821 | 0.0235 | 114.2632 | `UNDER_BUDGET_MAX_STEPS` |

## Localization And Stability Diagnostics

| variant | edema GT+ components | edema GT+ remote FP | edema CenterC Dice | no-T2 edema components | scar components | scar remote FP | scar LGE-only Dice |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `soft_anatomy_containment` | 84.88 | 66.75 | 0.0770 | 13.89 | 121.98 | 89.32 | 0.0848 |
| `component_compactness_loss` | 28.88 | 21.38 | 0.0395 | 50.46 | 74.68 | 54.93 | 0.0709 |
| `scar_lge_fallback_boost` | 136.31 | 109.12 | 0.0280 | 100.57 | 211.09 | 157.34 | 0.0695 |
| `edema_t2_center_balance` | 0.12 | 0.00 | 0.0000 | 6.04 | 8.36 | 6.52 | 0.0004 |

## Readout

- L1 `soft_anatomy_containment` slightly improved both primary Dice values over D4, but worsened HD95 and produced severe component/remote-FP burden.
- L2 `component_compactness_loss` improved both edema and scar HD95 relative to D4, but scar Dice dropped and no-T2/remote-FP burden remained high.
- L3 `scar_lge_fallback_boost` did not rescue scar; scar Dice and HD95 both worsened relative to D4.
- L4 `edema_t2_center_balance` collapsed on GT-positive edema and harmed scar, despite low HD95 values caused by mostly empty predictions.
- None of the four variants clears the compact-package gate. The most useful signal is L2 HD95 improvement, not a selectable package.
