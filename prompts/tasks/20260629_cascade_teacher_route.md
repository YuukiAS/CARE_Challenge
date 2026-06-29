---
task_key: "20260629_cascade_teacher_route"
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

# Task 20260629 Cascade Teacher Route

## 目标

当前 SRR 系列连续低于 nnU-Net baseline。若继续只让弱 SRR 从头替代 nnU-Net，风险很高。本任务建立一条 baseline-preserving 的强备胎路线：利用已有 nnU-Net / anatomy-first / coarse prediction 作为第一阶段空间先验或 teacher，再让 SRR/Result5 模块专注于缺模态、scar/edema proposal 和 local refinement。目标不是放弃 SRR，而是把 SRR 放到更合理的位置：作为 pathology-specific refinement/evidence module，而不是独自承担全图 backbone。

这条路线的成功标准是至少接近或超过现有 nnU-Net fold0 reference；如果它有效，后续可以作为追榜主线或与 SRR-v2 并行。

## 必读材料

必须读取 `AGENTS.md`、`prompts/AGENT_RULES.md`、本任务文件、`docs/notes/20260629_srr_capacity_and_result5_audit.md`、`docs/notes/deep_research/Result5.pdf` 或等价文本、`baseline_report.md`、`results/20260626_dict_bank/selection.md`、`results/20260628_myops_proposal/selection.md`、`results/20260629_srr_v2_unet_core/selection.md` 若已存在、nnU-Net Dataset501 fold0/five-fold reference metrics、现有 nnU-Net predictions/checkpoints、Dataset501 label mapping 和 evaluator。

Result5 与公开强系统都提示：强成绩通常不是全图一次性 dense head，而是 anatomy localization 或 coarse-to-fine 后再 pathology refinement。当前 SRR 低分时，必须验证“强空间先验 + SRR pathology refinement”是否比弱 SRR 从头训练更接近 baseline。

## 允许动作

允许读取现有 nnU-Net predictions/checkpoints；若缺失，可训练或调用已有 fold0 nnU-Net/coarse anatomy route，但单 job 不超过八小时。允许新增 first-party cascade dataset、coarse-prediction loader、ROI builder、teacher-channel generator、distillation loss、refiner model、evaluation scripts 和 jobs。允许最多四个并行 GPU jobs。允许将 nnU-Net anatomy/pathology logits、hard/soft masks、distance maps、ROI crops 作为输入特征或 teacher signal，但必须记录来源、checkpoint、fold、case list 和 no-leakage contract。

## 禁止动作

不要 validation submission、upload package、external upload、外部数据、新权重或新 repo。不要使用 validation labels 或 hosted labels。不要改变 fold split、label mapping 或 evaluator。不要把 no-T2 myocardium 当 edema hard negative。不要把 nnU-Net 预测直接当最终提交伪装成新方法；必须明确它是 teacher/coarse prior/refinement input，并与原 nnU-Net reference 对照。不要覆盖旧 nnU-Net outputs。

## Variants

至少运行以下三个 formal variants，资源允许则四个。

第一条是 `nnunet_anatomy_prior_refiner`。使用 nnU-Net 或现有 best anatomy/coarse prediction 生成 union/LV/RV soft prior、distance maps 和 ROI，训练一个 pathology-specific refiner。输入为原始 LGE/T2/C0 + availability + coarse anatomy prior。目标是判断强 anatomy prior 是否立刻降低 remote FP/HD95。

第二条是 `nnunet_pathology_teacher_srr_refiner`。使用 nnU-Net pathology logits或 masks作为 teacher，不直接复制其输出，而是训练 SRR/refiner学习 residual correction。目标是判断 SRR 是否能在 nnU-Net 之上改善 T2-present edema 或 scar remote FP。

第三条是 `coarse_to_fine_srr_roi`。第一阶段用 coarse prediction 生成 soft ROI，第二阶段在 ROI 中训练 scar 小ROI refiner与 edema 大ROI refiner。此路线应尽量接近 Result5 的 soft-cascade，但以可靠 coarse prior 启动，而不是依赖当前弱 proposal。

第四条可选是 `teacher_distilled_availability_model`。让完整三模态或 nnU-Net teacher 指导缺模态/availability-aware student，在不违反 no-T2 edema contract 的前提下做特征/日志蒸馏。此 variant 只有在 teacher artifacts 明确可用且不拖慢前三条时运行。

## 训练预算

每个 formal job 不超过八小时，尽量使用六到七小时有效训练预算。若需要预生成 coarse priors 或 ROI caches，应先用脚本完成并写入 cache contract，不把 cache 生成算作正式训练结果。若 nnU-Net artifacts 缺失且无法在八小时内补齐，则改用已有 anatomy labels 训练一个 coarse anatomy route作为临时 teacher，并记录 caveat。

## 评估

必须报告 full-volume predictions 上的 `myops_scar` 与 `myops_edema` Dice、HD、HD95；分层报告 edema GT-positive、T2-present/complete、CenterB、CenterC、no-T2 stability；scar all、scar-positive、LGE-only、complete、center groups。必须报告 ROI coverage、coarse prior quality、remote FP、component count、volume ratio、teacher agreement、student improvement over teacher、failure cases。必须与 nnU-Net fold0 reference、SRRMyoPSLite D4、repaired proposal、SRR-v2 结果对照。

## 决策门

写 `results/20260629_cascade_teacher_route/selection.md`，状态只能是 `SELECT_CASCADE_TEACHER_ROUTE`、`SELECT_NNUNET_PLUS_REFINER`、`REVISE_CASCADE_AND_REPEAT`、`ROUTE_BACK_TO_SRR_V2`、`STOP_TEACHER_ARTIFACT_BUG`、`STOP_NO_CASCADE_SIGNAL`。选择 cascade route 的最低条件是相比 nnU-Net reference 至少在一个核心方面有可解释正信号，如 scar HD95/remote FP、edema GT-positive Dice、T2-present HD95、component burden，且另一个 pathology 不灾难性退化。若它只复制 nnU-Net 或明显低于 nnU-Net，应说明 SRR/refiner 没有给 teacher 增益。

## 预期产出

必须写 `results/20260629_cascade_teacher_route/result.md`、`MANIFEST.md`、`selection.md`、`teacher_artifact_contract.md`、`variant_matrix.md`、`metrics_summary.md`、`subgroup_metrics.csv`、`component_hd_by_case.csv`、`roi_coverage.csv`、`teacher_student_delta.csv`、`failure_interpretation.md`，并索引 all jobs/logs/configs/checkpoints/predictions/caches。

## 停止条件

只有 teacher/coarse artifacts 不存在且无法安全生成、label/fold/evaluator/cache 错误、no-T2 edema hard-negative 出现且无法修复、ROI/inverse mapping 不可靠、predictions invalid、或单 job 超过八小时，才停止。单个 variant 失败不能停止整个任务。
