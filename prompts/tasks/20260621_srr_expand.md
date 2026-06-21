---
task_key: "20260621_srr_expand"
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
requires_result: "results/20260621_srr_ablation/model_selection.md:SELECT_*"
---

# Task 20260621 SRR Expand

## 目标

只有在 `20260621_srr_ablation` 选出通过全部 fold0 gate 的最小正式模型后，使用完全冻结的 config、code revision、seed policy、preprocessing、evaluator 和 checkpoint rule，并行训练 folds 1-4，形成 MyoPS SRR 的 5-fold 本地证据。不得在本任务继续发明模块或按 fold 调参。

## 依赖

必须读取：

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/tasks/20260621_srr_expand.md`
- `results/20260621_srr_ablation/result.md`
- `results/20260621_srr_ablation/model_selection.md`
- `results/20260621_srr_ablation/MANIFEST.md`
- selected config、fold0 checkpoint、metrics、subgroup和retrieval diagnostics
- nnU-Net Dataset501 5-fold reference和protocol split

仅当 model selection 为以下之一时允许执行：

- `SELECT_SRR_FULL`
- `SELECT_RETRIEVAL_NO_SIP`
- `SELECT_LATE_FUSION`
- `SELECT_CONDITIONAL_ONLY`

若为 `NO_MODEL_PASSES` 或 `STOP_COMPARABILITY_BUG`，必须停止。

## 允许动作

- 将选定config冻结并复制到本任务结果目录，记录git commit和hash。
- 最多并行提交folds 1-4四个单GPU jobs，每个不超过8小时；fold0复用已验证checkpoint。
- 运行5-fold统一推理、aggregation、subgroup、HD/component和retrieval diagnostics。
- 修复明确的fold-independent pipeline bug，但修复后必须重跑受影响fold，并记录；不得按fold调参。
- 写task-scoped result、manifest和final local gate。

## 禁止动作

- 不要更换模型模块、loss、sampler、preprocessing或postprocess。
- 不要针对某个fold单独改超参数。
- 不要联网、外部权重、外部数据或新repo。
- 不要validation submission、upload-ready package或外部上传。
- 不要接受只改善一个leaderboard metric的模型。
- 不要用foreground mean替代scar/edema判断。
- 不要复用模糊或stale prediction cache。

## 训练和资源

- folds 1-4可并行，每个job `--time<=08:00:00`，优先`htzhulab`，fallback按AGENTS。
- 每个fold使用与fold0相同的effective training budget、validation cadence、best-checkpoint rule和max-runtime。
- 每个fold独立checkpoint、prediction、metrics、diagnostics和timestamped log。
- 若某个fold因调度或硬件失败，可重提同config job；不得改变模型以适配该fold。

## 必须报告

使用与`results/metrics/nnUNet.md`一致的结构，至少包括：

- Setup；
- label semantics；
- metric paths；
- Fold0-Fold4的`myops_scar` Dice/HD/HD95；
- Fold0-Fold4的`myops_edema` Dice/HD/HD95；
- mean和标准差；
- modality-group/center subgroup；
- GT-positive/T2-present edema；
- scar-positive/LGE-only scar；
- component count、remote FP、volume ratio；
- retrieval usage/collapse，若所选模型包含retrieval；
- efficiency和failure cases。

## 最终门

写 `results/20260621_srr_expand/final_local_gate.md`，状态只能是：

- `LOCAL_GO`
- `LOCAL_GO_WITH_CAVEAT`
- `LOCAL_STOP`
- `RETRAIN_FAILED_FOLDS`
- `STOP_PIPELINE_BUG`

`LOCAL_GO`要求：

- 5-fold mean scar和edema均超过对应nnU-Net本地reference，或在统计和HD/component上形成明确、可解释的综合优势；
- 不能是一项上升、另一项显著下降；
- HD/HD95不系统恶化；
- T2-present/GT-positive edema真实改善；
- LGE-only scar无隐藏collapse；
- 无中心或模态组灾难性失败；
- 所有fold预测、label、cache、checkpoint和export contract有效。

`LOCAL_GO_WITH_CAVEAT`仅用于小幅优势且方差较大，但不得掩盖metric tradeoff。任何是否提交的决策必须另开task，本任务不生成submission。

## 预期产出

必须写：

- `results/20260621_srr_expand/result.md`
- `results/20260621_srr_expand/MANIFEST.md`
- `results/20260621_srr_expand/final_local_gate.md`
- `results/20260621_srr_expand/frozen_config.yaml`
- `results/20260621_srr_expand/fold_metrics.csv`
- `results/20260621_srr_expand/aggregate.md`
- `results/20260621_srr_expand/subgroup_metrics.csv`
- `results/20260621_srr_expand/component_hd_by_case.csv`
- `results/20260621_srr_expand/failure_registry.md`
- checkpoints/predictions/metrics/logs索引

## 停止条件

- ablation未选出合格模型。
- selected config或code revision无法冻结。
- fold0证据不可复现或cache不清楚。
- 任一job需超过8小时且无法按相同budget截断。
- label/evaluator/export contract错误。
- 需要validation upload、外部数据或高风险配置修改。

## 人工决策点

- 是否接受5-fold本地证据。
- 是否另开submission packaging/validation task。
- 是否继续CineMyoPS次线。
