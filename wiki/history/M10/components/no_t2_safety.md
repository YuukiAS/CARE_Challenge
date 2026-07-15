# no-T2 edema 安全门

Component ID: `no_t2_safety`

Branch: `MyoPS`

Current status: `implemented`

Evidence status: `verified`

Review token: `M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY`

Source: `src/care_myocardium/models/srr_propref.py` / `canonical_t2_present`

Runtime evidence: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md`

Final-output effect: forces no-T2 edema logits to safe blocked values

Notes: 安全已实现，但不能替代 T2-present edema 性能。
