# Unit Test Report

## Commands

- `python -m py_compile scripts/evaluation/export_srr_v3_m2_runtime_repair_smoke.py scripts/training/run_srr_propref_myops_fold0.py`: PASS.
- `python scripts/evaluation/export_srr_v3_m2_runtime_repair_smoke.py --known-bad-validator-smoke`: PASS; claim-only packet failed closed.
- `python scripts/evaluation/export_srr_v3_m2_runtime_repair_smoke.py`: PASS; generated M2 smoke outputs.
- `python scripts/evaluation/export_srr_v3_m2_runtime_repair_smoke.py --strict-validate`: PASS.

## Required Coverage

- Closed-gate identity: `PASS`, max abs diff `0.0`.
- Synthetic correction-positive gate opening: `PASS`, gate mean `0.9241417646408081`, correction abs mean `0.07663097977638245`, bounded delta max `3.9802191257476807`.
- T2-present prototype selection: `PASS`, repair-added cases `Case2001;Case2003;Case2004;Case2005`, edema positive `4`, edema negative `17`, T2-present edema positive voxels `4351`.
- No-T2 edema blocking: `PASS`, proposal logit max `-20.0`, final edema logit max `-20.0`, decode edema voxels `0`.
- Bounded local crop behavior: scar crop ratio `0.046875`, edema crop ratio `0.08544921875`, both `is_full_volume_crop=False`.

## Validator

The M2 strict validator requires every required CSV to have headers, rows, non-claim evidence, and passing statuses. The real packet passes; the synthetic known-bad packet fails closed.
