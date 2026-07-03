# Execution Plan 20260703_hardmode_goal

status: EXECUTION_PLANNED
controller_role: Codex controller session
generated_at: 2026-07-03 02:55:53 EDT
task: prompts/tasks/20260703_hardmode_goal.md

## Protocol Boundary

This controller stays inside the GPT-authored controller task. It does not act as a strategic planner, does not invent new CARE research routes, and does not run the six execution subtasks as a single executor-only task.

The controller may coordinate separate executor and auditor sessions. Each executor must write its own `results/<task_key>/result.md` and `MANIFEST.md`, then stop at `EXECUTED_UNAUDITED`. Independent audit is required before any promotion decision, fold expansion, validation packaging, upload, or next-stage training.

## Required Reads Completed By Controller

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/CHATGPT_RULES.md`
- `prompts/HANDOFF_ROLES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `.agents/skills/agent-task-executor/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`
- `/users/a/e/aereinh/.codex-global/skills/core-codex-system-codex-workflow-protocol/SKILL.md`
- `/users/a/e/aereinh/.codex-global/skills/core-codex-system-codex-workflow-protocol/references/live-state-delegation.md`
- `results/20260629_rescue_goal/final_status.md`
- `results/20260629_rescue_goal/completion_audit.md`
- `results/20260629_rescue_goal/gpu_action_status.md`
- `results/20260629_rescue_goal/route_status.csv`
- all six executor subtask files listed below

## Subtask Order

1. Phase 0/1: `prompts/tasks/20260703_myops_audit.md`
   - Launch first.
   - Output must include mechanism audit, label/export QC, architecture gap audit, route gap table, failure case table, code path audit, and next-route gate.
   - No training, fold expansion, validation upload, or package generation.
2. Phase 2A: `prompts/tasks/20260703_myops_fp_control.md`
   - Launch only after `20260703_myops_audit` produces sufficient gate evidence or explicitly marks what is missing.
   - Fast fixed-rule/component-scoring work anchored to nnU-Net, not SRR-v2 tuning.
3. Phase 2B: `prompts/tasks/20260703_myops_srr_propose_refine.md`
   - Launch only after audit gate and only as SRR evidence-engine propose/refine work.
   - No dictionary-only, threshold/gate/mix-weight tuning continuation.
4. Phase 2C: `prompts/tasks/20260703_myops_alignment_gate.md`
   - Launch after audit, or when complete-case alignment evidence is needed and authorized by the controller gate.
   - Translation-only is a baseline, not completion.
5. Phase 3: `prompts/tasks/20260703_myops_anchor_refine.md`
   - Launch only when Phase 0/1 and Phase 2 evidence supports trainable refinement, or it must write `NEEDS_EVIDENCE`.
6. Phase 4: `prompts/tasks/20260703_cine_motion.md`
   - Secondary route. It may run only when it does not block MyoPS priority.
   - Must use non-reference frame evidence for any temporal completion claim.

## Resource Budget

- Default single training/evaluation job walltime: 8 hours or less.
- Preferred GPU partition: `htzhulab`.
- Before switching to `a100-gpu` or `volta-gpu`, executor must inspect queue state and justify the switch.
- No validation upload, upload-ready package, fold expansion, label mapping change, fold split change, or evaluator change is authorized by this controller stage.
- Network is not authorized.

## Cache And Evidence Isolation

Every executor must write outputs under its own `results/<task_key>/` directory and must use task/config/checkpoint/fold-specific prediction and metric paths. Stale predictions may be read as baseline evidence only when their path, timestamp, task/config, fold, and evaluator contract are recorded. New comparisons require isolated output directories.

## Audit Plan

The controller will use separate read-only auditor sessions after executor outputs exist. Auditors must not fix code, generate missing artifacts, launch training, or rerun execution commands. Each audit must review claims against files, commands, metrics, logs, label/export QC, cache isolation, and forbidden substitutes.

The controller will not promote or commit/push until required executor result and auditor review evidence exists and the promotion gate is satisfied.

## Current Controller Decision

Automatic subagent tooling is available via `multi_agent_v1.spawn_agent`. The controller will launch only the Phase 0/1 `20260703_myops_audit` executor first. Later executor launches are gated on the audit result and review.
