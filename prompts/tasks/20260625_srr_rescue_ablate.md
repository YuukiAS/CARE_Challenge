---
task_key: "20260625_srr_rescue_ablate"
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
requires_result: "results/20260625_srr_recovery/decision.md:GO_*"
---

# Task 20260625 SRR Rescue Ablate

## 目标

在 `20260625_srr_recovery` 产生 `GO_RESCUE_ABLATION` 或 `GO_CONDITIONAL_ABLATION` 后，继续完成不轻易阻塞的 fold0 ablation。目标是在保留上一轮正信号的基础上，判定应推进完整 SRR dictionary、简化 retrieval、modality-specific late fusion，还是 conditional dual-head。不要因为 routing 仍不完美就停止；只有 label/fold/cache/no-T2 supervision 或预测有效性出错才硬停。

## 必读材料

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/tasks/20260625_srr_rescue_ablate.md`
- `docs/notes/deep_research/Result4.pdf`
- `results/20260621_srr_spec/architecture_contract.md`
- `results/20260621_srr_fold0/result.md`
- `results/20260621_srr_fold0/metrics_summary.md`
- `results/20260625_srr_recovery/result.md`
- `results/20260625_srr_recovery/decision.md`
- `results/20260625_srr_recovery/metrics_summary.md`
- `results/20260625_srr_recovery/retrieval_usage.md`

## 允许动作

- 新增/修改 config 开关、ablation wrappers、report scripts和独立Slurm jobs。
- 最多并行4个单GPU fold0 jobs，每个`<=08:00:00`。
- 复用已完成的候选checkpoint作为比较锚点，但新variant必须写入独立路径。
- 在同一fold0、同一evaluator、同一label mapping下比较variants。
- 写 `results/20260625_srr_rescue_ablate/result.md`、`MANIFEST.md`和`model_selection.md`。

## 禁止动作

- 不要folds1-4、5-fold、validation submission、upload package。
- 不要联网、外部数据、新repo、新权重。
- 不要改变fold split、label mapping、evaluator或postprocess制造收益。
- 不要混入alignment、新backbone、Cine模块或外部pretrained模块。
- 不要把foreground mean或empty-GT gain当作成功。
- 不要因单一routing caveat停止整个ablation；要把caveat记录在model selection中。

## Ablation matrix

根据recovery结果选择至少3个、最多5个variants。必须包含：

### B0: `best_conditional_control`

上一轮或recovery中的最佳conditional dualhead/t2-masked control。

### B1: `best_srr_recovered`

recovery中最好的SRR/retrieval variant。

### B2: `late_fusion_no_dictionary`

模态特异encoder + availability-aware late fusion + dualheads + T2-masked edema loss，但关闭shared/private dictionary和learned retrieval。目的：判断dictionary是否真有价值。

### B3: `retrieval_no_sip_or_weak_sip`

保留retrieval gate和dictionary，但关闭或弱化SIP/integrativeness，只保留必要anti-collapse。目的：判断SIP正则是否帮助还是妨碍。

### Optional B4: `srr_no_anatomy_or_containment`

只有时间和资源允许时运行。目的：判断anatomy prior对scar/edema是否有真实贡献。

如果recovery已经完成其中某些等价variant，可复用其结果并补齐report，不必重复训练。

## 训练预算

- 每个新formal job尽量使用6-7小时有效训练预算，总walltime不超过8小时。
- 不允许只跑几个epoch作为最终ablation证据。
- 若某variant明显bug，允许fail fast并修正重跑；必须记录失败。
- 所有variant使用独立checkpoint/prediction/cache/log路径。

## 评估和选择

报告每个variant：

- myops_scar Dice/HD/HD95 all、scar-positive、complete、LGE-only、center groups；
- myops_edema Dice/HD/HD95 all、GT-positive、T2-present、CenterB、CenterC、no-T2 stability；
- component/remote FP/volume ratio；
- retrieval usage、entropy、max weight、coverage、expert starvation；
- training loss curves、best step、runtime、GPU。

最终写 `results/20260625_srr_rescue_ablate/model_selection.md`，状态只能是：

- `SELECT_SRR_RECOVERED`
- `SELECT_RETRIEVAL_SIMPLE`
- `SELECT_LATE_FUSION`
- `SELECT_CONDITIONAL_ONLY`
- `REVISE_AND_REPEAT`
- `NO_MODEL_PASSES`
- `STOP_PIPELINE_BUG`

选择规则：

- 不要求routing完美才选择SRR；只要SRR相对简化模型有真实metric/HD/subgroup收益，且routing可解释、不破坏no-T2 contract，即可选择SRR并记录caveat。
- 如果conditional模型明显更稳，选择conditional，不为故事强留dictionary。
- 如果所有模型绝对指标远低但SRR相对有正信号，选择`REVISE_AND_REPEAT`并明确下一步预算和修正，而不是直接stop。
- 只有所有模型无正信号且无可修实现问题时，选择`NO_MODEL_PASSES`。

## 预期产出

必须写：

- `results/20260625_srr_rescue_ablate/result.md`
- `results/20260625_srr_rescue_ablate/MANIFEST.md`
- `results/20260625_srr_rescue_ablate/model_selection.md`
- `results/20260625_srr_rescue_ablate/ablation_matrix.csv`
- `results/20260625_srr_rescue_ablate/metrics_summary.md`
- `results/20260625_srr_rescue_ablate/subgroup_metrics.csv`
- `results/20260625_srr_rescue_ablate/retrieval_diagnostics.csv`
- `results/20260625_srr_rescue_ablate/efficiency.csv`

## 停止条件

- recovery decision不是GO类。
- label/evaluator/fold/cache错误。
- no-T2 edema hard negative再次出现。
- predictions invalid且无法修复。
- 需要外部数据、网络、validation upload、或单job超过8小时。

## 人工决策点

- 是否接受模型选择。
- 是否允许下一步fold expansion。
- 是否回到Result4重新设计。
