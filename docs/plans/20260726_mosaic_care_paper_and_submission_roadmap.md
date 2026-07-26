# 20260726 MoSAIC + CARE paper and submission roadmap

## Objective

Do not submit pure nnU-Net or pure MoSAIC as the final CARE contribution. Use MoSAIC as a strong pathology candidate source, nnU-Net as an anatomical/safety anchor, and develop CARE selective component fusion.

## Validation plan

### Validation 1: CARE-SafeScar-v1

Goal: test whether MoSAIC scar expertise can be retained while suppressing failure cases.

- MoSAIC scar proposal generation.
- nnU-Net anatomy and uncertainty support.
- Component-level positive/negative evidence arbitration.
- No aggressive edema replacement.
- Exact fallback per pathology.

### Validation 2: CARE-SCF-v2

Goal: enable full selective correction.

- Add retain/suppress/replace decisions.
- Use cross-fitted MoSAIC and nnU-Net evidence.
- Preserve MMRD reliable edema supervision semantics.
- Keep scar and edema independent.

### Validation 3: CARE-SCF-final

Goal: freeze the Docker candidate.

- Same code path as validation.
- Same weights and thresholds.
- No post-hoc leaderboard tuning.

## Training priorities

1. Complete MoSAIC fold1-4 OOF predictions for component evidence.
2. Build scar/edema component evidence tables.
3. Train lightweight CARE arbitration modules.
4. Keep interactive Slurm job only; do not submit additional waiting jobs.

## Paper strategy

Complete one joint MoSAIC paper. Do not start a separate CARE paper before CARE-SCF has independent positive evidence.

Paper narrative:

- MoSAIC: pathology expert for complete multi-sequence CMR.
- CARE contribution: reliability-aware selective arbitration between experts and robust anchors.
- Avoid claiming universal superiority over nnU-Net.

## Evidence rules

- Separate clean CV, hosted validation, and contaminated full-data diagnostics.
- Do not mix pure edema and edema-zone metrics.
- Every numerical claim requires provenance.
