你现在在 `/overflow/htzhu/CARE` 中工作。请只创建 Lane A 下一阶段计划，不要立即执行实验、不要训练、不要提交 Slurm、不要下载权重、不要 clone 外部 repo、不要创建 validation zip、不要上传、不要修改生产代码。这个计划将作为后续 goal-mode 的大规模外部机制接入 controller；后续我会开 goal-mode 按这个 plan 尽可能向前推进，并允许在通过 gate 的前提下一次性提交较大规模 smoke jobs。

请先检查 `docs/plans/` 下的命名规则或 registry，由你决定具体文件名。计划主题必须体现以下含义：

`laneA_round16_external_mechanism_integration_large_smoke_plan`

或类似含义。

不要使用模糊文件名，例如 `next.md`、`new_plan.md`、`laneA_plan.md`。如果命名规则要求 `next`、`active`、`execution` 等状态词，请按现有规则选择，但必须清楚表达这是 Lane A Round16 的 external mechanism integration large-smoke plan。

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

重点读取 Round12-Round15 输出：

`results/diagnostics/phase0_phase1/laneA_myops/round12_refiner_salvage_high_upside_transition/`
`results/diagnostics/phase0_phase1/laneA_myops/round13_t2_lge_intensity_anatomy_consistency/`
`results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator/`
`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/`

重点读取以下关键文件：

`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/round15_decision_table.md`
`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/round15_round16_recommendation.md`
`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/round15_deep_research_need_assessment.md`
`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/baseline_vs_candidate_by_subset.csv`
`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/case_level_failure_flags.csv`
`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/centerB_centerC_edema_table.csv`
`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/no_t2_empty_gt_fp_table.csv`
`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/scar_guardrail_table.csv`
`results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/component_remote_fp_table.csv`
`round15_detailed_failure_analysis.md`，如果该文件已复制到 repo；否则在当前工作区中定位同名文件或相近文件

请在计划开头写清楚当前证据链和最新判断。

Round2 证明 edema inference postprocess route fail，小组件/ROI 删除不能作为主线。Round3 证明 loss wiring / gradient / tiny-overfit 可跑，但不代表性能。Round4 证明 `edema_focal_tversky + no_t2_edema_loss_downweighting` 在真实 fold0 short train 中 fail，原因包括 remote FP、no-T2 FP、HD95 恶化和 scar guardrail 不干净。Round5 证明 alignment 是 watch，boundary/distance 是 watch，anatomy soft prior 进入 bounded diagnostic。Round6 证明当前 anatomy soft attenuation fail；missing-modality audit 指出 no-T2 empty-GT 不能作为强 negative，explicit modality presence 和 uncertainty-weighted supervision 是后续信号。Round7 证明 first-party 6-channel modality-presence pipeline 工程上可行，但简单 presence channels + scalar no-T2 weighting 没有通过 tiny gate。Round8 证明 T2-present edema expert / separated edema supervision 的 tiny gate 有信号，但 scratch / near-scratch very-short fold0 train 全面崩溃。Round9 证明 nnU-Net501 checkpoint 可以成功迁移到 6-channel model，初始 logits 与 baseline 可做到完全一致，但 whole-network checkpoint-initialized fine-tune 只有极弱 edema signal，component / HD95 / scar guardrail 不干净。Round10 证明 add-only edema residual refiner 安全性较好，scar unchanged，no-T2 clean，但只有极小 Dice gain，HD95/component 不 clean。Round11 证明 component-safe bidirectional refiner 仍然 fail，scar unchanged、no-T2 clean，但 CenterC、remote FP 和 component guardrail 不干净。Round12 证明 deployable fallback salvage 只能作为 optional calibration，不能回到主线。Round13 证明 T2/LGE intensity prior 和 anatomy-lesion consistency 有弱信号，但 feature-only rule 不足。Round14 证明 feature-calibrator 工程链路可跑，但普通 feature-calibrator 没有 clean CenterC/T2-present improvement。Round15 成功把 first-party high-priority candidates A/B/C 跑到 fold0 very-short evaluation，但没有任何候选进入 fold0 short：A 有极弱 intensity-prior 信号但 CenterC component safety fail，B/C 基本等同 baseline fallback。Round15 的失败不是 NaN、缺 prediction、scar regression、no-T2 FP 爆炸、label/evaluator/cache 错误或 Slurm 失败，而是 first-party feature-head abstraction 缺乏足够强的 lesion-level / representation-level edema support。

请明确当前新结论：

Lane A 下一阶段不应继续普通 refiner/calibrator/feature-head 小修，不应继续直接给 A/B/C 加 epoch，不应扩 fold1-4，不应提交 validation，不应回到 Focal Tversky、小组件、hard ROI、anatomy attenuation 或 whole-network fine-tune。现在应该正式进入：

`DeepResearch-guided external mechanism integration with large controlled smoke`

用户 token、Slurm、GPU/CPU 资源充足。Round16 计划应允许后续 goal-mode 一次性推进多个外部/半外部机制，并可以批量提交多个 fold0 smoke jobs。但所有 candidate 仍必须 staged、gated、compliance-checked、label-safe、cache-isolated、metric-comparable。目标不是节省计算，而是尽快判断 Deep Research 里的高收益机制是否比 first-party 小修更有希望，并判断是否需要新一轮更窄的 deep research。

计划必须包含四个主路线和两个辅助路线。

第一主路线：

`I_MMSeg_style_strong_intensity_prior_route`

目标是从 Round15 的弱 intensity signal 出发，接入更强的 T2/LGE intensity-prior representation。不是继续使用简单 scalar feature head，而是尝试 I-MMSeg-style 或 intensity-prompt / modality-specific intensity prior 的 CARE-compatible 版本。计划应包含两个层次：第一层是 CARE-first stronger intensity-prior implementation，例如局部 T2/LGE patch features、within-myocardium intensity ranking、T2 support map、LGE/T2 contrast embedding、edema-support score；第二层是外部 I-MMSeg repo metadata/import/one-case smoke，如果合规且可接入，再进入 fold0 smoke。必须记录是否需要 GPT/CLIP/文本 prompt、是否依赖 external data、是否可用 CARE-only implementation 替代。

第二主路线：

`Cascaded_FSN_PTNet_anatomy_pathology_cascade_route`

目标是从 current weak anatomy scalar feature 升级到更结构化的 anatomy-pathology cascade。不要 hard ROI deletion，不要 simple distance attenuation。应设计 anatomy-first / pathology-second 的 CARE-compatible smoke，例如用 baseline or nnU-Net anatomy probability maps 生成 pathology ROI features，或者训练一个 small pathology head conditioned on myocardium/LV/RV support。也要对 Cascaded FSN / PT-Net-style 外部实现做 metadata/import/one-case smoke。重点判断它是否能在 CenterC/T2-present edema 上提供比 current anatomy support 更强的 lesion-level support。

第三主路线：

`Boundary_HD_component_objective_route`

目标是接入 InverseForm / surface / HD-aware / component-aware objective，但必须作为 support 已存在后的 auxiliary，而不是主导 recall。Round16 可以把它作为一个独立 smoke candidate，因为 Round15 A 的失败点是 component fragmentation。应测试 small-weight surface/HD/component penalty 是否能在 intensity/anatomy route 上抑制 CenterC component worse。若只单独训练 boundary objective，应标记为 auxiliary-only，不得作为主线。

第四主路线：

`Missing_modality_representation_route`

目标是探索 UniME / AdaMM / CoPeDiT / MoE / MMPL-Seg 等 missing-modality representation 方法。考虑到 complete-case teacher 当前不可靠，不应直接完整 AdaMM distillation。计划应优先做 metadata/compliance/import/one-case smoke，以及一个 CARE-first small MoE / modality-conditioned representation candidate。必须处理 no-T2 empty-GT 不能当 strong negative 的问题。该路线优先级中高，但需要更严格 supervision policy gate。

第一辅助路线：

`Pretrained_backbone_or_feature_route`

候选包括 MedNeXt、nnU-Net Task114/M&Ms、BiomedParse 或 Deep Research 中合规的医学/心脏 pretrained assets。目标是增强 CenterC/T2 edema representation。必须做 license、pretrained data、external data risk、weight availability、input/output compatibility audit。若可用，可以设计 one-case feature smoke 或 fold0 very-short fine-tune，不得直接 full benchmark。

第二辅助路线：

`CAA_Seg_SSA_alignment_watch_route`

当前 alignment 是 watch，因为前面没有发现强 geometry mismatch。但 Round16 可以做 metadata/one-case/CenterC-focused smoke，尤其如果 CAA-Seg/SSA 接入成本低。不得让 alignment 占用最大 batch，除非 smoke 显示 CenterC failure 与 sequence alignment 相关。

计划必须包含 `round16_large_smoke_candidate_matrix`。后续 goal-mode 应能据此生成多个 candidate config、job script、output dirs 和 result collectors。矩阵至少包含以下候选，Codex 可根据 repo 实际情况微调名称，但必须保持可追踪。

优先级 P0 / P1：

`R16_A_care_strong_t2_lge_intensity_prior_fold0_vs`
`R16_B_external_I_MMSeg_metadata_import_onecase`
`R16_C_anatomy_pathology_cascade_care_fold0_vs`
`R16_D_external_CascadedFSN_PTNet_metadata_import_onecase`
`R16_E_intensity_plus_component_surface_aux_fold0_vs`
`R16_F_small_modality_conditioned_moe_fold0_vs`
`R16_G_unime_adamm_copedit_metadata_import_onecase`
`R16_H_pretrained_mednext_or_mms_readiness_smoke`

优先级 P2 / watch：

`R16_I_inverseform_surface_loss_metadata_loss_smoke`
`R16_J_caa_seg_ssa_metadata_centerc_smoke`
`R16_K_biomedparse_feature_readiness_smoke`

每个候选必须定义 job type：metadata-only、import smoke、one-case smoke、tiny-overfit、fold0 very-short、fold0 short。计划中必须允许 goal-mode 在通过 metadata/import/one-case gate 后批量提交多个 fold0 very-short jobs，规模可以比前几轮更大。建议允许第一批同时提交 3–6 个 fold0 very-short jobs，前提是每个 candidate output dir 独立、config 独立、seed 独立、job name 清楚，不覆盖 baseline，不生成 validation zip。只有 fold0 very-short clean 的候选才进入 fold0 short。fold1-4、5-fold 和 validation submission 仍需用户另行授权。

计划必须包含合规规则。CARE 允许使用 pretrained model，但不能用 external data 训练。每个外部 repo / pretrained asset 必须记录：

repo URL
license
pretrained weights 是否使用
pretrained data 来源
是否需要 external dataset
是否只用 CARE 数据 fine-tune
是否会使用 validation pseudo-label supervised training
是否有 commercial/research-only 限制
是否可离线复现
是否改变 label semantics
是否影响 submission/export format

任何需要外部训练数据、validation pseudo-label supervised training、license 不清楚、label mapping 不清楚、raw output semantics 不清楚的候选不得进入训练。公开 pretrained weights 可以作为可能可用项，但必须记录 pretrained data 和规则风险。

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
case-level failure flags
candidate-specific diagnostics, such as intensity support score, anatomy support score, component safety, alignment score, or representation feature stats

通过标准必须严格但适合 large-smoke portfolio。候选若在 CenterC 或 T2-present edema 上无信号，或 HD95/component/remote FP 明显恶化，或 scar guardrail 不干净，或 no-T2 FP 失控，应 stop。候选若有弱信号但不 clean，watch。候选若 T2-present/CenterC 有 clear improvement 且 scar/no-T2/HD/component clean，可 promote 到 fold0 short 或 longer。任何 candidate 不允许靠 foreground mean、all-case aggregate 或 empty-GT artifact 过 gate。

计划必须包含 output root：

`results/diagnostics/phase0_phase1/laneA_myops/round16_external_mechanism_integration/`

建议输出文件至少包括：

`round16_goal_execution_readme.md`
`round16_candidate_registry.csv`
`round16_compliance_matrix.csv`
`round16_repo_metadata_audit.md`
`round16_external_import_smoke_summary.csv`
`round16_onecase_smoke_summary.csv`
`round16_large_smoke_candidate_matrix.csv`
`round16_batch_job_submission_plan.md`
`round16_batch_job_status.csv`
`round16_fold0_very_short_results.csv`
`round16_fold0_short_results.csv`
`round16_baseline_vs_candidate_by_subset.csv`
`round16_case_level_failure_flags.csv`
`round16_centerC_edema_table.csv`
`round16_no_t2_empty_gt_fp_table.csv`
`round16_scar_guardrail_table.csv`
`round16_component_remote_fp_table.csv`
`round16_candidate_decision_table.md`
`round16_external_method_readiness_update.md`
`round16_new_deep_research_need_assessment.md`
`round16_round17_recommendation.md`

如果生成 overlays 或 feature visualizations，请放在：

`results/diagnostics/phase0_phase1/laneA_myops/round16_external_mechanism_integration/overlays/`

计划必须包含阶段化 goal-mode 执行路线。至少包含以下阶段：

第一阶段：`round16_portfolio_reproducibility_gate`。复核 baseline、fold0、label semantics、metric/evaluator、cache、Round15 failure conclusions。

第二阶段：`external_candidate_compliance_and_metadata_audit`。对 I-MMSeg、Cascaded FSN/PT-Net、InverseForm/surface loss、UniME/AdaMM/CoPeDiT/MoE/MMPL-Seg、MedNeXt/M&Ms/BiomedParse、CAA-Seg/SSA 做 license、weights、data、I/O、label mapping、dependency 风险检查。

第三阶段：`import_and_onecase_smoke_for_external_candidates`。只对通过 metadata 的候选做 import、one-case、shape、label、spacing、output smoke，不训练。允许 goal-mode 下载或 clone repo 吗？计划中请明确：后续 goal-mode 可以在合规矩阵初步通过后 clone lightweight repo 或 inspect official repo metadata，但不得下载大权重或外部数据，除非计划中明确记录并用户授权。若没有网络或 repo 不可用，应记录为 blocked，不要伪造。

第四阶段：`care_first_strong_mechanism_implementation`。对无需外部 repo 即可实现的 P0 candidate 先实现 CARE-first version，例如 strong T2/LGE intensity prior、anatomy-pathology cascade、small MoE / modality-conditioned representation、intensity+component surface auxiliary。允许 goal-mode 批量生成多个 configs。

第五阶段：`first_batch_large_fold0_very_short_jobs`。对通过 gate 的优先候选批量提交 fold0 very-short jobs。用户资源充足，计划应允许第一批 3–6 个 Slurm jobs。每个 job 必须独立 output dir、config、seed、job name。若集群 pending，goal-mode 可记录 pending 并继续准备 collector，不得无限等待。

第六阶段：`automatic_result_collection_and_gate`。收集所有 very-short jobs，统一评估，生成 candidate decision table。不能手工 cherry-pick，只能按预设 gate。

第七阶段：`promoted_fold0_short_jobs`。只对通过 very-short gate 的候选提交 fold0 short jobs。允许多个 jobs，但不得提交 validation zip，不得扩 fold1-4。

第八阶段：`round17_recommendation_and_deep_research_need_assessment`。判断哪些 Deep Research 方法有信号，是否需要新一轮更窄 deep research。如果所有 high-upside candidates 都失败，则建议新 deep research 聚焦：CenterC/T2 edema representation、T2 intensity prior、edema label ambiguity、missing-modality supervision、component-aware lesion support，而不是泛泛 cardiac segmentation。

计划末尾必须写一个完整中文 `Next Goal Execution Prompt Draft`，供用户后续直接开 goal-mode 使用。这个 draft 应要求 Codex 尽可能推进 Round16：建立候选注册表和合规矩阵；对 Deep Research 外部候选做 metadata audit、import/one-case smoke；实现 CARE-first strong intensity/anatomy/MoE candidates；生成并批量提交多个 fold0 very-short Slurm jobs；收集结果；只对通过 gate 的候选继续 fold0 short；输出统一指标和决策表。draft 必须仍然禁止 validation submission，禁止 fold1-4/5-fold，除非 fold0 candidates clean 且用户另行授权。draft 要明确：资源充足，可以一次性推进多个候选和多个 jobs，但每个 candidate 必须 staged/gated/compliance-checked，失败即停，不得自动扩大到 full benchmark 或 validation upload。

完成后只输出简短 summary：创建了哪个 plan 文件、计划主题是什么、后续 goal-mode 应执行什么、哪些事情仍被禁止。