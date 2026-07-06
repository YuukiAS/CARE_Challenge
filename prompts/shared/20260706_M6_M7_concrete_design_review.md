# 20260706 M6/M7 具体设计审阅结论

status: `DESIGN_ADDENDUM_FOR_SHARED_PROMPTS`
scope: `prompts/shared` 中 M6/M7 相关 executor/reviewer 文档
planner: `ChatGPT/GPT thread`
intended_merge_target:
  - `prompts/shared/EXECUTOR_PROMPTS.md`
  - `prompts/shared/REVIEWER_PROMPTS.md`

## 0. 图像读取与证据边界

当前仓库规则要求：SRR-v2、SRR-v2.5、SRR-v3 以及后续版本的架构图必须通过 ChatGPT Project background materials 或当前对话上传图片进行视觉读取；GitHub connector 暴露的 PNG blob、SHA、base64 metadata、文件名或旧总结都不能替代视觉读取。

本次审阅中，Project background 的三张 canonical 图没有在当前可检索文件库中找到；GitHub connector 也只能确认仓库 PNG 文件存在和 SHA，不能稳定提供视觉内容。因此，本文件不能声称 `visual_read_status: READ_FROM_PROJECT_BACKGROUND`。本文件基于仓库中已经可读、可审计的文本与源码证据来补足 M6/M7 的具体实现合同：

- `START_HERE_FOR_GPT.md` 与 `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md` 的当前图片规则；
- `results/figures/srr_myops_architecture.py` 与其 caption 中可读出的 SRR-MyoPS 模块结构；
- `results/20260705_srr_v3_m0_architecture_master_contract/review.md`；
- `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md`；
- `results/20260705_srr_v3_m3_myops_min_effective_pilot_training/review.md`；
- `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md` 与 `mechanism_decision.md`；
- `results/20260705_srr_v3_m5_cine_secondary_contract/review.md`；
- 当前 SRR 相关源码，尤其是 `src/care_myocardium/models/srr_blocks.py`、`src/care_myocardium/models/srr_v2_unet.py`、`src/care_myocardium/models/srr_propref.py`、`src/care_myocardium/losses/srr_losses.py` 和 `scripts/training/run_srr_propref_myops_fold0.py`。

合并本 addendum 时不能把它写成“已经完成 Project-background 图像读取”。如果后续 executor/reviewer 需要正式记录 diagram bootstrap，必须由能访问 Project background 或当前对话图片的线程补上 `diagram_versions_read` 与 `visual_read_status`。不过，M6/M7 的实现细节不能再留给 Codex 自行发挥；本文件以下内容应作为 GPT 设计决定进入 shared prompts。

## 1. 总体判断

M6/M7 不能再停留在“按图实现”“补足机制”这类抽象表述。当前已有证据说明：M3 训练不是几分钟 smoke，而是达到了最低有效 pilot 预算；它能训练、能输出 12 个 eval cases 的预测和 gate/prototype 统计，但相对同 split nnU-Net 是负向的。M4 进一步说明 closed-gate identity 本身是中性的，no-anchor 很伤，trained gate 几乎关闭，但 proposal/refinement/decode 仍然能改标签。也就是说，问题不是“nnU-Net fallback 是否存在”，而是 SRR 证据、proposal、refiner、decode 和 arbitration 没有形成一个可控、可解释、可训练的联合机制。

M6 应是实现修复 milestone，不应训练 full fold，也不应 route promotion。M6 的目标是把当前 SRR-v3 从“能运行的 bounded prototype”提升到“每个设计模块都能在 forward/loss/runtime evidence 中被明确调用、校准、约束、审计”的状态。

M7 应是 M6 通过独立审阅之后的最小有效训练与 Cine 诊断利用 milestone。M7 不能只跑一个几分钟 job，也不能只看 loss 降了；必须训练到稳定证据、定期验证，并对预定义 variant 做同 split nnU-Net help/harm、hard subgroup、loss component、branch arbitration、no-T2 safety 和 CineMA/registration/temporal dictionary 证据的完整判断。

## 2. nnU-Net 的位置

nnU-Net 应放在“强分割证据接口”和“安全 fallback”位置，而不是唯一主角，也不是被 SRR 无约束覆盖的靶子。M6/M7 必须把 nnU-Net 的以下对象作为显式输入：

- probabilities 或 logits；
- hard prediction；
- scar/edema connected components；
- per-class confidence、entropy、margin、uncertainty；
- anatomy/union support 或从 anchor prediction 派生的 anatomy context；
- component size、component distance、remote component 统计。

这些输入必须进入 proposal、refiner 和 branch arbitration。final output 可以等于 nnU-Net，但只能在 explicit safety fallback 或 arbitration 选择 anchor 时发生，并且必须记录 reason。若 final output 在没有 explicit reason 时直接绕过 SRR/proposal/refiner 等于 nnU-Net，M6/M7 reviewer 必须判为 `NEEDS_REVISION`。

## 3. encoder/decoder 深度

当前代码已有 `strong_4scale` 路径和 `base_channels=8` smoke 证据，但这不足以作为 M6/M7 的最终网络设计。M6 必须明确实现并报告三档 encoder profile：

1. `full_4scale`: channel profile `32/64/128/256`，用于 architecture-fidelity smoke 或局部 patch smoke；如显存不够，必须记录 OOM/内存证据，不得静默降级。
2. `balanced_4scale`: channel profile `16/32/64/128`，作为 M7 训练的默认候选。
3. `safe_4scale`: channel profile `12/24/48/96` 或 `8/16/32/64`，只允许在 full/balanced 确认不可运行时使用；使用时必须把 capacity caveat 写入结果和 review request。

禁止把三尺度 `10/20/40` 或仅 tiny smoke 当成 SRR-v3 的有效架构证据。decoder 也不能只是最浅的 shared head：M6 必须保留 anatomy、scar、edema 三个 task-specific decoder，并报告每个 decoder 的输入尺度、skip connection、输出 shape、参数量和是否实际参与 loss/backward。

## 4. dictionary 设计必须具体化

M6 不能只说“multi-slot dictionary”。必须实现以下至少两套可选 dictionary，并在 M7 训练中按预定义规则选择表现最好的，而不是让 Codex 临场设计。

### 4.1 默认完整 dictionary：`dict_full_interaction`

每个尺度包含：

- shared slots: `K_shared=8`；
- LGE-private slots: `K_lge=4`；
- C0-private slots: `K_c0=4`；
- T2-private slots: `K_t2=4`；
- interaction slots: `K_lge_t2=4`、`K_lge_c0=4`、`K_t2_c0=4`。

每个 task 有独立 router：`router_anatomy`、`router_scar`、`router_edema`。router query 至少包含 pooled scale feature、availability vector、nnU-Net anchor summary、anchor uncertainty、component summary。无对应 modality 时 private/interaction slots 必须被 mask；T2 缺失时 T2-private 与含 T2 interaction slots 对 edema 不能被当作 evidence。

### 4.2 保守 dictionary：`dict_conservative_private_shared`

每个尺度包含：

- shared slots: `K_shared=6`；
- LGE-private slots: `K_lge=4`；
- C0-private slots: `K_c0=2`；
- T2-private slots: `K_t2=4`；
- no interaction slots，或者只保留 `LGE-T2` interaction `K_lge_t2=2`。

该 variant 作为稳定性对照，防止 interaction dictionary 过度自由导致 remote FP。它不能替代 full dictionary 的实现；它只是 M7 variant matrix 中的一个候选。

### 4.3 dictionary runtime 必须导出

每个 variant 必须导出：slot usage、gate entropy、top-k active slots、inactive slots、collapse warning、availability pattern coverage、task-specific family mass、interaction mass、T2-private usage in no-T2 cases、dictionary regularizer value、dictionary gradient norm。没有这些字段，不能写 `M6_READY_FOR_REVIEW`。

## 5. prototype / hard negative 设计

当前 M2 修复了 T2-present edema prototype coverage 的 smoke 级空银行问题，M3 记录了非空 edema prototype coverage。但 M6/M7 不能只满足“非空”。prototype 必须有来源、类别、安全策略和 leakage 策略。

M6/M7 必须构建四类 prototype bank：

- scar-positive：来自 train/OOF 中 scar GT 或 anchor high-confidence scar TP region；
- scar-safe-negative：outside myocardium、blood pool、normal myocardium far from scar、LGE artifact/hard FP；
- edema-positive：只能来自 T2-present 且 edema-labeled evidence；
- edema-safe-negative：只能来自 T2-present normal myocardium far from edema、outside myocardium、blood pool、reviewed artifact/hard FP；no-T2 myocardium 不能作为 edema negative。

每个 bank 至少报告 case count、component count、voxel count、feature stage、prototype count、source paths、是否来自 train/OOF、是否包含 validation leakage。M7 训练前如果 edema-positive 或 edema-safe-negative 为空，必须停止为 `M7_NEEDS_EVIDENCE`，不得回退到 random prototype 并继续训练。

## 6. proposal 与 refiner

proposal 不能是一层 dense head。M6 必须把 scar proposal 和 edema proposal 分开，并且每个 proposal logits 的数学构成必须可解释：

`proposal = positive_similarity - negative_similarity + anchor_component_evidence + anatomy_distance_prior + uncertainty/context evidence + learned residual`

scar proposal 必须 LGE-dominant、高精度、remote-FP 敏感；edema proposal 必须 T2-conditioned，no-T2 时 proposal logits、refiner logits、decode/export 全链路安全关闭。

refiner 必须是真正 bounded soft-ROI crop refiner，不是 full-volume residual。scar refiner 默认小 ROI，目标是高精度和 remote FP 抑制；edema refiner 默认较大 ROI，目标是 T2-present diffuse lesion coverage，但 no-T2 时完全 inert。每个 refiner 必须消费 original modality crop、proposal、anchor logits/probabilities、component evidence、prototype similarity、dictionary feature、anatomy prior、distance map、uncertainty。输出必须是 bounded local correction，并导出 crop ratio、crop bounds、residual magnitude、proposal recall/precision proxy、component/remote-FP proxy。

## 7. loss 必须补足

当前 `srr_total_loss` 只有 anatomy、scar、T2-masked edema、prior、retrieval 和 semantic retrieval，不足以支撑 M6/M7。M6 必须补充或重构 loss，使其至少包含：

- anatomy loss：`P_union/P_LV/P_RV` 的 CE/Dice 或 DiceCE；
- scar proposal loss：scar candidate BCE/Dice、positive-vs-negative prototype margin、hard-negative/remote-FP penalty；
- edema proposal loss：只在 T2-present labeled evidence 上计算；
- scar refiner loss：ROI 内 BCE/Dice、boundary/distance/HD surrogate、remote-FP penalty；
- edema refiner loss：T2-present ROI/context loss、no-T2 zero/inert regularizer；
- segmentation anchor preservation：ROI 外或 arbitration 选择 anchor 时保持 nnU-Net；
- branch arbitration consistency：训练 arbitration 选择更可信证据，并在 fallback/closed gate 时保证 label identity；
- bounded correction penalty：限制 delta magnitude、gate area、component explosion；
- dictionary/prototype regularization：slot entropy、coverage、load balance、semantic family mass、interaction mass、prototype diversity；
- no-T2 safety loss/report：no-T2 不贡献 edema negative dense loss，但必须惩罚 no-T2 edema emission。

M6 reviewer 必须看到每一项 loss 的非空数值、是否参与 backward、gradient norm 或 one-step update sanity。M7 必须按 step 导出 loss component 曲线，不能只有 total loss。

## 8. registration 与 CineMA

M5 已经证明：CineMA/anatomy prior 目前只是 `PARTIAL_SUPPORTED_ANATOMY_ONLY`，frame0 CineMA 是 control，不是 registration；ANTsPy SyN 只有 one-case smoke；VoxelMorph 是 untrained adapter，不是 usable registration；temporal dictionary 仍是 `TEMPORAL_DICTIONARY_NOT_READY`。这意味着 CineMA 尚未被充分利用。

M7 的 Cine 线必须把 CineMA 明确变成 anatomy prior 和 frame-quality/router evidence，而不是继续停留在“尝试过”的文字层面。M7 必须至少完成同一 safe subset 上的 matrix：

- frame0/ED identity control；
- CineMA frame-wise anatomy prior；
- CineMA + ANTsPy SyN；
- CineMA + SimpleITK Demons/B-spline fallback；
- optical-flow/feature-warp proxy，只能标为 descriptor/proxy；
- VoxelMorph，只有在有训练或可审计 public weights 时才能进入 usable registration，否则必须标 `UNTRAINED_NOT_USABLE`。

每个 registration row 必须报告 same cases、same frames、input/output paths、class mapping、Dice/HD95 before/after、Jacobian/fold proxy、inverse consistency 或 round-trip proxy、runtime、failure reason。没有 same-safe-subset matrix，不能称为 registration completion。

CineMA 输出不能直接被当成 pathology prediction。它只能提供 myocardium/anatomy support、frame quality、motion saliency、registration target/context。Cine pathology 仍应与已有 `pathology_direct` / `topology_lcc` / temporal dictionary evidence 分开比较，并保留 hosted metric caveat。

## 9. 训练时长和稳定性

M7 不能再允许几分钟结束的训练被写成 formal evidence。M7 不要求超过 8 小时，但必须训练到稳定证据：

- one-batch overfit 必须 pass；
- 每个 MyoPS variant 至少 `3000` optimizer steps 且 `train_loop_seconds >= 1800`，除非提前满足稳定 plateau；
- 推荐目标为 `6000-12000` steps，验证间隔 `300-500` steps；
- 至少 12 个固定 eval cases，优先 20 个，覆盖 T2-present、no-T2、CenterB/CenterC、GT-positive、remote-FP-positive；
- plateau 定义：最近 5 个 validation points 中 primary target 或 composite objective 的相对改善低于 `1%`，且 loss component 无明显单项爆炸；
- 如果不足 1800 秒且没有 plateau，必须写 `SCIENTIFIC_UNDERTRAINED` 或 `M7_NEEDS_MONITOR`，不能写失败或成功。

## 10. M6/M7 文件合并原则

合并到 `prompts/shared/EXECUTOR_PROMPTS.md` 时，M6 应替换当前较抽象的 diagram-faithful prompt；M7 应新增为 M6 后的训练/选择/Cine utilization milestone。合并到 `prompts/shared/REVIEWER_PROMPTS.md` 时，reviewer 必须逐项检查本文件中的具体字段，而不是只看自然语言 claim。

Codex 只能实现这里已经决定的 variant、loss、registration matrix 和 selection rules。Codex 不负责选择研究方向；如果某个设计不可实现，Codex 必须写 `NEEDS_EVIDENCE`、`NEEDS_REVISION` 或 `NEEDS_GPT_PLANNER`，不得自行替换为更省事的路线。
