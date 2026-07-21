# Batch6 Mapper Final

## Evidence Used

- `src/care_myocardium/models/srr_propref.py`
- `src/care_myocardium/losses/srr_losses.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `scripts/srr_production/infer_myops.py`
- `configs/srr_production/myops_batch6.yaml`
- `results/20260721_srr_batch6_final_objective_alignment/fixed_batch_overfit.json`
- `results/20260721_srr_batch6_final_objective_alignment/training_adequacy.json`
- `results/20260721_srr_batch6_final_objective_alignment/final_mechanism_interventions.csv`

## Final Mapping

Batch6 keeps the existing `SRRProposeRefineMyoPS` MyoPS backbone and changes the final objective authority. The verified runtime path is now: nnU-Net anchor logits plus bounded scar/edema corrections from proposal/refiner/gate, with direct final-logits scar and T2-present edema losses and a production gate repair/preserve loss.

The fixed-overfit packet verifies this path can receive directional correction gradients and change final logits. Formal300 verifies the path ran for exactly 300 optimizer steps and 44-case full-volume evaluations at 100/200/300. The scientific signal remains below usable because the step300 mean positive-pathology Dice delta is `+0.001699358`, below the `+0.003` continuation gate.

No Cine architecture, fold expansion, upload path, backbone replacement, or Batch7 path was mapped as active.
