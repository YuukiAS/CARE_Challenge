# Batch6 Executor Packet Manifest

task_key: `20260721_srr_batch6_final_objective_alignment`
executor_role: `batch6_executor_only`
status: `STOPPED_BEFORE_FORMAL_TRAINING_FIXED_OVERFIT_GATE_FAILED`

## Packet Files

- `batch5_reconciliation.md`
- `resolved_loss_weights.csv`
- `loss_gradient_authority.csv`
- `pure_intervention_metrics.csv`
- `proposal_roi_metrics.csv`
- `implementation_snapshot.md`
- `fixed_batch_overfit.json`
- `fixed_batch_overfit_trace.csv`
- `training_adequacy.json`
- `slurm_attempts.csv`
- `finalizer_state.json`
- `completion_check.md`
- `commands_run.md`

## Validators

- `./envs/env_CARE/bin/python scripts/evaluation/validate_srr_batch6_packet.py --result-root results/20260721_srr_batch6_final_objective_alignment`
- `./envs/env_CARE/bin/python -m pytest tests/srr_production/test_myops_batch6_objective_alignment.py tests/srr_production/test_myops_batch5_diagnostics.py tests/srr_production/test_myops_batch4_contract.py`

## Runtime Logs

- `logs/srr_batch6/B6FixedOverfit_59737558_20260721_031618.log`
- `logs/srr_batch6/B6FixedOverfit_59737686_20260721_031900.log`
- `logs/srr_batch6/B6FixedOverfit_59737738_20260721_032059.log`
- `logs/srr_batch6/B6FixedOverfit_59737830_20260721_032323.log`

## Stop Boundary

The fixed-overfit gate did not pass. Formal 300-step fold0 calibration and conditional 900-step extension were not submitted.
