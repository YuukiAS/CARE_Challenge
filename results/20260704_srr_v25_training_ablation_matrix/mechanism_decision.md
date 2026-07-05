# Mechanism Decision

decision: `FULL_FOLD0_MATRIX_COMPLETE_NEEDS_FINAL_READONLY_AUDIT`

The bounded matrix produced same-split hard-subgroup help/harm rows for three PropRef variants, three isolated ablation rows, and two identity rows.
The full fold0 eval-only pass now covers all six expected non-identity rows from those bounded checkpoints.
It is useful for mechanism triage and final audit, but remains underpowered and does not support route promotion or scientific stop by itself.

Current decision: hard-subgroup ablation rows and full-fold0 eval-only rows are complete; final read-only audit is still required.
