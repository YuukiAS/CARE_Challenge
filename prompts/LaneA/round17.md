你现在在 `/overflow/htzhu/CARE` 中工作。请只创建 Lane A 下一阶段计划，不要立即执行实验、不要训练、不要提交 Slurm、不要下载权重、不要 clone 外部 repo、不要创建 validation zip、不要上传、不要修改生产代码。这个计划将作为后续 goal-mode 的执行 controller；后续我会开 goal-mode 按这个 plan 尽可能向前推进。

请先检查 `docs/plans/` 下的命名规则或 registry，由你决定具体文件名。计划主题必须体现以下含义：

`laneA_round17_mednext_stronger_backbone_integration_plan`

或类似含义。

不要使用模糊文件名，例如 `next.md`、`new_plan.md`、`laneA_plan.md`。如果命名规则要求 `next`、`active`、`execution` 等状态词，请按现有规则选择，但必须清楚表达这是 Lane A Round17 的 MedNeXt / stronger backbone integration plan。

请先读取并吸收以下文件和目录；如果某些路径不存在，请用 `find docs results scripts src jobs -maxdepth 9 -type f | sort` 定位相近文件，不要臆造路径：

`README.md`
`CARE-README.md`
`TODO.md`，如果存在
`docs/plans/`
`docs/notes/baseline/`
`docs/notes/deep_research/Result1.pdf`
`docs/notes/deep_research/Result2.pdf`
`docs/notes/domain_adaptation/domain_adaptation_relevance_20260519.md`
`phase0_phase1_execution_results.md`

重点读取 Lane A 历史计划与结果：

`docs/plans/laneA_round2_targeted_execution.md`
`docs/plans/laneA_round03_next_edema_trainable_smoke_execution.md`，如果存在
`docs/plans/laneA_round04_active_fold0_short_train_execution.md` 或相近文件
`docs/plans/laneA_round05_active_controlled_mechanism_integration_execution.md`
`docs/plans/laneA_round06*` 或相近文件
`docs/plans/laneA_round07*` 或相近文件
`docs/plans/laneA_round08*` 或相近文件
`docs/plans/laneA_round09*` 或相近文件
`docs/plans/laneA_round10*` 或相近文件
`docs/plans/laneA_round11*` 或相近文件
`docs/plans/laneA_round12*` 或相近文件
`docs/plans/laneA_round13*` 或相近文件
`docs/plans/laneA_round14*` 或相近文件
`docs/plans/laneA_round15*` 或相近文件
`docs/plans/laneA_round16*` 或相近文件

重点读取 Round14-Round16 输出：

`results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator/`
`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/`
`results/diagnostics/phase0_phase1/laneA_myops/round16_external_mechanism_integration/`
`results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/`

重点读取以下关键文件，如存在：

`round15_detailed_failure_analysis.md`
`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/round15_decision_table.md`
`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/round15_round16_recommendation.md`
`results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/round16_candidate_decision_table.md`
`results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/round16_round17_recommendation.md`
`results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/round16_compliance_matrix.csv`
`results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/round16_repo_metadata_audit.md`
`results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/round16_external_import_smoke_summary.csv`
`results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/round16_fold0_very_short_results.csv`
`results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/round16_baseline_vs_candidate_by_subset.csv`

请在计划开头写清楚当前证据链和最新判断。

Round2 证明 edema inference postprocess route fail，小组件/ROI 删除不能作为主线。Round3 证明 loss wiring / gradient / tiny-overfit 可跑，但不代表性能。Round4 证明 `edema_focal_tversky + no_t2_edema_loss_downweighting` 在真实 fold0 short train 中 fail，原因包括 remote FP、no-T2 FP、HD95 恶化和 scar guardrail 不干净。Round5 证明 alignment 是 watch，boundary/distance 是 watch，anatomy soft prior 进入 bounded diagnostic。Round6 证明当前 anatomy soft attenuation fail；missing-modality audit 指出 no-T2 empty-GT 不能作为强 negative，explicit modality presence 和 uncertainty-weighted supervision 是后续信号。Round7 证明 first-party 6-channel modality-presence pipeline 工程上可行，但简单 presence channels + scalar no-T2 weighting 没有通过 tiny gate。Round8 证明 T2-present edema expert / separated edema supervision 的 tiny gate 有信号，但 scratch / near-scratch very-short fold0 train 全面崩溃。Round9 证明 nnU-Net501 checkpoint 可以成功迁移到 6-channel model，初始 logits 与 baseline 可做到完全一致，但 whole-network checkpoint-initialized fine-tune 只有极弱 edema signal，component / HD95 / scar guardrail 不干净。Round10 到 Round14 的 refiner/calibrator 路线说明 baseline-preserving class_4 correction 可以保持 scar/no-T2 安全，但无法产生 clean CenterC/T2-present edema improvement。Round15 的 first-party feature-head portfolio 中，A 有极弱 intensity signal 但 CenterC component safety 失败，B/C 回退 baseline，F 小 MoE 方向严重打坏 edema。Round16 的 first-party A/C/E/F fold0 very-short gate 没有候选进入 fold0 short；外部候选的 metadata/import/readiness 显示 MedNeXt 是目前最干净的 stronger-backbone readiness candidate，而 I-MMSeg、AdaMM、InverseForm、BiomedParse 等多数仍有 license、dependency、import、weight provenance 或合规阻塞。

请明确当前新结论：

Lane A 下一阶段不应继续普通 refiner/calibrator/feature-head 小修，不应继续给 Round15/16 A/C/E/F 加 epoch，不应扩 fold1-4，不应提交 validation，不应回到 Focal Tversky、小组件、hard ROI、anatomy attenuation 或 whole-network nnU-Net small tweak。当前需要进入：

`MedNeXt / stronger backbone CARE-native integration`

目标不是继续修补 nnU-Net baseline 输出，而是测试更强 3D segmentation architecture 是否能改善 CenterC / T2-present edema representation。MedNeXt 是当前最优先的外部/半外部 readiness candidate，因为它是 ConvNeXt-style 3D medical segmentation backbone，license 相对清楚，repo 可达，且比 I-MMSeg / AdaMM / BiomedParse 等更容易接入 CARE-native training/evaluator/export。Round17 的主线应优先做 MedNeXt v1 architecture 的 CARE-only fold0 smoke；只有合规和 provenance 明确时，才考虑 MedNeXt-v2 或 pretrained weights。

计划必须包含三个主路线和两个辅助路线。

第一主路线：

`MedNeXt_v1_CARE_only_architecture_route`

目标是将 MedNeXt v1 architecture 接入 CARE Dataset501 fold0 pipeline，只使用 CARE training data，不使用 external images/labels，不下载大权重。优先复用 MedNeXt 作为 PyTorch module 或 blocks，而不是照搬完整 nnU-Net v1 training pipeline。计划应包含 import/install strategy、input channels、output classes、spacing/patch compatibility、loss/evaluator/export compatibility、fold0 very-short 和 fold0 short smoke。第一轮应优先小模型，例如 MedNeXt-S 或 Base，kernel size 3，3D fullres 或 CARE-compatible patch setting。必须明确如何对齐 nnU-Net501 label semantics：class_4 edema、class_5 scar，保持 same fold0 split、same evaluator、same export mapping。

第二主路线：

`MedNeXt_baseline_preserving_or_pretrained_initialization_route`

目标是探索 MedNeXt 是否能利用安全初始化，而不是从头训练太久。候选包括：MedNeXt from scratch CARE-only、MedNeXt with UpKern small-to-large kernel within CARE-only training、如果已有公开 pretrained weights 且规则允许则做 pretrained initialization audit。计划必须强调：公开 pretrained model 可能允许，但必须记录 pretrained data source、license、external data risk 和 challenge rules；不得下载或使用不清楚来源的大权重；不得用 external image/label data 训练。MedNeXt-v2 / nnU-Net repo pretrained models 只能在合规通过后进入 one-case smoke，不得直接训练。

第三主路线：

`MedNeXt_plus_edema_specific_objective_route`

目标是在 MedNeXt backbone 上重新测试更合理的 edema objective，但不能重复 Round4 的 Focal Tversky 失败。候选包括 conservative Dice/CE baseline、small-weight boundary/surface auxiliary、component/HD-aware auxiliary、T2-present edema reporting、no-T2 supervision policy。第一轮应从 standard Dice/CE + class-balanced reporting 开始，避免一开始加复杂 loss；只有 baseline MedNeXt signal 明确后再加 edema-specific auxiliary。

第一辅助路线：

`MedNeXt_external_repo_compliance_and_import_route`

目标是系统审查 MedNeXt v1/v2 repo、license、installation、dependencies、expected nnU-Net version、preprocessing assumptions、1mm isotropic spacing assumption、2D/3D support、gradient checkpointing、memory footprint、model sizes S/B/M/L。必须输出 compliance matrix 和 integration risk table。计划必须记录 MedNeXt v1 repo 是 Apache-2.0 license、基于 nnU-Net v1 training pipeline 但 architecture 可作为 external PyTorch module 使用；还要记录 MedNeXt v1 的 1mm isotropic spacing assumption 与 CARE nnU-Net median spacing pipeline 可能不一致，需要 smoke 验证。

第二辅助路线：

`Round18_external_method_fallback_readiness`

目标是如果 MedNeXt 没有 clean signal，Round18 应回到外部机制路线，例如 I-MMSeg intensity prior、Cascaded FSN/PT-Net anatomy-pathology cascade、InverseForm/surface loss、UniME/AdaMM/MoE missing-modality representation。Round17 不应无差别推进这些外部 repo，但应保留 readiness update。

计划必须包含至少八个阶段，每个阶段都要写清楚目标、允许事项、禁止事项、输出文件、通过标准、失败标准、以及通过后进入哪一阶段。

第一阶段：`round17_mednext_reproducibility_and_registry_gate`

目标是复核 Round16 结论、nnU-Net501 fold0 baseline、Dataset501 paths、fold split、label semantics、evaluator、export、spacing/patch metadata、GPU memory constraints。后续 goal-mode 可以创建 MedNeXt registry 和 config 草案，但不得训练。通过标准是 baseline metrics 和 paths 可复现，MedNeXt output root 明确，label/evaluator/cache 风险清楚。

第二阶段：`mednext_repo_metadata_and_compliance_audit`

目标是审查 MedNeXt v1/v2 repo 和可能的 pretrained weights。记录 repo URL、license、version、dependencies、nnU-Net v1/v2 assumption、model sizes、spacing assumptions、whether weights are used、pretrained data source、external data risk、install/import status。若 license或 weight provenance 不清楚，不能进入 weight-based training；仍可做 code-only architecture CARE-only training。

第三阶段：`mednext_import_and_onecase_shape_smoke`

目标是 clone/install 或 vendor MedNeXt 的最小代码路径，做 import、instantiate、one-case forward shape smoke。不得下载大权重或外部数据。必须测试输入 channel 数、class 数、patch shape、device CPU/GPU fallback、deep supervision on/off、memory footprint。通过标准是 forward/backward shape 正确，输出可映射到 class 0-5，no NaN/Inf。

第四阶段：`mednext_care_dataset_adapter_smoke`

目标是把 MedNeXt 接到 CARE Dataset501 fold0 data pipeline，但仍不跑长训练。要检查 preprocessing、spacing、patch extraction、data augmentation、class labels、modality missingness、C0/LGE/T2 channel handling、modality mask optional channels。通过标准是 one-batch train/val 可跑，label semantics 与 nnU-Net501 一致。

第五阶段：`mednext_fold0_very_short_training_batch`

目标是在后续 goal-mode 中允许提交多个 MedNeXt fold0 very-short jobs。建议第一批包含：

`R17_A_mednext_s_kernel3_standard_dicece_fold0_vs`
`R17_B_mednext_b_kernel3_standard_dicece_fold0_vs`
`R17_C_mednext_s_kernel5_upkern_or_largekernel_fold0_vs`，只有 UpKern 或 kernel5 可安全实现时
`R17_D_mednext_s_modality_channels_fold0_vs`，如果 6-channel modality presence implementation 成本低
`R17_E_mednext_s_small_boundary_aux_fold0_vs`，只作为 auxiliary watch

每个 job 必须独立 output dir、config、seed、job name。用户资源充足，允许并行提交多个 very-short jobs，但不得跳过 import/adapter gate。不得提交 validation zip，不得 fold1-4。若资源不足，可优先 A/B。

第六阶段：`mednext_result_collection_and_gate`

目标是自动收集 very-short jobs，并统一评估。必须与 nnU-Net501 fold0 baseline 比较，分别报告 myops_edema class_4、myops_scar class_5、T2-present GT-positive、CenterB、CenterC、no-T2 empty-GT、HD95、component、remote FP、scar guardrail。通过标准是至少有一个 MedNeXt candidate 在 T2-present/CenterC edema 上有 clean positive signal，且 scar/no-T2/HD/component 不崩。若全都无信号或崩溃，停止 MedNeXt expansion并写明原因。

第七阶段：`promoted_mednext_fold0_short_training`

目标是只对通过 very-short gate 的 MedNeXt candidates 提交 fold0 short jobs。允许多个 jobs，但不得 fold1-4，不得 validation submission。通过标准必须比 very-short 更严格：CenterC 或 T2-present edema Dice/HD95 有 clean gain，component/remote FP 不恶化，scar guardrail clean。若 fold0 short 仍 clean，可准备 fold0 longer 或 fold1-4 plan，但不得自动执行 fold1-4。

第八阶段：`round17_decision_and_round18_recommendation`

目标是根据 MedNeXt 结果决定下一步。如果 MedNeXt 有 clean signal，Round18 应进入 MedNeXt fold0 longer / fold1-4 expansion plan。如果 MedNeXt 无信号但稳定，Round18 应回到 I-MMSeg / Cascaded FSN / InverseForm / UniME/AdaMM 的 one-case smoke 或更窄 deep research。如果 MedNeXt 工程阻塞，则判断是否使用 MIST/nnU-Net MedNeXt-v2 或其他 stronger backbone。如果所有路线仍失败，则建议新 deep research 聚焦 CenterC/T2 edema representation、limited complete-modality teacher、CMR edema intensity prior 和 label ambiguity，而不是泛泛 cardiac segmentation。

计划必须包含统一评估规则。所有 candidates 必须报告：

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
Case2031
Case3011
Case3012
Case3040
Case3044, 如果仍是 CenterC failure case

必须同时报告：

Dice
HD
HD95
component count
small/remote FP
pred/GT volume ratio
no-T2 edema FP voxel count
no-T2 edema FP case count
scar Dice/HD95 guardrail
training stability
cache/label/evaluator integrity
memory/runtime
case-level failure flags

通过标准必须严格但适合 stronger-backbone smoke。候选若在 CenterC 或 T2-present edema 上无信号，或 HD95/component/remote FP 明显恶化，或 scar guardrail 不干净，或 no-T2 FP 失控，应 stop。候选若有弱信号但不 clean，watch。候选若 T2-present/CenterC 有 clear improvement 且 scar/no-T2/HD/component clean，可 promote 到 fold0 short 或 longer。任何 candidate 不允许靠 foreground mean、all-case aggregate 或 empty-GT artifact 过 gate。

计划必须包含 output root：

`results/diagnostics/phase0_phase1/laneA_myops/round17_mednext_backbone/`

建议输出文件至少包括：

`round17_goal_execution_readme.md`
`round17_mednext_compliance_matrix.csv`
`round17_mednext_repo_metadata_audit.md`
`round17_import_onecase_smoke_summary.csv`
`round17_dataset_adapter_smoke_summary.csv`
`round17_mednext_candidate_matrix.csv`
`round17_batch_job_submission_plan.md`
`round17_batch_job_status.csv`
`round17_fold0_very_short_results.csv`
`round17_fold0_short_results.csv`
`round17_baseline_vs_candidate_by_subset.csv`
`round17_centerC_edema_table.csv`
`round17_no_t2_empty_gt_fp_table.csv`
`round17_scar_guardrail_table.csv`
`round17_component_remote_fp_table.csv`
`round17_case_level_failure_flags.csv`
`round17_candidate_decision_table.md`
`round17_round18_recommendation.md`

如果生成 overlays 或 feature visualizations，请放在：

`results/diagnostics/phase0_phase1/laneA_myops/round17_mednext_backbone/overlays/`

计划中还必须包含后续 goal-mode 的 resource stance。请明确：用户 token、Slurm、GPU 资源充足，goal-mode 可以尽可能多往前推进；但推进方式必须 staged, gated, compliance-checked, and comparable。goal-mode 可以在一个 run 中完成 MedNeXt metadata audit、repo install/import smoke、one-case smoke、CARE adapter smoke、多个 fold0 very-short Slurm jobs、自动结果收集、promoted fold0 short jobs 和 decision table；如果 very-short gates 通过，可以继续 fold0 short；如果 fold0 short clean，可以准备 fold0 longer / fold1-4 plan，但 fold1-4 和 validation submission 仍需用户另行授权。不要因为资源充足就跳过 import/shape/cache/evaluator gates。

计划末尾必须写一个完整中文 `Next Goal Execution Prompt Draft`，供用户后续直接开 goal-mode 使用。这个 draft 应要求 Codex 尽可能推进 Round17：审查 MedNeXt 合规与 repo metadata；安装/导入 MedNeXt；做 one-case shape smoke；接入 CARE Dataset501 fold0 adapter；批量提交 MedNeXt fold0 very-short jobs；收集结果；只对通过 gate 的候选继续 fold0 short；输出统一指标和决策表。draft 必须仍然禁止 validation submission，禁止 fold1-4/5-fold，除非 fold0 candidates clean 且用户另行授权。draft 要明确：资源充足，可以一次性推进多个 MedNeXt candidates 和多个 jobs，但每个 candidate 必须 staged/gated/compliance-checked，失败即停，不得自动扩大到 full benchmark 或 validation upload。

完成后只输出简短 summary：创建了哪个 plan 文件、计划主题是什么、后续 goal-mode 应执行什么、哪些事情仍被禁止。