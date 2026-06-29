---
task_key: "20260629_proposal_memory_hardneg"
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

# Task 20260629 Proposal Memory and Hard-Negative Replay

## Objective

Add the Result5 mechanism that is currently missing from the first-stage proposal implementation: explicit negative-space learning with memory/replay. This task should build on completed `20260628_myops_proposal` artifacts when available. It must not kill, overwrite, or restart the current proposal formal jobs.

The purpose is to turn proposal from a shallow current-batch positive/negative margin into a lesion candidate generator that learns from remote false positives, safe hard negatives, and pathology-specific prototype memory.

## Required reading

Read `docs/notes/20260629_result5_gap_audit.md`, `prompts/tasks/20260628_myops_proposal.md`, `results/20260628_myops_proposal/progress.md`, `src/care_myocardium/models/srr_myops.py`, `scripts/training/run_srr_myops_fold0.py`, and any completed `proposal_metrics.csv`, `prototype_usage.csv`, and `component_hd_by_case.csv` under `results/20260628_myops_proposal/variants/`.

## Non-conflict rule

Use outputs under `results/20260629_proposal_memory_hardneg/`. If only `proposal_pos_neg_basic` has completed, run replay mining as a preflight/audit only. Do not run a new formal hard-negative job until either all current proposal formal jobs complete or the orchestrator confirms GPU capacity will not interfere.

## Mechanisms to implement or preflight

1. Hard-negative miner from existing predictions. Mine false-positive connected components for scar and edema. Record component size, distance from GT lesion, distance from anatomy union, center, class, and safety type.

2. Scar safe negatives. Include myocardium non-scar, blood pool, remote FP components, normal anatomy, and high-confidence artifacts if detectable. Scar can use stronger hard-negative mining because LGE is present.

3. Edema safe negatives. Use only T2-present far-from-GT myocardium, blood pool/background, and no-T2 true background. Never use no-T2 myocardium or scar as edema hard negative.

4. Prototype memory. Add a small first-party memory bank or replay buffer for positive and negative prototype updates. It can be class-specific and task-specific; it does not need to be large. The key is to persist hard negatives across batches or mining epochs.

5. Proposal loss. Add margin or contrastive loss against memory negatives. Keep dense proposal BCE/Dice for T2-present edema and scar. Add conservative weights so Dice does not collapse from over-penalizing positives.

6. Replay schedule. Warm up proposal for a short period before strong hard-negative replay. If using completed predictions only, run one replay epoch/preflight and report instead of claiming a full route.

## Evaluation

Report whether hard-negative replay improves:

- scar remote FP and component burden
- scar all Dice and GT-positive Dice
- edema T2-present/GT-positive Dice
- edema no-T2 empty stability
- proposal precision without catastrophic recall loss
- pos-minus-neg separation on GT positive vs safe negative voxels

## Outputs

Write:

- `results/20260629_proposal_memory_hardneg/result.md`
- `results/20260629_proposal_memory_hardneg/MANIFEST.md`
- `results/20260629_proposal_memory_hardneg/mined_components.csv`
- `results/20260629_proposal_memory_hardneg/memory_usage.csv` if implemented
- `results/20260629_proposal_memory_hardneg/subgroup_metrics.csv` if a formal/preflight training run is executed
- `results/20260629_proposal_memory_hardneg/selection.md`

Selection states:

- `HARDNEG_PREFLIGHT_ONLY`
- `HARDNEG_REPLAY_SIGNAL`
- `HARDNEG_REPLAY_NO_SIGNAL`
- `HARDNEG_REPLAY_TOO_AGGRESSIVE`
- `HARDNEG_BLOCKED_WAITING_FOR_PROPOSAL_JOBS`

## Stop conditions

Stop only for missing artifacts, label contract errors, or inability to construct safe negatives. Do not stop because one class has no safe hard negatives; run the other class and document the gap.
