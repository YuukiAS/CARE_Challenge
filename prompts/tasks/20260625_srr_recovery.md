---
task_key: "20260625_srr_recovery"
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
max_parallel_gpu_jobs: 3
---

# Task 20260625 SRR Recovery

## 目标

在上一轮 `20260621_srr_fold0` 已显示 SRR 正信号但 router collapse 的基础上，修正 Result4 SRR-MyoPS 的 routing / dictionary usage / anti-collapse training，并重跑 fold0 revised variants。目标不是重做规格，也不是轻易停止，而是在保持 label/fold/cache/no-T2 supervision 正确的前提下，尽最大努力把 shared/private dictionary 训练成可解释、可用、非退化的 dense segmentation 模块。

## 背景

必须读取：

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/tasks/20260625_srr_recovery.md`
- `docs/notes/deep_research/Result4.pdf`
- `docs/notes/20260620_r2_deep_research_assessment.md`
- `docs/notes/20260625_srr_recovery_assessment.md`
- `results/20260621_srr_spec/result.md`
- `results/20260621_srr_spec/architecture_contract.md`
- `results/20260621_srr_spec/architecture_contract.yaml`
- `results/20260621_srr_fold0/result.md`
- `results/20260621_srr_fold0/decision.md`
- `results/20260621_srr_fold0/metrics_summary.md`
- `results/20260621_srr_fold0/retrieval_usage.md`
- `results/20260621_srr_fold0/subgroup_metrics.csv`
- `src/care_myocardium/` SRR code
- nnU-Net Dataset501 fold0 reference metrics and evaluator

上一轮事实：`srr_minimal` 相对 `conditional_dualhead_control` 有正信号：edema GT-positive Dice `+0.0323`，scar all-case Dice `+0.0250`，edema GT-positive HD95 `-15.4582`。但 routing caveat 为 row-level expert weight `1.0000`，scar expert1 mean `0.9431`，旧 goal 因此停在 `REVISE_ROUTING`。本任务应把 collapse 视为可修问题，而不是方法失败。

## 允许动作

- 修改 `src/care_myocardium/models/srr_blocks.py`、`srr_myops.py`、`srr_losses.py`、training config、reporting和job wrapper。
- 增加 router temperature、temperature annealing、entropy floor、coverage/load-balance loss、expert dropout、task-specific anti-collapse、top-k/softmax/entmax-like fallback、warmup schedule、gate clipping或其他轻量 anti-collapse 机制。
- 在不改变 fold/evaluator/label mapping 的前提下调整训练预算、loss权重、sampling和checkpoint cadence。
- 提交最多三个并行 fold0 GPU jobs，每个 `<=08:00:00`，优先 `htzhulab`，fallback按AGENTS。
- 运行 one-batch、tiny-overfit、full fold0 revised variants，并导出 predictions/metrics/usage reports。
- 写 `results/20260625_srr_recovery/result.md`、`MANIFEST.md` 和 `decision.md`。

## 禁止动作

- 不要 validation submission、upload-ready package 或 external upload。
- 不要联网、外部数据、新repo、新权重。
- 不要修改 `third_party/` baseline 主路径。
- 不要改变 fold split、compact/raw label mapping、evaluator 或用 foreground mean 决策。
- 不要把 no-T2 cases 当作 edema hard negative。
- 不要通过 postprocess 或清空病灶伪造 metric gain。
- 不要因为单一 routing collapse 就停止，只要 label/fold/cache/supervision 仍正确，必须尝试至少两个修正 variant。

## 必须先做的诊断

读取上一轮 artifacts 后，生成：

- `results/20260625_srr_recovery/root_cause.md`

至少回答：

1. gate collapse 是由 temperature 太低、SIP/entropy权重太弱、coverage定义错误、expert初始化、loss imbalance、sampling imbalance，还是reporting口径造成？
2. scar collapse 到 expert1 是否可能是合理的 LGE-dominant specialization，还是过度 one-hot？
3. edema 使用三个专家是否相对健康？
4. all-case edema 高是否主要来自 no-T2 empty-GT stability？
5. scar 绝对 Dice 很低的首要原因是训练不足、loss imbalance、label mapping、prediction empty/overgrowth、还是模型容量/patch问题？

## Revised variants

必须至少运行以下两个 revised variants；若资源允许可运行第三个。

### R1: `srr_soft_entropy`

目标：降低one-hot collapse但保留SRR。建议改动：

- router temperature > 1 或 warmup后退火；
- entropy floor或negative entropy regularization；
- coverage/load-balance loss；
- expert usage logging per task/modality group；
- 不强制完全均匀，允许scar偏向LGE expert但禁止单expert长期>0.90。

### R2: `srr_expert_dropout`

目标：防止固定expert独占。建议改动：

- training-time expert dropout或drop-path，只对有效experts生效；
- fallback deterministic availability fusion保持可用；
- 对scar/edema/anatomy分别记录dropout后usage；
- 不在inference时随机drop。

### Optional R3: `srr_task_tempered`

目标：允许scar的LGE specialization，但约束edema/anatomy更均衡。建议改动：

- task-specific temperature或regularizer；
- scar允许较低entropy但不得完全one-hot；
- edema要求覆盖T2/private/shared专家；
- anatomy鼓励shared expert。

如果上述机制已有实现，重点调参和重跑；若没有，新增最小实现。

## 训练预算

- 每个formal job walltime最多8小时。
- 不要只跑短wiring。one-batch/tiny-overfit通过后，formal jobs应尽量使用6-7小时有效训练预算，并保留导出评估余量。
- 允许并行最多3个GPU jobs。
- 如果一个variant早期明显bug，可fail fast并重提同variant修正job；但必须在result记录。
- 每个variant输出路径必须包含task key、variant、fold、checkpoint/config，不得覆盖旧`20260621_srr_fold0`结果。

## 评估

必须复用同一fold0 evaluator，并与上一轮 `conditional_dualhead_control` 和 `srr_minimal` 对照。

报告：

- `myops_scar` Dice/HD/HD95 all cases、scar-positive、complete、LGE-only、center groups；
- `myops_edema` Dice/HD/HD95 all cases、GT-positive、T2-present/complete、CenterB、CenterC、no-T2 empty-GT stability；
- component count、remote FP、volume ratio、empty prediction；
- gate entropy、max expert weight、mean usage、per-task usage、per-modality-pattern usage、coverage、integrativeness proxy、expert starvation；
- class4/class5 loss curves和best checkpoint step；
- runtime、GPU、memory、throughput。

## 决策门

写 `results/20260625_srr_recovery/decision.md`，状态只能是：

- `GO_RESCUE_ABLATION`
- `GO_CONDITIONAL_ABLATION`
- `REVISE_TRAINING_BUDGET`
- `REVISE_LOSS_BALANCE`
- `STOP_PIPELINE_BUG`
- `STOP_SRR_NO_SIGNAL`

选择 `GO_RESCUE_ABLATION` 的条件不要过度苛刻：

- 至少一个 revised SRR variant 相比上一轮 `srr_minimal` 或 conditional control 在 GT-positive/T2-present edema 或 scar all-case 上有非退化正信号；
- HD95/remote components不出现不可解释大恶化；
- no-T2 supervision contract正确；
- routing虽然不必完美，但max expert weight、entropy或coverage至少有可解释改善，或能证明scar specialization合理且edema/anatomy不collapse；
- predictions/cache/evaluator有效。

如果 SRR routing仍不理想但conditional/t2-masked双头稳定优于旧baseline，选择 `GO_CONDITIONAL_ABLATION`，继续保留更简单模型，不要停止整个MyoPS主线。

只有当所有revised variants都无正信号且没有可修pipeline解释时，才选择`STOP_SRR_NO_SIGNAL`。

## 预期产出

必须写：

- `results/20260625_srr_recovery/result.md`
- `results/20260625_srr_recovery/MANIFEST.md`
- `results/20260625_srr_recovery/decision.md`
- `results/20260625_srr_recovery/root_cause.md`
- `results/20260625_srr_recovery/metrics_summary.md`
- `results/20260625_srr_recovery/subgroup_metrics.csv`
- `results/20260625_srr_recovery/retrieval_usage.csv`
- `results/20260625_srr_recovery/retrieval_usage.md`
- `results/20260625_srr_recovery/loss_curves.csv`
- checkpoint/prediction/metric/log索引

result 必须列出job IDs、commands、logs、runtime、GPU、best checkpoint、diff和下一步建议。

## 停止条件

- label/fold/evaluator/cache contract错误。
- no-T2 edema supervision错误。
- predictions invalid或大量empty且不能修复。
- 需要外部数据、网络、validation upload或单job>8小时。
- 工作树冲突无法安全隔离。

## 人工决策点

- 是否接受 router recovery 作为继续ablation的证据。
- 是否保留SRR复杂路线，或降级conditional dualhead路线。
- 是否允许后续fold expansion或submission packaging。
