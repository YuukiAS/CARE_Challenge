---
task_key: "20260621_srr_ablation"
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
max_parallel_gpu_jobs: 3
requires_result: "results/20260621_srr_fold0/decision.md:GO_ABLATION"
---

# Task 20260621 SRR Ablation

## 目标

在 `20260621_srr_fold0` 明确给出 `GO_ABLATION` 后，以相同 fold0、相同训练预算和相同 evaluator 完成 Result4 正式 MyoPS 方法的关键机制消融，判断收益究竟来自条件监督、模态特异表示、selective retrieval、SIP-inspired shared/private regularization 还是 anatomy prior，从而冻结可进入后续 fold 扩展的最小正式版本。

## 依赖

必须读取：

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/tasks/20260621_srr_ablation.md`
- `docs/notes/deep_research/Result4.pdf`
- `results/20260621_srr_spec/architecture_contract.md`
- `results/20260621_srr_fold0/result.md`
- `results/20260621_srr_fold0/decision.md`
- `results/20260621_srr_fold0/MANIFEST.md`
- Variant A/B checkpoints、metrics、logs 和 usage reports

只有 `decision.md` 为 `GO_ABLATION` 才能执行训练。否则写 result 并停止。

## 允许动作

- 在已验证 first-party SRR code 中新增 config 开关、ablation configs、reporting 和独立 Slurm jobs。
- 最多并行提交三个单 GPU fold0 jobs，每个不超过 8 小时。
- 复用已经完成的 Variant A/B 指标和 checkpoint，但不得重用其 prediction/cache 目录作为新 variant 输出。
- 对 gate、expert、loss 和 anatomy prior 做模块级关闭，不得同时改变 backbone、数据 split、训练预算和 postprocess。
- 写 `results/20260621_srr_ablation/result.md`、`MANIFEST.md` 和最终选择报告。

## 禁止动作

- 不要 folds 1-4、5-fold、validation submission 或外部上传。
- 不要联网、引入新 repo、权重、外部数据、复杂 alignment 或新 backbone。
- 不要为每个 ablation 单独调一套大幅不同的超参数。
- 不要改变 label mapping、evaluator、sampling contract 或 T2-conditioned supervision。
- 不要把只改善 empty-GT cases 的结果作为正信号。

## Ablation matrix

以 fold0 任务已经存在的两个 variant 为锚点：

- `A0 conditional_dualhead_control`
- `A3 srr_full`

新增并训练以下最小消融，命名和 exact module 以 architecture contract 为准。

### `A1 modality_specific_late_fusion`

保留：

- modality-specific encoders；
- separate scar/edema/anatomy heads；
- T2-conditioned edema supervision；
- modality dropout；
- anatomy prior。

删除：

- learned selective retrieval；
- shared/private dictionary selection；
- SIP-inspired regularizer。

使用确定性的 availability-aware late fusion。目的：判断 modality-specific representation 本身是否足够。

### `A2 retrieval_no_sip`

保留：

- shared/private representer dictionary；
- availability + feature-conditioned retrieval；
- pathology-specific heads；
- conditional supervision；
- anatomy prior。

关闭：

- SIP-inspired integrativeness/shared-use regularizer；
- 仅保留最小 anti-collapse/load-balance项。

目的：判断 retrieval gain 是否依赖 selective integration，而不是普通 MoE/gating。

### Optional `A4 srr_no_anatomy`

只有当前三个 GPU slot/时间足够，且 A3 的 anatomy prior 可通过单一 config 开关安全关闭时运行。其他设置与 A3 完全相同。目的：判断 anatomy prior 是否为真实贡献而非冗余。

若 optional job 会拖慢主消融，不运行并在 result 中说明。

## 公平性约束

- 同一 fold、seed、preprocessing、patch、sampler、batch size、optimizer、learning-rate schedule、max-runtime、epoch/iteration cap、validation cadence 和 best-checkpoint rule。
- 每个 job 应充分使用 4-6 小时有效训练预算，并保留导出评估余量；不能用几个 epoch 代替对比。
- 所有 output/cache/checkpoint 路径包含完整 variant 名、fold、seed、checkpoint。
- 不允许针对 validation cases 人工选择超参数。
- 使用 A0/A3 已有结果时，先确认其预算和 evaluator与新任务完全一致；否则公平重跑对应锚点。

## 必须报告

除 primary Dice/HD/HD95 和全部 subgroup/structural diagnostics 外，必须增加：

- retrieval gate entropy；
- shared/private expert usage；
- expert starvation；
- per-pattern integrativeness；
- A2 versus A3 的 representation sharing变化；
- parameter count、peak GPU memory、train throughput、inference time；
- scar/edema tradeoff；
- CenterB/CenterC 差异；
- LGE-only scar fallback；
- no-T2 edema loss audit。

## 最终选择门

写 `results/20260621_srr_ablation/model_selection.md`，最终状态只能是：

- `SELECT_SRR_FULL`
- `SELECT_RETRIEVAL_NO_SIP`
- `SELECT_LATE_FUSION`
- `SELECT_CONDITIONAL_ONLY`
- `NO_MODEL_PASSES`
- `STOP_COMPARABILITY_BUG`

选择正式版本必须满足：

- `myops_scar` 和 `myops_edema` 均不低于最强 baseline-preserving candidate的合理误差范围，至少一个 primary metric有明确正信号；
- T2-present/GT-positive edema真实改善，不依赖 empty-GT；
- LGE-only scar不崩溃；
- HD/HD95、remote components 和 volume ratio不恶化；
- gate/expert使用可解释，无 collapse/starvation；
- 复杂版本若没有稳定收益，必须选择更简单版本，不为叙事保留无效模块。

## 预期产出

必须写：

- `results/20260621_srr_ablation/result.md`
- `results/20260621_srr_ablation/MANIFEST.md`
- `results/20260621_srr_ablation/model_selection.md`
- `results/20260621_srr_ablation/ablation_matrix.csv`
- `results/20260621_srr_ablation/ablation_summary.md`
- `results/20260621_srr_ablation/subgroup_metrics.csv`
- `results/20260621_srr_ablation/retrieval_diagnostics.csv`
- `results/20260621_srr_ablation/efficiency.csv`
- job/checkpoint/prediction/metric/log 索引

result 必须记录每个 job ID、runtime、GPU、epoch/iteration、best checkpoint、stop reason、commands、diff 和下一步是否允许 fold expansion。

## 停止条件

- fold0 decision 不是 `GO_ABLATION`。
- 锚点和新 variants 不可公平比较。
- config 开关实际改变了无关模块或数据路径。
- no-T2 edema loss contract 被破坏。
- 任一 job 需要超过 8 小时或覆盖旧输出。
- 需要 external upload、外部数据或新 repo。

## 人工决策点

- 是否接受选中的最小正式版本。
- 是否允许下一阶段 folds 1-4 扩展。
- 是否另开 alignment ablation，而不是混入本任务。
