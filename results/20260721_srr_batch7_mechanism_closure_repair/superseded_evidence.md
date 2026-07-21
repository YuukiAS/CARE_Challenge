# Superseded Batch7 Mechanism Evidence

The original Batch7 formal300 run remains valid as an operational 300-step training record. Its mechanism-closure tables are not valid intervention evidence because they reuse formal metrics rather than independent mode-specific predictions.

Superseded files:

- `results/20260721_srr_batch7_upstream_candidate_quality/final_mechanism_interventions.csv`
- `results/20260721_srr_batch7_upstream_candidate_quality/proposal_refiner_metrics.csv`
- `results/20260721_srr_batch7_upstream_candidate_quality/source_arbiter_metrics.csv`

Reason: `copied_or_placeholder_not_independent_intervention_evidence`.

Replacement evidence for this repair must come from `results/20260721_srr_batch7_mechanism_closure_repair/` after the repair runner writes one prediction root and manifest per mode, the aggregator recomputes metrics from predictions, and the strict validator rejects the old Batch7 packet as a known-bad fixture.
