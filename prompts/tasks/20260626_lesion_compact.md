---
task_key: "20260626_lesion_compact"
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
requires_result: "results/20260626_dict_bank/selection.md:SELECT_*"
---

# Task 20260626 Lesion Compactness

## 目标

在 `20260626_dict_bank` 选出最有希望的 dictionary route 后，不再泛泛修小 loss，而是在该 route 上系统构建一个 lesion localization / compactness package，集中解决当前 SRR 的核心短板：scar 和 edema 预测太散、远端 false positives 太多、component burden 高、HD/HD95 高、scar LGE fallback 不够稳、CenterC edema 定位差。该任务仍以 MyoPS 为主，并要求多个充分训练的 fold0 variants，不允许几个 epoch 后草率判定。

## 背景

必须读取：

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/tasks/20260626_lesion_compact.md`
- `docs/notes/deep_research/Result4.pdf`
- `docs/notes/20260626_dictionary_next_batch_strategy.md`
- `results/20260626_dict_bank/result.md`
- `results/20260626_dict_bank/selection.md`
- `results/20260626_dict_bank/metrics_summary.md`
- `results/20260626_dict_bank/component_hd_by_case.csv`
- `results/20260626_dict_bank/failure_interpretation.md`
- `results/20260625_srr_rescue_ablate/model_selection.md`
- nnU-Net fold0/five-fold reference metrics
- `src/care_myocardium/` selected dictionary code

当前问题不是 dictionary 是否有价值，而是 selected dictionary route 的病灶预测质量仍低。必须把 Dice、HD95、component count、remote FP、volume ratio、scar/edema subgroup 一起看。

## 允许动作

- 在 selected dictionary route 上新增或配置 lesion compactness、anatomy containment、remote-FP penalty、scar/LGE fallback strengthening、T2-positive edema balance、center-aware sampling/reporting。
- 最多提交 4 个并行 GPU jobs，每个 `<=08:00:00`。
- 每个 formal job 必须尽量使用 6-7 小时有效训练预算。
- 可新增 loss、sampler、diagnostic、config、reporting 和 job wrappers，但不得改变 fold/evaluator/label mapping。
- 写 `results/20260626_lesion_compact/result.md`、`MANIFEST.md`、`selection.md`。

## 禁止动作

- 不要 validation submission、upload package、external upload。
- 不要联网、外部数据、新repo、新weights。
- 不要把 postprocess-only cleanup 作为主线；可以有 inference-time diagnostic，但正式 variants 必须是 trainable 或 training-integrated。
- 不要用 hard anatomy deletion 直接删掉病灶；anatomy prior 应该是 soft constraint，除非作为单独诊断输出。
- 不要只看 all-case edema，因为 no-T2 empty-GT 会虚高。
- 不要把一个中心或一个 empty-GT group 的改善当作整体成功。

## Variants

至少运行以下 4 条路线中的 3 条；资源允许则全部运行。每条路线都必须基于 `20260626_dict_bank` 的 selected route 或 base SRR route，保持 dictionary 主体不变。

### L1: `soft_anatomy_containment`

目标：减少远离心肌区域的 scar/edema false positives，但不硬删真实病灶。实现方式可以是 myocardium/anatomy probability soft prior、distance-to-myocardium penalty、outside-myocardium confidence penalty、anatomy-aware decoder attention。必须报告真实病灶是否被过度压制。

### L2: `component_compactness_loss`

目标：减少碎片化和远端小岛。可以使用 differentiable connectedness proxy、soft size/volume regularizer、boundary/HD surrogate、distance-transform compactness、remote-component penalty 的轻量实现。不得只依赖后处理删除小岛。

### L3: `scar_lge_fallback_boost`

目标：修 scar 极低 Dice 和 LGE-only collapse。强化 LGE-driven scar route、scar-positive sampling、scar class weighting、LGE-only scar auxiliary head 或 scar one-vs-rest auxiliary objective。必须确保 edema 不被 scar route 干扰。

### L4: `edema_t2_center_balance`

目标：修 T2-present edema 尤其 CenterC 差的问题。可用 complete-case oversampling、CenterB/CenterC balanced sampling、T2 robust intensity normalization、edema boundary loss、T2-specific auxiliary head。no-T2 cases 继续不能当 class-4 hard negative。

### Optional L5: `joint_compact_package`

只有 L1-L4 中至少两个机制独立产生正信号后，才允许组合最好的两个机制跑一个 joint package。不得一开始就把所有机制堆在一起。

## 训练与评估要求

- 每个 formal variant 使用 6-7 小时有效训练预算，单 job 不超过 8 小时。
- 每个 variant 必须有独立 output/cache/checkpoint/prediction/log。
- 必须与 selected dictionary route、conditional control、nnU-Net fold0 reference 对照。
- 必须报告 myops_scar 和 myops_edema 的 Dice、HD、HD95，而不是 foreground mean。
- 必须分层报告：edema GT-positive、T2-present/complete、CenterB、CenterC、no-T2 stability；scar all、scar-positive、LGE-only、complete、center groups。
- 必须报告 component count、small FP、remote FP、volume ratio、bbox distance、empty prediction。
- 必须保留 dictionary usage 诊断，确认 compactness package 没让 dictionary collapse。

## 结果解释要求

如果某路线失败，必须解释失败机理：是 anatomy prior 误删病灶、compactness 造成过度收缩、scar boost 伤害 edema、center balancing 导致 scar collapse、loss 权重不稳定、dictionary usage改变、还是训练预算不足。不得只写“没有提升”。

## 决策门

写 `results/20260626_lesion_compact/selection.md`，状态只能是：

- `SELECT_COMPACT_PACKAGE`
- `SELECT_SCAR_ROUTE_FIX`
- `SELECT_EDEMA_ROUTE_FIX`
- `SELECT_BASE_DICTIONARY`
- `REVISE_COMPACTNESS_AND_REPEAT`
- `STOP_PIPELINE_BUG`
- `STOP_NO_LOCALIZATION_SIGNAL`

选择进入下一阶段至少要求：

- 相比 selected dictionary route，至少一个主问题有正信号：scar Dice、edema GT-positive Dice、HD95、component/remote FP；
- 另一个 pathology 不出现灾难性退化；
- dictionary usage 不发生不可解释 collapse；
- no-T2 contract 正确；
- gain 不是 empty-GT artifact。

如果所有 compactness 机制都失败，但 dictionary route 仍是最强，选择 `SELECT_BASE_DICTIONARY` 并解释下一步是否应扩 folds 或返回 architecture。

## 预期产出

必须写：

- `results/20260626_lesion_compact/result.md`
- `results/20260626_lesion_compact/MANIFEST.md`
- `results/20260626_lesion_compact/selection.md`
- `results/20260626_lesion_compact/variant_matrix.md`
- `results/20260626_lesion_compact/metrics_summary.md`
- `results/20260626_lesion_compact/subgroup_metrics.csv`
- `results/20260626_lesion_compact/component_hd_by_case.csv`
- `results/20260626_lesion_compact/dictionary_usage.csv`
- `results/20260626_lesion_compact/failure_interpretation.md`

## 停止条件

- dict bank 没有选出可继续 route。
- label/fold/evaluator/cache 错误。
- no-T2 edema hard-negative 出现。
- predictions invalid 且无法修复。
- 需要外部数据、网络、validation upload 或单 job 超过 8 小时。

## 人工决策点

- 是否接受 compactness package 进入 fold expansion。
- 是否允许下一阶段 folds1-4。
- 是否允许 validation packaging。当前任务不授权。
