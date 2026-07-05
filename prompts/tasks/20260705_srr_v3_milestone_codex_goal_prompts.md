---
task_key: "20260705_srr_v3_milestone_codex_goal_prompts"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "prompt_index"
risk_level: "low"
allow_code_change: false
allow_shell_command: false
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "Chinese Codex goal prompts for SRR-v3 milestones"
expected_result_dir: "results/20260705_srr_v3_milestone_codex_goal_prompts/"
blocking: false
---

# SRR-v3 Milestone Codex Goal Prompts

This file stores the short Chinese goal prompts to give Codex for each SRR-v3 milestone. Do not execute multiple milestones in one Codex goal. Each milestone must check its prerequisite review first and stop if the prerequisite hard gate is not satisfied.

## Global Rule For Every Milestone

Every Codex goal must include this hard-gate sentence:

```text
执行科学任务前，先强制执行 hard-gate policy：精确 task graph、strict validator、completion-check-before-final-audit、minimum effective training、current-bad-packet regression。如果任何 hard gate 失败，停止并写 NEEDS_REVISION 或 NEEDS_EVIDENCE；不要继续 final audit、不要 route promotion、不要 validation packaging/upload。
```

## M0 Prompt: Architecture Master Contract

```text
只执行 `prompts/tasks/20260705_srr_v3_m0_architecture_master_contract.md`。这是架构契约 milestone，不训练、不改模型、不跑后续 milestone。先读取 handoff hard-gate repair review、SRR-v2.5 evidence supplement audit、HANDOFF_GATE_POLICY、GPT_HARD_GATE_PROMPT；确认 hard-gate repair 是 AUDITED_GO。然后在 `results/20260705_srr_v3_m0_architecture_master_contract/` 写齐要求文件，锁定 SRR-v3 架构故事、接口、指标、下游 milestone graph、completion_check 和 review_request。执行科学任务前，先强制执行 hard-gate policy：精确 task graph、strict validator、completion-check-before-final-audit、minimum effective training、current-bad-packet regression。如果任何 hard gate 失败，停止并写 NEEDS_REVISION 或 NEEDS_EVIDENCE；不要继续 final audit、不要 route promotion、不要 validation packaging/upload。
```

## M1 Prompt: Runtime Instrumentation Gate

```text
只执行 `prompts/tasks/20260705_srr_v3_m1_runtime_instrumentation_gate.md`。开始前必须确认 `results/20260705_srr_v3_m0_architecture_master_contract/review.md` 存在且包含 `M0_AUDITED_GO`，否则停止。目标是补足运行时证据，不训练新模型：导出 gate open-rate、bounded delta、gate*delta、decode label delta、anchor confidence、prototype T2-present coverage、anchor/component alignment、no-T2 safety。结果写入 `results/20260705_srr_v3_m1_runtime_instrumentation_gate/`，必须有 completion_check 和 review_request。执行科学任务前，先强制执行 hard-gate policy：精确 task graph、strict validator、completion-check-before-final-audit、minimum effective training、current-bad-packet regression。如果任何 hard gate 失败，停止并写 NEEDS_REVISION 或 NEEDS_EVIDENCE；不要继续 final audit、不要 route promotion、不要 validation packaging/upload。
```

## M2 Prompt: MyoPS Bounded Runtime Repair

```text
只执行 `prompts/tasks/20260705_srr_v3_m2_myops_bounded_runtime_repair.md`。开始前必须确认 `results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md` 存在且包含 `M1_AUDITED_GO`，否则停止。目标是修复 MyoPS 运行时架构缺口，只允许小规模 smoke，不允许 full-fold training：closed gate 要精确复现 nnU-Net，同时要有 correction-positive gate opening sanity；strong encoder/context 要有现实可运行证据；prototype bank 必须包含 T2-present edema 正负证据；proposal/refinement 必须有 bounded local ROI 证据；no-T2 edema 必须端到端安全。结果写入 `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/`。执行科学任务前，先强制执行 hard-gate policy：精确 task graph、strict validator、completion-check-before-final-audit、minimum effective training、current-bad-packet regression。如果任何 hard gate 失败，停止并写 NEEDS_REVISION 或 NEEDS_EVIDENCE；不要继续 final audit、不要 route promotion、不要 validation packaging/upload。
```

## M3 Prompt: MyoPS Minimum-Effective Pilot Training

```text
只执行 `prompts/tasks/20260705_srr_v3_m3_myops_min_effective_pilot_training.md`。开始前必须确认 `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md` 存在且包含 `M2_AUDITED_GO`，否则停止。这是最小有效 pilot，不是 full fold、不是 challenge candidate。必须满足 frontmatter 的 minimum_effective_training：至少 1200 optimizer steps、1800 秒 train loop、12 个 eval cases、one-batch overfit、prediction sanity、loss decrease、same-split nnU-Net baseline、cache isolation。必须输出 gate/residual stats、prototype bank summary、same-split help/harm、hard subgroup metrics、adequacy_check、completion_check 和 review_request。执行科学任务前，先强制执行 hard-gate policy：精确 task graph、strict validator、completion-check-before-final-audit、minimum effective training、current-bad-packet regression。如果任何 hard gate 失败，停止并写 NEEDS_REVISION 或 NEEDS_EVIDENCE；不要 route promotion、不要 validation packaging/upload。
```

## M4 Prompt: MyoPS Mechanism Ablation Readiness

```text
只执行 `prompts/tasks/20260705_srr_v3_m4_myops_mechanism_ablation_readiness.md`。开始前必须确认 `results/20260705_srr_v3_m3_myops_min_effective_pilot_training/review.md` 存在且包含 `M3_AUDITED_GO`，否则停止。目标是解释 SRR-v3 机制的 help/harm，而不是训练 full folds。围绕 closed gate、no anchor、residual frozen、dictionary/prototypes、semantic retrieval、component proposal、anatomy ROI、local refinement 做 bounded ablation；每行必须报告 same-split nnU-Net help/harm、gate/residual、prototype/dictionary、proposal/refinement、hard subgroup 和 provenance。结果写入 `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/`。执行科学任务前，先强制执行 hard-gate policy：精确 task graph、strict validator、completion-check-before-final-audit、minimum effective training、current-bad-packet regression。如果任何 hard gate 失败，停止并写 NEEDS_REVISION 或 NEEDS_EVIDENCE；不要 route promotion、不要 validation packaging/upload。
```

## M5 Prompt: Cine Secondary Contract

```text
只执行 `prompts/tasks/20260705_srr_v3_m5_cine_secondary_contract.md`。开始前必须确认 `results/20260705_srr_v3_m0_architecture_master_contract/review.md` 存在且包含 `M0_AUDITED_GO`，否则停止。Cine 是副线，不阻塞 MyoPS。目标是审计和补足 Cine secondary diagnostic evidence：CineMA/anatomy prior、ANTsPy SyN same-safe-subset matrix、VoxelMorph trained/usable status、frame0/ED controls、temporal dictionary readiness、frame-quality/motion-saliency router。不能把 frame0-only、one-case SyN smoke、untrained VoxelMorph adapter 冒充 full temporal retrieval。结果写入 `results/20260705_srr_v3_m5_cine_secondary_contract/`。执行科学任务前，先强制执行 hard-gate policy：精确 task graph、strict validator、completion-check-before-final-audit、minimum effective training、current-bad-packet regression。如果任何 hard gate 失败，停止并写 NEEDS_REVISION 或 NEEDS_EVIDENCE；不要 hosted Cine metric claim、不要 validation packaging/upload。
```

## Normal Operating Flow

1. User gives Codex exactly one milestone prompt.
2. Codex checks prerequisite review and hard gates before doing any scientific work.
3. Codex executes only that milestone scope.
4. Codex writes exact required outputs under the exact `results/<task_key>/` directory.
5. Codex writes `completion_check.md` and `review_request.md`.
6. A separate read-only review must write `review.md`.
7. Only after the review contains the audited-go state may the user start the next milestone.

Do not skip directly from one milestone result to the next milestone execution without a separate review.
