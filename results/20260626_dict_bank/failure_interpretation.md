# Dictionary Bank Failure Interpretation

Status: `COMPLETE`

All five dictionary variants completed.

## D1 `multiscale_dictionary`

D1 reached the intended runtime budget (`stop_reason=max_runtime_seconds`, `elapsed_seconds=23400.0`, `budget_status=OK`) and exported predictions/metrics. It produced a weak but nonzero edema signal on GT-positive/T2-present cases (`Dice=0.1001`) and a very weak scar signal (`all_cases Dice=0.0253`, `gt_positive_only Dice=0.0026`). Scar HD95 and component burden remain high, consistent with fragmented false positives and poor scar localization.

Dictionary usage did not collapse at the per-expert mean level: anatomy, scar, edema, and their context-scale gates all distributed mass across multiple experts. However, logged row-level max weights reached `1.0000`, so some batches still show hard routing. This is not enough to select the multiscale variant by itself.

## D2 `task_specific_dictionary`

D2 reached the intended runtime budget (`stop_reason=max_runtime_seconds`, `elapsed_seconds=23400.0`, `budget_status=OK`) and exported predictions/metrics. It improved scar relative to D1 (`all_cases Dice=0.0956`, `gt_positive_only Dice=0.0978`) but did so with very high HD95, component count, and remote-FP burden. Edema did not improve (`gt_positive_only Dice=0.0968`) and the no-T2 groups show non-empty edema predictions where they should remain stable, suggesting overprediction rather than a clean T2-specific edema route.

Task-specific routing is more distributed than D1 at the logged-row level (`max_logged_weight` around `0.77`-`0.81` instead of `1.00`), so the architecture improves usage balance. The metric tradeoff is not yet enough for final selection because scar localization remains poor and edema behavior is worse than the multiscale route.

## D4 `cross_modal_interaction_dictionary`

D4 reached the intended runtime budget (`stop_reason=max_runtime_seconds`, `elapsed_seconds=23400.0`, `budget_status=OK`) and currently has the strongest partial tradeoff: edema GT-positive Dice `0.1599` and scar all-case Dice `0.1054`. This supports the interaction-expert hypothesis more than D1/D2 on raw Dice.

The caveat is localization quality. HD95 remains high (`114.03` for edema GT-positive and `129.22` for scar all-cases), and component/remote-FP burden remains large. D4 is the current partial front-runner, but it still needs comparison with D5 and D6 before writing `selection.md`.

## D5 `anchor_guided_dictionary`

D5 reached the intended runtime budget (`stop_reason=max_runtime_seconds`, `elapsed_seconds=23400.0`, `budget_status=OK`). It is currently the strongest partial edema variant (`gt_positive Dice=0.1755`) and has lower edema component burden than D4 on GT-positive/T2-present cases. Scar is weaker than D4 (`all_cases Dice=0.0877`), so it does not dominate the current partial comparison.

The anchor route still has the same broad localization caveat: HD95 remains high (`102.88` edema GT-positive, `136.80` scar all-cases), and no-T2 edema empty-GT cases are not perfectly stable. It may be a useful edema-side idea, but it is not enough for final selection without D6 and the full decision table.

## D6 `hierarchical_router_dictionary`

D6 completed successfully but stopped by `max_steps` before reaching the requested `min_effective_seconds` (`elapsed_seconds=20961.2`, `budget_status=UNDER_BUDGET_MAX_STEPS`). It produced the strongest edema GT-positive Dice (`0.2079`) and the best edema Dice above the previous recovered SRR baseline, but scar all-case Dice fell to `0.0651`, below both D4 and the previous recovered SRR baseline. HD95 and no-T2 empty-GT component burden also remain high.

D6 is evidence that the availability-aware hierarchical route can help edema sensitivity, but it is not the best single variant for the next compactness/localization step because its scar tradeoff is too large and its budget status is weaker than D4/D5.

## Pending Evidence

## Cross-Variant Conclusion

D4 `cross_modal_interaction_dictionary` is the selected dictionary route for the next compactness/localization step. It has the strongest scar all-case Dice among new variants (`0.1054`) and beats the previous recovered SRR scar baseline (`0.0923`) while retaining a non-collapsed edema signal (`0.1599`). D5 and D6 show useful edema-side signals but do not offer the same scar tradeoff; D6 also ended under the effective-time budget. The common unresolved failure mode across all variants is localization quality: HD95, component count, and remote false positives remain too high, so the next step should target compactness and false-positive morphology rather than another pure dictionary expansion.
