
# Prototype Bank Audit

Audit basis commit: `3f30e0ee4b8c951f700fe50de8810bac8e196c23`.

The T2-focused smoke claim in the prior controller report said a smoke bank had scar-positive `6`, scar-safe-negative `28`, edema-positive `8`, and edema-safe-negative `30`. That evidence is not the same as the full-fold0 primary rows.

For the full-fold0 eval source summaries, prototype counts are recorded in `bounded_source_summary.json`. The primary anchor-enabled rows have scar prototypes but `edema_positive=0` and `edema_negative=0`; `t2_present_edema_positive` is also `0`. `srr_propref_no_proto_cascade` explicitly skips prototype fitting. `selected_case_ids` for the full eval source are CenterA `Case1001` etc., not a T2-present edema-positive set, so the full eval did not actually exercise an edema prototype bank.

Critical implication: if full eval primary rows have edema prototypes equal to zero, then the full-fold0 matrix did **not** test whether an edema prototype bank helps edema inference. It only tested anchor-preserved bounded checkpoints whose edema prototype path was empty or skipped.

Machine-readable evidence: `prototype_bank_audit.csv`.
