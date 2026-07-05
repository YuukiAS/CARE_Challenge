# SRR-v3 Metric Contract

status: `M0_READY_FOR_REVIEW`

## Primary CARE Metrics

The primary challenge-facing MyoPS metrics remain:

- `myops_scar`
- `myops_edema`

Do not treat myocardium, LV blood, foreground mean, or other aggregate values as primary optimization targets. They may be reported only as sanity/context metrics.

## Required Same-Split Comparison

Every MyoPS milestone that reports model quality must compare against same-split nnU-Net on the same cases, checkpoint/evaluator contract, and label mapping.

Required columns for help/harm tables:

- `case_id`
- `center`
- `modality_group`
- `t2_present`
- `class`
- `metric`
- `srr_value`
- `nnunet_value`
- `delta_srr_minus_nnunet`
- `decision`
- `fold`
- `variant`
- `checkpoint_or_run_id`

## Minimum Metrics By Class

For `myops_scar` and `myops_edema`, report:

- Dice
- HD95 or surface-distance equivalent
- component count
- remote false-positive count
- proposal recall/precision where proposal paths are claimed
- gate open-rate and residual magnitude where residual correction is claimed

## Meaningful Improvement Threshold

Mean Dice delta with absolute value below `0.005` is `near_identity_not_meaningful` unless a hard-subgroup table shows a clearly material gain without unacceptable harm. Positive no-anchor or non-baseline-preserving rows cannot be used as route evidence unless the baseline preservation contract is also satisfied.

## Training Adequacy Labels

| evidence stage | allowed conclusion |
| --- | --- |
| source code only | `code_path_exists` |
| one-case or shape smoke | `runtime_smoke_only` |
| eval-only over old checkpoints | `diagnostic_eval_only` |
| bounded 6-step probe | `undertrained_diagnostic` |
| M3 minimum-effective pilot | `pilot_training_evidence` if all M3 fields pass |
| full-fold and hosted validation | only future authorized task may define |

## No-T2 Edema Reporting

Edema metrics must distinguish:

- all cases;
- T2-present cases;
- T2-present edema-positive cases;
- no-T2 cases, where edema should be safely blocked and not treated as a hard negative training source.
