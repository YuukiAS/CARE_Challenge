---
task_key: "20260629_result5_continuation_goal"
project: "CARE-Myocardium"
status: "ready"
executor: "Codex-Goal"
mode: "goal"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
max_single_job_walltime: "08:00:00"
max_parallel_gpu_jobs: 6
allow_subtask_execution: true
---

# Goal 20260629 Result5 Continuation and Repair Sprint

## Objective

Continue the existing CARE Result5 proposal-refinement sprint without discarding the still-running `20260628_myops_proposal` formal jobs. Do not wait idle. Monitor and aggregate the current proposal jobs, but in parallel execute non-conflicting audit and implementation tasks that address the gaps between current code, Result4 SRR, Result5, and the submitted architecture figure.

The core scientific direction remains: first-party SRR evidence retrieval, pathology-specific proposal, negative-space discrimination, and soft-cascade refinement. Do not revert to nnU-Net as the method. nnU-Net may only remain a reference metric.

## Coordination rule

Use one orchestrator as the owner of code writes. If additional Codex sessions or subagents are used, assign non-overlapping tasks and output directories. Do not create extra git branches unless a human explicitly approves. Avoid code confusion by using new variant names and task-scoped result directories. Every subtask must record what it changed and what files it owns.

## Current work that must continue

Continue `prompts/tasks/20260628_myops_proposal.md` until all formal jobs finish or fail with documented reasons:

- `proposal_pos_neg_basic`
- `proposal_anatomy_distance`
- `proposal_uncertainty_gate`

Do not kill, overwrite, or restart these jobs just because a new audit task exists. After they complete, write or update the proposal aggregate result and selection files. Only enter formal MyoPS refinement if the proposal selection state is `SELECT_PROPOSAL_ROUTE`.

## Why new parallel tasks are needed

The current Result5 code does not yet fully implement the Result4/Result5 design. The urgent audit conclusions are recorded in `docs/notes/20260629_result5_gap_audit.md`. In particular, current gaps include: no true soft-ROI refinement, proposal logits mixed directly into final outputs, no hard-negative replay or memory bank, no true multi-scale modality-private sparse SRR, patch-loss checkpoint selection, and likely loss/decoding calibration issues.

## Subtask registry

The following subtasks may run in parallel if they do not conflict with the current proposal jobs:

1. `prompts/tasks/20260629_loss_decode_calibration.md`
   - Highest priority.
   - Audit ignore-label masking, raw argmax vs pathology-priority decoding, original/proposal/mixed logits, threshold sweeps, and checkpoint-best vs checkpoint-final.
   - This can use existing completed checkpoints and should not need a long new GPU job.

2. `prompts/tasks/20260629_pathology_checkpoint_selection.md`
   - Evaluate checkpoint selection by full-volume pathology metrics.
   - Prepare a future-safe pathology-aware checkpoint selection route.

3. `prompts/tasks/20260629_proposal_memory_hardneg.md`
   - Add or preflight hard-negative replay, remote FP mining, and pathology-specific prototype memory.
   - It should use completed proposal artifacts when available; before all proposal jobs finish, keep this as preflight/audit only.

4. `prompts/tasks/20260629_true_soft_roi_refine.md`
   - Implement actual soft-ROI refinement scaffolding and geometry tests.
   - Do not run formal refinement until `SELECT_PROPOSAL_ROUTE`; preflight only is allowed.

5. `prompts/tasks/20260629_result4_srr_core_rebuild.md`
   - Implement an isolated SRR-v2 route closer to Result4: multi-scale, true modality-private features, sparse retrieval, and SIP-inspired usage by availability pattern.
   - Use preflight first. Formal training only if resources are safe and the orchestrator decides it is needed.

## Execution order

Phase A: Monitor current proposal jobs and preserve artifacts.

Phase B: Run `20260629_loss_decode_calibration` and `20260629_pathology_checkpoint_selection` as soon as at least one checkpoint is available. These tasks answer whether the 0.1 Dice regime is partly caused by pipeline/loss/decode/checkpoint selection rather than by the SRR idea itself.

Phase C: If decode/loss/checkpoint bugs are confirmed, implement the smallest safe repair and run a short isolated sanity/preflight. Do not reinterpret old Result5 jobs as failed science if the pipeline was broken.

Phase D: Once all proposal jobs are complete, write proposal aggregate and selection. If `SELECT_PROPOSAL_ROUTE`, proceed to true refinement using the existing or updated refine task plus `20260629_true_soft_roi_refine`. If not selected but there is proposal signal, route to `REVISE_PROPOSAL_AND_REPEAT` using the hard-negative memory and calibration repairs.

Phase E: If the current SRR trunk remains near 0.1 after calibration, use `20260629_result4_srr_core_rebuild` to produce a more faithful SRR-v2 implementation. This is a paper-preserving first-party route, not a fallback to nnU-Net.

## Hard constraints

Do not change fold split, label mapping, evaluator, or hosted validation semantics. Do not upload validation packages or external artifacts. Do not use external weights. Do not treat no-T2 myocardium as edema negative. Do not use anatomy prior as hard deletion. Do not let a single failed variant stop the whole goal. Do not launch unnecessary long jobs before running the short audit tasks.

## Required outputs

Update or write:

- `results/20260628_result5_goal/progress.md`
- `results/20260628_result5_goal/final_status.md` when the goal concludes
- each subtask's required `result.md`, `MANIFEST.md`, metrics CSVs, and `selection.md`
- an aggregate human-readable explanation that says which gaps were fixed, which remain, and whether the next action is proposal repeat, refinement, SRR-v2, or stop for pipeline bug.

## Final status options

Use one of:

- `PROPOSAL_REFINE_SELECTED`
- `PROPOSAL_SELECTED_REFINE_REVISE`
- `PROPOSAL_REVISE_REPEAT_WITH_REPAIRS`
- `SRR_CORE_REBUILD_REQUIRED`
- `STOP_PIPELINE_BUG`
- `STOP_NO_PROPOSAL_SIGNAL`

Do not use `FALLBACK_TO_SRR` unless it clearly means a first-party SRR-v2 repair route, not a return to a weaker dense-head-only run.
