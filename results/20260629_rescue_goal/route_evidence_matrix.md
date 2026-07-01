# 20260629 Rescue Goal Route Evidence Matrix

Status: interim evidence matrix only; this is not `final_status.md`.

## MyoPS Route Readout

| route | status | formal ready | scar all Dice | scar all HD95 | edema GT+ Dice | edema GT+ HD95 | interpretation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| repaired_proposal | ROUTE_TO_CASCADE_TEACHER | 3/3 | 0.1038 | 136.0183 | 0.1545 | 128.6386 | completed negative evidence for shallow repaired proposal |
| srr_v2 | missing | 1/3 | 0.1998 | 82.7490 | 0.1431 | 94.9052 | partial positive scar signal, incomplete route |
| cascade_teacher | PENDING_FORMAL_CASCADE | 0/3 |  |  |  |  | best next MyoPS route to run once GPU approval/capacity exists |
| nnUNet_fold0_reference | reference_only | 44 cases | 0.5602 |  |  |  | hard reference, not a custom route selection |

## Cine Secondary Readout

| route | status | interpretation | next action |
| --- | --- | --- | --- |
| cine_motion_alignment | SELECT_MOTION_DESCRIPTOR_ONLY | motion descriptor only, no alignment route selected | keep as secondary-line evidence |
| cine_motion_pathology | SELECT_REFERENCE_CONTROL_ONLY | reference control only | do not block MyoPS |

## Current Synthesis

- Repaired proposal is complete but negative: it did not beat D4/proposal references enough and remains far below nnU-Net.
- SRR-v2 has the best current first-party scar signal (`0.1998` all-case Dice, HD95 `82.7490`) but is incomplete because two formal variants are still pending/missing.
- Cascade teacher is the most justified next MyoPS execution route once approval/capacity is available, because the shallow proposal route failed and SRR-v2 remains far below nnU-Net while incomplete.
- Cine evidence currently supports `CINE_REFERENCE_ONLY`; it should not block MyoPS route completion.
