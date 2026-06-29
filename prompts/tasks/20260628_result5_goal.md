---
task_key: "20260628_result5_goal"
project: "CARE-Myocardium"
status: "ready"
executor: "Codex-Goal"
mode: "goal"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: true
allow_external_upload: false
requires_human_approval: false
max_single_job_walltime: "08:00:00"
max_parallel_gpu_jobs: 6
allow_subtask_execution: true
---

# Goal 20260628 Result5 Proposal-Refinement Sprint

## 总目标

按照 Result5 的结论，停止把当前 SRR dictionary 当作最终分割器，也停止继续做纯 dictionary 形状小改动。下一轮的目标是把 SRR 降位为第一阶段 evidence engine，在其上建立病种专属 lesion proposal dictionaries、正负原型判别、soft-cascade refinement 和安全负空间学习。MyoPS 是绝对主线；CineMyoPS 同步推进 reference-frame registration/warping，但不得阻塞 MyoPS。

本 goal 目标工作量约一天。每个单 job 仍然不超过八小时，但允许多个子任务和多个并行 jobs 连续推进。Codex 不能因为一个 variant 失败、一个 external resource 安装失败、几个 sample 表现差、一个 metric caveat 或一个短 preflight 就停止整个 goal。失败必须解释其数据机制和模型机制，而不是只写“没有提升”。

## 旧任务处理

`prompts/tasks/20260626_dict_research.md`、`20260626_dict_bank.md`、`20260626_lesion_compact.md`、`20260626_cine_temporal.md` 和 `20260626_next_goal.md` 已经执行并产生 `results/20260626_*` 证据。它们应保留为历史审计，不再作为下一轮执行入口。新的唯一 goal 入口是本文件 `prompts/tasks/20260628_result5_goal.md`。

## 必读材料

必须读取 `AGENTS.md`、`prompts/AGENT_RULES.md`、`prompts/CHATGPT_RULES.md`、本 goal 文件、`docs/notes/deep_research/Result5.pdf` 或等价 Result5 文本、`docs/notes/20260628_result5_plan_review.md`、`results/20260626_next_goal/result.md`、`results/20260626_dict_bank/selection.md`、`results/20260626_dict_bank/failure_interpretation.md`、`results/20260626_lesion_compact/selection.md`、`results/20260626_lesion_compact/failure_interpretation.md`、`results/20260626_cine_temporal/result.md`、`results/20260626_cine_temporal/failure_interpretation.md`、当前 `src/care_myocardium/` 代码和 Dataset501/Dataset502 evaluator。

## Subtask registry

主线任务是 `prompts/tasks/20260628_myops_proposal.md` 和 `prompts/tasks/20260628_myops_refine.md`。Cine 次线任务是 `prompts/tasks/20260628_cine_register.md`。本 goal 自身必须写 `results/20260628_result5_goal/result.md`、`MANIFEST.md`、`progress.md` 和 `final_status.md`。

## 2026-06-29 continuation amendment

新的 continuation prompt 已写入 `prompts/tasks/20260629_result5_continuation_goal.md`。如果启动新的 Codex goal session，应优先使用该文件；如果继续使用当前 Codex session，则本 amendment 作为当前 goal 的附加要求执行。

不要停止或覆盖当前仍在跑的 `20260628_myops_proposal` formal jobs。继续等待并评估 `proposal_pos_neg_basic`、`proposal_anatomy_distance`、`proposal_uncertainty_gate`，并在三者完成后写 proposal aggregate/selection。只有满足 `SELECT_PROPOSAL_ROUTE` 后才进入 formal MyoPS refinement。

同时不要等待 idle。由于当前实现与 Result4/Result5/示意图之间存在明确差距，允许并行执行以下非冲突任务，所有输出必须隔离在 `results/20260629_*`：

1. `prompts/tasks/20260629_loss_decode_calibration.md`：最高优先级，审计 ignore-label loss、raw argmax 解码、binary pathology priority decode、original/proposal/mixed logits、threshold sweep，以及 checkpoint_best vs checkpoint_final。
2. `prompts/tasks/20260629_pathology_checkpoint_selection.md`：用 full-volume scar/edema Dice、HD95、remote FP 和 component burden 审计 checkpoint selection，而不是只用 patch loss。
3. `prompts/tasks/20260629_proposal_memory_hardneg.md`：补 Result5 当前缺失的 hard-negative replay、remote FP mining、safe negative memory/prototype bank。当前 proposal jobs 未完成前只能做 preflight/audit，不得覆盖 formal outputs。
4. `prompts/tasks/20260629_true_soft_roi_refine.md`：实现真正 soft-ROI refinement scaffold、ROI geometry test 和 crop-restore sanity；未达到 `SELECT_PROPOSAL_ROUTE` 前不得启动 formal refinement。
5. `prompts/tasks/20260629_result4_srr_core_rebuild.md`：实现更接近 Result4 的 SRR-v2 preflight，包括 multi-scale、true modality-private features、sparse retrieval 和 SIP-inspired usage regularization；formal run 只有在资源安全且 orchestrator 判定需要时才启动。

协调规则：默认一个 orchestrator 拥有代码写入权。如果它决定开额外 Codex session/subagent，必须给每个 subagent 分配不重叠文件和输出目录。不要新增 git branch，除非 human explicit approval。不要回退到 nnU-Net 作为方法；nnU-Net 只能作为 reference metric。

## Phase 0：安全与结果复核

记录 branch、HEAD、git status、Slurm 队列、上轮 selected dictionary route、上轮 compactness 失败原因、Cine safe/mismatch split。确认不会覆盖 `results/20260625_*` 或 `results/20260626_*`。若并行 worktree 可用，应将 MyoPS proposal、MyoPS refinement 和 Cine registration 隔离；否则以 MyoPS proposal 为最高优先级。

## Phase 1：MyoPS proposal stage

执行 `20260628_myops_proposal`。该任务必须至少完成三个 formal proposal variants：positive/negative prototype proposal、anatomy-distance proposal、uncertainty-gated proposal；资源允许则完成 hard-negative replay preflight。formal jobs 应尽量使用六到七小时有效训练预算，单 job 不超过八小时。只有 label/fold/evaluator/no-T2 supervision 或 proposal sampling 出现硬错误才停止。

如果 `20260628_myops_proposal` 选出 proposal route，则进入 Phase 2。若状态为 `REVISE_PROPOSAL_AND_REPEAT`，但失败原因可在同一任务边界内修复，并且仍有时间和 GPU，可以允许一次修复重跑；否则写 final_status 并停止 MyoPS 主线。不得在 proposal 未选出前进入 refinement。

## Phase 2：MyoPS soft-cascade refinement

执行 `20260628_myops_refine`。该任务必须在 selected proposal route 上至少完成三个 refinement variants：scar 小 ROI refiner、edema 大 ROI refiner、shared anatomy dual refiner；只有前面有正信号时才运行 joint finetune。formal jobs 仍尽量使用六到七小时有效训练预算。它必须评估 full-volume restored predictions，而不是只看 crop 内指标。

Phase 2 的成功不要求达到 validation submission 水平，但必须回答：proposal + refinement 是否真正降低 remote FP、component burden 或 HD95，同时不牺牲 GT-positive Dice。如果没有，必须解释是 proposal recall、ROI 过窄、negative prototype 过强、refiner 容量、inverse mapping 还是 loss 冲突。

## Phase 3：Cine registration/warping 次线

尽早并行执行 `20260628_cine_register`，但不得阻塞 MyoPS。该任务允许联网 clone 或 pip install registration resources，但必须记录 license 与 install 细节。至少尝试 classical registration 与另一个候选，资源允许则尝试 learning-based registration 和 motion descriptor。若 external resource 失败，不得停止；必须至少完成一个 SimpleITK/现有依赖的 classical baseline。Cine 结果只用于决定下一轮是否接 temporal/pathology route，不用于 validation submission。

## 资源策略

每个 job 的 walltime 不超过八小时。formal MyoPS jobs 不得短跑；应设置 `max_steps` 与 `min_effective_seconds`，避免上一轮 compactness 的 under-budget 问题。最多允许六个并行 GPU jobs，但每个 variant 必须有独立 output、cache、checkpoint、prediction、log 和 config。默认 `htzhulab`，fallback 按 AGENTS。若队列造成长等待，继续记录 progress，不要把 pending 当失败。

## 强制解释要求

所有 result 必须先用人类可读语言讲清楚：本阶段原本想解决什么，为什么 Result5 要这么改，实际做了什么，结果说明了什么，是否达到了阶段目标，下一步为什么这样做。内部代号和指标表只能作为证据补充。失败不能只写“无提升”，必须解释失败来自数据机制、proposal recall、负原型、ROI、anatomy prior、registration、loss、sampling、center split、HD/component 形态，还是训练预算。

## 硬性禁止

不要 validation submission、upload-ready package、external upload。不要使用非公开权重、未核查许可资源或需要账号的资源。不要改变 fold split、label mapping、evaluator。不要把 no-T2 cases 当 edema hard negative。不要把 anatomy prior 用作硬删除。不要因为单个 variant 或单个外部资源失败就停止整个 goal。不要重新执行 `20260626_next_goal.md`。

## 最终状态

写 `results/20260628_result5_goal/final_status.md`，状态只能是 `PROPOSAL_REFINE_SELECTED`、`PROPOSAL_SELECTED_REFINE_REVISE`、`PROPOSAL_REVISE_REPEAT`、`PROPOSAL_REVISE_REPEAT_WITH_REPAIRS`、`SRR_CORE_REBUILD_REQUIRED`、`FALLBACK_TO_SRR`、`STOP_PIPELINE_BUG`、`STOP_NO_PROPOSAL_SIGNAL`。同时记录 Cine 状态：`CINE_REGISTRATION_SELECTED`、`CINE_CLASSICAL_BASELINE_ONLY`、`CINE_REVISE_REGISTRATION` 或 `CINE_STOP`。

final_status 必须列出每个 subtask 的 result/selection 路径、所有 job IDs、logs、runtime、GPU、proposal/refinement/Cine registration 结果、未执行事项和下一轮建议。不得自动生成 validation package。

## 人工决策点

是否接受 proposal/refinement route 进入下一轮 fold0 repeat 或 folds1-4。是否允许后续 validation packaging。是否接受某个 Cine registration module 进入 temporal/pathology route。本 goal 不授权 fold expansion 或 validation submission。
