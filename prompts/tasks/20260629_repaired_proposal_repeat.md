---
task_key: "20260629_repaired_proposal_repeat"
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

# Task 20260629 Repaired Proposal Repeat

## 目标

不要把 `20260628_myops_proposal` 的低分直接解释为 Result5 思路失败。本任务基于已经发现的损失、解码、checkpoint、hard-negative replay 和 no-T2 stability 问题，重跑一轮真正修复后的 Result5 proposal。目标是在当前 SRRMyoPSLite 体系上尽量恢复可用 proposal 信号，为后续 refinement 或 SRR-v2 提供明确参照。

本任务不是小样本 smoke。每个 formal job 仍限制在 8 小时内，但必须尽量使用 6-7 小时有效训练预算；one-batch 和 tiny-overfit 只是入场检查，不是结果。

## 必读材料

必须读取 `AGENTS.md`、`prompts/AGENT_RULES.md`、本任务文件、`docs/notes/20260629_srr_capacity_and_result5_audit.md`、`docs/notes/20260629_result5_gap_audit.md`、`docs/notes/deep_research/Result5.pdf` 或等价文本、`results/20260628_myops_proposal/selection.md`、`results/20260628_myops_proposal/metrics_summary.md`、`results/20260628_myops_proposal/failure_interpretation.md`、`results/20260629_loss_decode_calibration/selection.md`、`results/20260629_pathology_checkpoint_selection/selection.md`、`results/20260629_proposal_memory_hardneg/selection.md`、`results/20260629_true_soft_roi_refine/selection.md`、`src/care_myocardium/models/srr_myops.py`、`src/care_myocardium/losses/srr_losses.py`、`scripts/training/run_srr_myops_fold0.py`。

当前已知事实：上一轮 proposal 的 aggregate selection 是 `REVISE_PROPOSAL_AND_REPEAT`，不是 `SELECT_PROPOSAL_ROUTE`。`proposal_uncertainty_gate` 有最好的 edema GT-positive Dice `0.2034` 和 all-case Dice `0.4376`，但 HD95 与 component/remote-FP burden 高；scar 最好 all-case Dice 只有 `0.1017`。续跑审计显示 raw argmax 解码不合适、patch-loss best checkpoint 不是 pathology-optimal、ignore-label loss masking bug 已修复到未来 runs、hard-negative mining 已得到 `7237` 个 mined FP components，其中 scar replay-safe `4167`、edema replay-safe `1561`。

## 允许动作

允许修改 first-party training/evaluation code、loss、decode、checkpoint selection、proposal replay sampler、variant configs 和 Slurm wrappers。允许使用 `results/20260629_proposal_memory_hardneg/mined_components.csv` 或等价 artifact 做 hard-negative replay。允许最多四个并行 GPU jobs，每个 job 不超过 8 小时。允许在正式训练前做短审计与 one-batch sanity。

## 禁止动作

不要 validation submission、upload package、external upload、外部数据、新权重或新 repo。不要改变 fold split、label mapping 或 evaluator。不要把 no-T2 myocardium 当 edema hard negative。不要用 raw argmax 作为唯一最终解码。不要因为一个 variant 失败就停止其它 variants。不要覆盖 `20260628_*` 或 `20260629_*` 已有结果。

## 必须修复的管线问题

本任务开始 formal jobs 前必须写 `results/20260629_repaired_proposal_repeat/repair_contract.md`，说明以下修复已经落实或明确无法落实：ignore-label masking 在 anatomy/scar/edema/proposal loss 中一致；final decoding 使用 pathology-priority/threshold-calibrated decode，而不是只用 raw argmax；checkpoint selection 至少保存 patch-loss best、checkpoint final 和 pathology-aware candidate，并在评估中显式比较；hard-negative replay sampler 能读取 mined FP components 并区分 scar safe negative、edema T2-present safe negative、no-T2 unsafe myocardium；proposal logits 不再无校准地固定按 `0.40 original + 0.60 proposal` 强混入 final logits，至少要支持 original/proposal/mixed 多模式输出。

## Variants

至少运行以下三个 formal variants，资源允许则运行第四个。所有 variants 必须同 fold0、同 evaluator、同 no-T2 contract 比较。

第一条是 `repaired_uncertainty_hardneg`。它继承 `proposal_uncertainty_gate` 的 edema/no-T2 稳定信号，加入 repaired losses、pathology-aware checkpoint selection、calibrated decode 和 hard-negative replay。它的目标是提高 edema GT-positive Dice，同时减少 no-T2 FP 和 remote component。

第二条是 `repaired_posneg_scar_hardneg`。它继承 `proposal_pos_neg_basic` 的 scar相对信号，重点加入 scar safe hard-negative replay、LGE-driven scar sampling、pathology-aware checkpoint selection 和 calibrated decode。它的目标是让 scar all-case Dice 超过 D4 dictionary reference，同时降低 HD95/remote FP。

第三条是 `repaired_joint_calibrated_proposal`。它同时保留 scar positive/negative prototype、edema uncertainty gate 和 hard-negative replay，但用明确的解码策略输出 original/proposal/mixed 三套 predictions，避免训练阶段某个 logit scale 偶然主导最终 argmax。

第四条可选是 `repaired_final_checkpoint_route`。如果 checkpoint audit 已经证明 final checkpoint 明显优于 patch-loss best，则单独训练/评估一个以 final-checkpoint/pathology checkpoint 为主的 route，用于确认上一轮结果是否主要被 checkpoint selection 压低。

## 训练和评估

每个 formal job 应尽量使用 6-7 小时有效训练预算，单 job 不超过 8 小时。必须报告 `myops_scar` 和 `myops_edema` 的 Dice、HD、HD95，同时报告 GT-positive、T2-present/complete、CenterB、CenterC、no-T2 stability、LGE-only scar、component count、remote FP、small FP、pred/GT volume ratio、proposal recall、proposal precision、prototype usage、negative replay usage、decode mode 和 checkpoint source。必须与 D4 dictionary reference、上一轮 proposal variants、nnU-Net fold0 reference 对照。

## 决策门

写 `results/20260629_repaired_proposal_repeat/selection.md`，状态只能是 `SELECT_REPAIRED_PROPOSAL_ROUTE`、`REVISE_PIPELINE_AGAIN`、`ROUTE_TO_SRR_V2_ONLY`、`ROUTE_TO_CASCADE_TEACHER`、`STOP_PIPELINE_BUG`、`STOP_NO_PROPOSAL_SIGNAL`。选择 proposal route 的最低条件是至少一个 pathology 在 Dice/HD95/remote-FP/component 或 GT-positive recall 上相比上一轮 selected dictionary route 和上一轮 proposal有明确正信号，另一个 pathology 不灾难性退化，no-T2 contract 正确，且 decode/checkpoint 不是未校准伪收益。

若 repaired route 仍然处在 `0.1` scar Dice 量级且没有显著 component/HD 改善，应明确判断这更像架构容量不足，而不是继续无限修 proposal head。

## 预期产出

必须写 `results/20260629_repaired_proposal_repeat/result.md`、`MANIFEST.md`、`selection.md`、`repair_contract.md`、`variant_matrix.md`、`metrics_summary.md`、`subgroup_metrics.csv`、`component_hd_by_case.csv`、`proposal_metrics.csv`、`decode_checkpoint_metrics.csv`、`hardneg_replay_usage.csv`、`failure_interpretation.md`，并索引所有 jobs、logs、checkpoints、predictions 和 configs。

## 停止条件

只有 label/fold/evaluator/cache contract 错误、no-T2 edema hard-negative 再次出现且无法修复、hard-negative replay sampler 无法安全区分负样本、predictions invalid 且无法修复、或单 job 超过 8 小时，才停止。单个 variant 失败不能停止整个任务。
