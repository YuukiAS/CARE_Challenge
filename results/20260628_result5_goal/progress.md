# Result5 Goal Progress

## 2026-06-28 Start

Started the new Result5 goal from `prompts/tasks/20260628_result5_goal.md`.

Current phase: `Phase 1 - MyoPS proposal stage`.

Actions completed:

- Loaded repo rules, handoff rules, Result5, and prior 20260626 results.
- Implemented first-stage MyoPS proposal variants.
- Submitted three formal proposal jobs to `htzhulab`.

Active jobs:

| job_id | subtask | variant | status at first check |
| --- | --- | --- | --- |
| `56912267` | `20260628_myops_proposal` | `proposal_pos_neg_basic` | `PD (Priority)` |
| `56912269` | `20260628_myops_proposal` | `proposal_anatomy_distance` | `PD (Priority)` |
| `56912268` | `20260628_myops_proposal` | `proposal_uncertainty_gate` | `PD (Priority)` |

Not started yet:

- `20260628_myops_refine`: waits for `SELECT_PROPOSAL_ROUTE`.

## 2026-06-28 Cine Registration Completed

Completed `20260628_cine_register` as the parallel Cine secondary track.

Outputs:

- Result: `results/20260628_cine_register/result.md`
- Selection: `results/20260628_cine_register/selection.md`
- Metrics: `results/20260628_cine_register/registration_metrics.csv`
- Warp sanity: `results/20260628_cine_register/warp_sanity.csv`

Decision:

- Cine status: `SELECT_MOTION_DESCRIPTOR_ONLY`
- Safe cases evaluated: `59`
- Mismatch cases held out: `5`
- SimpleITK classical registration succeeded on all `116` non-reference frame evaluations after adding a thin-volume `slice2d_translation` fallback, but anatomy consistency improved only marginally (`class_1` delta mean `0.0001`, `class_2` delta mean `0.0000`), so it was not selected as a dense registration module.

Still waiting:

- `20260628_myops_refine`: waits for `SELECT_PROPOSAL_ROUTE`.
- `20260628_myops_proposal`: formal jobs remain queued on `htzhulab`.

## 2026-06-29 Result5 Continuation Tasks Prepared

A ChatGPT audit concluded that the current Result5 implementation should keep running its formal proposal jobs, but should not wait idle because several Result4/Result5 mechanisms are not yet implemented. The audit note was added at `docs/notes/20260629_result5_gap_audit.md`.

Main conclusions recorded:

- Current proposal jobs can still answer whether the existing proposal head has weak signal, but they cannot add true soft-ROI refinement, memory-based hard-negative replay, multi-scale modality-private SRR, pathology-aware checkpointing, or calibrated final decoding.
- The current implementation is closer to an SRR-lite proposal-head run than to the full Result4-to-Result5 architecture in the figure.
- High-priority suspected bottlenecks include ignore-label loss masking, raw argmax decoding of mixed multiclass/binary logits, patch-loss checkpoint selection, proposal logits directly mixed into final outputs, lack of memory hard negatives, and lack of true modality-private sparse multi-scale retrieval.

New non-conflicting task prompts were added:

- `prompts/tasks/20260629_result5_continuation_goal.md`
- `prompts/tasks/20260629_loss_decode_calibration.md`
- `prompts/tasks/20260629_pathology_checkpoint_selection.md`
- `prompts/tasks/20260629_proposal_memory_hardneg.md`
- `prompts/tasks/20260629_true_soft_roi_refine.md`
- `prompts/tasks/20260629_result4_srr_core_rebuild.md`

The existing goal prompt `prompts/tasks/20260628_result5_goal.md` was amended with a 2026-06-29 continuation section. The amendment says to keep monitoring and aggregating the running `20260628_myops_proposal` jobs, but to run the new audit/calibration/checkpoint tasks in parallel when they do not conflict. Formal MyoPS refinement remains gated on `SELECT_PROPOSAL_ROUTE`.

Coordination policy recorded:

- One orchestrator should own code writes.
- If extra Codex sessions or subagents are used, each must own non-overlapping files and output directories.
- Do not create new git branches unless explicitly approved by a human.
- Do not fall back to nnU-Net as the method; nnU-Net can only remain a reference metric.
