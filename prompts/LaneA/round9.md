你现在在 `/overflow/htzhu/CARE` 中工作。请只创建 Lane A 下一阶段计划，不要立即执行训练、不要提交 Slurm、不要下载权重、不要拉取外部 repo、不要创建 validation zip、不要上传、不要修改生产代码。这个计划将作为后续 goal-mode 的 controller document；后续 goal-mode 会在资源充足的前提下尽可能向前推进，但必须遵守 staged gates。

请先检查 `docs/plans/` 下的命名规则或 registry，由你决定具体文件名。计划主题必须体现以下含义：

`laneA_round09_baseline_initialized_edema_adaptation_plan`

或类似含义。

不要使用模糊文件名，例如 `next.md`、`new_plan.md`、`laneA_plan.md`。如果命名规则要求 `next` / `active` / `execution` 等状态词，请按现有规则选择，但必须清楚表达这是 Lane A Round9 的 plan。

请先读取并吸收以下文件和目录；如果某些路径不存在，请用 `find docs results scripts src jobs -maxdepth 8 -type f | sort` 定位相近文件，不要臆造路径：

`README.md`
`CARE-README.md`
`TODO.md`，如果存在
`docs/plans/`
`docs/notes/baseline/`
`docs/notes/deep_research/Result1.pdf`
`docs/notes/deep_research/Result2.pdf`
`docs/notes/domain_adaptation/domain_adaptation_relevance_20260519.md`
`phase0_phase1_execution_results.md`

重点读取 Lane A 相关文件：

`docs/plans/laneA_round2_targeted_execution.md`
`docs/plans/laneA_round03_next_edema_trainable_smoke_execution.md`，如果存在
`docs/plans/laneA_round04_active_fold0_short_train_execution.md` 或相近文件
`docs/plans/laneA_round05_active_controlled_mechanism_integration_execution.md`
`docs/plans/laneA_round06*` 或相近文件
`docs/plans/laneA_round07*` 或相近文件
`docs/plans/laneA_round08*` 或相近文件

重点读取 Round2-Round8 输出：

`results/diagnostics/phase0_phase1/laneA_myops/round2/`
`results/diagnostics/phase0_phase1/laneA_myops/round3_trainable_smoke/`
`results/diagnostics/phase0_phase1/laneA_myops/round4_fold0_short_train/`
`results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/`
`results/diagnostics/phase0_phase1/laneA_myops/round6_anatomy_missing_modality/`
`results/diagnostics/phase0_phase1/laneA_myops/round7_modality_uncertainty/`
`results/diagnostics/phase0_phase1/laneA_myops/round8_t2_edema_expert/`

也请读取 Round7 / Round8 实现相关文件：

`src/care_myocardium/nnunet/laneA_round7_trainer.py`
`src/care_myocardium/nnunet/laneA_round8_trainer.py`
`scripts/diagnostics/laneA_round7_modality_uncertainty.py`
`scripts/diagnostics/laneA_round8_t2_edema_expert.py`
`scripts/training/run_laneA_round8_nnunet_train.py`
`jobs/nnUNet/` 下与 Lane A Round7 / Round8 相关 job 脚本

计划开头必须写清楚当前证据链和最新阶段判断。

Round2 证明 edema inference postprocess route fail，小组件/ROI 删除不能作为主线。Round3 证明 loss wiring / gradient / tiny-overfit 可跑，但不代表性能。Round4 证明 `edema_focal_tversky + no_t2_edema_loss_downweighting` 在真实 fold0 short train 中 fail，原因包括 remote FP、no-T2 FP、HD95 恶化和 scar guardrail 不干净。Round5 证明 alignment 是 watch，boundary/distance 是 watch，anatomy soft prior 进入 bounded diagnostic。Round6 证明当前 anatomy soft attenuation fail；missing-modality audit 指出 no-T2 empty-GT 不能作为强 negative，explicit modality presence 和 uncertainty-weighted supervision 是下一步信号。Round7 证明 first-party 6-channel modality-presence pipeline 工程上可行，但简单 presence channels + scalar no-T2 weighting 没有通过 tiny gate。Round8 证明 T2-present edema expert / separated edema supervision 的 tiny gate 有信号，但 scratch / near-scratch very-short fold0 train 全面崩溃；更准确地说，Round8 没有证明机制最终失败，而是证明从 scratch 用极短预算训练改结构模型不能和完整 nnU-Net501 baseline 公平比较，也不能继续直接扩训练。

请明确当前新结论：

Lane A 下一阶段不应继续从 scratch 训练复杂新结构，不应继续在 U1/U2 权重、小组件、Focal Tversky、hard ROI、anatomy attenuation 附近微调。下一阶段应切换到：

`baseline-preserving adaptation`

也就是从已有 nnU-Net501 fold0 checkpoint 初始化，尽量保留 backbone / scar / anatomy 表征，只在 edema route、modality conditioning、no-T2 supervision policy 或轻量 refiner 上做增量适配。核心问题变成：

在不丢掉 nnU-Net 已学到的表征和 scar guardrail 的前提下，Round7/Round8 的 modality-aware / T2-present edema expert 思想是否能改善 edema？

计划必须包含两个主路线和一个预备路线。

第一主路线是：

`nnUNet501_checkpoint_initialized_6channel_finetune`

目标是把 Round7/Round8 的 6-channel modality-presence 输入和 separated edema supervision 迁移到一个由 nnU-Net501 fold0 checkpoint 初始化的模型上，而不是从 scratch 训练。计划必须详细说明如何处理 3-channel checkpoint 到 6-channel model 的权重迁移。原始 `LGE/T2/C0` 图像通道对应的第一层卷积权重应从 nnU-Net501 checkpoint 复制；新增的 `C0_present/LGE_present/T2_present` 通道权重应初始化为 0 或极小值，使模型初始状态尽量复现 baseline。除第一层通道扩展外，其余 backbone / decoder / segmentation head 权重应尽量从 nnU-Net501 checkpoint 加载。计划必须要求后续 goal-mode 先做 checkpoint load audit，确认 loaded / missing / shape-mismatch keys，确认第一层权重拷贝正确，确认初始 inference 在 modality channels 为常数时尽可能接近 baseline prediction。若不能做到 baseline-like initialization，则不得进入训练。

第二主路线是：

`edema_only_residual_refinement_module`

目标是不直接改动 nnU-Net501 主 segmentation backbone，而是训练一个轻量 edema correction / refinement module。输入可以包括 baseline nnU-Net501 的 class probability/logits、T2 image、LGE image、modality presence mask、possibly myocardium probability 或 distance support；输出只针对 class_4 edema 做 residual correction 或 binary edema refinement，不改变 class_5 scar prediction。推理时必须保留 fallback：如果 refiner 不通过 gate，可以回退 baseline edema；scar 始终来自 baseline 或不被 refiner 修改。计划必须比较它与 checkpoint-initialized 6-channel finetune 的风险：refiner 更安全、更保护 scar，但可能改进幅度有限；checkpoint finetune 潜在增益更高，但更容易破坏 baseline 表征。

预备路线是：

`catastrophic_failure_audit_and_engineering_sanity`

目标是先解释 Round8 全面崩溃的直接原因，避免把工程/初始化/预算问题误判为机制失败。计划必须要求后续 goal-mode 在任何训练前先做 Round8 catastrophic failure audit，包括 prediction label histogram、per-class volume、spacing/origin/affine consistency、class_4/class_5 logits/prob summary、baseline-vs-Round8 overlay、checkpoint initialization status、loss curve、train/export channel order、validation channel injection、evaluator class mapping。若发现 label mapping、spacing、channel order、export 或 evaluator 问题，必须先修工程，不得继续训练。

计划必须包含至少六个阶段，每个阶段都要写清楚目标、允许事项、禁止事项、输出文件、通过标准、失败标准、以及通过后进入哪一阶段。

第一阶段：`round9_failure_audit_and_baseline_reproducibility_gate`

目标是做 Round8 catastrophic failure audit，并确认 nnU-Net501 fold0 baseline、fold split、label semantics、evaluator、cache 和 prediction export 都可复现。后续 goal-mode 可以创建诊断脚本和读取已有 predictions，但不得训练。通过标准是：确认 Round8 崩溃不是因为明显 label/export/evaluator bug；确认 baseline predictions、metrics 和 file paths 正确；确认有可用 nnU-Net501 fold0 checkpoint 和 predictions。若发现工程 bug，应优先修复并重新跑 sanity，不进入训练。

第二阶段：`checkpoint_initialized_6channel_loader_gate`

目标是实现并验证 nnU-Net501 checkpoint 到 6-channel Round9 model 的迁移。必须记录第一层卷积 shape、原 3-channel 权重拷贝、新 modality channel 权重初始化、其余 keys 加载比例、missing keys、unexpected keys、strict / non-strict loading 规则。必须做 initial-inference sanity：在加载 checkpoint 后，未训练或极少训练前，candidate predictions 应尽量接近 baseline，至少 class_5 scar 和 major anatomy 不应完全崩。若 initial predictions 与 baseline 差异过大，停止并修 loader，不训练。

第三阶段：`edema_refiner_baseline_preserving_gate`

目标是设计并测试 edema-only residual refiner。该模块应尽量不影响 scar。计划中必须要求先做 one-case / tiny forward、gradient smoke、baseline fallback smoke，并确认 refiner 输出可以被安全融合到 baseline class_4 edema，而 class_5 scar 完全不变。若 refiner 引入 label mapping 风险或破坏 export，则停止。

第四阶段：`bounded_training_ladder`

目标是在后续 goal-mode 中允许积极推进训练，但必须 staged/gated。用户 token、Slurm、GPU 资源充足，goal-mode 可以尽可能向前推进，但不能跳过 gates。训练阶梯建议为：

1. import / py_compile / config smoke
2. checkpoint loader smoke
3. initial inference baseline-reproduction smoke
4. one-batch forward + backward
5. tiny-overfit on selected T2-present CenterB/CenterC cases and selected no-T2 empty-GT cases
6. fold0 very-short train
7. fold0 short train
8. fold0 longer train
9. only if fold0 longer clean: prepare fold1-4 expansion plan, but do not submit validation without explicit user authorization

计划中必须明确：可以在 goal-mode 中自动推进多个阶段，只要前一阶段明确通过 gate；如果任一 gate fail，必须停止该 candidate 并记录原因。禁止直接从 loader smoke 跳到 fold0 long train。禁止 validation zip 或 submission。fold1-4 只有在 fold0 longer clean 且用户另行授权时才允许执行。

第五阶段：`evaluation_and_non_regression_gate`

目标是统一评估并把 “不丢 baseline” 作为核心 gate。必须分别报告：

`myops_edema` class_4
`myops_scar` class_5
all-case
T2-present GT-positive
complete-modality
CenterB
CenterC
no-T2 empty-GT
C0+LGE no-T2
LGE-only
center groups

必须同时报告：

Dice
HD
HD95
component count
small/remote FP
pred/GT volume ratio
no-T2 edema FP voxel count
no-T2 edema FP case count
scar guardrail Dice/HD95
case-level failure flags
baseline reproduction delta
candidate-vs-baseline overlay summary

通过标准必须强调 baseline-preserving。class_5 scar Dice/HD95 不得明显回退；major anatomy / prediction volume 不得崩；T2-present GT-positive edema 或 CenterC complete-case edema 必须有 clean positive signal；HD95/component/remote FP 不能明显恶化；no-T2 empty-GT edema FP 可以有极低上限，但不能失控；不能靠 all-case aggregate 或 empty-GT artifact 过 gate。若 candidate 一开始不能复现 baseline 表征，即使 tiny edema signal 好，也不得进入 longer train。

第六阶段：`promotion_and_next_route_decision`

目标是定义后续路径。如果 checkpoint-initialized finetune 有 clean positive signal，则进入 fold0 longer train 或 fold1-4 expansion plan。如果 edema-only refiner 有 clean positive signal，则优先推广 refiner，因为它更保护 scar。如果两者都失败，但 loader/inference sanity 正常，则说明 first-party baseline-preserving adaptation 仍不足，下一步进入 controlled external method readiness：UniME / AdaMM / I-MMSeg / MoE / CAA-Seg / Cascaded FSN / InverseForm 等只做 metadata audit 和 one-case smoke，不得直接 full training。如果失败来自工程或 initialization，则优先修工程，不做模型结论。

计划必须包含 `controlled_external_method_readiness` 小节，但只能作为后续分支，不在 Round9 第一轮直接执行。请把 Deep Research 中相关方法按机制归类：

AdaMM / UniME / CoPeDiT / MoE / MMPL-Seg: missing-modality routing、student-teacher、modality-conditioned representation
I-MMSeg: modality/intensity prior for edema/scar
CAA-Seg/SSA: alignment watch
Cascaded FSN / PT-Net: anatomy prior watch
InverseForm / surface loss / HD loss: boundary watch
BiomedParse / MedNeXt / nnU-Net Task114/M&Ms: pretrained backbone watch

请明确：外部 repo 后续只有在 Round9 baseline-preserving adaptation 有正信号、或者明确失败需要升级时，才进入 metadata audit / one-case smoke。不得在本 plan 的 first goal 中无差别拉取所有 repo。任何 external repo 必须先通过 license/compliance、pretrained data source、external data risk、input-output shape、label mapping、one-case smoke，再进入 fold0 smoke。

计划必须规定输出根目录：

`results/diagnostics/phase0_phase1/laneA_myops/round9_baseline_initialized_adaptation/`

建议输出文件至少包括：

`round9_goal_execution_readme.md`
`round9_failure_audit.md`
`round9_failure_audit_case_table.csv`
`round9_checkpoint_loader_audit.md`
`round9_checkpoint_key_report.csv`
`round9_initial_inference_baseline_reproduction.csv`
`round9_train_config_checkpoint_initialized.yaml`
`round9_train_config_edema_refiner.yaml`
`round9_train_commands.txt`
`round9_unit_gradient_smoke.csv`
`round9_tiny_overfit_metrics.csv`
`round9_fold0_very_short_metrics.csv`
`round9_fold0_short_train_metrics.csv`
`round9_fold0_longer_train_metrics.csv`
`baseline_vs_candidate_by_subset.csv`
`no_t2_empty_gt_fp_table.csv`
`centerB_centerC_edema_table.csv`
`scar_guardrail_table.csv`
`case_level_failure_flags.csv`
`round9_decision_table.md`
`round9_next_actions.md`

如果生成 overlays，请放在：

`results/diagnostics/phase0_phase1/laneA_myops/round9_baseline_initialized_adaptation/failure_overlays/`

计划中还必须包含后续 goal-mode 的 resource stance。请明确：用户 token、Slurm、GPU 资源充足，goal-mode 可以尽可能多往前推进；但推进方式必须是 staged, gated, and baseline-preserving。goal-mode 可以在一个 run 中完成 audit、loader implementation、unit tests、initial inference, tiny-overfit, fold0 very-short train, fold0 short train, evaluation and decision table；如果所有 gates 通过，可以继续到 fold0 longer train；但只要任一 gate fail，必须停止该候选并记录原因，不能自动扩大规模。不要因为资源充足就跳过 gates。

计划末尾必须写一个完整中文 `Next Goal Execution Prompt Draft`，供用户后续直接开 goal-mode 使用。这个 draft 应要求 Codex 尽可能推进 Round9：先做 Round8 failure audit 和 nnU-Net501 checkpoint-initialized 6-channel loader；验证 baseline reproduction；然后实现 checkpoint-initialized modality-aware finetune 和/or edema-only residual refiner；执行 staged smoke 和 bounded fold0 training；输出全部 metrics 和 gate decision。draft 必须仍然禁止 validation submission、禁止 fold1-4，除非 fold0 gates 全部通过并且用户另行授权。draft 要明确：资源充足，可以尽可能推进，但每个阶段必须 gate，失败即停，不得自动跳到更大训练。

完成后只输出简短 summary：创建了哪个 plan 文件、计划主题是什么、后续 goal-mode 应执行什么、哪些事情仍被禁止。