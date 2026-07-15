# 输入与 availability mask

Component ID: `inputs_availability`

Branch: `MyoPS`

Current status: `implemented`

Evidence status: `verified`

Review token: `M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY`

Source: `src/care_myocardium/models/srr_propref.py` / `availability`

Runtime evidence: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md`

Final-output effect: controls modality evidence and no-T2 branch behavior

Notes: 当前代码使用 LGE,T2,C0 availability 顺序；仍需 M10 继续证明困难子组收益。
