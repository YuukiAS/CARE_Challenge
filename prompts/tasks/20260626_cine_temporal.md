---
task_key: "20260626_cine_temporal"
project: "CARE-Myocardium"
status: "ready"
executor: "Codex"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
max_single_job_walltime: "08:00:00"
max_parallel_gpu_jobs: 2
---

# Task 20260626 Cine Temporal

## 目标

在上一轮 Cine geometry 已经给出 `GO_CINE_TEMPORAL_PREFLIGHT` 的基础上，继续推进 CineMyoPS 次线：在 59 个 strict safe cases 上构建并运行 anatomy-first temporal retrieval preflight。目标不是提交，也不是复活旧 single-frame wrapper，而是验证 4D cine 的关键帧、CineMA anatomy prior、frame-difference/motion-like context 与 temporal retrieval 是否能比 reference-frame control 提供本地 proxy 正信号。5 个 metadata mismatch cases 保持 repair queue，不阻塞 safe subset 推进。

## 背景

必须读取：

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/tasks/20260626_cine_temporal.md`
- `docs/notes/deep_research/Result4.pdf`
- `results/20260625_cine_geometry/result.md`
- `results/20260625_cine_geometry/decision.md`
- `results/20260625_cine_geometry/safe_cases.csv`
- `results/20260625_cine_geometry/mismatch_cases.csv`
- `results/20260625_cine_geometry/crop_roundtrip.csv`
- `results/20260625_cine_geometry/metrics_summary.md`
- `results/20260620_cinema_adapter_pilot/result.md`
- raw CineMyoPS 4D data、Dataset502/Task026、CineMA adapter outputs、existing evaluator

当前事实：safe subset 59 cases 上，CineMA frame0/reference anatomy preflight 的 class_1 myocardium Dice mean 约 `0.5626`，class_2 LV Dice mean 约 `0.7709`；class_3 scar sanity 为 `0.0000`，因为冻结 CineMA anatomy prior 无 scar head。下一步需要验证 temporal/anatomy retrieval，而不是继续停在 geometry 或 anatomy-only。

## 允许动作

- 新增/修改 first-party Cine temporal preflight scripts、safe subset dataset、key-frame selection、temporal retrieval module、reporting 和 jobs。
- 复用已有 CineMA code/weights/predictions；不得联网下载新资源。
- 在 59 safe cases 上运行 reference-frame control 与 temporal retrieval preflight，可提交最多 2 个并行 GPU jobs，每个 `<=08:00:00`。
- 使用 5 个 mismatch cases 做只读 repair analysis，不强行纳入训练。
- 写 `results/20260626_cine_temporal/result.md`、`MANIFEST.md`、`decision.md`。

## 禁止动作

- 不要 validation submission、upload package 或 external upload。
- 不要联网、外部数据、新repo、新weights。
- 不要把非reference frame与单一reference GT直接算逐帧Dice当成temporal效果。
- 不要把 frozen CineMA anatomy prior 当作 scar model。
- 不要恢复旧 middle-frame single-frame wrapper 作为正式故事。
- 不要让 5 个 mismatch cases 阻塞 59 safe cases。
- 不要覆盖已有 CineMA/nnU-Net/CineMyoPS outputs。

## Variants

### C0: `reference_control_safe`

在 59 safe cases 上建立强 reference-frame control：reference frame + geometry-aware crop + optional frozen CineMA anatomy prior。输出在 reference geometry，报告 class_1 myocardium、class_2 LV、class_3 scar sanity。该 variant 是 temporal retrieval 的基准，不是最终目标。

### C1: `keyframe_context_retrieval`

选择固定关键帧，例如 reference、mid、representative、ES-like 或基于 LV/foreground变化的 frames。非reference帧不直接与GT逐帧比较，而是提取 context/motion-like descriptors 或 anatomy summaries，用 retrieval/attention 调制 reference decoder。必须记录 frame weights、reference dominance、temporal entropy 和 failure cases。

### C2: `anatomy_consistency_temporal`

使用 CineMA 或 reference control 的 anatomy prior，对关键帧引入 temporal consistency / anatomy union / stability regularization，不把 anatomy prior 等同于 scar prediction。目标是减少 myocardium/LV jitter 并改善 reference-frame segmentation。

若时间足够，可将 C1+C2 组合成一个 small temporal package；但不得一开始就把所有机制堆在一起导致不可归因。

## 训练预算和评估

- 每个 formal job 尽量使用 4-7 小时有效预算，单 job 不超过 8 小时。
- 如果只做 preflight/inference 远低于 8 小时，应继续推进 C1/C2，而不是过早停止。
- 必须使用 59 safe cases 的 fold或固定 train/val split；split 和 case list写入结果。
- 必须报告 class_1 myocardium、class_2 LV、class_3 scar sanity 的 Dice、HD、HD95、component count、empty prediction、volume ratio。
- 必须报告 temporal retrieval diagnostics：frame weights、entropy、reference dominance、per-center performance、mismatch repair status。
- 不得把本地 proxy 直接解释为 hosted `myocardium_cinemyops`。

## 结果解释要求

若 temporal retrieval 失败，必须解释是 reference-frame label语义限制、nonreference feature未配准、CineMA anatomy prior不足、key-frame选择差、retrieval collapse、scar head缺失，还是geometry/crop问题。不得只写“temporal无效”。若 reference control 已经是最佳，也要说明是否值得保留 anatomy-first路线。

## 决策门

写 `results/20260626_cine_temporal/decision.md`，状态只能是：

- `GO_CINE_TEMPORAL_NEXT`
- `KEEP_REFERENCE_CONTROL`
- `REVISE_KEYFRAMES`
- `REVISE_GEOMETRY_REPAIR`
- `STOP_CINE_NO_SIGNAL`
- `STOP_PIPELINE_BUG`

`GO_CINE_TEMPORAL_NEXT` 要求 temporal variant 相比 reference control 在 class_1 或 class_2 至少一个本地 proxy 有正信号，另一个不崩溃，且 HD/component 不恶化；class_3 scar仍可作为negative control，但不能作为唯一失败理由，因为当前 anatomy prior没有scar head。

## 预期产出

必须写：

- `results/20260626_cine_temporal/result.md`
- `results/20260626_cine_temporal/MANIFEST.md`
- `results/20260626_cine_temporal/decision.md`
- `results/20260626_cine_temporal/safe_split.md`
- `results/20260626_cine_temporal/metrics_summary.md`
- `results/20260626_cine_temporal/case_metrics.csv`
- `results/20260626_cine_temporal/frame_retrieval.csv`
- `results/20260626_cine_temporal/failure_interpretation.md`
- logs/prediction/metric索引

## 停止条件

- safe subset reference geometry无法复现。
- crop/inverse mapping 不安全。
- one-batch/preflight失败且无法修复。
- 需要网络、外部数据、validation upload 或单 job 超过 8 小时。

## 人工决策点

- 是否继续 Cine temporal route。
- 是否把 mismatch cases 纳入下一轮 repair。
- 是否未来为 Cine 引入 scar-specific head。当前任务不授权 submission。
