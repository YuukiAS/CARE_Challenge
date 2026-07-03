# Proposal Failure Audit

task: `prompts/tasks/20260703_srr_failure_audit.md`

## Decision

proposal_failure_decision: NEEDS_REVISION
route_negative_decision: STOP_NOT_SUPPORTED

The proposal metrics show severe failure, but they were evaluated only at a fixed threshold of `0.50` after an undertrained/step-1-best run. The evidence supports a diagnosis of proposal flooding and poor precision, not a scientifically adequate route stop.

## Aggregate Proposal Evidence

| variant | metric | GT-positive recall | GT-positive precision | lesion recall | outside-myocardium FP ratio | mean proposal components | mean proposal voxels |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `srr_propref_shared_dual_dict` | scar | 0.1756 | 0.0041 | 0.8042 | 0.9577 | 31125.95 | 103085.55 |
| `srr_propref_shared_dual_dict` | edema | 0.9985 | 0.0039 | 1.0000 | 0.9670 | 1.00 | 705106.70 |
| `srr_propref_scar_precision` | scar | 0.0798 | 0.0044 | 0.7720 | 0.9535 | 18734.48 | 42030.48 |
| `srr_propref_scar_precision` | edema | 0.6440 | 0.0040 | 0.7635 | 0.9678 | 1336.18 | 538145.89 |
| `srr_propref_no_proto_cascade` | scar | 0.5582 | 0.0046 | 0.9221 | 0.9574 | 9224.82 | 309500.30 |
| `srr_propref_no_proto_cascade` | edema | 1.0000 | 0.0039 | 1.0000 | 0.9669 | 1.00 | 707279.91 |

## Findings

- Scar proposals either had low recall (`shared_dual_dict`, `scar_precision`) or extreme volume/flooding (`no_proto_cascade`) while precision stayed near `0.004`.
- Edema proposals generally flooded large fractions of volume with precision near `0.004`; the high recall is not useful without precision.
- Outside-myocardium FP ratio is approximately `0.95-0.97`, indicating proposal maps mostly land outside target myocardium/pathology context.
- Only threshold `0.50` is represented. A PR curve or threshold sweep is evidence not found.
- The logged training and checkpoint policy make it impossible to determine whether this is a stable mechanism failure versus an optimization/checkpoint failure.

## Evidence Index

- `scripts/training/run_srr_propref_myops_fold0.py:260-299` computes proposal rows at fixed threshold `0.50`.
- `results/20260703_myops_srr_propose_refine/proposal_metrics.csv` contains proposal recall, precision, component count, remote FP count, outside-myocardium FP ratio, and similarity diagnostics.
- `results/20260703_myops_srr_propose_refine/metrics_summary.md:8-12` summarizes near-zero proposal precision and final Dice.

## Required Future Evidence

- Proposal PR/threshold sweep for scar and edema, at minimum across thresholds such as `0.1, 0.2, 0.3, 0.5, 0.7, 0.9`.
- Lesion-wise recall and precision at the selected operating point.
- Outside-myocardium FP ratio and remote FP components at each threshold.
- Same-checkpoint comparison of proposal-gated decode versus argmax decode.
- Separation of undertraining/checkpoint effects from proposal-head design effects.
