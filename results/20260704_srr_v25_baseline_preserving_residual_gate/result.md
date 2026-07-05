# Result 20260704 Baseline-Preserving nnU-Net Anchored SRR Residual Gate

status: `EXECUTED_UNAUDITED`
self_assessed_status: `NEEDS_EVIDENCE`
domain_evidence_label: `PARTIAL_MECHANISM_INCOMPLETE`

## Summary

Implemented a callable baseline-preserving residual/gated correction path in
`SRRProposeRefineMyoPS`. When nnU-Net anchor probabilities/logits are present,
the model now emits:

```text
final_logits = nnunet_anchor_logits + baseline_residual_gate * bounded_delta_srr
```

with bounded delta and a closed-biased gate. The formal runner records gate mean
and residual magnitude in `training_log.csv` and writes the formula into
`summary.json`.

## Files Changed

- `src/care_myocardium/models/srr_propref.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `src/care_myocardium/tests/test_srr_baseline_gate.py`
- `scripts/validation/validate_srr_v25_anti_laziness.py`

## Evidence

- Closed-gate toy identity test passes.
- Formal model forward emits gate/delta/anchor/SRR logits tensors.
- Anti-laziness validator no longer reports
  `BASELINE_PRESERVING_GATE_MISSING`.

## Missing For PASS

- Real validation-case identity fallback.
- Same-case shifted/mismatched anchor rejection artifact.
- Bounded residual stats from a formal fold0 run.
- Same-split help/harm vs nnU-Net.
- Required ablations.
- Read-only audit.

## Gate Decision

decision: `NEEDS_EVIDENCE`

This is code and toy-test progress, not a promoted route and not a full
scientific result.
