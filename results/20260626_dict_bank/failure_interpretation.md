# Dictionary Bank Failure Interpretation

Status: `PARTIAL`

Only `multiscale_dictionary` has completed so far. The remaining variants are still running or pending, so this is not a final failure interpretation.

## D1 `multiscale_dictionary`

D1 reached the intended runtime budget (`stop_reason=max_runtime_seconds`, `elapsed_seconds=23400.0`, `budget_status=OK`) and exported predictions/metrics. It produced a weak but nonzero edema signal on GT-positive/T2-present cases (`Dice=0.1001`) and a very weak scar signal (`all_cases Dice=0.0253`, `gt_positive_only Dice=0.0026`). Scar HD95 and component burden remain high, consistent with fragmented false positives and poor scar localization.

Dictionary usage did not collapse at the per-expert mean level: anatomy, scar, edema, and their context-scale gates all distributed mass across multiple experts. However, logged row-level max weights reached `1.0000`, so some batches still show hard routing. This is not enough to select the multiscale variant by itself.

## Pending Evidence

Final interpretation requires D2, D4, D5, and D6 formal outputs. No `selection.md` should be written until enough completed variants are available to compare against the base SRR route and the dictionary-bank decision criteria.
