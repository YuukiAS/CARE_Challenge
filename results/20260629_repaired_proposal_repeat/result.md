# Result 20260629 Repaired Proposal Repeat

Status: formal fold0 variants complete; route not selected.

## Summary

This task tested whether the weak Result5 proposal results were mainly caused by known repairable issues: ignore-label masking, raw argmax decoding, checkpoint choice, hard-negative replay, and fixed proposal-logit mixing. The repaired routes were executable and produced complete fold0 predictions, but they did not recover a competitive proposal signal.

The main result is negative: repaired SRRMyoPSLite proposal remains far below nnU-Net and does not beat the D4 dictionary or previous proposal route on the required pathology targets. This supports routing the active rescue goal to SRR-v2 and the nnU-Net anchored cascade teacher route rather than continuing to patch the shallow proposal head.

## Files Read

- `prompts/tasks/20260629_repaired_proposal_repeat.md`
- `docs/notes/20260629_srr_capacity_and_result5_audit.md`
- `docs/notes/20260629_result5_gap_audit.md`
- `docs/notes/deep_research/Result5.pdf`
- `results/20260628_myops_proposal/selection.md`
- `results/20260629_loss_decode_calibration/selection.md`
- `results/20260629_pathology_checkpoint_selection/selection.md`
- `results/20260629_proposal_memory_hardneg/selection.md`
- `results/20260629_true_soft_roi_refine/selection.md`
- `src/care_myocardium/models/srr_myops.py`
- `src/care_myocardium/losses/srr_losses.py`
- `scripts/training/run_srr_myops_fold0.py`

## Code and Script Changes

- Added configurable proposal final mix weight in `src/care_myocardium/models/srr_myops.py`.
- Added repaired proposal variants, hard-negative replay loading, and SRR-v2 plumbing in `scripts/training/run_srr_myops_fold0.py`.
- Added aggregation support in `scripts/evaluation/finalize_rescue_srr_route.py`.
- Added task Slurm wrapper `jobs/src/run_repaired_proposal_repeat.sh`.

## Jobs

| job | variant | partition | state | elapsed | exit |
| --- | --- | --- | --- | ---: | --- |
| `57094448_0` | `repaired_uncertainty_hardneg` | `htzhulab` | `COMPLETED` | 06:35:50 | `0:0` |
| `57094448_1` | `repaired_posneg_scar_hardneg` | `htzhulab` | `COMPLETED` | 06:33:22 | `0:0` |
| `57094448_2` | `repaired_joint_calibrated_proposal` | `htzhulab` | `COMPLETED` | 06:31:31 | `0:0` |

Log paths:

- `logs/RePropF0_repaired_uncertainty_hardneg_57170530_20260630_193743.log`
- `logs/RePropF0_repaired_posneg_scar_hardneg_57170596_20260630_194005.log`
- `logs/RePropF0_repaired_joint_calibrated_proposal_57094448_20260630_194156.log`

## Metrics

Best repaired scar:

- `repaired_posneg_scar_hardneg`, scar all-case Dice `0.1038`, HD95 `136.0183`.
- D4 dictionary scar all-case reference is `0.1054`; nnU-Net fold0 scar Dice is `0.5602`.

Best repaired edema:

- `repaired_uncertainty_hardneg`, edema GT-positive Dice `0.1545`, HD95 `128.6386`.
- D4 dictionary edema GT-positive reference is `0.1599`; previous `proposal_uncertainty_gate` was `0.2034`; nnU-Net fold0 edema Dice is `0.3944`.

## Decision

Selection: `ROUTE_TO_CASCADE_TEACHER`.

The task was completed technically, but the repaired proposal route was not selected. The likely mechanism is architecture and lesion-formation capacity rather than a single remaining pipeline bug.

## Outputs

- `results/20260629_repaired_proposal_repeat/selection.md`
- `results/20260629_repaired_proposal_repeat/failure_interpretation.md`
- `results/20260629_repaired_proposal_repeat/metrics_summary.md`
- `results/20260629_repaired_proposal_repeat/subgroup_metrics.csv`
- `results/20260629_repaired_proposal_repeat/component_hd_by_case.csv`
- `results/20260629_repaired_proposal_repeat/proposal_metrics.csv`
- `results/20260629_repaired_proposal_repeat/decode_checkpoint_metrics.csv`
- `results/20260629_repaired_proposal_repeat/hardneg_replay_usage.csv`
- `results/20260629_repaired_proposal_repeat/aggregation_status.md`
- `results/20260629_repaired_proposal_repeat/MANIFEST.md`

No validation package or external upload was produced.
