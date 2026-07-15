# arbitration 与 final output

Component ID: `arbitration_final_output`

Branch: `MyoPS`

Current status: `partial`

Evidence status: `verified`

Review token: `M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY`

Source: `src/care_myocardium/models/srr_propref.py` / `BranchArbitrationGate`

Runtime evidence: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md`

Final-output effect: proposal/refiner weights can affect final logits when gates open

Notes: M9 SRR-main 未超过 anchor；不能包装成 ready。
