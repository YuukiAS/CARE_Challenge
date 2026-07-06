# M7 具体 executor 合同：MyoPS 最小有效训练、variant 选择与 CineMA/Cine 诊断利用

status: `MERGE_INTO_SHARED_EXECUTOR_PROMPTS`
merge_target: `prompts/shared/EXECUTOR_PROMPTS.md`
new_section: `M7 executor: concrete MyoPS training and CineMA/Cine diagnostic utilization`
expected_result_dir: `results/20260705_srr_v3_m7_training_and_cine_utilization/`

## 1. M7 启动条件

M7 只能在 M6 独立审阅通过后启动。必须确认：

- `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` 存在且包含 `M6_AUDITED_GO`；
- 如果 M7 中启用 Cine 子线，还必须确认 `results/20260705_srr_v3_m5_cine_secondary_contract/review.md` 包含 `M5_AUDITED_DIAGNOSTIC_GO`；
- M7 仍不是 route promotion、不是 validation packaging/upload、不是 hosted metric claim；
- M7 必须停止在 executor result + completion_check + review_request，不得写 `review.md`，不得启动后续 milestone。

如果 M6 未通过，写 `M7_BLOCKED_BY_M6` 并停止。Cine 子线若 M5 未通过，可以只阻塞 Cine 子线，不应阻塞 MyoPS M7 训练；但必须写清 `CINE_BLOCKED_BY_M5`。

## 2. M7 的目标

M7 是第一个允许训练 M6 修复后 concrete variants 的 milestone。它的目标不是把结果包装成 challenge candidate，而是判断 M6 修复后的 SRR-v3 是否在最小有效训练下产生可靠、可解释、可审计的 help/harm 证据，并且判断 CineMA/registration/temporal evidence 是否已经从 M5 的 diagnostic gap 走向可用的 Cine secondary diagnostic path。

M7 必须回答四个问题：

1. M6 的三个 concrete variants 在足够训练后是否有任一 variant 相对同 split nnU-Net 改善或至少不伤害关键 metric？
2. 改善或伤害来自哪里：dictionary、prototype、proposal、refiner、arbitration、loss 还是 no-T2 safety？
3. 训练是否稳定：loss 是否下降并 plateau，validation 是否稳定，不是几分钟结束的假证据？
4. CineMA 是否真正被用作 Cine anatomy/frame-quality/registration/temporal-dictionary evidence，而不是只作为 frame0 control 或文字状态？

## 3. MyoPS variant matrix

M7 必须训练并评估下列 variants，除非 M6 review 明确禁止某个 variant。Codex 不能自行缩减 matrix；如资源不足，必须按顺序训练并记录 blocker。

### 3.1 `m7_full_srr_context_arbitration`

来自 M6 的 `m6_full_srr_context_arbitration`。默认 encoder 为 `balanced_4scale` `16/32/64/128`。如果 `full_4scale` `32/64/128/256` 在 M6 smoke 中可运行，允许作为额外 high-capacity variant，但不能替代 balanced 默认。

### 3.2 `m7_conservative_component_arbitration`

来自 M6 的 `m6_conservative_component_arbitration`。它是安全/稳定对照，目标是减少 remote FP、HD95 和 component explosion。

### 3.3 `m7_scar_precision_edema_safe`

来自 M6 的 `m6_scar_precision_edema_safe`。它必须报告 scar 和 edema 分支的不同 loss、ROI、proposal、arbitration 行为，不能只给总 Dice。

### 3.4 可选 ablation variants

只有当前三项主 variant 至少完成 one-batch overfit 与 baseline sanity 后，才允许新增最多两个 ablation：

- `no_interaction_dictionary`：去掉 interaction slots；
- `frozen_prototype_bank`：prototype 固定，仅训练 proposal/refiner/arbitration。

不得跑大规模 temperature/threshold grid。阈值、温度、gate bias 只能在预先记录的有限集合中选择，且不能用 validation GT 做 case-id tuning。

## 4. 训练预算与稳定性判据

M7 不要求超过 8 小时，但必须避免几分钟结束的训练假证据。每个 MyoPS variant 必须满足以下条件之一：

- `optimizer_steps >= 3000` 且 `train_loop_seconds >= 1800`；或
- 明确达到 plateau：最近 5 个 validation events 中 primary composite objective 相对改善 `< 1%`，且各核心 loss component 没有单项爆炸；或
- 因 scheduler/OOM/bug 中止，并写 `M7_NEEDS_REVISION` 或 `M7_NEEDS_EVIDENCE`，不得写成功或失败。

推荐训练目标：

- `optimizer_steps`: `6000-12000`；
- validation interval: 每 `300-500` steps；
- eval cases: 至少 `12` 个固定 case，优先 `20` 个；
- hard subgroups: all-case、T2-present、GT-positive、no-T2 empty-GT、CenterB/CenterC、remote-FP-positive、small-lesion、large-lesion；
- one-batch overfit: 每个 variant 必须 pass；
- loss decrease: total loss 与关键 loss component 均需报告，不只总 loss。

如果训练不足 1800 秒且没有 plateau，`experiment_adequacy_decision` 必须是 `FAIL` 或 `PARTIAL`，`scientific_resolution_status` 必须是 `SCIENTIFIC_UNDERTRAINED` 或 `SCIENTIFIC_NEEDS_EVIDENCE`。不得把 undertrained run 写成 route failure 或 route promotion。

## 5. MyoPS metric 与选择规则

M7 必须用同 split nnU-Net 作为 reference，不能只和旧 SRR 比。每个 variant 必须报告：

- scar Dice、HD95、component count、remote FP、volume ratio；
- edema all-case Dice/HD95；
- edema T2-present/complete Dice/HD95；
- edema GT-positive Dice/HD95；
- no-T2 empty-GT edema stability；
- CenterB/CenterC 指标；
- per-case help/harm；
- branch arbitration chosen_source 分布；
- dictionary/prototype usage；
- proposal recall/precision proxy；
- refiner crop/residual statistics；
- label/export caveat。

Best variant selection 不是 Codex 主观判断，必须按下列规则：

1. 任何 no-T2 edema unsafe 的 variant 直接 `REJECT`；
2. 任何 scar 相比 nnU-Net 明显退化且没有 edema 大幅收益的 variant 直接 `REJECT`；
3. 首先看 primary target：`myops_scar` 与 `myops_edema` 的同 split help/harm；
4. 若 Dice 接近，优先 HD95、component_count、remote_FP 更好者；
5. 若 MyoPS 没有任何 variant 同时满足 no-T2 safety、scar non-regression 和 edema hard-subgroup improvement，则写 `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`，不得包装为成功；
6. 只有在至少一个 primary 或 critical secondary metric 明确改善，且无 catastrophic regression，且 M7 review 支持时，后续 GPT 才能考虑下一 milestone；M7 executor 本身不许 route promotion。

## 6. loss 与训练日志输出

M7 必须按 step 导出 loss component 曲线，至少包含：

- anatomy union/LV/RV；
- scar proposal；
- edema proposal T2-present；
- scar refiner ROI；
- edema refiner ROI；
- anchor preservation；
- branch arbitration consistency；
- bounded correction；
- component/remote-FP；
- no-T2 edema safety；
- dictionary entropy/coverage/load-balance；
- semantic family/interaction mass；
- prototype diversity/margin。

必须输出 `loss_component_by_step.csv` 与 `loss_component_gradient_sanity.csv`。如果某个 loss component 长期为 0，必须解释它是合法不适用还是 bug；无解释的空 loss component 是 reviewer blocker。

## 7. CineMA 的具体使用方式

M5 已经说明 CineMA/anatomy prior 目前只是部分支持，不能当成 registration 或 temporal retrieval completion。M7 若启用 Cine 子线，必须把 CineMA 用成以下三类 evidence，而不是只写“尝试过”：

### 7.1 CineMA anatomy prior

对 same-safe-subset 的 cine frames 运行或读取 CineMA/equivalent anatomy output。必须记录：

- source path、version、weights/source status；
- input preprocessing；
- frame selection；
- class mapping；
- output label/probability shape；
- myocardium/anatomy Dice/HD95 against available local reference 或 frame0 control；
- whether anatomy-only or pathology-capable。

CineMA 输出不能直接当 pathology prediction。

### 7.2 CineMA-assisted registration

构建 same-safe-subset matrix，至少包含：

- frame0/ED identity control；
- CineMA frame-wise anatomy prior control；
- CineMA + ANTsPy SyN；
- CineMA + SimpleITK Demons/B-spline fallback；
- optical-flow/feature-warp proxy，必须标为 descriptor/proxy；
- VoxelMorph，如果没有训练或可审计 weights，必须标 `UNTRAINED_NOT_USABLE`，不能进 usable registration。

每行必须报告 same case/frame、before/after anatomy Dice/HD95、Jacobian/fold proxy、round-trip/inverse consistency proxy、runtime、failure reason。one-case SyN smoke 不能作为 full registration matrix。

### 7.3 Cine temporal dictionary

如果 registration matrix 至少有一个非-reference option 合格，才允许构建 temporal dictionary。temporal dictionary 必须包括：

- ED/reference anchor features；
- selected non-reference frame features；
- warped or descriptor features；
- frame-quality score；
- motion-saliency score；
- temporal representer slot usage；
- temporal aggregation output；
- local class_1 myocardium proxy and class_3 sanity；
- hosted metric caveat。

如果 registration matrix 不合格，必须写 `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP`，不得用 frame0-only 代替 temporal retrieval。

## 8. Cine 与 MyoPS 的关系

Cine 是 secondary diagnostic，不得阻塞 MyoPS 主线训练。M7 可以把 Cine 子线作为同一 milestone 的 secondary packet，但必须分开写 MyoPS 与 Cine 的 decision：

- `myops_decision`: variant improvement / no promotion / needs revision / undertrained；
- `cine_decision`: CineMA used / registration gap remains / temporal dictionary ready or blocked；
- `combined_decision`: 不得把 Cine diagnostic success 当成 MyoPS promotion，也不得把 MyoPS failure 当成 Cine stop。

## 9. M7 必需输出文件

M7 结果写入 `results/20260705_srr_v3_m7_training_and_cine_utilization/`，必须写齐：

- `result.md`
- `m7_execution_plan.md`
- `variant_matrix.csv`
- `training_adequacy_by_variant.csv`
- `one_batch_overfit_by_variant.csv`
- `training_curve_by_variant.csv`
- `validation_curve_by_variant.csv`
- `loss_component_by_step.csv`
- `loss_component_gradient_sanity.csv`
- `prediction_sanity_by_variant.csv`
- `same_split_help_harm.csv`
- `hard_subgroup_metrics.csv`
- `branch_arbitration_by_case.csv`
- `dictionary_prototype_usage_by_variant.csv`
- `proposal_refiner_by_case.csv`
- `no_t2_safety_by_variant.csv`
- `best_variant_decision.md`
- `failure_interpretation.md`
- `cinema_usage_report.md` if Cine subline runs, otherwise `cinema_blocker_report.md`
- `registration_same_subset_matrix.csv` if Cine subline runs
- `temporal_dictionary_evidence.csv` if temporal dictionary is attempted
- `cine_metrics_summary.csv` if Cine metrics are computed
- `label_export_qc.md`
- `commands_run.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`

## 10. M7 completion states

`completion_check.md` 只能写：

- `M7_READY_FOR_REVIEW`
- `M7_NEEDS_REVISION`
- `M7_NEEDS_EVIDENCE`
- `M7_NEEDS_MONITOR`
- `M7_BLOCKED_BY_M6`

不能写 `M7_READY_FOR_REVIEW` 的情况：

- 任一必跑 MyoPS variant 没有训练且没有 blocker；
- 训练不足 1800 秒且没有 plateau；
- 没有 same-split nnU-Net help/harm；
- 没有 loss component 曲线；
- 没有 hard subgroup metrics；
- no-T2 edema unsafe；
- best variant decision 由自然语言主观判断而非 metric table 决定；
- Cine 子线声称使用 CineMA 但没有 class mapping/output path/metric 或 blocker；
- registration 被 one-case SyN/untrained VoxelMorph/frame0-only 冒充完成；
- temporal dictionary 在 registration gap 下仍被写成 ready；
- reviewer 所需轻量证据没有 git-tracked。

完成后必须 `git add -f` 并本地 commit M7 轻量证据和必要 first-party helper/source/config；不要提交 checkpoint、NIfTI、upload package、大日志、raw data、secrets、environment dump 或整棵 runtime tree；不要 push；不要写 `review.md`；不要启动后续 milestone。
