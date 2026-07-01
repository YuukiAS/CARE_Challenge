# Repaired Proposal Failure Interpretation

The repaired proposal repeat was designed to answer whether the previous low Result5 proposal scores were mainly caused by fixable training and decoding bugs. The answer is mostly no: the fixes made the route executable and auditable, but they did not turn the shallow SRRMyoPSLite proposal head into a competitive pathology model.

## Evidence

All three variants completed the formal budget:

| variant | job | stop reason | elapsed seconds | best step | predictions |
| --- | --- | --- | ---: | ---: | ---: |
| `repaired_uncertainty_hardneg` | `57094448_0` | `max_runtime_seconds` | 23400.0 | 105000 | 44 |
| `repaired_posneg_scar_hardneg` | `57094448_1` | `max_runtime_seconds` | 23400.0 | 105000 | 44 |
| `repaired_joint_calibrated_proposal` | `57094448_2` | `max_runtime_seconds` | 23400.0 | 105000 | 44 |

Key route-level metrics:

| variant | metric | group | Dice | HD95 | components mean | remote FP mean |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `repaired_uncertainty_hardneg` | edema | GT-positive | 0.1545 | 128.6386 | 102.1250 | 77.6875 |
| `repaired_uncertainty_hardneg` | scar | all cases | 0.0761 | 130.6030 | 101.3182 | 75.4091 |
| `repaired_posneg_scar_hardneg` | edema | GT-positive | 0.0909 | 114.3274 | 57.0000 | 37.5625 |
| `repaired_posneg_scar_hardneg` | scar | all cases | 0.1038 | 136.0183 | 78.9545 | 56.6136 |
| `repaired_joint_calibrated_proposal` | edema | GT-positive | 0.1460 | 121.1045 | 93.0625 | 72.4375 |
| `repaired_joint_calibrated_proposal` | scar | all cases | 0.0922 | 140.9393 | 89.0227 | 68.7500 |

## Mechanism

The repairs addressed real pipeline problems, but the remaining bottleneck is the model role. The current SRRMyoPSLite route still uses shallow stems, early masked fusion, a single-scale retrieval core, and a proposal head that shapes final logits rather than a true soft cascade refiner. That leaves it weak at lesion formation: remote false positives, high component counts, and poor scar recall remain.

This is consistent with the Result5 audit: SRR can still be useful as an evidence or proposal module, but this lightweight full-volume proposal implementation is not strong enough to replace nnU-Net or serve as the final route.

## Decision Implication

The repaired route should not be expanded. The rescue goal should continue through SRR-v2 and cascade teacher evidence. If the cascade route also fails to improve over nnU-Net, the final status should explain whether the remaining blocker is teacher/refiner design, training budget, or the SRR direction itself.
