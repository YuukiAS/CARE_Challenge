---
task_key: "20260626_dict_research"
project: "CARE-Myocardium"
status: "ready"
executor: "Codex"
risk_level: "low"
allow_code_change: false
allow_shell_command: true
allow_network: true
allow_external_upload: false
requires_human_approval: false
max_single_job_walltime: "02:00:00"
---

# Task 20260626 Dictionary Research

## 目标

做一次非常有边界的 dictionary / routing / shared-private representation 文献与实现机制检索，服务 CARE MyoPS 下一批 dictionary bank 实验。目标不是泛泛综述，也不是找新大模型，而是把 Result4 的 selective representation retrieval 具体化成若干可在当前 `src/care_myocardium/` 内实现的 dense segmentation dictionary 设计。

## 背景

必须读取：

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/tasks/20260626_dict_research.md`
- `docs/notes/deep_research/Result4.pdf`
- `docs/notes/20260620_r2_deep_research_assessment.md`
- `docs/notes/20260625_srr_recovery_assessment.md`
- `docs/notes/20260626_dictionary_next_batch_strategy.md`
- `results/20260625_fast_goal/result.md`
- `results/20260625_srr_recovery/metrics_summary.md`
- `results/20260625_srr_rescue_ablate/model_selection.md`
- `results/20260625_srr_rescue_ablate/metrics_summary.md`

当前事实：SRR dictionary 已经比 conditional control、late fusion no-dictionary 和 weak-SIP retrieval 更有信号，但绝对 pathology Dice 低，false positives 和 component burden 高。下一步不是证明 dictionary 是否存在价值，而是系统构建和比较多种 dictionary 设计。

## 允许动作

- 联网检索论文、repo、官方实现和开源代码。
- 只做 read-only research，不 clone 大型 repo，不安装复杂依赖，不训练模型。
- 可读取本仓库现有代码与结果，判断哪些设计能接入现有 SRR code。
- 写 `results/20260626_dict_research/result.md`、`MANIFEST.md` 和 `dictionary_design_matrix.md`。

## 禁止动作

- 不要训练、下载外部权重、改代码或启动 Slurm。
- 不要扩展成 foundation model 搜索。
- 不要推荐需要外部训练数据、validation pseudo-label 或长周期重写的方案作为下一批主线。
- 不要只列论文名。每个机制都必须转成 CARE 可执行设计。

## 检索范围

重点查找以下机制，优先 2022 年之后，但经典方法可以保留：

- sparse mixture-of-experts、soft MoE、expert dropout、load balancing、router anti-collapse、top-k/entmax routing；
- shared-private representation learning、multi-task shared/private segmentation、domain-specific adapters；
- prototype dictionary、slot attention、vector-quantized dictionary、learned visual dictionary for segmentation；
- missing-modality medical segmentation，尤其 HeMIS、ModDrop、modality dropout、availability-aware fusion、BraTS missing-modality 方法中可迁移到 CMR 的设计；
- cross-modal interaction dictionary、task-conditioned retrieval、class-specific dictionary；
- anti-false-positive lesion compactness 与 dictionary/prototype 结合的思路。

## 必须回答的问题

请用 CARE 语境回答：

1. dictionary 应放在 encoder bottleneck、多尺度 skip、decoder head、task head，还是 prototype memory？
2. gate 应由 availability vector 决定，还是由 availability + feature summary + task embedding 共同决定？
3. 如何避免 expert collapse，又不强迫所有 expert 均匀使用？
4. 如何让 scar 允许 LGE specialization，同时让 edema 使用 T2-specific 和 shared anatomy/pathology expert？
5. SIP/integrativeness 在 dense segmentation 中可用哪些近似：load balance、entropy floor、coverage、group-lasso、usage diversity、prototype separation、contrastive diversity？
6. 哪些设计可以在当前 `src/care_myocardium/` 中 1-2 天内实现并用 8 小时 job 验证？
7. 哪些看起来漂亮但会引入过重实现或不适合 CARE？

## 输出要求

必须写：

- `results/20260626_dict_research/result.md`
- `results/20260626_dict_research/MANIFEST.md`
- `results/20260626_dict_research/dictionary_design_matrix.md`
- `results/20260626_dict_research/query_log.md`

报告必须给出 5-8 个可执行 dictionary designs，并按优先级排序。每个 design 包含：核心思想、对应文献/实现、CARE 数据适配、需要修改的代码位置、训练风险、预计影响 `myops_scar`/`myops_edema` 哪一部分、失败时如何解释。最后必须明确建议哪些 designs 进入 `20260626_dict_bank`，哪些只作为背景。

## 停止条件

- 网络不可用时，记录失败并基于已有 Result4/R2/CARE 结果给出本地设计矩阵。
- 检索开始偏离 dictionary/routing/shared-private/missing-modality dense prediction 时停止扩大范围。
- 需要下载大模型、外部权重或外部数据时停止并记录，不执行。

## 人工决策点

- 是否接受某个外部机制进入后续代码实现。
- 是否允许未来下载某个外部 repo 或权重。当前任务不授权。
