# CARE-DG Gate B-R2 Candidate Selection Report

created_at_utc: `2026-07-28T03:38:11Z`
base_git_head: `557f09c0a6bbb0a6f228f9b06b6180604369e1cf`

## Plain Judgment

Gate B-R2 is ready for GPT review, but it is not a successful scientific expansion gate. The train-side-only scale/checkpoint search found no eligible CARE-DG candidate: the best safe recipe changes the masks in the right direction, but its largest target gain is scar Dice `+0.004258`, below the pre-registered `+0.005` threshold. Folds 1-4, all-data fitting and validation packaging remain unauthorized.

## Scope Boundary

This file is a fold0 Gate B-R2 pre-expansion decision, not the original W4 five-fold OOF candidate selection. W3 was intentionally not run after the later user/GPT instruction paused folds 1-4 unless repaired fold0 met the stricter Gate B expansion criteria.

## Fixed Train-Side Search

- selection population: `fixed_train_side_complete_inner_select_full_volume_scale_grid`
- outer fold0 used for selection: `False`
- outer fold0 re-evaluated after R2: `False`
- checkpoints: `8`
- scar/edema scale grid: `[0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]`
- evaluated rows: `512`
- eligible candidates: `0`

## Best Candidate

- checkpoint step: `4000`
- checkpoint sha256: `1378795ba262807d045f7c9a7d72fa45adb9730c29c9baa58ad2a07752161312`
- scar scale: `1.0`
- edema scale: `0.25`
- status: `FAIL`
- failures: `no_pathology_improves_by_more_than_0.005`
- help/harm: `25` / `7`

| pathology | anchor Dice | candidate Dice | delta | HD95 ok | remote FP ok | component ok |
|---|---:|---:|---:|---:|---:|---:|
| scar | 0.696721 | 0.700979 | 0.004258 | True | True | True |
| edema-zone | 0.735973 | 0.736603 | 0.000630 | True | True | True |
| pure-edema | 0.536848 | 0.537455 | 0.000607 | True | True | True |

## Validator Status

- Gate B-R2 validator: `PASS` (`NO_INNER_ELIGIBLE_CANDIDATE`)
- strict validator: `PASS`
- Gate B consistency validator: `PASS`

## Boundary

Do not start folds 1-4, all-data fit, validation inference/package, validation upload, Docker upload, new Slurm jobs, runtime push, outer-fold0 tuned selection or external-model substitution without explicit new GPT/user approval.
