# Batch6 Controller Packet Manifest

task_key: `20260721_srr_batch6_final_objective_alignment`
executor_role: `batch6_executor_only`
controller_verification_decision: `VERIFIED_COMPLETE`
status: `FORMAL_300_COMPLETE_GATE_FAIL_STOP_AT_300`
scientific_signal_class: `BELOW_USABLE`

## Required Packet Files

- `controller_context.json`
- `controller_ledger.csv`
- `controller_bootstrap_snapshot.md`
- `batch5_reconciliation.md`
- `resolved_loss_weights.csv`
- `pure_intervention_metrics.csv`
- `proposal_roi_metrics.csv`
- `implementation_snapshot.md`
- `fixed_batch_overfit.json`
- `fixed_batch_overfit_trace.csv`
- `loss_gradient_authority.csv`
- `training_adequacy.json`
- `checkpoint_selection.csv`
- `subgroup_metrics.csv`
- `help_harm.csv`
- `casewise_metrics.csv`
- `final_mechanism_interventions.csv`
- `slurm_attempts.csv`
- `finalizer_state.json`
- `mapper_report_draft.md`
- `architecture_delta_draft.md`
- `mapper_report_final.md`
- `architecture_delta_final.md`
- `controller_report.md`
- `completion_check.md`
- `commands_run.md`

## Runtime Evidence

- fixed-overfit passing job: `59743323`, log `logs/srr_batch6/B6FixedOverfit_59743323_20260721_054154.log`
- formal 300 passing job: `59744053`, log `logs/srr_batch6/B6Formal300_59744053_20260721_060207.log`
- final interventions passing job: `59744941`, log `logs/srr_batch6/B6FinalInterventions_59744941_20260721_062621.log`
- selected checkpoint: `results/20260721_srr_batch6_final_objective_alignment/runtime/attempts/batch6_formal300_htzhulab_59744053/variants/batch6_formal300_htzhulab_59744053/checkpoints/fold_0/propref_config/checkpoint_validation_step_300.pt`
- selected checkpoint sha256: `729c81e49bf846339ed2f39ef0f2656319befd2b9cfe73268d7cf501e6b40fbd`

## Validators

- `./envs/env_CARE/bin/python scripts/srr_production/audit_formal_entrypoints.py --strict`
- `./envs/env_CARE/bin/python scripts/evaluation/validate_srr_batch6_packet.py --result-root results/20260721_srr_batch6_final_objective_alignment`
- `./envs/env_CARE/bin/python -m pytest -q tests/srr_production/test_myops_batch6_objective_alignment.py tests/srr_production/test_myops_batch5_diagnostics.py tests/srr_production/test_myops_batch4_contract.py`
- `./envs/env_CARE/bin/python scripts/architecture/validate_care_architecture_wiki.py --strict`
- `./envs/env_CARE/bin/python scripts/architecture/generate_care_architecture_wiki.py --check`
- `git diff --check`

## Stop Boundary

The fixed-overfit gate passed and formal 300 ran. The step300 continuation gate failed only the mean Dice delta check (`0.001699358420302757 < 0.003`), so the 900-step extension was skipped by contract.
