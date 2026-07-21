# Batch6 Implementation Snapshot

executor_role: batch6_executor_only
status: IMPLEMENTED_THEN_STOPPED_AT_FIXED_OVERFIT_GATE

## Code Changes

- `src/care_myocardium/models/srr_propref.py`: expanded `production_correction_gate` from 4 to 13 input channels and exposed fixed channel names/order in outputs.
- `src/care_myocardium/models/srr_propref.py`: added pure Batch6 intervention modes `proposal_only_gate_one` and `refiner_only_gate_one`; proposal-only gate inputs zero refiner channels, refiner-only gate inputs zero proposal channels.
- `src/care_myocardium/losses/srr_losses.py`: added direct deployed-logit scar/edema one-vs-rest final pathology losses.
- `src/care_myocardium/losses/srr_losses.py`: added production gate repair/preserve balanced BCE with no-T2 edema masking.
- `src/care_myocardium/srr_production/checkpoint.py`: added strict 4-to-13 production gate checkpoint migration: copy old channels 0:4, zero initialize channels 4:13, keep non-gate load strict.
- `scripts/training/run_srr_propref_myops_fold0.py`: added Batch6 canonical loss keys to logging/gradient tables and stores resolved loss contract in checkpoints.
- `scripts/evaluation/audit_srr_batch5_loss_authority.py`: records Batch6 resolved weights and loss gradient authority under the Batch6 result root.
- `scripts/evaluation/reconcile_srr_batch6_batch5_evidence.py`: creates Batch6 pure intervention and proposal/ROI reconciliation tables from Batch5/B4 evidence.
- `scripts/training/run_srr_batch6_fixed_overfit.py`: fixed Case2002+Case1002 60-step overfit gate from the Batch4 selected checkpoint.
- `jobs/srr_production/run_myops_batch6_fixed_overfit_htzhulab.sh` and `jobs/srr_production/run_myops_batch6_fixed_overfit_a100.sh`: Slurm entrypoints with isolated logs and stage winner lock.
- `tests/srr_production/test_myops_batch6_objective_alignment.py`: focused tests for Batch6 final objective, gate channel contract, no-T2 masking, pure interventions, canonical weights, and checkpoint migration.

## Contract Notes

- Formal 300-step calibration was not submitted.
- Conditional 900-step extension was not submitted.
- No validation upload, hosted claim, fold expansion, Cine work, backbone swap, prototype rebuild, push, or Batch7 start was performed.
