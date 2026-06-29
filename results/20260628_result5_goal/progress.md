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

## 2026-06-29 Orchestrator Continuation

Executed the requested synchronization sequence on `main`:

- `git status`
- `git pull --ff-only`
- `git status`

The pull fast-forwarded the continuation registry from `origin/main`; the branch stayed on `main`.

Formal proposal job status at continuation:

| job_id | variant | status |
| --- | --- | --- |
| `56912267` | `proposal_pos_neg_basic` | completed; weak local fold0 pathology signal |
| `56912269` | `proposal_anatomy_distance` | still running on `htzhulab`; not killed, restarted, or overwritten |
| `56942380` | `proposal_uncertainty_gate` | repaired resubmission still running on `htzhulab`; not killed, restarted, or overwritten |

Non-idle parallel work started:

- `20260629_loss_decode_calibration`: confirmed a core SRR loss bug where `-1` ignore/padding voxels contributed as background to anatomy, scar, edema, and soft anatomy prior losses. Repaired this for future runs without changing fold split, label mapping, evaluator, or hosted validation semantics.
- `20260629_pathology_checkpoint_selection`: added a read-only audit script for completed proposal checkpoints, comparing raw/decode alternatives and best-vs-final checkpoints with pathology-aware metrics.
- Preflight smoke completed on two cases for `proposal_pos_neg_basic` under ignored `results/20260629_*/preflight/` directories. It produced the expected task files and confirmed the audit pipeline runs before launching a full fold0 GPU audit.

Current gate state:

- `SELECT_PROPOSAL_ROUTE` has not been reached.
- Formal `20260628_myops_refine` remains blocked by the proposal selection gate.
- The new loss fix should be treated as future-run infrastructure; the already-running formal proposal jobs still reflect the code state at their launch.

## 2026-06-29 Loss/Decode and Checkpoint Audit Completed

Completed the first non-idle continuation audits for the only finished proposal variant so far, `proposal_pos_neg_basic`.

Slurm audit:

- job: `56946010`
- script: `jobs/evaluation/audit_result5_decode_calibration.sh`
- log: `logs/R5DecodeAudit_56946010_20260629_055753.log`
- state: `COMPLETED`
- elapsed: `00:15:38`

Outputs:

- `results/20260629_loss_decode_calibration/result.md`
- `results/20260629_loss_decode_calibration/selection.md`
- `results/20260629_loss_decode_calibration/decode_metrics.csv`
- `results/20260629_loss_decode_calibration/decode_case_metrics.csv`
- `results/20260629_pathology_checkpoint_selection/result.md`
- `results/20260629_pathology_checkpoint_selection/selection.md`
- `results/20260629_pathology_checkpoint_selection/checkpoint_metrics.csv`

Selections:

- `20260629_loss_decode_calibration`: `DECODE_CALIBRATION_SIGNAL`
- `20260629_pathology_checkpoint_selection`: `FINAL_BETTER_THAN_PATCH_BEST`

Interpretation:

- The signal is positive for pipeline debugging: raw argmax is not the right decode surface, and patch-loss best checkpoint is not reliably pathology-optimal.
- The signal is not enough to start formal MyoPS refinement: best calibrated local combo remains around `0.28` on fold0 pathology targets, far below a credible proposal-route selection threshold.
- The loss masking bug repair and calibration/checkpoint findings should inform future runs after the `20260628_myops_proposal` formal jobs finish, but they do not retroactively change those running jobs.

## 2026-06-29 Hard-Negative Memory Preflight

Completed `20260629_proposal_memory_hardneg` as a non-conflicting preflight using only the completed `proposal_pos_neg_basic/checkpoint_best` predictions.

Outputs:

- `results/20260629_proposal_memory_hardneg/result.md`
- `results/20260629_proposal_memory_hardneg/selection.md`
- `results/20260629_proposal_memory_hardneg/mined_components.csv`
- `results/20260629_proposal_memory_hardneg/memory_usage.csv`

Selection:

- `HARDNEG_PREFLIGHT_ONLY`

Mining result:

- mined false-positive components: `7237`
- scar replay-safe components: `4167`
- edema replay-safe components: `1561`

Safety note:

- No-T2 edema handling followed the continuation rule: no-T2 myocardium or scar-adjacent components were excluded from edema replay, while no-T2 true-background components were allowed as safe background negatives.
- No formal hard-negative replay training was started because `proposal_anatomy_distance` and repaired `proposal_uncertainty_gate` are still running.

## 2026-06-29 True Soft-ROI Geometry Preflight

Completed `20260629_true_soft_roi_refine` as geometry-only scaffold and preflight. No formal refinement job was launched because `SELECT_PROPOSAL_ROUTE` has not been reached.

Outputs:

- `results/20260629_true_soft_roi_refine/result.md`
- `results/20260629_true_soft_roi_refine/selection.md`
- `results/20260629_true_soft_roi_refine/roi_sanity.csv`

Selection:

- `REFINE_WAITING_FOR_PROPOSAL_SELECTION`

Sanity result:

- ROI rows: `88`
- restore invalid rows: `0`
- GT-positive rows with ROI coverage < `0.95`: `0`
- edema GT-positive mean coverage: `1.0`
- scar GT-positive mean coverage: `1.0`

Caveat:

- Mean ROI volume ratio on GT-positive rows is high at about `0.74`; this proves safe extraction/restoration, but it is not yet a focused refinement crop policy.

## 2026-06-29 Result4 SRR-v2 Core Rebuild Preflight

Completed `20260629_result4_srr_core_rebuild` as an architecture preflight/defer package. No SRR-v2 formal GPU job was launched.

Outputs:

- `results/20260629_result4_srr_core_rebuild/result.md`
- `results/20260629_result4_srr_core_rebuild/selection.md`
- `results/20260629_result4_srr_core_rebuild/architecture_note.md`
- `results/20260629_result4_srr_core_rebuild/gate_usage.csv`

Selection:

- `CORE_REBUILD_DEFER`

Reason:

- The current sprint has already confirmed nearer pipeline blockers: ignore-label loss masking, decode calibration, and pathology checkpoint selection.
- Current formal proposal jobs are still running, so a new SRR-v2 formal GPU run would weaken attribution and compete with unfinished gated evidence.
- Code review confirms the current `ExpertBank` private experts operate on fused features, so future SRR-v2 should be an isolated new route with modality-private inputs rather than an in-place change to existing variants.

## 2026-06-29 Anatomy-Distance Proposal Completed

`proposal_anatomy_distance` job `56912269` completed naturally.

Slurm:

- state: `COMPLETED`
- exit code: `0:0`
- elapsed: `06:33:09`
- node: `g180702`
- MaxRSS batch: about `5.9 GiB`

Summary:

- `stop_reason=max_runtime_seconds`
- `budget_status=OK`
- `best_step=105000`
- summary: `results/20260628_myops_proposal/variants/proposal_anatomy_distance/summary.md`

Initial readout:

| variant | edema all Dice | edema GT+ Dice | edema no-T2 empty Dice | scar all Dice | scar LGE-only Dice |
| --- | ---: | ---: | ---: | ---: | ---: |
| `proposal_pos_neg_basic` | `0.1768` | `0.1737` | `0.1786` | `0.1017` | `0.0722` |
| `proposal_anatomy_distance` | `0.0635` | `0.1745` | `0.0000` | `0.0956` | `0.0783` |

Interpretation:

- Anatomy-distance did not provide a credible proposal-route improvement.
- The no-T2 edema stability is worse than `proposal_pos_neg_basic`; do not select this route from the partial readout.
- Final proposal aggregation still waits for repaired `proposal_uncertainty_gate` job `56942380`.
