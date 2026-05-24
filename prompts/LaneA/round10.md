你现在在 `/overflow/htzhu/CARE` 中工作。请只创建 Lane A 下一阶段计划，不要执行任何实验、不要训练、不要提交 Slurm、不要下载权重、不要拉取外部 repo、不要创建 validation zip、不要上传、不要修改生产代码。这个计划将作为后续 goal-mode 的 controller document；后续我会开 goal-mode 按这个 plan 尽可能向前推进。

请先检查 `docs/plans/` 下的命名规则或 registry，由你决定具体文件名。计划主题必须体现以下含义：

`laneA_round10_edema_only_residual_refiner_plan`

或类似含义。

不要使用模糊文件名，例如 `next.md`、`new_plan.md`、`laneA_plan.md`。如果命名规则要求 `next` / `active` / `execution` 等状态词，请按现有规则选择，但必须清楚表达这是 Lane A Round10 的 plan。

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

重点读取 Lane A 相关计划与输出：

`docs/plans/laneA_round2_targeted_execution.md`
`docs/plans/laneA_round03_next_edema_trainable_smoke_execution.md`，如果存在
`docs/plans/laneA_round04_active_fold0_short_train_execution.md` 或相近文件
`docs/plans/laneA_round05_active_controlled_mechanism_integration_execution.md`
`docs/plans/laneA_round06*` 或相近文件
`docs/plans/laneA_round07*` 或相近文件
`docs/plans/laneA_round08*` 或相近文件
`docs/plans/laneA_round09*` 或相近文件

重点读取 Round2-Round9 输出：

`results/diagnostics/phase0_phase1/laneA_myops/round2/`
`results/diagnostics/phase0_phase1/laneA_myops/round3_trainable_smoke/`
`results/diagnostics/phase0_phase1/laneA_myops/round4_fold0_short_train/`
`results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/`
`results/diagnostics/phase0_phase1/laneA_myops/round6_anatomy_missing_modality/`
`results/diagnostics/phase0_phase1/laneA_myops/round7_modality_uncertainty/`
`results/diagnostics/phase0_phase1/laneA_myops/round8_t2_edema_expert/`
`results/diagnostics/phase0_phase1/laneA_myops/round9_baseline_initialized_adaptation/`

也请读取 Round8 / Round9 实现相关文件：

`src/care_myocardium/nnunet/laneA_round8_trainer.py`
`src/care_myocardium/nnunet/laneA_round9_checkpoint_loader.py`
`src/care_myocardium/nnunet/laneA_round9_trainer.py`
`src/care_myocardium/nnunet/laneA_round9_refiner.py`
`scripts/diagnostics/laneA_round8_t2_edema_expert.py`
`scripts/diagnostics/laneA_round9_*.py`
`scripts/training/run_laneA_round9_nnunet_train.py`
`jobs/nnUNet/` 下与 Lane A Round8 / Round9 相关 job 脚本

计划开头必须写清楚当前证据链和最新阶段判断。

Round2 证明 edema inference postprocess route fail，小组件/ROI 删除不能作为主线。Round3 证明 loss wiring / gradient / tiny-overfit 可跑，但不代表性能。Round4 证明 `edema_focal_tversky + no_t2_edema_loss_downweighting` 在真实 fold0 short train 中 fail，原因包括 remote FP、no-T2 FP、HD95 恶化和 scar guardrail 不干净。Round5 证明 alignment 是 watch，boundary/distance 是 watch，anatomy soft prior 进入 bounded diagnostic。Round6 证明当前 anatomy soft attenuation fail；missing-modality audit 指出 no-T2 empty-GT 不能作为强 negative，explicit modality presence 和 uncertainty-weighted supervision 是下一步信号。Round7 证明 first-party 6-channel modality-presence pipeline 工程上可行，但简单 presence channels + scalar no-T2 weighting 没有通过 tiny gate。Round8 证明 T2-present edema expert / separated edema supervision 的 tiny gate 有信号，但 scratch / near-scratch very-short fold0 train 全面崩溃，因此不能拿 scratch 3 epoch 与完整 nnU-Net501 baseline 硬比。Round9 证明 nnU-Net501 checkpoint 可以成功迁移到 6-channel model，初始 logits 与 baseline 可做到完全一致，但 whole-network checkpoint-initialized fine-tune 只有极弱 edema signal，component / HD95 / scar guardrail 不干净，不应继续 longer train；同时 Round9 的 edema-only residual refiner safety gate 通过，class_5 scar unchanged，no-T2 crop FP unchanged，说明 refiner 是当前最符合 baseline-preserving 原则的下一条主线。

请明确当前新结论：

Lane A 下一阶段不应继续 whole-network fine-tune，不应继续从 scratch 训练复杂新结构，不应在 U1/U2 权重、小组件、Focal Tversky、hard ROI、anatomy attenuation 附近微调。下一阶段应切换到：

`edema-only residual refiner / baseline-preserving correction`

核心思想是：nnU-Net501 baseline 继续负责整体 anatomy、scar 和主要 segmentation structure；refiner 只对 class_4 edema 做局部 residual correction；class_5 scar 必须完全保持 baseline 或在导出层面可证明不被修改；如果 refiner 不通过 gate，必须能 fallback 到 baseline。目标问题是：

在完全保护 nnU-Net baseline scar/anatomy 表征的前提下，能不能通过一个轻量 class_4 edema refiner 改善 T2-present / CenterC edema Dice、HD95、component 和 remote FP？

计划必须包含两个主路线和一个预备路线。

第一主路线是：

`cached_baseline_edema_refiner_dataset`

目标是构建一个 cached dataset，用于训练 edema-only residual refiner，而不是每次训练都跑完整 nnU-Net。输入可以包括 nnU-Net501 fold0 baseline 的 class logits/probabilities、baseline class_4 edema probability、baseline class_5 scar probability、baseline myocardium/LV/RV probabilities、T2/LGE/C0 image channels、modality presence channels、possibly myocardium distance/support feature。输出目标只针对 class_4 edema。计划必须说明如何缓存、如何记录 spacing/origin/shape、如何防止 label mapping 错误、如何保证 refiner 训练时不修改 baseline predictions。

第二主路线是：

`edema_only_residual_refiner_trainable_smoke`

目标是训练一个只修 class_4 edema 的轻量 residual module。请设计至少两个候选，按保守程度排序。

候选 A：conservative logit residual refiner。输入为 baseline logits/probs + image/modality features，输出 class_4 residual logit `delta_edema_logit`。融合方式为 `new_edema_logit = baseline_edema_logit + clipped_delta`，其中 residual magnitude 必须有上限，避免大范围改写 baseline。class_5 scar 和其他类别不变。

候选 B：binary edema correction refiner。输入为 baseline predictions/probabilities + T2/LGE/C0 + modality mask + anatomy support，输出一个 binary edema correction probability，只允许在 T2-present / complete cases 上强监督；no-T2 cases 只用于 weak calibration 或 FP control。融合时必须可回退 baseline。

候选 C：T2-focused CenterC refiner。只在 A/B 有安全信号后考虑。目标是针对 CenterC complete-case edema weakness 引入 T2-intensity / baseline uncertainty / myocardium support 的局部 correction，但不能 overfit CenterC。

计划中必须说明：Round10 goal-mode 第一轮应优先实现 A 和/或 B 的最小版本，不应一次性实现复杂外部 repo，不应训练 whole-network，不应修改 class_5 scar。

预备路线是：

`controlled_external_feature_readiness`

目标是为后续外部方法接入准备特征槽位，而不是直接拉 repo 训练。请把 Deep Research 中相关方法映射到 refiner 可使用的 feature / loss / prior 上：I-MMSeg 对应 T2/LGE intensity prior feature；Cascaded FSN / PT-Net 对应 anatomy support feature；InverseForm / surface loss 对应 refiner 的小权重 boundary auxiliary；AdaMM / UniME / CoPeDiT / MoE 对应未来 missing-modality representation，不在 Round10 第一轮直接实现；CAA-Seg/SSA 对应 alignment watch；BiomedParse / MedNeXt / nnU-Net Task114/M&Ms 对应 future backbone watch。请明确：Round10 不做无差别 repo integration；只有 refiner first-party route 有信号或明确失败后，才进入 external method metadata audit / one-case smoke。

计划必须包含至少六个阶段，每个阶段都要写清楚目标、允许事项、禁止事项、输出文件、通过标准、失败标准、以及通过后进入哪一阶段。

第一阶段：`round10_reproducibility_and_cache_gate`

目标是复核 nnU-Net501 fold0 baseline predictions、fold split、label semantics、evaluator、spacing/origin、modality metadata 和 Round9 refiner safety gate。后续 goal-mode 可以创建缓存和诊断脚本，但不得训练。通过标准是：baseline prediction files、GT、image channels、modality metadata、class mapping、baseline metrics 都可定位且一致。若发现路径或 mapping 不一致，先修 cache，不进入训练。

第二阶段：`cached_refiner_dataset_construction`

目标是生成 cached refiner dataset。计划中必须要求记录每个 case 的 baseline logits/probs、image/modalities、GT edema mask、scar/anatomy labels、modality group、center、T2-present flag、edema GT-positive flag、no-T2 empty-GT flag。必须输出 dataset manifest 和 sanity summary。若无法获得 logits，只能使用 probabilities或 labels，但必须记录信息损失。缓存必须放在 Round10 输出目录下，不得污染 nnU-Net baseline cache。

第三阶段：`refiner_architecture_and_loss_gate`

目标是实现最小 refiner 架构和 loss。loss 需要以 class_4 edema 为目标，但必须包含安全约束：residual magnitude regularization、no-T2 FP penalty 或 weak calibration、possibly volume/remote FP penalty。T2-present GT-positive cases 使用主监督，no-T2 empty-GT 不作为 dense hard negative，但需要防止 FP 泄漏。计划必须明确 class_5 scar 不参与 refiner 输出，也不能被修改。通过标准是 import / py_compile / one-batch forward / backward / no NaN/Inf / residual clipping 生效 / baseline fallback 生效。

第四阶段：`tiny_overfit_and_safety_screen`

目标是在少量 selected cases 上测试 refiner 能否学习 class_4 edema correction，同时不引入 no-T2 FP。tiny set 必须包含 CenterB complete、CenterC complete、no-T2 empty-GT cases。通过标准是：T2-present edema 有非零学习信号，no-T2 FP 不增加或低于极小阈值，residual magnitude 不失控，class_5 scar 完全 unchanged。若 tiny gate fail，不得进入 fold0 training。

第五阶段：`bounded_fold0_refiner_training_ladder`

目标是在后续 goal-mode 中允许积极推进训练，但必须 staged/gated。用户 token、Slurm、GPU 资源充足，goal-mode 可以尽可能向前推进，但不能跳过 gates。训练阶梯建议为：

1. fold0 very-short refiner train
2. fold0 short refiner train
3. fold0 longer refiner train
4. only if fold0 longer clean: prepare fold1-4 expansion plan, but do not execute fold1-4 without explicit user authorization

计划中必须明确：refiner 小、风险低，可以比 whole-network route 更积极推进；但如果任何 gate fail，必须停止该 candidate，不得自动扩大训练。禁止 validation zip 或 submission。禁止修改 baseline scar/anatomy predictions。

第六阶段：`evaluation_and_refiner_decision_gate`

目标是统一评估并把 baseline preservation 作为硬门槛。必须分别报告：

`myops_edema` class_4
`myops_scar` class_5, 但 scar 应为 unchanged guardrail
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
scar unchanged check
baseline-vs-refiner edema delta
residual magnitude distribution
case-level failure flags
overlay summary

通过标准必须严格。class_5 scar 必须逐 case 不变或在导出层面证明不变；no-T2 empty-GT edema FP 不得增加或必须低于极小阈值；T2-present GT-positive edema 或 CenterC complete-case edema 必须有 clean positive signal；HD95/component/remote FP 不能明显恶化；不能靠 empty-GT artifact 或 all-case aggregate 过 gate；refiner residual 不能大面积改写 baseline。若 refiner 只提高 Dice 但 HD95/component 变差，fail；若只对 CenterB 有用、CenterC 不干净，watch 但不 promote；若 CenterC 有 clean gain 且 scar/no-T2 guardrail clean，promote。

计划还必须包含 `promotion_and_next_route_decision`。如果 refiner 有 clean signal，则下一步进入 fold0 longer 或 fold1-4 expansion plan。如果 refiner 没有 clean signal，但 safety clean，则可以尝试更强 feature set，例如 T2 intensity prior、anatomy support feature、boundary auxiliary。如果 refiner 不安全，则停止 refiner route，进入 controlled external method readiness。如果 refiner 有强信号，后续可考虑把 refiner 蒸馏回 nnU-Net 或作为 final package postprocess/refinement branch，但 validation submission 需要用户另行授权。

计划必须规定输出根目录：

`results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner/`

建议输出文件至少包括：

`round10_goal_execution_readme.md`
`round10_cache_manifest.csv`
`round10_cache_sanity.md`
`round10_refiner_config.yaml`
`round10_train_commands.txt`
`round10_unit_gradient_smoke.csv`
`round10_tiny_overfit_metrics.csv`
`round10_fold0_very_short_metrics.csv`
`round10_fold0_short_train_metrics.csv`
`round10_fold0_longer_train_metrics.csv`
`baseline_vs_refiner_by_subset.csv`
`no_t2_empty_gt_fp_table.csv`
`centerB_centerC_edema_table.csv`
`scar_unchanged_guardrail_table.csv`
`residual_magnitude_summary.csv`
`case_level_failure_flags.csv`
`round10_decision_table.md`
`round10_next_actions.md`

如果生成 overlays，请放在：

`results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner/failure_overlays/`

计划中还必须包含后续 goal-mode 的 resource stance。请明确：用户 token、Slurm、GPU 资源充足，goal-mode 可以尽可能多往前推进；但推进方式必须 staged, gated, refiner-only, and baseline-preserving。goal-mode 可以在一个 run 中完成 cache construction、refiner implementation、unit tests、tiny-overfit、fold0 very-short train、fold0 short train、evaluation and decision table；如果所有 gates 通过，可以继续到 fold0 longer train；但只要任一 gate fail，必须停止该 candidate并记录原因，不能自动扩大规模。不要因为资源充足就跳过 gates。

计划末尾必须写一个完整中文 `Next Goal Execution Prompt Draft`，供用户后续直接开 goal-mode 使用。这个 draft 应要求 Codex 尽可能推进 Round10：构建 baseline cached refiner dataset，实现 edema-only residual refiner，执行 staged smoke 和 bounded fold0 refiner training，输出全部 metrics 和 gate decision。draft 必须仍然禁止 validation submission、禁止 fold1-4，除非 fold0 gates 全部通过并且用户另行授权。draft 要明确：资源充足，可以尽可能推进，但每个阶段必须 gate，失败即停，不得自动跳到更大训练。

完成后只输出简短 summary：创建了哪个 plan 文件、计划主题是什么、后续 goal-mode 应执行什么、哪些事情仍被禁止。