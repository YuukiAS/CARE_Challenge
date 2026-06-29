---
task_key: "20260629_true_soft_roi_refine"
project: "CARE-Myocardium"
status: "ready"
executor: "Codex"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
max_single_job_walltime: "08:00:00"
max_parallel_gpu_jobs: 1
---

# Task 20260629 True Soft-ROI Refinement

## Objective

Implement the missing Result5 soft-cascade refinement mechanism. This task must not conflict with `20260628_myops_refine`: no formal refinement job may start until the proposal selection state is known. However, code scaffolding, CPU tests, ROI extraction tests, and one-case export preflights may proceed in parallel under isolated outputs.

The goal is to make Result5 real: proposal gates should generate soft candidate regions, and scar/edema should be refined by pathology-specific refiner heads with restored full-volume predictions.

## Required reading

Read `docs/notes/20260629_result5_gap_audit.md`, `prompts/tasks/20260628_myops_proposal.md`, `prompts/tasks/20260628_myops_refine.md`, `src/care_myocardium/models/srr_myops.py`, `scripts/training/run_srr_myops_fold0.py`, completed proposal artifacts under `results/20260628_myops_proposal/variants/`, and current evaluator code.

## Non-conflict rule

Use `results/20260629_true_soft_roi_refine/`. Do not run formal refinement unless `results/20260628_myops_proposal/selection.md` exists and is `SELECT_PROPOSAL_ROUTE`, or unless the orchestrator explicitly labels the run as `PREFLIGHT_ONLY_NO_SELECTION`. Do not overwrite `results/20260628_myops_refine/`.

## Required implementation concepts

1. Soft ROI generator. Convert proposal gates into soft candidate crops or candidate masks. Avoid hard myocardium deletion. Use dilated proposal/anatomy neighborhoods and keep context.

2. Scar refiner. Small ROI, higher-resolution, high-precision scar refiner. It should receive image features, scar proposal gate, anatomy union prior, local anatomy confidence or distance, and original LGE/C0 evidence when available.

3. Edema refiner. Larger ROI, more context-preserving, T2-conditioned edema refiner. It should receive T2 evidence when present, anatomy prior, edema proposal gate, uncertainty, and larger contextual dilation.

4. Restore full-volume output. Refined crops must be mapped back into the original volume with correct affine/spacing/shape semantics. Full-volume metrics, not crop-only metrics, decide selection.

5. Losses. Use pathology-specific binary losses with ignore masks. Edema dense loss remains T2-present only. Add conservative boundary/HD or component pressure only after a Dice-preserving baseline refiner works.

6. Decode. Use calibrated pathology-priority composition for refined outputs rather than raw uncalibrated argmax between anatomy and pathology heads.

## Minimum path

1. Implement ROI extraction and restoration as unit-testable utilities.
2. Run one-case and multi-case CPU/GPU smoke tests to prove crop/restore label geometry is correct.
3. If proposal selection exists, run at least one formal refiner route. If proposal selection does not exist, stop after preflight and write `REFINE_WAITING_FOR_PROPOSAL_SELECTION`.

## Evaluation

Report:

- scar all and GT-positive Dice/HD95/component count/remote FP
- edema all, T2-present, GT-positive Dice/HD95/component count/remote FP
- ROI recall before refinement
- refined mask recall/precision
- number of crops per case, crop volume ratio, empty ROI rate
- full-volume restoration validity

## Outputs

Write:

- `results/20260629_true_soft_roi_refine/result.md`
- `results/20260629_true_soft_roi_refine/MANIFEST.md`
- `results/20260629_true_soft_roi_refine/roi_sanity.csv`
- `results/20260629_true_soft_roi_refine/refine_metrics.csv` if formal/preflight predictions exist
- `results/20260629_true_soft_roi_refine/selection.md`

Selection states:

- `REFINE_WAITING_FOR_PROPOSAL_SELECTION`
- `REFINE_PREFLIGHT_READY`
- `REFINE_FORMAL_SIGNAL`
- `REFINE_NO_SIGNAL`
- `REFINE_ROI_RECALL_FAILURE`
- `REFINE_RESTORE_BUG`

## Stop conditions

Stop for geometry restoration bugs, label/evaluator mismatch, or unsafe no-T2 edema supervision. Do not stop because a scar ROI is empty in a negative case; that is expected and should be measured.
