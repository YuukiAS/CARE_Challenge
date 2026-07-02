# Result 20260629 Rescue Goal

Status: final.

Final status: `STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL`

Cine status: `CINE_REFERENCE_ONLY`

## Summary

The full rescue goal was executed: repaired proposal repeat, required SRR-v2,
cascade teacher, Cine motion alignment, Cine motion pathology, and multiple
follow-up SRR-v2/cascade improvement probes after weak intermediate results.
All submitted GPU actions are complete, the GPU action ledger has
`open_actions=0`, and the completion audit proves all required route evidence is
present.

No MyoPS route reached the conservative 80% nnU-Net selection gates:

- nnU-Net scar all-case reference: `0.5602`; 80% gate `0.4481`.
- nnU-Net edema GT-positive reference: `0.3944`; 80% gate `0.3155`.
- Best first-party scar signal: `srr_v2_capacity12_hardneg`, scar all-case
  Dice `0.3090`.
- Best final edema GT-positive signal: `srr_v2_capacity12_scar_precision_interact`,
  edema GT-positive Dice `0.2063`.

The best available interpretation is that the current SRR direction can learn
some weak pathology signal, but the limiting failure is not solved by proposal
repair, extra U-Net capacity, targeted class weighting, interaction toggles, or
the nnU-Net teacher refiner variants tested in this sprint. None should be
expanded to folds 1-4 or validation packaging under this goal.

## Final Artifacts

- Final status: `results/20260629_rescue_goal/final_status.md`
- Completion audit: `results/20260629_rescue_goal/completion_audit.md`
- Progress log: `results/20260629_rescue_goal/progress.md`
- Manifest: `results/20260629_rescue_goal/MANIFEST.md`
- GPU action ledger: `results/20260629_rescue_goal/gpu_action_status.md`
- Route status matrix: `results/20260629_rescue_goal/pending_status.md`

## Route Decisions

| Route | Selection | Best target evidence |
| --- | --- | --- |
| Repaired proposal | `ROUTE_TO_CASCADE_TEACHER` | scar all-case `0.1038`; edema GT-positive `0.1545` |
| Required SRR-v2 | `STOP_NO_SRR_V2_SIGNAL` | scar all-case `0.2474`; edema GT-positive `0.1855` |
| SRR-v2 light-refine extras | `STOP_NO_SRR_V2_SIGNAL` | scar all-case `0.2431`; edema GT-positive `0.1879` |
| SRR-v2 capacity extras | `STOP_NO_SRR_V2_SIGNAL` | scar all-case `0.3090`; edema GT-positive `0.1894` |
| SRR-v2 targeted extras | `STOP_NO_SRR_V2_SIGNAL` | scar all-case `0.2377`; edema GT-positive `0.1873` |
| SRR-v2 capacity-targeted extras | `STOP_NO_SRR_V2_SIGNAL` | scar all-case `0.2643`; edema GT-positive `0.1939` |
| SRR-v2 balanced-targeted extras | `STOP_NO_SRR_V2_SIGNAL` | scar all-case `0.2678`; edema GT-positive `0.2063` |
| Cascade teacher | `STOP_NO_CASCADE_SIGNAL` | all formal variants failed route-selection criteria |
| Cine motion alignment | `SELECT_MOTION_DESCRIPTOR_ONLY` | motion descriptor only; not a pathology success |
| Cine motion pathology | `SELECT_REFERENCE_CONTROL_ONLY` | motion variants did not beat reference control |

## Commands And Verification

- Refreshed route status with `./envs/env_CARE/bin/python scripts/evaluation/report_rescue_goal_status.py`.
- Refreshed GPU ledger with `./envs/env_CARE/bin/python scripts/evaluation/report_rescue_gpu_action_status.py`.
- Ran completion audit with `./envs/env_CARE/bin/python scripts/evaluation/finalize_rescue_goal.py`.
- Wrote final status with `./envs/env_CARE/bin/python scripts/evaluation/finalize_rescue_goal.py --write-final`, then expanded it with required route/job/log details.

Latest audit:

- `completion_proven=True`
- `blocking_requirements=0`
- GPU ledger `open_actions=0`

## Explicit Non-Actions

- No validation upload.
- No upload-ready package.
- No fold expansion.
- No fold split, label mapping, or evaluator change.
- No no-T2 myocardium-as-edema-negative change.

## Recommendation

Do not promote repaired proposal, SRR-v2, or cascade teacher to fold expansion
from this sprint. If a future task continues MyoPS work, it should be a new
hypothesis rather than another small SRR tuning pass. The strongest diagnostic
starting point is the capacity-extra scar signal, but the practical challenge
baseline remains nnU-Net unless a future route can close the large nnU-Net gate
gap.
