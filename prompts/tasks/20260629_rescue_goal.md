---
task_key: "20260629_rescue_goal"
project: "CARE-Myocardium"
status: "ready"
executor: "Codex-Goal"
mode: "goal"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: true
allow_external_upload: false
requires_human_approval: false
max_single_job_walltime: "08:00:00"
max_parallel_gpu_jobs: 6
allow_subtask_execution: true
---

# Goal 20260629 High-Capacity SRR Rescue Sprint

## 总目标

确认前后两批任务已经给出共同结论：SRR/Result5 的思想没有被否定，但当前轻量实现远低于 nnU-Net baseline。下一轮不能继续在 shallow SRRMyoPSLite 上小修小补。目标是在不改变 fold/evaluator/no-T2 contract、不做 validation upload 的前提下，同时推进三条互补路线：修复当前 proposal 管线并重跑、实现真正 multi-scale U-Net-like SRR-v2、建立 nnU-Net anchored cascade teacher route。MyoPS 是绝对主线；CineMyoPS 作为次线同步推进，但不能再停留在 translation 或未配准 keyframe context，必须补做 motion alignment / deformable registration 与 motion descriptor。

每个单 job 仍然不超过八小时，但本 goal 允许多个子任务和最多六个并行 jobs 连续推进。Codex 不得因为一个 variant 失败、一个外部资源安装失败、一个 metric caveat、几个 sample表现差就停止整个 goal。失败必须解释是架构容量、训练/解码、proposal、负样本、teacher artifact、数据机制还是实现 bug。

## 必读材料

必须读取 `AGENTS.md`、`prompts/AGENT_RULES.md`、`prompts/CHATGPT_RULES.md`、本 goal 文件、`docs/notes/20260629_srr_capacity_and_result5_audit.md`、`docs/notes/20260629_result5_gap_audit.md`、`docs/notes/deep_research/Result5.pdf` 或等价文本、`results/20260626_dict_bank/selection.md`、`results/20260626_lesion_compact/selection.md`、`results/20260628_myops_proposal/selection.md`、`results/20260628_result5_goal/final_status.md`、`results/20260629_loss_decode_calibration/selection.md`、`results/20260629_pathology_checkpoint_selection/selection.md`、`results/20260629_proposal_memory_hardneg/selection.md`、`results/20260629_result4_srr_core_rebuild/selection.md`、`src/care_myocardium/models/srr_myops.py`、`src/care_myocardium/models/srr_blocks.py`、`scripts/training/run_srr_myops_fold0.py`。

## Subtask registry

主线任务：`prompts/tasks/20260629_repaired_proposal_repeat.md`、`prompts/tasks/20260629_srr_v2_unet_core.md`、`prompts/tasks/20260629_cascade_teacher_route.md`。

Cine 次线任务：`prompts/tasks/20260629_cine_motion_alignment.md`、`prompts/tasks/20260629_cine_motion_pathology.md`。先执行 motion alignment；若 alignment 选出可用路线或仅选 motion descriptor，则把结果传给 motion pathology。若无法完成 alignment，但 first-party motion descriptor 可用，也不得阻塞 MyoPS。

本 goal 自身必须写 `results/20260629_rescue_goal/result.md`、`MANIFEST.md`、`progress.md` 和 `final_status.md`。

## 执行顺序

Phase 0 是安全与容量审计。记录 branch、HEAD、git status、available disk/quota、GPU队列、已存在的 Result5 outputs、nnU-Net reference artifacts、hard-negative mined components、current SRR code diff。确认新结果不会覆盖 `results/20260626_*`、`results/20260628_*`、`results/20260629_*` 已有审计结果。

Phase 1 同时启动两件事。第一，执行 `20260629_repaired_proposal_repeat`，用修复后的 loss/decode/checkpoint/hardneg replay 重跑 proposal，验证当前弱信号是否被管线问题压低。第二，执行 `20260629_srr_v2_unet_core` 的 architecture/test/preflight，并在通过后尽快启动 formal jobs。两者可以并行，因为一个验证管线修复，一个验证架构容量。

Phase 2 根据 Phase 1 结果决定强备胎。若 repaired proposal 或 SRR-v2 任一出现接近 nnU-Net 或明显高于旧SRR的正信号，继续该路线并记录。若二者仍远低于 nnU-Net，必须执行 `20260629_cascade_teacher_route`，用 nnU-Net/anatomy coarse prior 作为强空间先验，让 SRR承担 pathology-specific refinement，而不是继续让弱SRR单独替代 nnU-Net。

Phase 3 同步推进 Cine 次线。先执行 `20260629_cine_motion_alignment`，不要把上一轮 translation 结果当作充分配准探索；至少尝试 nonrigid/deformable 或 first-party motion descriptor。随后执行 `20260629_cine_motion_pathology`，但不得阻塞 MyoPS。若网络/安装失败，保留 first-party frame-difference motion descriptor fallback。Cine结果只用于下一轮判断，不做 validation upload。

## 资源策略

每个训练 job `<=08:00:00`。formal jobs 应尽量使用六到七小时有效训练预算，不得只跑几个 epoch。最多六个并行 GPU jobs，必须输出隔离。默认 `htzhulab`，fallback 按 AGENTS。若磁盘/配额不足，应先清理 task-scoped scratch 或避免提交大型 artifacts，不得删除旧summary/manifest/metrics。

## 成功标准

不要把“相对旧SRR涨一点”当成成功。以 nnU-Net reference 为硬参照。MyoPS路线至少要回答：是否有任何 route 能在 scar all、edema GT-positive、HD95、remote FP、component burden 或 no-T2 stability 上逼近或超过 nnU-Net；若不能，问题是架构容量、teacher/ROI、训练预算、损失/解码，还是SRR方向本身不适合当前冲刺。Cine路线至少要回答：motion alignment 或 motion descriptor 是否比 reference-only control 提供正信号。

## 强制解释要求

所有 result 必须先用人能读懂的故事解释：本阶段为什么做，实际改了什么，结果说明什么，是否达到阶段目标，下一步为什么这样做。内部代号和表格只能作为证据补充。失败不能只写“低于 baseline”，必须解释机制。

## 硬性禁止

不要 validation submission、upload-ready package、external upload。不要改 fold split、label mapping、evaluator。不要把 no-T2 myocardium 当 edema hard negative。不要把 anatomy prior 当 hard deletion。不要覆盖旧outputs。不要在没有证据时继续扩 folds。不要因为一个 variant 失败停止整个 goal。

## 最终状态

写 `results/20260629_rescue_goal/final_status.md`，状态只能是 `REPAIRED_PROPOSAL_SELECTED`、`SRR_V2_SELECTED`、`CASCADE_TEACHER_SELECTED`、`MULTI_ROUTE_REVISE_REPEAT`、`STOP_PIPELINE_BUG`、`STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL`。同时记录 Cine 状态：`CINE_MOTION_ALIGNMENT_SELECTED`、`CINE_MOTION_DESCRIPTOR_SELECTED`、`CINE_REFERENCE_ONLY`、`CINE_REVISE` 或 `CINE_STOP`。

final_status 必须列出每个 subtask result/selection 路径、job IDs、logs、runtime、GPU、selected route、与 nnU-Net reference 的差距、未执行事项、下一轮建议。不得自动生成 validation package。

## 人工决策点

是否接受 selected route 进入 fold0 repeat 或 folds1-4；是否允许 validation packaging；是否把 cascade teacher route 升为主线；是否继续 Cine motion/pathology route。本 goal 不授权 fold expansion 或 validation submission。
