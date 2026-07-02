# 20260629 Rescue Goal Route Evidence Matrix

Status: interim evidence matrix only; this is not `final_status.md`. Updated to
reflect completed formal MyoPS routes plus targeted extra jobs still pending on
down GPU partitions.

## MyoPS Route Readout

| route | status | formal ready | scar all Dice | scar all HD95 | edema GT+ Dice | edema GT+ HD95 | interpretation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| repaired_proposal | ROUTE_TO_CASCADE_TEACHER | 3/3 | 0.1038 | 136.0183 | 0.1545 | 128.6386 | completed negative evidence for shallow repaired proposal |
| srr_v2_required | STOP_NO_SRR_V2_SIGNAL | 3/3 | 0.2474 | 83.1291 | 0.1855 | 106.3624 | completed negative evidence for required SRR-v2 route; hardneg improved scar but stayed below nnU-Net gate |
| cascade_teacher | STOP_NO_CASCADE_SIGNAL | 3/3 |  |  |  |  | completed negative evidence; formal variants had tiny deltas and failed route selection |
| cascade_component_guard | STOP_NO_COMPONENT_GUARD_SIGNAL | 2/2 |  |  |  |  | revision failed to create selectable component/remote-FP improvement |
| cascade_signal_seek | STOP_NO_SIGNAL_SEEK_ROUTE | 2/2 |  |  |  |  | wider residual signal-seeking still failed selection |
| cascade_postprocess_sweep | STOP_NO_POSTPROCESS_ROUTE | postprocess |  |  |  |  | pruning sweep reduced some burden but did not fix remote FP/Dice tradeoff |
| srr_v2_light_refine_extras | STOP_NO_SRR_V2_SIGNAL | 2/2 | 0.2431 | 76.7039 | 0.1879 | 84.7449 | completed extra probe; still below nnU-Net gate |
| srr_v2_capacity_extras | STOP_NO_SRR_V2_SIGNAL | 2/2 | 0.3090 | 70.3468 | 0.1894 | 108.8751 | best first-party scar signal so far, still below nnU-Net gate |
| srr_v2_targeted_extras | QUEUED_OR_RUNNING | 0/2 |  |  |  |  | full GPU runs pending on down partitions; CPU preflight only proves executability |
| nnUNet_fold0_reference | reference_only | 44 cases | 0.5602 |  |  |  | hard reference, not a custom route selection |

## Cine Secondary Readout

| route | status | interpretation | next action |
| --- | --- | --- | --- |
| cine_motion_alignment | SELECT_MOTION_DESCRIPTOR_ONLY | motion descriptor only, no alignment route selected | keep as secondary-line evidence |
| cine_motion_pathology | SELECT_REFERENCE_CONTROL_ONLY | reference control only | do not block MyoPS |

## Current Synthesis

- Repaired proposal is complete but negative: it did not beat D4/proposal references enough and remains far below nnU-Net.
- Required SRR-v2 is complete but negative: hard-negative SRR-v2 improved scar relative to the basic route, but best scar all-case Dice `0.2474` remained below the 80% nnU-Net gate `0.4481`.
- Cascade teacher and its component-guard/signal-seek/postprocess follow-ups are complete but negative: teacher/refiner edits were too small or traded component burden against remote FP without closing the nnU-Net gap.
- SRR-v2 capacity extras produced the best first-party scar signal so far (`0.3090`), but this is still below the nnU-Net gate and does not justify route selection or fold expansion.
- Targeted extras are the only remaining live improvement attempt. Their CPU preflight passed, but full GPU training/export/evaluation is still pending because all allowed GPU partitions are down.
- Cine evidence currently supports `CINE_REFERENCE_ONLY`; it should not block MyoPS route completion.
