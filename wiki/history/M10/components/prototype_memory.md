# prototype memory 与 hard-negative

Component ID: `prototype_memory`

Branch: `MyoPS`

Current status: `partial`

Evidence status: `verified`

Review token: `M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY`

Source: `src/care_myocardium/models/srr_propref.py` / `ProposalDictionary`

Runtime evidence: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_prototype_update_ledger.csv`

Final-output effect: can affect proposal logits, but memory helper integration remains incomplete

Notes: SafePrototypeMemoryBank 仍需证明进入正式前向闭环。
