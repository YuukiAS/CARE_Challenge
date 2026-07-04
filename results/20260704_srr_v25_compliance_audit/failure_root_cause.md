# Failure Root Cause

## Root Cause Decision

root_cause_decision: MIXED

Primary causes:

1. `ARCHITECTURE_MISMATCH`
2. `MISSING_NNUNET_ANCHOR`
3. proposal/ROI false-positive flooding
4. no-T2 edema inference leakage

Secondary cause:

5. formal adequacy failed on train-loop seconds

This is not `UNDERTRAINING_ONLY`.

## Why The Current Run Gets Around 0.1 Dice

### 1. The current model is not SRR-v2.5

The diagram expects a strong four-scale encoder, true retrieval dictionaries, anatomy geometry outputs, distance/uncertainty gates, and crop-based refiners. The formal route uses:

- three scales only: `srr_propref.py:148-156`;
- `base_channels=10`: `run_srr_propref_myops_fold0.py:984-987`, `run_srr_propref_formal_myops_fold0.sh:63-65`;
- routed ConvBlock experts rather than dictionary retrieval: `srr_v2_unet.py:58-120`;
- randomly initialized trainable prototypes: `srr_propref.py:34-47`;
- full-volume residual refinement: `srr_propref.py:82-120`.

This architecture can easily produce non-empty predictions without learning a robust segmentation representation.

### 2. It has no nnU-Net anchor

The nnU-Net fold0 reference already has scar Dice `0.5602` and edema Dice `0.3944`. The formal PropRef runner constructs a fresh `SRRProposeRefineMyoPS` and trains it from scratch. It does not load nnU-Net predictions, probabilities, logits, components, or teacher features.

This matters because the formal model is much weaker than nnU-Net and is asked to solve anatomy, scar, edema, retrieval, proposal, and refinement jointly from scratch. The OOF component scorer is a useful contrast: `scripts/evaluation/run_nnunet_oof_component_20260703.py` explicitly consumes nnU-Net predictions/probabilities/components, while PropRef does not.

### 3. Proposals flood remote false positives

At proposal threshold `0.5`, existing diagnostics show:

- shared dual scar precision about `0.098`, outside-myocardium FP ratio about `0.735`, remote FP count about `69.4`;
- shared dual edema precision about `0.020`, outside-myocardium FP ratio about `0.833`, remote FP count about `86.0`;
- scar-precision variant has scar remote FP count about `172.0`.

This is a proposal quality failure, not just a final decoder threshold issue. The proposal mechanism is broad and noisy, so the residual refiner receives poor ROI support.

### 4. No-T2 edema inference is unsafe

Training masks edema supervision when T2 is absent (`srr_losses.py:36-49`), but inference decode does not mask edema by availability (`run_srr_propref_myops_fold0.py:259-275`). Prediction sanity shows no-T2 edema voxels:

- shared dual checkpoint_best total no-T2 edema voxels: `546970` across both decode modes;
- scar-precision checkpoint_best total no-T2 edema voxels: `344783`;
- no-proto checkpoint_best total no-T2 edema voxels: `1374888`.

This can directly depress edema Dice and violates the CARE no-T2 edema contract.

### 5. Formal training adequacy still failed, but is not the main repair

The formal audit correctly records `experiment_adequacy_decision: FAIL` because train-loop seconds were `138-152`, below the task's `1800` second requirement, even though each variant reached `1800` optimizer steps.

That gate failure blocks a scientific route-negative stop. It does not explain away the architecture gaps above, and it does not justify another step/time-only run of the same code as the primary fix.

## Fairness Of The Test

The run is not a fair test of the SRR-v2/v2.5 diagram. It is evidence that the current simplified PropRef implementation is weak and non-compliant, not evidence that a real SRR-v2.5 or nnU-Net-anchored proposal/refinement route cannot work.
