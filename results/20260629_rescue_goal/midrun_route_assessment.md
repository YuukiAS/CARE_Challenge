# 20260629 Rescue Goal Mid-run Route Assessment

Status: interim assessment only; not a final route selection.

## Current Queue State

- Repaired proposal formal array: `57094448_[0-2]`, pending on `htzhulab` with reason `(Priority)`.
- SRR-v2 formal job: `57094446_[0]`, pending on `htzhulab` with reason `(Priority)`.
- No repaired proposal or SRR-v2 formal `summary.json`, predictions, task-level metrics, or selections exist yet.
- Current route status: `11` rows total, `2` ready rows, `9` pending/missing formal MyoPS outputs.

## Route Evidence So Far

### Repaired Proposal

CPU preflight passed for all three required variants. This validates the repaired loss/proposal/hard-negative/checkpoint paths but does not provide formal validation metrics.

| variant | CPU loss | val patch loss | hardneg components | checkpoint |
| --- | ---: | ---: | ---: | --- |
| `repaired_uncertainty_hardneg` | `4.7372` | `3.3294` | `1561` | written |
| `repaired_posneg_scar_hardneg` | `5.1300` | `3.5163` | `4167` | written |
| `repaired_joint_calibrated_proposal` | `4.7866` | `3.3479` | `5728` | written |

Formal question still unanswered: whether repaired proposal improves scar/edema Dice, HD95, remote FP, component burden, or no-T2 stability over the previous proposal and D4 dictionary references.

### SRR-v2

Model-level tiny smoke and runner-level CPU preflights passed. This validates missing-modality gate masking, multi-scale route wiring, loss wiring, proposal wiring, hard-negative loading, and task-scoped checkpoint paths.

| variant | CPU loss | val patch loss | hardneg components | checkpoint |
| --- | ---: | ---: | ---: | --- |
| `srr_v2_multiscale_private_basic` | `3.9514` | `2.4594` | `0` | written |
| `srr_v2_multiscale_private_proposal` | `4.2588` | `2.4000` | `0` | written |
| `srr_v2_proposal_uncertainty_hardneg` | `4.3738` | `2.5234` | `5728` | written |

Formal question still unanswered: whether SRR-v2 capacity improves over shallow SRRMyoPSLite and approaches nnU-Net reference.

### Cascade Teacher

Teacher artifact blocker is cleared by OOF-5 nnU-Net cache.

- Fold0 train teacher coverage: `176/176`.
- Fold0 validation teacher coverage: `44/44`.
- Teacher baseline: train edema Dice `0.4399`, train scar Dice `0.5786`, validation edema Dice `0.3944`, validation scar Dice `0.5732`.
- ROI warning: `26` GT-positive class rows have teacher-derived ROI coverage `<0.95`, mostly scar, so hard teacher-mask-only crops are unsafe.
- CPU refiner preflight passed with finite 2-step loss `0.4042`, scar changed voxels `0`, no-T2 new edema voxels `0`.

Formal question still unanswered: whether an OOF teacher/refiner can improve over teacher/nnU-Net reference, not merely copy it.

### Cine Secondary Route

- Motion alignment: `SELECT_MOTION_DESCRIPTOR_ONLY`.
- Motion pathology: `SELECT_REFERENCE_CONTROL_ONLY`.
- Current Cine evidence does not select a motion pathology route; keep reference control as local secondary-line baseline.

## Next GPU Priority When Capacity Frees

1. Let `57094448_[0-2]` and `57094446_[0]` start or complete before adding more load.
2. If any repaired proposal array tasks finish, run `scripts/evaluation/finalize_rescue_srr_route.py --route repaired`.
3. If SRR-v2 basic finishes, run `scripts/evaluation/finalize_rescue_srr_route.py --route srr_v2 --force-partial` only for interim readout, and submit remaining SRR-v2 variants when pending count drops.
4. Submit `jobs/src/run_cascade_oof_refiner.sh` after current pending GPU count drops, because cascade teacher cache and CPU preflight are ready.

## Not Yet Complete

The rescue goal cannot be marked complete because no MyoPS formal route has produced full validation predictions, metrics, failure interpretation, or route selection. The current evidence supports readiness to run formal jobs; it does not yet answer which route is best.
