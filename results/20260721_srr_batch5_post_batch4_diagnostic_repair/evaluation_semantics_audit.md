# Batch5 Evaluation Semantics Audit

status: BATCH5_EVALUATION_SEMANTICS_COMPLETE
result_root: results/20260721_srr_batch5_post_batch4_diagnostic_repair
case_count: 44
checkpoint_steps: 600,1200,1800
decode_rule: outputs_logits_argmax
metric_populations: positive_gt_cases, all_case_empty_safe

## Checkpoint Eligibility

`checkpoint_reranking.csv` includes the Batch5 gates for Dice delta, help>=harm, HD95 relative worsening <=5%, and remote-FP relative worsening <=5%.

Formal rerank result:

- step_1800: eligible, formal_argmax_rank 1
- step_600: eligible, formal_argmax_rank 2
- step_1200: not eligible because help/harm failed

## Intervention Modes

All seven required modes were evaluated on the same 44-case validation set:

- anchor_identity_control
- anchor_bounded_full
- srr_no_anchor_control
- anchor_bounded_proposal_only
- anchor_bounded_refiner_only
- production_gate_closed
- production_gate_open_bounded_control

Key step_1800 positive-case deltas:

- anchor_bounded_full: edema +0.0006796506674334821; scar +0.0013726911360293149
- proposal_only: edema +0.00011768188064261408; scar +0.0009712969116208115
- refiner_only: edema +0.001390880527025535; scar +0.001126296286479862
- gate_open_bounded_control: edema +0.0010284036834695073; scar +0.001313312387252268
- srr_no_anchor_control: edema -0.08222263788926122; scar -0.034128191279282655

## Oracle Repair

`oracle_headroom.csv` now uses GT-aware anchor error voxels and candidate harmful-correction voxels. It contains 88 pathology rows and marks every oracle row as diagnostic-only, not deployable.

Mean numeric oracle Dice gain: +0.002557208291550748.
Maximum per-pathology oracle Dice gain: +0.02138642933183843.
