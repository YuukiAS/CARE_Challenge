---
task_key: "20260705_srr_v3_milestone_reviewer_goal_prompts"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "prompt_index"
risk_level: "low"
allow_code_change: false
allow_shell_command: false
allow_network: false
allow_external_upload: false
review_required: false
mechanism_class: "Chinese reviewer prompts for SRR-v3 milestones"
expected_result_dir: "results/20260705_srr_v3_milestone_reviewer_goal_prompts/"
blocking: false
---

# SRR-v3 Milestone Reviewer Goal Prompts

This file stores the short Chinese prompts to give a separate Codex reviewer/auditor session after each milestone executor has committed its result directory. It is the reviewer-side companion to `prompts/tasks/20260705_srr_v3_milestone_codex_goal_prompts.md`.

## Global Rule For Every Reviewer

```text
这是独立只读 reviewer/auditor session。不要补 executor 缺失文件，不要改模型代码，不要训练，不要 validation packaging/upload，不要 route promotion，不要启动下一个 milestone。只审阅对应的 `results/<task_key>/`，最后只写该目录下的 `review.md`，并给出该 milestone 允许的 controlled decision。写完后用 `git add -f` 提交轻量 review 文件，但不要 push；由用户手动 push。
```

## M0 Reviewer Prompt: Architecture Master Contract

```text
只读审阅 `results/20260705_srr_v3_m0_architecture_master_contract/`。请读取 `prompts/tasks/20260705_srr_v3_m0_architecture_master_contract.md`、`prompts/MILESTONE_REVIEW_PROTOCOL.md`、`prompts/HANDOFF_GATE_POLICY.md`、`prompts/GPT_HARD_GATE_PROMPT.md`、handoff hard-gate repair review、SRR-v2.5 evidence supplement audit，以及 M0 result directory。检查 required outputs 是否齐全，`completion_check.md` 是否为 `M0_READY_FOR_REVIEW`，architecture/interface/metric/hard-gate/downstream graph 是否 machine-checkable，是否违反 forbidden substitutes，是否错误写了 `review.md` 或启动 M1。最后只写 `results/20260705_srr_v3_m0_architecture_master_contract/review.md`，decision 只能是 `M0_AUDITED_GO`、`M0_AUDITED_NEEDS_REVISION` 或 `M0_AUDITED_NEEDS_EVIDENCE`。完成后 `git add -f results/20260705_srr_v3_m0_architecture_master_contract/review.md` 并 commit；不要 push，由用户手动 push。
```

## M1 Reviewer Prompt: Runtime Instrumentation Gate

```text
只读审阅 `results/20260705_srr_v3_m1_runtime_instrumentation_gate/`。请读取 `prompts/tasks/20260705_srr_v3_m1_runtime_instrumentation_gate.md`、M0 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M1 result directory。检查 M1 是否真的导出了 gate open-rate、bounded delta、gate*delta、decode label delta、anchor confidence、prototype T2-present coverage、anchor/component alignment、no-T2 safety；检查 required outputs 和 `completion_check.md`；确认没有训练新模型、没有跳到 M2、没有 route promotion。最后只写 `results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md`，decision 只能是 `M1_AUDITED_GO`、`M1_AUDITED_NEEDS_REVISION` 或 `M1_AUDITED_NEEDS_EVIDENCE`。完成后 `git add -f results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md` 并 commit；不要 push，由用户手动 push。
```

## M2 Reviewer Prompt: MyoPS Bounded Runtime Repair

```text
只读审阅 `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/`。请读取 `prompts/tasks/20260705_srr_v3_m2_myops_bounded_runtime_repair.md`、M1 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M2 result directory。检查 closed-gate identity、correction-positive gate opening sanity、strong encoder/context sanity、T2-present edema prototype coverage、proposal/refinement bounded local ROI evidence、no-T2 end-to-end safety、cache/provenance isolation、unit tests 和 required outputs。确认没有 full-fold training、没有 validation package/upload、没有 route promotion、没有启动 M3。最后只写 `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md`，decision 只能是 `M2_AUDITED_GO`、`M2_AUDITED_NEEDS_REVISION` 或 `M2_AUDITED_NEEDS_EVIDENCE`。完成后 `git add -f results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md` 并 commit；不要 push，由用户手动 push。
```

## M3 Reviewer Prompt: MyoPS Minimum-Effective Pilot Training

```text
只读审阅 `results/20260705_srr_v3_m3_myops_min_effective_pilot_training/`。请读取 `prompts/tasks/20260705_srr_v3_m3_myops_min_effective_pilot_training.md`、M2 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M3 result directory。检查 minimum_effective_training 是否满足：至少 1200 optimizer steps、1800 秒 train loop、至少 12 个 eval cases、one-batch overfit、prediction sanity、loss decrease、same-split nnU-Net baseline、cache isolation。检查 training curves、validation events、prediction sanity、gate/residual stats、prototype bank summary、same-split help/harm、hard subgroup metrics、adequacy_check 和 required outputs。确认它不是 6-step smoke、不是 eval-only over old checkpoint、不是 full-fold route promotion。最后只写 `results/20260705_srr_v3_m3_myops_min_effective_pilot_training/review.md`，decision 只能是 `M3_AUDITED_GO`、`M3_AUDITED_NEEDS_REVISION` 或 `M3_AUDITED_NEEDS_EVIDENCE`。完成后 `git add -f results/20260705_srr_v3_m3_myops_min_effective_pilot_training/review.md` 并 commit；不要 push，由用户手动 push。
```

## M4 Reviewer Prompt: MyoPS Mechanism Ablation Readiness

```text
只读审阅 `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/`。请读取 `prompts/tasks/20260705_srr_v3_m4_myops_mechanism_ablation_readiness.md`、M3 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M4 result directory。检查 ablation matrix 是否覆盖 closed gate、no anchor、residual frozen、dictionary/prototypes、semantic retrieval、component proposal、anatomy ROI、local refinement 等机制；每行是否有 same-split help/harm、gate/residual、prototype/dictionary、proposal/refinement、hard subgroup 和 provenance。确认没有把 undertrained smoke 当成机制结论，没有 route promotion，没有启动后续 MyoPS milestone。最后只写 `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md`，decision 只能是 `M4_AUDITED_GO`、`M4_AUDITED_NEEDS_REVISION` 或 `M4_AUDITED_NEEDS_EVIDENCE`。完成后 `git add -f results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md` 并 commit；不要 push，由用户手动 push。
```

## M5 Reviewer Prompt: Cine Secondary Contract

```text
只读审阅 `results/20260705_srr_v3_m5_cine_secondary_contract/`。请读取 `prompts/tasks/20260705_srr_v3_m5_cine_secondary_contract.md`、M0 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M5 result directory。检查 CineMA/anatomy prior、ANTsPy SyN same-safe-subset matrix、VoxelMorph status、frame0/ED controls、temporal dictionary readiness、frame-quality/motion-saliency router、missing evidence 和 required outputs。确认没有把 frame0-only、one-case SyN smoke 或 untrained VoxelMorph adapter 冒充 full temporal retrieval，没有 hosted Cine metric claim，没有 validation package/upload。最后只写 `results/20260705_srr_v3_m5_cine_secondary_contract/review.md`，decision 只能是 `M5_AUDITED_DIAGNOSTIC_GO`、`M5_AUDITED_NEEDS_REVISION` 或 `M5_AUDITED_NEEDS_EVIDENCE`。完成后 `git add -f results/20260705_srr_v3_m5_cine_secondary_contract/review.md` 并 commit；不要 push，由用户手动 push。
```

## Pairing With Executor Prompts

- Executor prompts: `prompts/tasks/20260705_srr_v3_milestone_codex_goal_prompts.md`
- Reviewer prompts: this file

Do not run a reviewer prompt before the corresponding executor result directory exists. Do not start the next executor prompt until the previous reviewer prompt writes the required audited-go token and the user has pushed the review commit if remote visibility is needed.
