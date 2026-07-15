# edema soft-ROI refiner

Component ID: `edema_refiner`

Branch: `MyoPS`

Current status: `partial`

Evidence status: `verified`

Review token: `M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY`

Source: `src/care_myocardium/models/srr_propref.py` / `edema_refiner`

Runtime evidence: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_edema_refiner_roi_stats.csv`

Final-output effect: affects ROI-local logits only when T2-present safety allows

Notes: 需要 edema-specific recall/HD95 证据。
