---
task_key: "20260628_myops_refine"
project: "CARE-Myocardium"
status: "ready_with_dependency"
executor: "Codex"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
max_single_job_walltime: "08:00:00"
max_parallel_gpu_jobs: 4
requires_result: "results/20260628_myops_proposal/selection.md:SELECT_PROPOSAL_ROUTE"
---

# Task 20260628 MyoPS Refine

## 目标

在 `20260628_myops_proposal` 选出 proposal route 后，按照 Result5 建议建立 soft-cascade refinement。SRR/proposal 第一阶段只负责证据组织和候选生成，第二阶段在 soft ROI、distance map、anatomy prior 和 uncertainty 条件下分别细化 scar 与 edema。目标是把 proposal 的召回和负空间判别转化成真正低 remote-FP、低 component burden、低 HD95 的 pathology mask，而不是继续在全图 dense head 上加 compactness loss。

## 背景

必须读取 `AGENTS.md`、`prompts/AGENT_RULES.md`、`prompts/tasks/20260628_myops_refine.md`、Result5、`docs/notes/20260628_result5_plan_review.md`、`results/20260628_myops_proposal/result.md`、`results/20260628_myops_proposal/selection.md`、`results/20260628_myops_proposal/proposal_metrics.csv`、`results/20260628_myops_proposal/failure_interpretation.md`、当前 selected proposal checkpoint 和 predictions、Dataset501 fold0 split、evaluator、nnU-Net fold0 reference。

Result5 的核心判断是，compactness 在 proposal 不可靠时只能压缩错误 logit 场。现在 refinement 必须建立在 proposal 之上，对 scar 使用更小、更高分辨率、更强 negative discrimination 的 ROI；对 edema 使用更大、更保留上下文、更重视 T2-positive recall 和 uncertainty 的 ROI。

## 允许动作

允许新增 first-party ROI builder、soft crop/inverse mapping、scar refinement head、edema refinement head、proposal-conditioned dataset/cache、refinement losses、training scripts、evaluation scripts 和 Slurm jobs。允许最多四个并行 GPU jobs，每个不超过八小时，formal jobs 应尽量使用六到七小时有效训练预算。允许使用 proposal predictions 作为训练中间产物，但必须 task-scoped、checkpoint-specific，不能复用 stale cache。

## 禁止动作

不要 validation submission、upload package、external upload、外部数据、新权重或新 repo。不要 hard ROI deletion；ROI 必须 soft/dilated，并保留回原图的逆映射。不要改变 fold split、label mapping 或 evaluator。不要把 no-T2 cases 当作 edema hard negative。不要只跑几个 patch 或几个 epoch 后判定 refinement 无效。不要把 refinement gain 限定为后处理；必须是 trainable 或 training-integrated。

## 设计要求

refinement 输入应包含原始可用模态 crop、proposal gate、anatomy union prior、distance-to-myocardium 或 endo/epi distance map、uncertainty map 和第一阶段 evidence maps。scar refinement 使用相对小 ROI、高分辨率 crop、strong hard-negative 或 prototype condition；edema refinement 使用较大 dilation ROI、T2-present supervision、uncertainty-aware boundary 和 recall guard。

ROI 生成不能硬删远端区域。应记录 proposal threshold、dilation radius、crop size、fallback strategy、empty proposal handling、inverse mapping、是否截断 GT lesion。若 proposal 为空或置信低，应保留 anatomy-based fallback ROI。

## Variants

至少运行三个 formal variants，资源允许则四个。

第一条是 `scar_small_roi_refiner`，重点修 scar：小 ROI、高分辨率、scar hard-negative、Focal-Tversky 或 DiceCE 加 boundary/surface 轻项。它应优先提升 scar Dice、scar HD95、LGE-only scar 和 remote FP。

第二条是 `edema_large_roi_refiner`，重点修 edema：较大 ROI、T2-present supervision、uncertainty-aware boundary、recall guard。它应优先提升 edema GT-positive Dice、CenterB/CenterC 和 T2-present HD95。

第三条是 `dual_refiner_shared_anatomy`，scar 与 edema 分别 refine，但共享 anatomy prior 和 proposal evidence。它测试二者是否能共享结构上下文而不互相牵制。

第四条可选是 `proposal_refine_joint_finetune`，低学习率联合微调第一阶段上层和 refinement heads，但仅在前面至少一条有正信号后运行。不得一开始就把所有模块全开导致不可归因。

## 训练日程

每个 formal job 应记录是否冻结 first-stage SRR/proposal、是否半冻结上层、refinement head 学习率、proposal cache checkpoint、ROI 采样比例、positive/negative crop 比例。建议先冻结第一阶段训练 refinement，再允许短联合微调；如果直接联合训练不稳，应回退冻结策略而不是停止任务。

## 评估

必须报告 full-volume restored predictions 上的 `myops_scar` 和 `myops_edema` Dice、HD、HD95。必须报告 ROI/proposal 指标：GT lesion 是否被 ROI 覆盖、ROI volume ratio、outside-ROI rescued lesion、inverse mapping errors、empty ROI fallback。必须报告 component count、remote FP、small FP、pred/GT volume ratio、scar LGE-only、edema T2-present、CenterB/CenterC。必须与 selected proposal route、selected dictionary route、nnU-Net fold0 reference 对照。

## 结果解释要求

如果 refinement 失败，必须解释是 proposal recall 不够、ROI 过窄、hard negatives 过强、refinement head 容量不足、inverse mapping 错误、Dice/HD 损失冲突、scar/edema mutual interference，还是训练预算不足。不得只写“无提升”。

## 决策门

写 `results/20260628_myops_refine/selection.md`，状态只能是 `SELECT_REFINE_PACKAGE`、`SELECT_PROPOSAL_ONLY`、`REVISE_REFINEMENT_AND_REPEAT`、`STOP_PIPELINE_BUG`、`STOP_NO_REFINEMENT_SIGNAL`。选择 refinement package 要求相比 proposal route 至少一个主 pathology 的 Dice、HD95、remote FP 或 component 有明确正信号，另一个 pathology 不灾难性退化，ROI 覆盖不漏主要 GT lesion，no-T2 contract 正确。

## 预期产出

必须写 `results/20260628_myops_refine/result.md`、`MANIFEST.md`、`selection.md`、`roi_contract.md`、`variant_matrix.md`、`metrics_summary.md`、`subgroup_metrics.csv`、`component_hd_by_case.csv`、`roi_coverage.csv`、`failure_interpretation.md`，并索引 jobs、logs、checkpoints、predictions、configs、proposal caches。

## 停止条件

只有 proposal selection 不满足依赖、ROI/inverse mapping 无法安全实现、label/evaluator/cache 错误、no-T2 edema hard-negative 出现、predictions invalid 或单 job 超过八小时，才停止。单个 variant 失败不能停止其他 variants。

## 人工决策点

是否接受 refinement package 进入下一阶段 fold0 repeat 或 folds1-4。是否允许 validation packaging。本任务不授权 fold expansion 或 validation submission。
