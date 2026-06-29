---
task_key: "20260629_srr_v2_unet_core"
project: "CARE-Myocardium"
status: "ready"
executor: "Codex"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
max_single_job_walltime: "08:00:00"
max_parallel_gpu_jobs: 4
---

# Task 20260629 SRR-v2 U-Net Core

## 目标

当前 `SRRMyoPSLite` 与论文图和 Result4/Result5 设计差距很大：它不是 nnU-Net/U-Net 式 encoder-decoder，而是三条一层 stem、masked average fusion、single-scale retrieval block、浅 refinement 和 1x1 heads。本任务的目标是新增一个 isolated SRR-v2 route，真正实现多尺度 encoder-decoder、true modality-private feature streams、多尺度 shared/private/interaction retrieval bank、pathology-specific proposal head 和可选 light refinement。它是验证“当前表现不如 nnU-Net 是否主要来自架构容量不足”的核心任务。

本任务不能直接改坏现有 SRRMyoPSLite。必须新增独立模型、配置、runner variant 和结果目录；旧 routes 保持可复现。

## 必读材料

必须读取 `AGENTS.md`、`prompts/AGENT_RULES.md`、本任务文件、`docs/notes/20260629_srr_capacity_and_result5_audit.md`、`docs/notes/20260629_result5_gap_audit.md`、`docs/notes/deep_research/Result5.pdf` 或等价文本、`docs/notes/deep_research/Result4.pdf` 或等价文本、`results/20260628_result5_goal/final_status.md`、`results/20260628_myops_proposal/selection.md`、`results/20260629_result4_srr_core_rebuild/selection.md`、`src/care_myocardium/models/srr_myops.py`、`src/care_myocardium/models/srr_blocks.py`、`src/care_myocardium/models/pathology_heads.py`、`scripts/training/run_srr_myops_fold0.py`、Dataset501 fold0 split、evaluator 和 nnU-Net fold0 reference。

当前代码事实必须写入 `architecture_audit.md`：`ModalityStem` 只有一层 Conv3d；private experts 吃的是 fused feature，不是 modality-specific features；没有四尺度 encoder/decoder；`multiscale_dictionary` 只是 pooled context，不是真正多尺度；heads 是 1x1 Conv3d；proposal head 把 logits 混回 final outputs，不是独立 candidate generator。

## 允许动作

允许新增 first-party 模型文件，例如 `src/care_myocardium/models/srr_v2_unet.py`、`srr_v2_blocks.py`、`srr_v2_heads.py`、`srr_v2_losses.py`。允许新增 configs、tests、training variants 和 Slurm jobs。允许最多四个并行 GPU jobs，每个不超过 8 小时。允许把现有 SRRMyoPSLite 的数据读取、loss、evaluation 和 availability contract 复用到 SRR-v2。允许使用轻量 3D U-Net/nnU-Net-like blocks，但不得下载外部权重或改变 evaluator。

## 禁止动作

不要 validation submission、upload package、external upload、外部数据、新权重或新 repo。不要修改 third_party baseline 主路径。不要把 no-T2 myocardium 当 edema hard negative。不要覆盖 SRRMyoPSLite 的 checkpoints/predictions。不要只写类不训练；本任务必须至少完成 one-batch、tiny-overfit 和 formal fold0 variants。不要让单个 variant 失败停止整个任务。

## SRR-v2 architecture contract

SRR-v2 至少必须满足以下结构。

首先，三个模态必须保留独立 feature streams 到多个尺度。输入通道仍然是 LGE、T2、C0；每个模态有独立 stem 和至少 3 个 encoder scales。缺失模态在该模态 stream 中严格关闭，但不能因为 masked average fusion 过早丢失 modality identity。

其次，每个尺度都有 retrieval bank。bank 至少包含 shared experts、LGE-private experts、T2-private experts、C0-private experts；资源允许时加入 interaction experts。与当前实现不同，private expert 应该处理对应模态或对应 interaction feature，而不是全部吃同一个 fused feature。router 可以读 availability + pooled multi-scale summary，但 retrieval 输出应保留 task-specific routed features：anatomy、scar、edema。

第三，decoder 必须是 U-Net-like。它应有下采样、上采样、skip connections 或等价多尺度融合，而不是 single-scale refine。Anatomy decoder 输出 union/LV/RV；scar decoder 输出 scar evidence/proposal；edema decoder 输出 edema evidence/proposal。可以先做 light proposal head，但必须保持 proposal logits、evidence logits 和 final logits 可分开导出。

第四，训练必须保留 T2-masked edema supervision。no-T2 cases 不能对 edema 产生 hard-negative dense loss。scar 必须在 LGE-only cases 上有梯度和诊断。所有 outputs 必须支持 calibrated decode 与 pathology-aware checkpoint selection。

## Variants

至少运行三个 formal variants，资源允许则四个。

第一条是 `srr_v2_multiscale_private_basic`。它实现完整多尺度 modality-private encoder/retrieval/decoder，但不启用 proposal prototype。目标是判断仅结构容量和真实私有流是否能明显超过 SRRMyoPSLite/D4。

第二条是 `srr_v2_multiscale_private_proposal`。在第一条基础上加入 scar/edema 正负 prototype proposal，但不启用 refinement。目标是判断更强 evidence trunk 是否让 Result5 proposal 真正起效。

第三条是 `srr_v2_proposal_uncertainty_hardneg`。在第二条基础上加入 uncertainty gating 与 hard-negative replay。目标是把现有最佳 edema/no-T2 稳定信号和已挖出的 hard negatives 接到更强 trunk 上。

第四条可选是 `srr_v2_light_refine`。只有前三条至少一条有 proposal 正信号时运行，加入 light soft-ROI refinement 或 local decoder。目标是预演真正 refinement，而不是一开始全量堆模块。

## 测试与训练预算

正式训练前必须运行：三种真实模态组合 forward/backward；缺失模态极端值不影响输出；LGE-only scar gradient；T2-present edema gradient；no-T2 edema dense loss 为零；每尺度 private expert receives modality-specific input 的单元测试；decoder full-volume restore sanity；calibrated decode sanity。

每个 formal job 不超过 8 小时，尽量使用 6-7 小时有效训练预算。若队列允许，最多四个 GPU jobs 并行。所有 output/cache/checkpoint/prediction/log 路径必须带 `20260629_srr_v2_unet_core`、variant、fold、seed、checkpoint。

## 评估

必须报告 `myops_scar` 和 `myops_edema` 的 Dice、HD、HD95，并分层报告 edema GT-positive、T2-present/complete、CenterB、CenterC、no-T2 stability；scar all、scar-positive、LGE-only、complete、center groups。必须报告 component count、remote FP、small FP、pred/GT volume ratio、proposal recall/precision、dictionary usage、per-scale expert usage、private/shared usage、gate entropy、expert starvation、checkpoint source、decode mode、parameter count、GPU memory、throughput。

必须与 SRRMyoPSLite D4、repaired proposal repeat、conditional control、nnU-Net fold0 reference 对照。若 SRR-v2 仍远低于 nnU-Net，必须判断是结构仍弱、训练预算不足、loss/decode问题、data sampling问题，还是SRR方向本身不适合当前冲刺。

## 决策门

写 `results/20260629_srr_v2_unet_core/selection.md`，状态只能是 `SELECT_SRR_V2_CORE`、`SELECT_SRR_V2_PROPOSAL`、`REVISE_SRR_V2_AND_REPEAT`、`ROUTE_TO_CASCADE_TEACHER`、`STOP_PIPELINE_BUG`、`STOP_SRR_V2_NO_SIGNAL`。进入 selected 状态至少要求相比 SRRMyoPSLite/D4 或 repaired proposal repeat 在 scar all、edema GT-positive、HD95、remote FP 或 component burden 上有明确正信号，且 no-T2 contract 正确。若结构明显更强但仍不接近 nnU-Net，下一步应转向 cascade/teacher，而不是继续堆小loss。

## 预期产出

必须写 `results/20260629_srr_v2_unet_core/result.md`、`MANIFEST.md`、`selection.md`、`architecture_audit.md`、`architecture_contract.md`、`variant_matrix.md`、`test_summary.md`、`metrics_summary.md`、`subgroup_metrics.csv`、`component_hd_by_case.csv`、`dictionary_usage.csv`、`decode_checkpoint_metrics.csv`、`failure_interpretation.md`，并索引所有 jobs、logs、configs、checkpoints 和 predictions。

## 停止条件

只有 label/fold/evaluator/cache contract 错误、no-T2 edema hard-negative 发生且无法修复、SRR-v2无法通过缺模态与梯度测试、predictions invalid且无法修复、或单 job 超过八小时，才停止。某个 variant OOM 或失败，应降低 batch/patch 或跳过该 variant，并继续其它 variants。
