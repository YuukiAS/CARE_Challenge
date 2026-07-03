# Result 20260703 SRR PropRef Repair

experiment_adequacy_decision: FAIL
route_promotion_decision: NOT_EVALUABLE
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNDERTRAINED
route_decision: SCIENTIFIC_UNDERTRAINED
self_assessed_status: EXECUTED_UNAUDITED
role: executor
review_required: true

## Execution Summary

Patched the SRR-ProposeRefine runner for task-scoped repair evidence: non-step1-only checkpoint policy, explicit optimizer/time/validation/stage/loss counters, one-batch overfit sanity, prototype gradient/update sanity, best/final checkpoint export comparison, argmax versus pathology-aware decode, proposal threshold/PR sweep, and provenance output.

No network, external upload, validation packaging/upload, fold expansion, label/evaluator/fold split change, old SRR-v2 tuning route, git commit, or git push was performed.

## Variant Evidence

| variant | adequacy | optimizer_steps | train_loop_seconds | validation_events | best_step | stop_reason |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `srr_propref_shared_dual_dict` | `FAIL` | 0 | 0.0 | 0 | evidence not found | `local_smoke_interrupted_before_formal_summary` |
| `srr_propref_scar_precision` | `EVIDENCE_NOT_FOUND` | evidence not found | evidence not found | evidence not found | evidence not found | `evidence not found` |
| `srr_propref_no_proto_cascade` | `EVIDENCE_NOT_FOUND` | evidence not found | evidence not found | evidence not found | evidence not found | `evidence not found` |

## Files Changed

- `scripts/training/run_srr_propref_myops_fold0.py`
- `jobs/src/run_srr_propref_myops_fold0.sh`
- `scripts/evaluation/aggregate_srr_propref_repair_20260703.py`
- `results/20260703_srr_propref_repair/`

## Incomplete Items

- `review.md` was not written because this session is executor-only.
- Adequate formal fold0 conclusions require the adequacy gate in `experiment_adequacy_report.md` plus separate audit.
- `STOP_NO_PROPREF_SIGNAL` is not claimed by this executor unless adequacy passes; current route-negative decision remains `STOP_NOT_SUPPORTED`.

## Required Next State

EXECUTED_UNAUDITED
