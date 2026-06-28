---
task_key: "20260628_myops_proposal"
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
max_parallel_gpu_jobs: 4
---

# Task 20260628 MyoPS Proposal

## 目标

按照 Result5 的结论，把当前 SRR dictionary 从最终 dense segmentation head 降位为第一阶段 evidence engine，并实现病种专属 lesion proposal dictionaries。任务目标不是再比较 dictionary 形状，而是让 SRR 输出 anatomy prior、scar evidence、edema evidence、uncertainty 和 scar/edema proposal gate，为后续 soft-cascade refinement 提供可靠候选区域。MyoPS 是主线，必须围绕 `myops_scar` 和 `myops_edema` 评估，不允许用 foreground mean 或 anatomy mean 替代。

## 背景

必须读取 `AGENTS.md`、`prompts/AGENT_RULES.md`、`prompts/tasks/20260628_myops_proposal.md`、`docs/notes/deep_research/Result5.pdf` 或仓库中等价的 Result5 文本、`docs/notes/20260628_result5_plan_review.md`、`results/20260626_dict_bank/selection.md`、`results/20260626_dict_bank/failure_interpretation.md`、`results/20260626_lesion_compact/selection.md`、`results/20260626_lesion_compact/failure_interpretation.md`、`results/20260625_srr_rescue_ablate/model_selection.md`、当前 `src/care_myocardium/` SRR 代码、Dataset501 fold0 split、label mapping、nnU-Net fold0 reference 和 evaluator。

当前事实是，cross-modal interaction dictionary 是上一轮相对最平衡的 dictionary route，但它仍然只是 evidence selection，并没有形成可靠 lesion proposal。soft anatomy containment、component compactness、scar LGE fallback 和 edema center balance 都没有形成可选 package。Result5 判断，下一步应建立 shared evidence trunk + pathology-specific proposal dictionaries，并显式加入 anatomy structure 与 negative-space discrimination。

## 允许动作

允许修改 first-party `src/care_myocardium/` 模型、loss、dataset、sampler、training script、evaluation script 和独立 Slurm jobs。允许基于当前 selected SRR route 增加 anatomy union prior、distance maps、positive/negative prototype dictionaries、proposal logits、uncertainty map、safe negative sampler 和 proposal-level diagnostics。允许最多四个并行 GPU jobs，每个 job walltime 不超过八小时，formal jobs 应尽量使用六到七小时有效训练预算。允许生成 task-scoped checkpoints、predictions、metrics 和 logs，但必须保持输出隔离。

## 禁止动作

不要 validation submission、upload package、external upload、外部数据、新权重或新 repo。不要改变 fold split、label mapping、evaluator 或 submission semantics。不要把 no-T2 cases 当作 edema hard negative。不要用 hard myocardium deletion 直接裁掉病灶；anatomy 必须先作为 soft prior、distance map、proposal gate 或 refinement condition。不要只跑几个 case 或几个 epoch 后下结论。不要继续把 SRR dense head 的小改动当作主线。

## 设计要求

本任务应实现一个第一阶段 proposal 系统。SRR evidence trunk 至少输出 anatomy union prior、scar evidence map、edema evidence map 和 uncertainty map。scar proposal dictionary 与 edema proposal dictionary 应分开维护。scar proposal 主要从 LGE-driven positive prototypes 和 remote/artifact/normal negative prototypes 中判别；edema proposal 主要从 T2-driven positive prototypes 和 safe negatives 中判别。no-T2 myocardium 不能进入 edema hard-negative pool。

proposal logit 应体现 Result5 的思想：病灶不仅要像正原型，还要不像负原型，并且应处在合理 anatomy neighborhood 中。可以采用相似度差、remote distance penalty、anatomy soft prior 和 evidence map 共同构造 proposal gate。数学形式不必完全照抄 Result5，但必须在 `architecture_note.md` 中说明每一项对应什么数据机制，尤其是 scar 的 LGE 小病灶与 edema 的 T2 条件监督。

## Variants

至少运行三个 formal variants，资源允许则四个。每个 variant 都以相同 fold0、相同 evaluator、相同 no-T2 contract 比较。

第一条是 `proposal_pos_neg_basic`，实现 scar/edema 正负 prototype proposal，但不使用 hard-negative replay，只使用当前 batch 的安全正负采样。它用于验证 positive/negative prototype proposal 是否能提高 lesion recall 或降低 remote FP。

第二条是 `proposal_anatomy_distance`，在第一条基础上显式加入 anatomy union prior、distance-to-myocardium-neighborhood penalty 和 soft ROI confidence。它用于验证 anatomy 结构是否真正减少远端假阳性，而不是只作为另一个 segmentation 输出。

第三条是 `proposal_uncertainty_gate`，加入 uncertainty map，对高不确定区域降低 proposal gate 的过度置信，并在低不确定 T2-present edema 区域启用 scar-edema soft relation。它用于避免硬 containment 误删真实病灶。

第四条可选为 `proposal_hard_negative_replay_preflight`，从前一轮预测或本轮早期预测中挖 remote false-positive components，构造 scar 安全 hard negatives 和 edema 安全 hard negatives。该 variant 若实现成本过高，可以只完成 replay buffer 与一次较短 formal run，但不能影响前三条运行。

## 训练预算

每个正式 job 仍然不超过八小时，但必须尽量用满六到七小时有效训练预算。必须修正上一轮 compactness 中 `max_steps` 过早截断的问题，确保 `max_steps` 不会早于 `min_effective_seconds` 停止。one-batch、tiny-overfit 和 proposal sampling sanity 只是 gate，不是正式结果。

## 评估

必须报告 `myops_scar` 和 `myops_edema` 的 Dice、HD、HD95，并分层报告 edema GT-positive、T2-present/complete、CenterB、CenterC、no-T2 stability；scar all、scar-positive、LGE-only、complete、center groups。必须报告 proposal recall、proposal precision、心肌外 FP 比例、remote FP、component count、small FP、pred/GT volume ratio、empty prediction、prototype usage、negative prototype usage、uncertainty calibration 和 dictionary usage。

评估时必须和上一轮 selected dictionary route、best recovered SRR、nnU-Net fold0 reference 对照。不能只因为 Dice 小幅改善就选择；必须看 proposal 是否真正减少 remote FP 或提高 GT-positive recall。

## 决策门

写 `results/20260628_myops_proposal/selection.md`，状态只能是 `SELECT_PROPOSAL_ROUTE`、`REVISE_PROPOSAL_AND_REPEAT`、`FALLBACK_TO_SELECTED_SRR`、`STOP_PIPELINE_BUG`、`STOP_NO_PROPOSAL_SIGNAL`。选择 proposal route 的最低条件是：相比 selected dictionary route，至少一个主问题有明确正信号，例如 GT-positive edema recall、scar Dice、HD95、remote FP 或 component burden；另一个 pathology 不灾难性退化；no-T2 contract 正确；proposal 指标显示它不是空预测或全图撒点。

## 预期产出

必须写 `results/20260628_myops_proposal/result.md`、`MANIFEST.md`、`selection.md`、`architecture_note.md`、`variant_matrix.md`、`metrics_summary.md`、`subgroup_metrics.csv`、`component_hd_by_case.csv`、`proposal_metrics.csv`、`prototype_usage.csv`、`failure_interpretation.md`，并索引所有 jobs、logs、checkpoints、predictions 和 configs。

## 停止条件

只有 label/fold/evaluator/cache contract 错误、no-T2 edema hard-negative 出现且无法修复、proposal sampling 无法构造、predictions invalid 且无法修复、需要外部数据或单 job 超过八小时，才停止。单个 variant 失败不能停止整个任务。

## 人工决策点

是否接受 selected proposal route 进入 soft-cascade refinement。是否允许未来 fold expansion 或 validation packaging。本任务不授权 fold expansion 和 validation submission。
