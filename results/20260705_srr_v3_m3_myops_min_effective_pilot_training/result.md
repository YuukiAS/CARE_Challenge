# SRR-v3 M3 MyoPS Minimum-Effective Pilot Training Result

status: `EXECUTED_UNAUDITED`
completion_state: `M3_READY_FOR_REVIEW`
adequacy_decision: `PASS`

## Summary

Executed one controlled fold0 SRR-v3 pilot variant and aggregated the required M3 evidence. This is not full fold training, not challenge readiness, not route promotion, and not validation packaging/upload.

- optimizer_steps: `6000`
- train_loop_seconds: `2126.2185006489744`
- eval_cases: `12`
- validation_events: `20`
- loss_decrease: `3.788084328174591`
- checkpoint_best: `/users/a/e/aereinh/CARE/results/20260705_srr_v3_m3_myops_min_effective_pilot_training/variants/srr_v3_m3_shared_dual_dict_pilot/checkpoints/fold_0/propref_config/checkpoint_best.pt`

## Evidence

- `training_curves.csv` and `validation_events.csv` summarize the pilot training loop.
- `prediction_sanity.csv` records compact-label and no-T2 edema checks.
- `gate_residual_stats.csv` records gate/residual means and decode deltas versus nnU-Net.
- `prototype_bank_summary.json` records T2-present edema prototype coverage.
- `same_split_help_harm.csv` and `hard_subgroup_metrics.csv` compare against same-split nnU-Net anchors.

## Issues

none
