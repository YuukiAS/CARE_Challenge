# Result 20260629 Rescue Goal

Status: active; not final. Repaired proposal and all cascade follow-ups through
postprocess sweep are complete but not selected. SRR-v2 remains incomplete, with
the required fallback variants and extra light-refine probes running.

## What Was Done

- Verified the active `/users/a/e/aereinh/CARE` workspace and kept all writes
  under `/users`.
- Refreshed remote refs earlier in the run; local `main` and `origin/main`
  were even at that check.
- Ran the repaired proposal repeat route, SRR-v2 route setup/basic recovery,
  cascade teacher route, and the two Cine secondary routes.
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

SRR-v2 is incomplete:

- basic job `57094446_0` failed during export after `06:37:38`, then was
  recovered from checkpoint after the safe-pooling fix.
- recovered basic metrics: scar all-case Dice `0.1998`, edema GT-positive Dice
  `0.1431`.
- old A100 variants job `57095505_[1-2]` was cancelled after the same variants
  were running on the preferred `htzhulab` partition.
- isolated htzhulab fallback `57272337_[1-2]` is running for the two missing
  variants under
  `results/20260629_srr_v2_unet_core_htzhulab_fallback/`.
- canonical SRR-v2 final artifacts are still missing:
  `results/20260629_srr_v2_unet_core/result.md`,
  `selection.md`, and `metrics_summary.md`.

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
the free GPU capacity was redirected to SRR-v2:

- wrapper: `jobs/src/run_srr_v2_light_refine_extra.sh`
- job: `57277361_[0-1]`
- partition: `htzhulab`
- status at latest refresh: running
- output root:
  `results/20260629_srr_v2_unet_core/light_refine_extras/`
- variants:
  - `srr_v2_light_refine_lowmix`
  - `srr_v2_light_refine_hardneg`

Cine secondary-line tasks are complete:

- `results/20260629_cine_motion_alignment/selection.md`:
  `SELECT_MOTION_DESCRIPTOR_ONLY`
- `results/20260629_cine_motion_pathology/selection.md`:
  `SELECT_REFERENCE_CONTROL_ONLY`

## Current Audit

Latest completion audit:

- path: `results/20260629_rescue_goal/completion_audit.md`
- `completion_proven: False`
- current blockers:
  - SRR-v2 result/selection/metrics artifacts are missing.
  - SRR-v2 has only `1/3` canonical formal variants ready.

Latest GPU ledger:

- path: `results/20260629_rescue_goal/gpu_action_status.md`
- rows: `8`
- open monitor actions: `2`
  - `57272337`: isolated htzhulab SRR-v2 fallback, running.
  - `57277361`: SRR-v2 light-refine extras, running.

## Decision

Do not write `final_status.md` yet. The goal is not complete because SRR-v2
formal evidence is still incomplete. The cascade formal route also should not
be treated as a success; it produced only tiny deltas and was explicitly stopped
by the route finalizer.

The correct current action is to monitor the running SRR-v2 htzhulab fallback
and light-refine extras, then aggregate SRR-v2 evidence when outputs land.
Cascade should not be selected from current evidence. No validation upload,
upload-ready package, fold expansion, evaluator change, or label mapping change
has been performed.
