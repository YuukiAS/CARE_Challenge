# Lesion Compact Selection

status: `REVISE_COMPACTNESS_AND_REPEAT`

selected_variant: `none`
base_dictionary_route: `cross_modal_interaction_dictionary`
best_signal_variant: `component_compactness_loss`

## Decision

Do not select a compactness package for fold expansion. Repeat a revised compactness/localization round on top of D4 `cross_modal_interaction_dictionary` instead.

## Evidence

- L2 `component_compactness_loss` is the only route with a direct HD95 signal: edema GT+ HD95 `99.3085` vs D4 `114.0297`, scar all HD95 `124.1339` vs D4 `129.2199`.
- L2 does not pass selection: scar all Dice falls to `0.0881` vs D4 `0.1054`, no-T2 edema component burden remains high, and predictions remain fragmented.
- L1 improves Dice slightly (`edema GT+ 0.1873`, `scar all 0.1091`) but worsens HD95 and creates severe component/remote-FP burden.
- L3 does not rescue scar (`scar all Dice 0.0800`, scar HD95 `147.4159`).
- L4 collapses GT-positive edema (`0.0004`) and scar (`0.0235`).
- All four jobs completed but have `budget_status=UNDER_BUDGET_MAX_STEPS`, so the next round must raise step caps or otherwise enforce the 6-7h effective budget.

## Next Repeat Requirements

- Keep D4 `cross_modal_interaction_dictionary` as the base dictionary route.
- Carry forward L2-style compactness/HD95 pressure, but add explicit no-T2 stability and remote-FP controls.
- Do not combine all mechanisms. Start with one revised compactness mechanism and one Dice-preserving guard.
- Use updated job wrappers with `--max-steps 1000000` so max-steps does not end before `--min-effective-seconds 21600`.
- Do not expand folds or prepare validation upload from this result.
