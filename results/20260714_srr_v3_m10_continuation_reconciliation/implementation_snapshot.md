# M10 Follow-up Implementation Snapshot

Generated at: `2026-07-15T01:20:27Z`

Git head before mapper/finalizer amend: `78d63987917ae4891ebae77628c6a624ba055c00`

Implemented or added first-party paths:

- `src/care_myocardium/cine/followup/`
- `src/care_myocardium/tests/test_m10_followup_cine_fidelity.py`
- `configs/srr_v3_m10_followup_cine.yaml`
- `jobs/src/run_srr_v3_m10_followup_cine_*.sh`
- `scripts/evaluation/*m10_followup*`
- `scripts/training/run_cine_*_m10_followup.py`

Runtime evidence packets:

- F1: `results/20260714_srr_v3_m10_followup_wave2_reconciliation/`
- F2: `results/20260714_srr_v3_m10_followup_cine_fidelity/`
- F3: `results/20260714_srr_v3_m10_followup_cine_runtime/`

F3 frozen-runtime status: `M10_FOLLOWUP_CINE_RUNTIME_NEEDS_REVISION_RETURN_TO_CINE_FIDELITY_WAVE`.
