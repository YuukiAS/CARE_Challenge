# Dictionary Bank Failure Interpretation

Status: `PARTIAL`

D1 `multiscale_dictionary` and D2 `task_specific_dictionary` have completed so far. The remaining variants are still running, so this is not a final failure interpretation.

## D1 `multiscale_dictionary`

D1 reached the intended runtime budget (`stop_reason=max_runtime_seconds`, `elapsed_seconds=23400.0`, `budget_status=OK`) and exported predictions/metrics. It produced a weak but nonzero edema signal on GT-positive/T2-present cases (`Dice=0.1001`) and a very weak scar signal (`all_cases Dice=0.0253`, `gt_positive_only Dice=0.0026`). Scar HD95 and component burden remain high, consistent with fragmented false positives and poor scar localization.

Dictionary usage did not collapse at the per-expert mean level: anatomy, scar, edema, and their context-scale gates all distributed mass across multiple experts. However, logged row-level max weights reached `1.0000`, so some batches still show hard routing. This is not enough to select the multiscale variant by itself.

## D2 `task_specific_dictionary`

D2 reached the intended runtime budget (`stop_reason=max_runtime_seconds`, `elapsed_seconds=23400.0`, `budget_status=OK`) and exported predictions/metrics. It improved scar relative to D1 (`all_cases Dice=0.0956`, `gt_positive_only Dice=0.0978`) but did so with very high HD95, component count, and remote-FP burden. Edema did not improve (`gt_positive_only Dice=0.0968`) and the no-T2 groups show non-empty edema predictions where they should remain stable, suggesting overprediction rather than a clean T2-specific edema route.

Task-specific routing is more distributed than D1 at the logged-row level (`max_logged_weight` around `0.77`-`0.81` instead of `1.00`), so the architecture improves usage balance. The metric tradeoff is not yet enough for final selection because scar localization remains poor and edema behavior is worse than the multiscale route.

## Pending Evidence

Final interpretation requires D4, D5, and D6 formal outputs. No `selection.md` should be written until enough completed variants are available to compare against the base SRR route and the dictionary-bank decision criteria.
