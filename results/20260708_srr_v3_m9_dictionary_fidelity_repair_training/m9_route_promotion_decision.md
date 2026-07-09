# M9 Route Promotion Decision

decision: `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`

M9 is complete enough for independent review, but it does not support route promotion.

Evidence:

- The alternate M9 training adequacy gate is satisfied: three formal SRR-main candidates reached `>=7200` train-loop seconds each.
- Aggregate formal train-loop seconds are `26415.268`, below the aggregate `28800` second gate.
- All selected metric-facing formal candidates remain negative against the tracked M8 nnU-Net anchor:
  - `m9_srr_main_true_br2_pattern_sip`: mean Dice delta `-0.0419089071946592`, HD95 delta `14.723931326384324`, remote-FP delta `2.28125`.
  - `m9_srr_main_lesion_proposal_memory`: mean Dice delta `-0.055947265941412486`, HD95 delta `14.009386143746562`, remote-FP delta `1.7604166666666667`.
  - `m9_srr_main_t2_edema_recall_focus`: mean Dice delta `-0.06009304704870019`, HD95 delta `21.32252454340387`, remote-FP delta `6.614583333333333`.
- Cine final-output evidence exists only as local safe-subset proxy evidence, not hosted/challenge evidence.

No route promotion is authorized. Explicit safety boundary: no validation upload, no hosted metric claim, no fold expansion, no M10.
