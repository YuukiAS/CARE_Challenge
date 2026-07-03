# Failure Interpretation

candidate_decision: `DIAGNOSTIC_ONLY`
scientific_resolution_status: `SCIENTIFIC_UNRESOLVED`

## Interpretation

- The OOF protocol produced only diagnostic evidence under the current gate.
- This does not support route promotion or route-negative stop.

## Key Fold0 Delta Lines

| class | group | delta Dice | HD improvement | HD95 improvement | remote FP improvement | small FP improvement |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| myops_scar | all_cases | -0.000053 | -0.115463 | -0.391181 | 0.090909 | 0.886364 |
| myops_scar | gt_positive_only | -0.000055 | -0.115463 | -0.391181 | 0.069767 | 0.883721 |
| myops_edema | gt_positive_only | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| myops_edema | no_T2_empty_GT | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

## Blocked Actions

- validation packaging/upload remains blocked.
- fold expansion or next-stage training remains blocked.
- hosted metric claims remain blocked.
- label/evaluator/fold split changes were not performed.
