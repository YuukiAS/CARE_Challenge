你现在在 `/overflow/htzhu/CARE` 中工作。请只创建 Lane A 下一阶段计划，不要立即执行实验、不要训练、不要提交 Slurm、不要下载权重、不要 clone 外部 repo、不要创建 validation zip、不要上传、不要修改生产代码。这个计划将作为后续 goal-mode 的大规模执行 controller；后续我会开 goal-mode 按这个 plan 尽可能向前推进，并允许在通过 gate 的前提下批量提交多个 fold0 job。

请先检查 `docs/plans/` 下的命名规则或 registry，由你决定具体文件名。计划主题必须体现以下含义：

`laneA_round15_deepresearch_portfolio_batch_execution_plan`

或类似含义。

不要使用模糊文件名，例如 `next.md`、`new_plan.md`、`laneA_plan.md`。如果命名规则要求 `next`、`active`、`execution` 等状态词，请按现有规则选择，但必须清楚表达这是 Lane A Round15 的 DeepResearch-guided portfolio batch execution plan。

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

重点读取 Lane A 相关计划与输出：

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

重点读取 Round10-Round14 输出：

`results/diagnostics/phase0_phase1/laneA_myops/round10_edema_refiner/`
`results/diagnostics/phase0_phase1/laneA_myops/round11_component_safe_refiner/`
`results/diagnostics/phase0_phase1/laneA_myops/round11_component_safe_refiner/failure_case_summary/`
`results/diagnostics/phase0_phase1/laneA_myops/round12_refiner_salvage_high_upside_transition/`
`results/diagnostics/phase0_phase1/laneA_myops/round13_t2_lge_intensity_anatomy_consistency/`
`results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator/`

重点读取以下关键文件：

`results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator/round14_decision_table.md`
`results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator/round14_round15_recommendation.md`
`results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator/feature_only_rule_grid.md`，如果存在
`results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator/round14_component_model_smoke.csv`，如果存在
`results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator/round14_external_method_readiness_matrix.md`，如果存在

也请读取已有实现文件，判断哪些可以复用：

`src/care_myocardium/refiner/`
`src/care_myocardium/calibrator/`
`src/care_myocardium/nnunet/`
`scripts/diagnostics/laneA_round*.py`
`scripts/training/run_laneA_round*.py`
`jobs/nnUNet/`

计划开头必须写清楚当前证据链和最新阶段判断。

Round2 证明 edema inference postprocess route fail，小组件/ROI 删除不能作为主线。Round3 证明 loss wiring / gradient / tiny-overfit 可跑，但不代表性能。Round4 证明 `edema_focal_tversky + no_t2_edema_loss_downweighting` 在真实 fold0 short train 中 fail，原因包括 remote FP、no-T2 FP、HD95 恶化和 scar guardrail 不干净。Round5 证明 alignment 是 watch，boundary/distance 是 watch，anatomy soft prior 进入 bounded diagnostic。Round6 证明当前 anatomy soft attenuation fail；missing-modality audit 指出 no-T2 empty-GT 不能作为强 negative，explicit modality presence 和 uncertainty-weighted supervision 是后续信号。Round7 证明 first-party 6-channel modality-presence pipeline 工程上可行，但简单 presence channels + scalar no-T2 weighting 没有通过 tiny gate。Round8 证明 T2-present edema expert / separated edema supervision 的 tiny gate 有信号，但 scratch / near-scratch very-short fold0 train 全面崩溃。Round9 证明 nnU-Net501 checkpoint 可以成功迁移到 6-channel model，初始 logits 与 baseline 可做到完全一致，但 whole-network checkpoint-initialized fine-tune 只有极弱 edema signal，component / HD95 / scar guardrail 不干净。Round10 证明 add-only edema residual refiner 安全性较好，scar unchanged，no-T2 clean，但只有极小 Dice gain，HD95/component 不 clean。Round11 证明 component-safe bidirectional refiner仍然 fail，scar unchanged、no-T2 clean，但 CenterC、remote FP 和 component guardrail 不干净。Round12 证明 deployable fallback salvage 只能作为 optional calibration，不能回到主线。Round13 证明 T2/LGE intensity prior 和 anatomy-lesion consistency 有弱信号，但 feature-only rule 不足。Round14 证明 feature-calibrator 工程链路可跑，component logistic 和 voxel/patch tiny smoke 可学习，但没有 clean CenterC/T2-present improvement beyond strict_support_filter，因此普通 CARE-first refiner/calibrator 不能继续作为主线。

请明确当前新结论：

Lane A 下一阶段不应继续普通 refiner/calibrator 小修，不应继续直接加 epoch，不应扩 fold1-4，不应提交 validation，不应回到 Focal Tversky、小组件、hard ROI、anatomy attenuation 或 whole-network fine-tune。当前需要进入 DeepResearch-guided controlled portfolio batch stage。用户 token、Slurm、GPU 资源充足，可以提交一批 fold0 job 等待结果；但必须是 staged、gated、comparable、compliance-checked 的批量实验，而不是无差别乱跑 repo。目标是快速判断 Deep Research 中的高收益方向在 CARE 上是否有足够信号，以及是否需要新一轮更窄的 deep research。

计划必须包含一个 `portfolio_hypothesis_table`。请把候选方向按机制而不是按 repo 名归类，并给出优先级、预期收益、风险、实现方式、是否需要外部 repo、是否需要预训练权重、是否允许批量 job、fail-fast 标准。

必须至少包含以下机制槽位。

第一，`I_MMSeg_style_T2_LGE_intensity_prior_route`。目标是把 Round12/13/14 的 T2/LGE intensity weak signal 提升为可学习的 stronger intensity prior。第一阶段不应完整复现 CLIP/GPT pipeline，而应做 CARE-first intensity-prior feature model；如果需要外部 I-MMSeg repo，应先 metadata audit / one-case smoke。该路线优先级最高。

第二，`Cascaded_FSN_PTNet_anatomy_pathology_consistency_route`。目标是把 anatomy 作为结构化 lesion support，而不是 hard ROI 或 distance attenuation。可以尝试 baseline myocardium/LV/RV probability maps、anatomy distance maps、component support features、lesion-anatomy consistency loss 或 two-stage pathology head。优先级高。

第三，`Boundary_HD_InverseForm_surface_auxiliary_route`。目标是解决 HD95/component/remote edge activation，但只能作为小权重辅助或 later-stage objective，不能像 Focal Tversky 那样主导 recall。优先级中等。

第四，`Missing_modality_representation_route`。候选包括 UniME、AdaMM、CoPeDiT、MoE、MMPL-Seg。目标是解决 no-T2 supervision ambiguity 和 modality-conditioned representation。由于 complete-case teacher 当前不可靠，这条线优先做 metadata/readiness、one-case smoke、small first-party MoE/modality-conditioned head，而不是完整 distillation。优先级中高，但训练风险高。

第五，`Pretrained_backbone_feature_route`。候选包括 MedNeXt、nnU-Net Task114/M&Ms、BiomedParse 或其他 Deep Research 中提到的公开预训练资产。目标是增强 baseline representation，尤其 CenterC/T2 edema。必须做 license/compliance、pretrained data、external data risk audit。优先级中高。

第六，`CAA_Seg_SSA_alignment_route`。当前 alignment 是 watch，因为 Round5 没发现强 geometry mismatch；但如果 implementation cost low，可做 metadata/one-case smoke 或 CenterC-focused alignment feasibility job。优先级中等偏低，不应占用最大 batch。

计划必须包含一个 `round15_batch_job_matrix`，用于后续 goal-mode 一次性生成并可选择性提交多个 job。矩阵至少应包含以下候选实验，具体命名可由 Codex 调整，但必须可追踪：

`R15_A_intensity_prior_feature_head_fold0_vs`
`R15_B_anatomy_pathology_cascade_fold0_vs`
`R15_C_intensity_plus_anatomy_support_head_fold0_vs`
`R15_D_boundary_surface_auxiliary_fold0_vs`
`R15_E_modality_conditioned_moe_small_fold0_vs`
`R15_F_pretrained_or_MedNeXt_readiness_smoke`
`R15_G_external_I_MMSeg_metadata_onecase_smoke`
`R15_H_external_CascadedFSN_or_PTNet_metadata_onecase_smoke`
`R15_I_external_InverseForm_metadata_loss_smoke`
`R15_J_CAA_Seg_SSA_metadata_centerC_smoke`

每个候选必须有明确的 job type：metadata-only、one-case smoke、tiny-overfit、fold0 very-short, fold0 short。计划中必须规定：metadata-only 和 one-case smoke 先跑；只有通过 import/shape/label/cache gate 的候选才允许 Slurm fold0 very-short；只有 fold0 very-short 有 clean signal 的候选才进入 fold0 short。用户允许后续 goal-mode 提交多个 Slurm jobs，但不得跳过 gate。不得提交 validation zip。不得扩 fold1-4，除非 fold0 short/longer clean 且用户另行授权。

计划必须包含合规规则。CARE 允许使用 pretrained model，但不能使用 external data 进行训练。每个外部 repo / pretrained asset 必须记录：repo URL、license、pretrained weights 是否使用、pretrained data 来源、是否需要 external dataset、是否只用 CARE 数据 fine-tune、是否会引入 validation pseudo-label supervised training、是否有商业/研究限制、是否可离线复现。任何需要外部训练数据、validation pseudo-label supervised training、license 不清楚、label mapping 不清楚的候选不得进入训练。

计划必须包含统一评估规则。所有候选都必须和 nnU-Net501 fold0 baseline 比较，并分别报告：

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
case-level failure flags
training stability
cache/label/evaluator integrity

通过标准必须严格但适合 portfolio stage。候选若在 CenterC 或 T2-present edema 上无信号，或者 HD95/component/remote FP 明显恶化，或者 scar guardrail 不干净，或者 no-T2 FP 失控，应 stop。候选若有弱信号但不 clean，watch。候选若 T2-present/CenterC 有 clear improvement 且 scar/no-T2/HD/component clean，可 promote 到 fold0 short 或 longer。任何 candidate 不允许靠 foreground mean、all-case aggregate 或 empty-GT artifact 过 gate。

计划必须包含 output root：

`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/`

建议输出文件至少包括：

`round15_goal_execution_readme.md`
`round15_candidate_registry.csv`
`round15_compliance_matrix.csv`
`round15_repo_metadata_audit.md`
`round15_batch_job_matrix.csv`
`round15_batch_job_submission_plan.md`
`round15_import_onecase_smoke_summary.csv`
`round15_fold0_very_short_results.csv`
`round15_fold0_short_results.csv`
`round15_baseline_vs_candidate_by_subset.csv`
`round15_case_level_failure_flags.csv`
`round15_centerC_edema_table.csv`
`round15_no_t2_empty_gt_fp_table.csv`
`round15_scar_guardrail_table.csv`
`round15_candidate_decision_table.md`
`round15_round16_recommendation.md`

如果生成 overlays 或 feature visualizations，请放在：

`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/overlays/`

计划必须包含阶段化 goal-mode 执行路线。至少包含以下阶段：

第一阶段：`round15_portfolio_reproducibility_gate`。复核 baseline、fold0、label semantics、metric/evaluator、cache、Round14 conclusions。

第二阶段：`candidate_compliance_and_metadata_audit`。对所有外部/预训练候选做 license、weights、data、I/O、label mapping、dependency 风险检查。

第三阶段：`candidate_import_and_onecase_smoke`。只对通过 metadata 的候选做 import/one-case/shape/label smoke，不训练。

第四阶段：`first_batch_fold0_very_short_jobs`。对通过 one-case smoke 的优先候选批量提交 fold0 very-short jobs。允许多个 jobs，但每个必须独立 output dir、config、seed、job name，且不覆盖 baseline。

第五阶段：`automatic_result_collection_and_gate`。收集所有 job，统一评估，生成 candidate decision table。

第六阶段：`promoted_fold0_short_jobs`。只对通过 very-short gate 的候选提交 fold0 short jobs。允许多个 jobs，但不得提交 validation zip，不得扩 fold1-4。

第七阶段：`round16_recommendation_and_deep_research_need_assessment`。判断哪些 Deep Research 方法有信号，是否需要新一轮更窄 deep research。如果所有 high-upside candidates 都失败，则建议新 deep research 聚焦于 CenterC/T2 edema representation、T2 intensity prior、edema label ambiguity、missing-modality supervision，而不是泛泛搜索。

计划末尾必须写一个完整中文 `Next Goal Execution Prompt Draft`，供用户后续直接开 goal-mode 使用。这个 draft 应要求 Codex 尽可能推进 Round15：建立候选注册表和合规矩阵；对 Deep Research 候选进行 metadata audit；通过者做 import/one-case smoke；生成并可提交一批 fold0 very-short Slurm jobs；收集结果；只对通过 gate 的候选继续 fold0 short；输出统一指标和决策表。draft 必须仍然禁止 validation submission，禁止 fold1-4/5-fold，除非 fold0 candidates clean 且用户另行授权。draft 要明确：资源充足，可以一次性推进多个候选和多个 jobs，但每个 candidate 必须 staged/gated/compliance-checked，失败即停，不得自动扩大到 full benchmark 或 validation upload。

完成后只输出简短 summary：创建了哪个 plan 文件、计划主题是什么、后续 goal-mode 应执行什么、哪些事情仍被禁止。