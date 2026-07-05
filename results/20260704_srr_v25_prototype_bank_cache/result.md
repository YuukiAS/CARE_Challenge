# Result 20260704 Real Train/OOF Prototype Bank Cache

status: `EXECUTED_UNAUDITED`
self_assessed_status: `RUNTIME_SMOKE_VERIFIED_NEEDS_FORMAL_METRICS`
domain_evidence_label: `PARTIAL_MECHANISM_INCOMPLETE`

## Summary

Integrated real train/OOF data-derived prototype bank fitting into the formal
SRR PropRef runner. The runner now fits prototype banks from train split patches
using `SRRProposeRefineMyoPS._evidence_features`, OOF nnU-Net anchors, compact
labels, and modality availability, then calls `load_prototype_bank` before
training.

The T2-focused CPU runtime smoke verifies nonzero scar and edema banks:

- scar-positive: `6`
- scar-safe-negative: `28`
- edema-positive: `8`
- edema-safe-negative: `30`
- no-T2 myocardium edema-negative voxels: `0`

## Files Changed

- `scripts/training/run_srr_propref_myops_fold0.py`
- `scripts/validation/validate_srr_v25_anti_laziness.py`
- `src/care_myocardium/tests/test_srr_runtime_prototype_bank.py`

## Runtime Evidence

- `results/20260704_srr_v25_prototype_bank_cache/prototype_bank_summary.json`
- `results/20260704_srr_v25_prototype_bank_cache/runtime_smoke_t2_focus/variants/srr_propref_shared_dual_dict/summary.json`
- `results/20260704_srr_v25_prototype_bank_cache/runtime_smoke_t2_focus/variants/srr_propref_shared_dual_dict/training_log.csv`

`training_log.csv` records:

```text
prototype_source_scar: train_oof_runtime_features_fold0
prototype_source_edema: train_oof_runtime_features_fold0
baseline_gate_status: baseline_preserving_residual
```

## Validator Effect

After this integration, the anti-laziness validator no longer reports:

- `UTILITY_ONLY_NOT_CALLED`
- `PROTOTYPE_SOURCE_NOT_FINAL`

## Missing For PASS

- Formal same-split proposal PR delta.
- Full fold0 metrics with prototype ablation.
- Help/harm vs nnU-Net.
- Read-only audit.

## Gate Decision

decision: `NEEDS_FORMAL_EVAL`

This subtask has runtime loading evidence, but it is not a full scientific pass
until formal same-split metrics and ablations exist.
