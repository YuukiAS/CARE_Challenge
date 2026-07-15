# scar soft-ROI refiner

Component ID: `scar_refiner`

Branch: `MyoPS`

Current status: `partial`

Evidence status: `verified`

Review token: `M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY`

Source: `src/care_myocardium/models/srr_propref.py` / `scar_refiner`

Runtime evidence: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_scar_refiner_roi_stats.csv`

Final-output effect: affects ROI-local final logits through refiner_delta

Notes: 需要 scar-specific 因果消融。
