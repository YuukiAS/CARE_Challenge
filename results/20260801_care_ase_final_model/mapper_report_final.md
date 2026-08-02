# CARE-ASE Mapper Final

review_token: W5_AGGREGATION_PASS_PENDING_FINAL_VALIDATOR

CARE-ASE is now represented in the root wiki as the current main-only model state for this task. This mapper report records architecture and evidence mapping only; it is not a reviewer gate, route promotion, validation upload, Docker upload, or hosted metric claim.

## Evidence Read

```text
src/care_myocardium/models/care_ase.py
src/care_myocardium/training/care_ase_trainer.py
src/care_myocardium/data/care_ase_splits.py
scripts/evaluation/care_ase/evaluate_care_ase_outer.py
scripts/evaluation/care_ase/aggregate_care_ase_final.py
results/20260801_care_ase_final_model/checkpoint_freeze_receipt.json
results/20260801_care_ase_final_model/full_reload_parity_receipt.json
results/20260801_care_ase_final_model/outer_access_audit_receipt.json
results/20260801_care_ase_final_model/w45_implementation_snapshot/w45_implementation_snapshot_push_receipt.json
results/20260801_care_ase_final_model/w5_aggregation_receipt.json
results/20260801_care_ase_final_model/module_intervention_outer.csv
wiki/toolkit_healthcheck.json
```

## Mapping Result

CARE-ASE stock inheritance, training contract, sliding-window outer evaluator, and module-off final-output intervention are marked `implemented/verified` in `wiki/COMPONENTS.csv`. The architecture source `wiki/architecture.yaml` now links stock inheritance to fixed 14000-step training, W4 freeze, W5 outer evaluation, and same-contract module intervention. `wiki/README.md` and `wiki/MODEL.md` now expose the W4/W4.5/W5 evidence paths and the boundary that no hosted claim is authorized.

Observed W5 pooled outer Dice: scar `0.523500573079597`, pure-edema `0.7953093461967583`. Full same-split stock Dice/HD was not recomputed by this mapper pass; the W5 receipt explicitly keeps that boundary.
