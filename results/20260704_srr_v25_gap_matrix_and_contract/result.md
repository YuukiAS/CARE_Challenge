# Result 20260704 SRR-v2.5 Gap Matrix And Contract

status: `EXECUTED_UNAUDITED`
self_assessed_status: `NEEDS_REVISION`
domain_evidence_label: `PARTIAL_MECHANISM_INCOMPLETE`

## Summary

Built a current source-line gap matrix against the locked SRR-v2/v2.5 contract.
The current code has meaningful anchored SRR pieces: availability-aware routing,
slot masking, nnU-Net anchor/component consumption, T2-safe edema blocking, and
bounded crop refinement. It is still not full SRR-v2.5.

The highest-impact gaps are:

1. missing baseline-preserving nnU-Net residual/gated correction;
2. weak encoder/backbone capacity;
3. real train/OOF prototype banks not loaded by formal runtime;
4. missing `P_LV/P_RV` true distance anatomy prior;
5. shallow proposal decoder and missing component-level objective.

## Files Read

- `images/SRR-v2.png`
- `images/SRR-v2.5.png`
- `prompts/tasks/20260704_srr_v25_visual_contract_lock.md`
- `results/20260704_anchor_srr_forensic_repro_audit/implementation_claim_truth_table.md`
- `src/care_myocardium/models/srr_propref.py`
- `src/care_myocardium/models/srr_v2_unet.py`
- `src/care_myocardium/models/srr_blocks.py`
- `src/care_myocardium/models/proposal_prototypes.py`
- `src/care_myocardium/models/pathology_heads.py`
- `src/care_myocardium/losses/srr_losses.py`
- `scripts/training/run_srr_propref_myops_fold0.py`

## Outputs

- `diagram_to_code_gap_matrix.md`
- `high_impact_gap_ranking.md`
- `baseline_preservation_gap.md`
- `no_lazy_completion_contract.md`
- `source_line_evidence.md`
- `MANIFEST.md`

## Gate Decision

decision: `NEEDS_REVISION`

Every high-impact gap now has a downstream subtask and anti-laziness check, so
the contract is actionable. The current implementation cannot pass full
SRR-v2.5 completion until those downstream tasks clear the listed gaps.

## Next State

next_state: `EXECUTED_UNAUDITED`
