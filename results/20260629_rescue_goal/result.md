# Result 20260629 Rescue Goal

Status: active; not final. The required repaired proposal, SRR-v2, cascade
teacher, and Cine subtask routes are complete. Repaired proposal, required
SRR-v2, cascade teacher, cascade follow-ups, SRR-v2 light-refine extras, and
SRR-v2 capacity extras are all not selected. The remaining live work is the
targeted SRR-v2 extra pair, which is queued on `htzhulab`, `a100-gpu`, and
`volta-gpu` but has not started because those partitions are down.

## What Was Done

- Verified the active `/users/a/e/aereinh/CARE` workspace and kept all writes
  under `/users`.
- Refreshed remote refs earlier in the run; local `main` and `origin/main`
  were even at that check.
- Ran the repaired proposal repeat route, SRR-v2 required route, cascade
  teacher route, cascade follow-up revisions/sweep, SRR-v2 light-refine/capacity
  extras, and the two Cine secondary routes.
- Added evidence-gated goal auditing in
  `scripts/evaluation/finalize_rescue_goal.py` so `final_status.md` is not
  written while required MyoPS evidence is missing.
- Added GPU action tracking in
  `scripts/evaluation/report_rescue_gpu_action_status.py`.
- After the long A100 wait, submitted independent remaining work to
  `htzhulab`, following the repo priority rule.

## Current Evidence

Repaired proposal is complete and not selected:

- job: `57094448_[0-2]`
- selection: `results/20260629_repaired_proposal_repeat/selection.md`
- status: `ROUTE_TO_CASCADE_TEACHER`
- best repaired scar all-case Dice: `0.1038`
- best repaired edema GT-positive Dice: `0.1545`

Required SRR-v2 is complete and not selected:

- basic job `57094446_0` failed during export after `06:37:38`, then was
  recovered from checkpoint after the safe-pooling fix.
- old A100 variants job `57095505_[1-2]` was cancelled after the same variants
  were running on the preferred `htzhulab` partition.
- isolated htzhulab fallback `57272337_[1-2]` completed for the two missing
  variants under
  `results/20260629_srr_v2_unet_core_htzhulab_fallback/`.
- selection: `results/20260629_srr_v2_unet_core/selection.md`
- status: `STOP_NO_SRR_V2_SIGNAL`
- best required SRR-v2 scar all-case Dice: `0.2474`, below the 80% nnU-Net
  gate `0.4481`.
- best required SRR-v2 edema GT-positive Dice: `0.1855`, below the 80% nnU-Net
  gate `0.3155`.

Formal cascade teacher route is complete and not selected:

- job: `57272502_[0-2]`
- selection: `results/20260629_cascade_teacher_route/selection.md`
- status: `STOP_NO_CASCADE_SIGNAL`
- all three formal variants completed with `44/44` validation predictions.
- all three were evaluated as `fail_stop_refiner_candidate`.
- largest deltas were tiny: T2+ edema Dice `+0.0019`, scar Dice `+0.0028`.

Because the formal cascade result was poor, a follow-up was submitted instead
of stopping:

- wrapper: `jobs/src/run_cascade_oof_refiner_revision_component_guard.sh`
- job: `57274444_[0-1]`
- partition: `htzhulab`
- status: completed, exit `0:0`
- output root:
  `results/20260629_cascade_teacher_route/revision_component_guard/`
- hypothesis: stricter residual magnitude and higher pathology thresholds may
  reduce component/remote false positives while preserving any small pathology
  gain.
- result: `STOP_NO_COMPONENT_GUARD_SIGNAL`; selected variant `none`.

Because the component-guard revision also failed, another isolated follow-up
was submitted to use the available goal capacity:

- wrapper: `jobs/src/run_cascade_oof_refiner_revision_signal_seek.sh`
- job: `57275246_[0-1]`
- partition: `htzhulab`
- status: completed, exit `0:0`
- output root:
  `results/20260629_cascade_teacher_route/revision_signal_seek/`
- hypothesis: the cascade refiner may be under-editing the teacher; wider
  residual heads, larger residual caps, and lower thresholds test that bounded
  signal-seeking alternative.
- result: `STOP_NO_SIGNAL_SEEK_ROUTE`; selected variant `none`.

The signal-seek outputs were then postprocessed with baseline-support component
pruning:

- script: `scripts/evaluation/postprocess_cascade_revision_sweep.py`
- output root:
  `results/20260629_cascade_teacher_route/revision_postprocess_sweep/`
- result: `STOP_NO_POSTPROCESS_ROUTE`; selected mode `none`.
- interpretation: pruning can reduce component burden in some modes, but remote
  FP regressions remain and Dice movement is still tiny.

After cascade formal, component-guard, signal-seek, and postprocess all failed,
the free GPU capacity was redirected to SRR-v2 extras:

- wrapper: `jobs/src/run_srr_v2_light_refine_extra.sh`
- job: `57277361_[0-1]`
- partition: `htzhulab`
- status: completed
- output root:
  `results/20260629_srr_v2_unet_core/light_refine_extras/`
- variants:
  - `srr_v2_light_refine_lowmix`
  - `srr_v2_light_refine_hardneg`
- selection: `STOP_NO_SRR_V2_SIGNAL`; selected variant `none`.
- best light-refine scar all-case Dice: `0.2431`; best edema GT-positive Dice:
  `0.1879`.

Because two GPU slots remained available under the goal budget, an additional
capacity probe was submitted rather than waiting idly:

- wrapper: `jobs/src/run_srr_v2_capacity_extra.sh`
- job: `57279322_[0-1]`
- partition: `htzhulab`
- status: completed
- output root:
  `results/20260629_srr_v2_unet_core/capacity_extras/`
- variants:
  - `srr_v2_capacity12_proposal`
  - `srr_v2_capacity12_hardneg`
- hypothesis: test whether increasing SRR-v2 U-Net capacity from
  `base_channels=8` to `base_channels=12` improves pathology signal while
  keeping the same fold/evaluator/label contract.
- selection: `STOP_NO_SRR_V2_SIGNAL`; selected variant `none`.
- best capacity-extra scar all-case Dice: `0.3090`; best edema GT-positive
  Dice: `0.1894`. This is the best first-party scar signal so far, but remains
  below the nnU-Net gate.

Because the above results were still weak, a final targeted SRR-v2 extra pair
was prepared and queued on all allowed partitions:

- wrapper: `jobs/src/run_srr_v2_targeted_extra.sh`
- htzhulab job: `57334792_[0-1]`
- a100 fallback job: `57340171_[0-1]`
- volta fallback job: `57340161_[0-1]`
- variants:
  - `srr_v2_edema_t2_focus`
  - `srr_v2_scar_precision_nointeract`
- status at latest refresh: all pending with `(PartitionDown)`, `START_TIME=N/A`.
- CPU-only two-step preflight passed for both variants under
  `results/20260629_srr_v2_unet_core/targeted_extras_cpu_preflight/`, but full
  GPU training/export/evaluation has not started.

Cine secondary-line tasks are complete:

- `results/20260629_cine_motion_alignment/selection.md`:
  `SELECT_MOTION_DESCRIPTOR_ONLY`
- `results/20260629_cine_motion_pathology/selection.md`:
  `SELECT_REFERENCE_CONTROL_ONLY`

## Current Audit

Latest completion audit:

- path: `results/20260629_rescue_goal/completion_audit.md`
- `completion_proven: True`
- `final_status.md` remains intentionally absent because the user requested
  continued targeted improvement attempts after poor results, and those full
  GPU jobs are still queued.

Latest GPU ledger:

- path: `results/20260629_rescue_goal/gpu_action_status.md`
- rows: `12`
- open monitor actions: `3`
  - `57334792`: targeted SRR-v2 extras on `htzhulab`, pending with
    `(PartitionDown)`.
  - `57340171`: targeted SRR-v2 extras on `a100-gpu`, pending with
    `(PartitionDown)`.
  - `57340161`: targeted SRR-v2 extras on `volta-gpu`, pending with
    `(PartitionDown)`.

## Decision

Do not write `final_status.md` yet while the targeted extras are queued and the
user has asked to continue improvement attempts after weak results. Current
evidence points to `STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL` if those targeted full
runs also fail to beat the nnU-Net gate. The strongest first-party route to
watch is SRR-v2 capacity/targeted tuning: capacity extras produced the best scar
signal (`0.3090`), while repaired proposal and cascade routes are weaker.

No validation upload, upload-ready package, fold expansion, evaluator change, or
label mapping change has been performed.
