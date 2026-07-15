# CineMA/registration/temporal fail-closed fidelity contracts

Component ID: `cine_followup_fidelity_contracts`

Branch: `Cine`

Current status: `implemented`

Evidence status: `verified`

Review token: `NOT_REVIEWED`

Source: `src/care_myocardium/cine/followup/contracts.py` / `RegistrationGateEvidence`

Runtime evidence: `results/20260714_srr_v3_m10_followup_cine_fidelity/validator_report.md`

Final-output effect: prevents proxy SyN, pair-as-case gate, frame0 fallback, and temporal output without passed registration; it is not runtime success evidence

Notes: F2 unit tests passed and freeze receipt exists; formal runtime remained F3-only.
