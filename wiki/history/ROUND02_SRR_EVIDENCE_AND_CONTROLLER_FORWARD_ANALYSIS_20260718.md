# Round02 SRR 历史证据与 Controller-forward 路线分析

- 日期：2026-07-18
- 类型：Planner 历史证据分析，不是 route contract 或 runtime review
- 远端证据基线：`main@fbd76a9c254846f3a5e88766330b15210e8d76fa`
- Route Planner commits：A `bb522e1b2be7ce671db0026a4b94cc1d18937780`；B `77fbde2e1936d19c9f0d6dc711ea37b4ae077eac`；C `fbf02a5883b0f08c0f2d9268a68dc486ae956d8e`
- 本地状态：`NOT_VERIFIED_REMOTE_ONLY`。若 `/users/a/e/aereinh/CARE` 有未推送提交，远端判断可能过时。
- 权限边界：本报告不授权 Controller、validation、route promotion、M11、cross-route merge、hosted metric 或最终科学决定。

本报告系统整理 M9、M10 与 Route A/B/C Round02 的结果证据，判断哪些历史 SRR 不是 nnU-Net near-identity、结果为何仍弱于 nnU-Net，并给出后续 controller-forward 修订方向。视觉架构基线为 Project 背景中的 SRR-v2、v2.5、v3：availability-aware modality evidence、shared/private/interaction retrieval、anatomy-guided scar/edema proposal、pathology-specific soft-ROI refinement，以及真实进入 final output 的 Cine registration/temporal path。nnU-Net 只能作为 anchor、context、evidence 或 safety source。

## 第一部分：总判断

### 1. 已确认的非 near-identity SRR

严格口径下，正式训练充分、由 SRR-main 形成最终输出、且有同一划分指标的版本共有三个，均来自 M9：

- `m9_srr_main_true_br2_pattern_sip`
- `m9_srr_main_lesion_proposal_memory`
- `m9_srr_main_t2_edema_recall_focus`

它们不是 nnU-Net 原样输出。M9 明确记录 `SRR_MAIN_NOT_ANCHOR_RESIDUAL`，每个候选均训练至少 7200 秒。然而三者相对同一划分 nnU-Net anchor 全部退化，属于“真实但有害的非 identity”。

宽口径下，M10 的 D0、D1、D2、D3、hard-negative refresh、no-context、alignment 七个阶段/控制输出也有不同指标，可视为 `UNDER_REVIEWED_NONIDENTITY`；但旧 evaluator 可复制历史 metrics，selected checkpoint 仍是 `SELECTED_PRELIMINARY_PENDING_VALIDATOR`，D2/D3 final-path intervention 未闭环，不能作为正式科学结论。

Route B 旧 implementation gate 证明多个 MyoPS/Cine 模块开关会改变 final logits，因此不是 identity；但评估只有 10 个 MyoPS、5 个 Cine case，且 MyoPS edema GT 全空，只能算实现信号。Route C 的单病例 intervention 也只能说明局部节点有作用，不能算正式候选。

### 2. Route A 建议暂停，不永久删除

建议当前状态为：

`ROUTE_A_PORTFOLIO_RECOMMENDATION=DEFERRED_FALLBACK_NOT_ACTIVE`

Route A 不应继续作为活跃 Controller/GPU 路线。旧正式 run 已完成 169694 optimizer steps、1800 秒和 44-case eval，但 44/44 MyoPS rows 的 `route_changed_voxels=0`；`myops_scar=0.022727`，唯一 T2-present edema-positive case 的 edema Dice 为 0。整体 edema 0.977 主要来自 no-T2/empty-GT，不能解释为能力。

Round02 A 若修好，必须补 proposal/refiner、gate、soft ROI、CineMA、SyN、temporal、validator、known-bad 和 state machine，已接近 Route B 的压缩子集。Deep Research 正在冻结这些相同设计；继续独立修 A 会重复实现并占用时间。

但不建议直接永久删除。若 Route B 在 implementation gate 前出现不可修复的时间、显存或依赖 blocker，可依据 Deep Research 结果执行一次最多 24 小时、带强制 MyoPS nonzero-effect gate 的压缩 fallback。若 Route B 通过 implementation gate，则 Route A 保持 reviewed negative/fallback，不再单独迭代。永久删除 Route A 或降低永久矩阵要求仍需用户明确授权。

### 3. Route B 与 Route C 的区别

- Route B 问：完整且正确实现 SRR-v3 后，能否形成新的模型候选？
- Route C 问：历史 M10 到底真实做了什么，哪些 checkpoint、component 和 Cine 资产可以可信继承？

| 维度 | Route B | Route C |
| --- | --- | --- |
| 性质 | 前瞻性模型构建与训练 | 回溯性 evidence/fidelity 与资产审计 |
| 模型自由度 | 可吸收 Deep Research 后冻结完整 SRR-v3 实现 | 必须保留 M10/follow-up/follow-up2 合同，不得自由改写 |
| MyoPS | 新四尺度 SRR、OOF memory、proposal/refiner、bounded correction | fingerprint、条件精确重训、fresh all-checkpoint replay、anchor-relative selector、D2/D3 intervention |
| checkpoint | 新 Route B 训练 | 旧 M10 checkpoint；仅 fingerprint mismatch 才按原 phase 重训 |
| Cine | 构建新候选的 CineMA + registration + temporal | 证明旧 Cine 链是否 faithful、补足完整 evidence burden |
| 不继承事项 | 不继承 M10 replay、D2/D3 repair、旧 selector 大包袱 | 全部继承旧 M10 硬门，不得裁剪 |

两条路线会共享 CineMA/registration/temporal 的技术问题，但当前禁止静默 cross-route merge。Route C 资产只有经独立 review 和后续 reconciliation 绑定 commit/hash 后，才能进入 Route B。

## 第二部分：判定分类

- `NEAR_IDENTITY`：正式 final labels 与 anchor 零或近零差异；只有配置、usage、summary 或 decode 变化。旧 Route A 是明确案例。
- `NONIDENTITY_HARMFUL`：SRR-owned 或 bounded correction 真实改变 final output，但 Dice、HD95、remote-FP 或困难子组整体更差。M9 三个正式候选属于此类。
- `WEAK_POSITIVE_LOCAL`：单类、单 checkpoint 或 local proxy 有改善，但另一类受损，或缺 clean reload、完整子组和 hosted-facing metric。
- `UNDER_REVIEWED_NONIDENTITY`：输出有差异，但缺 fingerprint、`--evaluate --force`、anchor-relative selector、selected reload、final-path intervention、strict validator 或独立 review。M10 preliminary 与旧 Route B 属于此类。

## 第三部分：关键结果证据

### M9 正式候选

nnU-Net anchor：scar Dice 0.587634，edema Dice 0.711389。

| candidate | scar Dice / delta | edema Dice / delta | mean Dice delta | HD95 delta | remote-FP delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| true BR2 Pattern-SIP | 0.568263 / -0.019371 | 0.646942 / -0.064447 | -0.041909 | +14.723931 | +2.281250 |
| lesion proposal memory | 0.529388 / -0.058247 | 0.657741 / -0.053648 | -0.055947 | +14.009386 | +1.760417 |
| T2 edema recall focus | 0.546225 / -0.041409 | 0.632612 / -0.078777 | -0.060093 | +21.322525 | +6.614583 |

三者均完成约 26k–30k steps、7200 秒、20 次 validation，不能简单归因于 smoke。M9 Cine 只在 12 个 safe train cases 上使用每例一个 non-reference frame 和 ANTsPy `SyNOnly`；class-1/2/3 相对 frame0 的 local Dice delta 为 +0.017473、+0.294540、-0.011230，不能解释为 hosted readiness。独立 token 为 `M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY`。

### M10 preliminary selected rows

| phase | scar Dice | scar HD95 | scar remote-FP | edema Dice | edema HD95 | edema remote-FP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| D0 | 0.383391 | 75.687660 | 35.136364 | 0.675228 | 56.783220 | 84.340909 |
| D1 | 0.428470 | 79.321063 | 43.590909 | 0.687713 | 58.644283 | 57.818182 |
| D2 | 0.435077 | 61.816337 | 8.204545 | 0.702300 | 60.890204 | 43.431818 |
| D3 | 0.441126 | 39.467006 | 7.681818 | 0.675715 | 69.163874 | 108.613636 |
| hard-negative refresh | 0.409645 | 75.034516 | 14.295455 | 0.691986 | 55.089532 | 56.977273 |

所有 selected rows 的 scar 都明显低于 anchor；D2 edema 最接近 anchor但仍低约 0.0091；D3 改善 M10 内部 scar HD95/remote-FP，却使 edema remote-FP 达 108.6。它提示真实病种权衡，但当前 evaluator 会复制旧 artifacts，selector 也未通过完整验证，因此不能形成正式正负结论。

### Route A/B/C

- Route A：充分训练、44-case MyoPS 零 changed voxels，是 near-identity negative。
- Route B：25000 steps、1908 秒；scar compact Dice 0.351852、edema NaN、Cine local proxy 0.794026。多个模块有 gradient/on-off final-logit effect，但旧结构只有两尺度，评估缺 edema-positive case，不能代表完整 SRR-v3。
- Route C：未提交 Slurm；仅 D2 `checkpoint_best`、`Case2002` 做单病例 intervention。旧 `residual_gate` 零 effect，Cine 只有 fail-closed preflight；不能支持科学结论。

## 第四部分：为什么仍不如 nnU-Net

1. **表示选择不等于病灶形成。** Dictionary/router 能改变“看什么”，但没有稳定建立 proposal recall、负空间判别、component formation 和 pathology-specific refinement。
2. **proposal/refiner 因果链不足。** 历史 memory/proposal/refiner 多为 helper、summary 或 gradient 证据，未闭合 `memory -> similarity -> proposal -> refiner -> final labels`。
3. **路由过于全局。** Pattern-SIP/usage 可能捕捉 availability/center style，而不是 lesion-local semantic retrieval。
4. **no-T2 safety 只证明安全。** 它不能替代 T2-present edema performance；M9 edema focus 仍显著退化。
5. **scar/edema 优化冲突。** Scar 需要小 ROI、高 precision、强负空间和 component replay；edema 需要大上下文、高 recall、T2-conditioned 与 uncertainty-aware boundary。共享 terminal dense head 很难兼顾。
6. **anchor 两个极端。** anchor-centered residual 容易全关形成 identity；完全 SRR-owned logits 又暴露主干远弱于 nnU-Net。正确方向是 nonzero pathology-specific correction + bounded safe composition。
7. **评估污染。** empty-GT、compact/local proxy、old metrics copy、非 anchor-relative selector、未 clean reload 都可能制造假结论。
8. **Cine fidelity 不足。** 单帧/少帧、binary prior、pair-as-case、direct velocity proxy、proxy Jacobian/SyN 都不是 faithful temporal evidence。

## 第五部分：Round02 是否解决问题

- Route A：方向上针对 identity，但模型、loss、soft ROI、registration pass、commands、checkpoint、known-bad 和 states 仍留白；当前不值得重复投入。
- Route B：科学方向正确，是 Deep Research 的主要承接路线。Critic 拒绝原因是设计未冻结和 machine contract 不完整，不是方向错误。
- Route C：科学合同基本完整，主要阻塞是 executor YAML schema、旧 evidence 映射和 reviewer token。它不应被 B 替代。

当前三个 token 均为：

- `ROUTE_A_ROUND02_PLANNING_NEEDS_REVISION`
- `ROUTE_B_ROUND02_PLANNING_NEEDS_REVISION`
- `ROUTE_C_ROUND02_PLANNING_NEEDS_REVISION`

因此当前可启动 Controller 数量为 0。

## 第六部分：修订后的 controller-forward 图

### Route A：仅条件 fallback

若 B 在 implementation gate 前出现不可修复 blocker，才执行：contract/schema binding -> frozen manifests（含 T2-positive、CenterB/C floors）-> exact two-scale live-evidence SRR -> real-case forward/gradient/save-reload/nonidentity gate -> 单次 bounded MyoPS train -> 44-case fresh eval -> real multi-frame fixed-registration Cine -> finalizer/validator/reviewer。

强制要求：Cine gain 不能掩盖 MyoPS zero effect；changed-case、changed voxels、gate-open voxels 必须非零。若再次 44-case zero effect，Route A 作为 reviewed negative 关闭。

### Route B：完整 SRR-v3 主模型

顺序应为：

1. 绑定 Deep Research 的唯一实现和 exact paths/hashes；
2. 冻结 MyoPS/Cine manifests 与 pathology-balanced sampler；
3. 四尺度 stems、16-slot shared/private/interaction bank；
4. spatial/pathology routing 与 exact Pattern-SIP/coverage/load objectives；
5. OOF positive/negative memory 和 safe hard-negative；
6. anatomy -> scar/edema proposal -> separate soft ROI -> separate refiners；
7. bounded final probability composition；
8. real-case intervention/save-reload/export/freeze；
9. staged MyoPS formal training；
10. CineMA pretrained 与 matched-random control；
11. faithful registration 与 temporal aggregation；
12. fresh selected-checkpoint eval、final-output interventions、finalizer、mapper、strict validator、reviewer。

Planner 必须在执行前冻结 expert topology、modality order、router query、invalid-slot mask、所有 loss/weights/warmup、prototype update、安全负样本、ROI/refiner、final composition、CineMA class/hook/shape、matched-random initialization artifact、registration frame/case gate、temporal input 和 checkpoint selector。

### Route C：M10 forensic evidence + Cine fidelity

修成五个串行 waves：C0 `tooling/wave1`；C0B `myops/wave2`；R1 `myops/wave3`；R2 `cine/wave4`；R3 `cine/wave5`。每个 executor 单独绑定 schema-required fields、write scope、result/runtime/log/lock、Slurm/retry/preflight 和 completion token。

- C0：code/config/split/case/label/preprocess/decode/metric/checkpoint/runtime fingerprint。
- C0B：仅 fingerprint mismatch 时按原 phase 精确重训。
- R1：所有 recoverable checkpoints `--evaluate --force`、44-case raw manifests、immutable anchor、anchor-relative selector、selected reload、D2/D3 deterministic/no-op/swap/replacement final-path interventions。
- R2：真实 CineMA、matched control、symmetric velocity、7-step scaling-and-squaring、true Jacobian、inverse consistency、real SyN、temporal consumption tests；只生成 freeze candidate。
- R3：只运行 R2 frozen source/config；cumulative resume、atomic saves、zero-credit partial/timeout、selected reload 和 final-output intervention。

## 第七部分：最终建议

1. 暂停 Route A active work，保留条件 fallback。
2. Deep Research 结论优先写入 Route B，使完整 SRR-v3 成为唯一新模型主线。
3. 并行快速修 Route C machine plan；其 C0/C0B/R1 可能以较低训练成本判断旧 M10 资产能否继承。
4. 若只保留两条活跃路线，保留 B + C：B 提供候选上限，C 提供历史资产可信度；A 与 B 重复且旧结果无信号。
5. 若只能先做一个短周期工作，优先 Route C 的 fingerprint/fresh replay，而不是直接开始 B 长训；若只有一个模型开发资源，则优先 B。
6. 任何 Controller 启动仍需新的 Planner revision、main handoff、exact commit/blob binding 和独立 Critic ready token。

## 主要证据入口

- `prompts/routes/handoffs/CURRENT.md`
- `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`
- `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`
- `wiki/history/COMPARISON.md`
- `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/result.md`
- `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md`
- `results/20260714_srr_v3_m10_followup_wave2_reconciliation/selected_checkpoints.json`
- `results/20260714_srr_v3_m10_followup_wave2_reconciliation/all_checkpoint_challenge_metrics.csv`
- `scripts/evaluation/evaluate_srr_v3_m10_followup_all_checkpoints.py`
- `route_A:results/route_A/result.md`
- `route_A:prompts/routes/route_A_round02_critic_review.md`
- `route_B:results/route_B/result.md`
- `route_B:results/route_B/gradient_and_intervention_report.csv`
- `route_B:prompts/routes/route_B_round02_critic_review.md`
- `route_C:results/route_C/result.md`
- `route_C:prompts/routes/route_C_round02_critic_review.md`

后续 Planner 使用本报告时仍必须重新读取 CURRENT 和三条 route 的最新 result/review/controller/completion/validator；本报告不能替代 current evidence，也不能直接启动执行。
