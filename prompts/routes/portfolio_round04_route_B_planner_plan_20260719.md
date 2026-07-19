---
document_type: route_specific_portfolio_plan
route_id: route_B
portfolio_round: round04
date: 2026-07-19
status: DRAFT_FOR_ROUND04_CRITIC_REVIEW
planner_branch: main
round03_review_commit: b9c7664da7cb1f1892fff37a4497722f31a0a96d
round03_reviewed_packet_head: 8dfa40f8c4cedb2507f35a482bd46244a7a1c94c
round03_review_token: ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE
controller_start_authorized: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# CARE Route B Portfolio Round04 Planner Plan

## 1. 本轮判断

Round03 已经给出一个可信的充分训练负结果，但它只否定旧合同中的 B3 anatomy warmup gate，不能被解释为完整 SRR-v3、proposal/refiner、CineMA、registration 或 registered temporal 的最终负结论。Reviewer 已确认 B3 运行了 43003 optimizer steps、1800.796486 秒、22 次 validation，并在修复为 `E,E,S,R` sampler 后仍得到 `anatomy_union_overfit=false`。因此 Controller 不能自行越过旧门；Planner 必须重新定义下一轮合同。

Round04 的目标是 leaderboard-facing full implementation：完整实现并正式评估 Route B 的 MyoPS 与 Cine 两条链，主目标对应 `myops_scar`、`myops_edema`、`myocardium_cinemyops`。它不是 Route A 压缩版，不允许退化为 nnU-Net-only、postprocess-only、wrapper-only 或 validator-only。

核心修订是把旧 B3 单点 kill switch 拆成两层。第一层 B3A 只验证 anatomy target、label mapping、loss wiring 和梯度路径是否正确；第二层 B3B 只验证正式训练是否 finite、下降、非坍缩、遵守 no-T2 与 invalid-slot 合同。真正的科学门移动到 proposal、refiner 与 final same-split lesion evidence。这样既不无条件绕过 anatomy，也不让一个与最终 scar/edema lesion formation 不等价的 micro-overfit 字段过早杀死整个 Route B。

## 2. Round03 当前实现审计

| 阶段 | 已实现并有证据 | 尚未实现或未被正式证明 | 证据与判断 |
| --- | --- | --- | --- |
| B0 | 固定 44-case MyoPS split、T2-positive/center manifests、12-case Cine manifest、sampler 与 source probes | 没有 Round04 fingerprint 继承审计 | `results/route_B/round03/executors/B0/completion.json` |
| B1 | canonical modality order `[LGE,T2,C0]`；四尺度 channels `[32,64,128,256]`；每尺度 16 experts；shared/private/interaction contract；official CineMA source SHA | 这些是 scaffold/static contract，不是完整正式训练结果 | `results/route_B/round03/executors/B1/completion.json` |
| B2 | final logits 对 dictionary/router/prototype/refiner intervention 非零；invalid slot 权重为零；no-T2 edema delta 为零；clean reload delta 为零；official CineMA logits smoke；32-channel decoder feature hook；七步 SVF 与 temporal input smoke | smoke 不能证明 formal bank、proposal/refiner、faithful registration 或 temporal aggregation 有效 | `results/route_B/round03/executors/B2/completion.json`、`gradient_intervention_report.csv`、`save_reload_report.json`、`cinema_real_frame_smoke.json`、`registration_temporal_smoke.json` |
| B3 | 充分 evidence warmup；43003 steps；1800.796486 秒；22 validation events；sampler 已修复；不是 monitor、pending 或 undertrained | `anatomy_union_overfit` 失败；B4-B9 因旧 blocking gate 未执行 | `results/route_B/round03/executors/B3/completion.json`、`training_adequacy.csv` |
| B4-B6 | 无正式 runtime | OOF prototype/frozen bank、hard-negative queue、proposal、scar/edema refiner、joint selector、same-split lesion evidence 全部未执行 | Round03 controller/completion packet |
| B7-B9 | 只有 B2 smoke | official-vs-matched-random CineMA、faithful SVF/SyN、registered temporal full ablation 全部未执行 | Round03 controller/completion packet |
| B10 | terminal accounting、forbidden action 与 packet completeness 通过 | 不能把 accounting 当科学完成 | `results/route_B/round03/executors/B10/completion.json` |

Reviewer token `ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE` 的边界保持不变：它不是 route promotion、final scientific stop，也不授权 validation upload、M11、cross-route merge、hosted metric 或最终结论。

## 3. 目标榜一实现规格

### 3.1 MyoPS：完整 SRR-v3

输入顺序固定为 `[LGE,T2,C0]`，缺失模态通过 availability mask 与 masked feature path 处理，不得依赖 zero-filled intensity 猜测缺失。四个尺度全部实例化 shared、LGE-private、T2-private、C0-private 与 interaction experts，每尺度 16 experts；anatomy、scar、edema 使用 task-specific spatial router，路由必须同时消费 availability 与图像内容。Pattern-SIP、load balance 与 coverage receipt 用于防止共享 expert collapse 和私有 expert under-training。

SRR trunk 只负责组织证据，不再充当最终 dense lesion head。正式 lesion formation 链为：

```text
four-scale routed evidence
-> anatomy union / scar evidence / edema evidence / uncertainty
-> OOF frozen positive and safe-negative prototype banks
-> training-only hard-negative queue
-> pathology-specific proposal logits
-> scar small high-resolution soft ROI refiner
-> edema larger-context soft ROI refiner
-> bounded residual correction over same-split nnU-Net anchor
-> official compact-label output
```

OOF bank 必须来自训练 fold 外预测或严格 frozen checkpoint，不得使用 bootstrap/EMA bank 冒充。Scar negatives 可包含 myocardium 外背景、血池、正常 myocardium、LGE artifact 与历史 remote FP；edema negatives 只能来自 T2-present 的安全区域和 myocardium 外区域，no-T2 myocardium 不得作为 edema-negative。Proposal 必须记录 lesion-wise recall、心肌外 FP、remote FP、component count、HD95 与 volume ratio。Scar 与 edema refiner 采用不同 ROI 半径、阈值、上下文和损失，不得共享一个终端 dense head后改名。

Final correction 必须有幅度边界、ROI 边界和可逆 selector。Selector 在 fresh `--force` 44-case same-split evaluation 上比较模型、nnU-Net anchor 与 bounded blend，任何选中 checkpoint 必须 clean reload 后重新评估。候选判据要求三个主目标中至少两个达到 positive gate，第三个 non-worse；即使未形成候选，完整忠实运行仍可形成 Route B adequate negative。

### 3.2 B3 gate 修订

B3A 使用 R4B0 固定的两个 case、八个 patch、无 augmentation、512 steps。Target 明确定义为：anatomy union=`{1,4,5}`，LV=`2`，RV=`3`。通过条件：loss ratio `<=0.20`，union Dice `>=0.55`，union gain `>=0.30`，LV/RV Dice 各 `>=0.40`，有效 anatomy family gradient coverage `>=0.90`，invalid slot max `<=1e-8`，clean reload delta `<=1e-5`。同一 write scope 只允许一次实现修复；第二次失败返回 `NEEDS_REVISION`，不得写 adequate negative。

B3B 从零计 Round04 训练信用：至少 6000 optimizer steps、1800 train-loop seconds、3 validation events。Entry 只检查 finite、loss decrease、全部有效 family gradients、invalid mask、no-T2 zero influence、exact sampler、positive low-threshold non-collapse 与 clean reload。旧 `anatomy_union_overfit>=0.70` 字段仍被记录，但不再控制 B4 entry；validator 若发现旧字段仍控制 flow 必须失败。

### 3.3 Cine：official source、faithful registration、registered temporal

CineMA formal comparison 使用 official pretrained 与 matched-random 两个源。两者必须保持相同 architecture、parameter count、downstream initialization、case/frame manifests、augmentation、optimizer、schedule、step budget 与 seed family；唯一差异是 source weights。记录 source SHA、hook shape、checkpoint hash、prediction hash、per-case anatomy metrics 与 clean reload。

Registration 必须实现 symmetric stationary velocity field，使用七步 scaling-and-squaring 积分后再 warp；记录真实 Jacobian determinant、fold ratio、inverse composition error、pair-level、case-level 与 aggregate denominators，并提供真实 SyN comparator。Direct velocity warp、proxy Jacobian、pair row 冒充 case aggregate 全部属于 known-bad。

Temporal aggregator 必须真实消费 registered image、registered CineMA anatomy/logits/features、forward/inverse displacement、Jacobian、frame time、validity mask 与 uncertainty。Formal ablation 至少包含：reference-only、unregistered temporal、registered temporal、temporal-off、motion-off、anatomy-off、official-pretrained 与 matched-random。每个 variant 按 case 输出 metric、help/harm、frame coverage、field-consumption receipt、checkpoint/prediction hash 与 reload receipt。Frame0-only 不得命名为 temporal。

## 4. 可执行 Controller task graph

| Executor | 任务 | 输入 | 输出和 gate | 失败分支 |
| --- | --- | --- | --- | --- |
| R4B0 | bind、source probe、fingerprint、manifests、known-bad fixtures | main 与 reviewed route_B | inheritance matrix、fixed manifests、validator fixtures | fingerprint mismatch 阻断继承 |
| R4B1 | Round04 package migration 与 B3A target/loss repair | R4B0 | 四尺度代码、target tests、static tests、job wrappers | shared defect 返回 Planner |
| R4B2 | real implementation gate 与 512-step microfit | R4B1 | interventions、microfit、reload、CineMA/SVF/temporal real gates | 第二次 microfit 失败=`NEEDS_REVISION` |
| R4B3 | 6000-step evidence warmup | R4B2 | sampler/gradient/non-collapse/reload receipts | 旧 anatomy 字段不得阻断；真实缺陷=`NEEDS_REVISION` |
| R4B4 | OOF bank、safe negatives、proposal 8000 steps | R4B3 | bank/queue provenance、proposal recall、case metrics | 充分运行未达 gate=stage adequate negative |
| R4B5 | scar/edema refiners 10000 steps | R4B4 | ROI retention、refiner metrics、component/FP interventions | 充分运行未达 gate=stage adequate negative |
| R4B6 | joint 8000 steps、fresh 44-case selector | R4B5 | same-split baseline、help/harm、subgroups、HD95/FP/components/volume | 完整运行未达 gate=MyoPS adequate negative |
| R4B7 | official CineMA 8000 steps | R4B2 | source/hook/hash、case metrics、reload | asset defect=`EXTERNAL_RESOURCE_BLOCKED` |
| R4B8 | matched-random CineMA 8000 steps | R4B2 | 完整 matched receipt | mismatch=`NEEDS_REVISION` |
| R4B9 | faithful SVF 25000 steps 与 real SyN | R4B7+R4B8 | Jacobian、inverse、pair/case/aggregate、SyN | 充分运行未达 gate=stage adequate negative |
| R4B10 | registered temporal 20000 steps 与七组 control | R4B9 | field consumption、casewise ablation、selector、reload | 完整运行未达 gate=Cine adequate negative |
| R4B11 | `afterany` finalizer、mapper、validators、local commit | 所有 started attempts | accounting、packet、known-bad、reports、review request | gap=`NEEDS_MONITOR`、`NEEDS_EVIDENCE` 或 `NEEDS_REVISION` |

MyoPS lane 内部保持顺序，Cine lane 内部保持顺序；R4B3 与 R4B7、R4B4 与 R4B8、R4B5 与 R4B9、R4B6 与 R4B10 可在两个隔离 executor slots 并行。每个 executor 使用独立 result/runtime/log/lock root；Controller 不得把一个 executor 拆成无审计的多写者。

## 5. 正式评价与 leaderboard 对齐

三项主指标为 `myops_scar`、`myops_edema`、`myocardium_cinemyops`。本轮只产生本地 same-split 科学证据，不把 local proxy 写成 hosted metric。MyoPS 必须输出：same-split nnU-Net baseline、模型与 anchor per-case rows、case-wise help/harm/severe-harm、scar-positive、T2-present edema-positive、no-T2 safety、CenterB、CenterC、remote-FP、component count、HD95、volume ratio。Cine 必须输出 official/random、reference/unregistered/registered 与三项 module-off controls 的 per-case 表。

No-T2 safety 既检查 edema loss/gradient 为零，也检查推理时未出现 availability shortcut 异常。CenterB/CenterC 单独报告，不能只给 pooled mean。Remote-FP、component count、HD95 与 volume ratio 必须按 class 和 case 记录，不能用单一 Dice 替代。

## 6. Deep research 映射

| Deep research 要求 | 代码/模块 | 阶段 | 证据 | Validator |
| --- | --- | --- | --- | --- |
| SRR 只做 evidence engine，补 lesion formation | four-scale trunk、proposal dictionaries、refiners | R4B1-R4B6 | intervention chain、proposal/refiner/final metrics | causal-chain validator |
| Anatomy localization 进入 pathology | union prior、distance/ROI features | R4B2-R4B6 | anatomy intervention、ROI retention | anatomy-target + ROI validator |
| Scar/edema pathology-specific | separate routers、banks、ROI、loss | R4B1-R4B6 | class-specific config/hash/metrics | no-shared-terminal-head known-bad |
| OOF prototype 与 adaptive memory | fold-excluded frozen bank | R4B4 | member/fold/checkpoint provenance | OOF leakage validator |
| Hard-negative replay | class-safe queue | R4B4-R4B5 | enqueue/dequeue/source class receipts | no-T2 negative validator |
| Soft cascade refinement | scar small ROI、edema large ROI | R4B5 | retention/recall/FP/component deltas | soft-ROI consumption validator |
| Same-split nnU-Net anchor | anchor context 与 bounded correction | R4B6 | anchor/model/blend per-case rows | same-split and fresh-force validator |
| CineMA source value | official vs matched-random | R4B7-R4B8 | matched-control matrix、hash、metrics | matched-control validator |
| Cine motion/anatomy | symmetric SVF、SyN、registered fields | R4B9 | Jacobian/inverse/SyN denominators | faithful-registration validator |
| Temporal aggregation | registered multi-field consumer | R4B10 | seven-control ablation、field receipts | temporal-field-consumption validator |
| Missingness/label mechanism | availability routing、T2-masked edema | 全 MyoPS 阶段 | no-T2 zero influence、安全负样本 provenance | missingness-contract validator |
| HD 与 remote FP | proposal/refiner/final evaluation | R4B4-R4B6 | HD95、remote FP、components、volume | metric denominator validator |

## 7. Slurm 与 anti-laziness hardening

所有正式 wrapper 只能调用 `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`，不得调用裸解释器。每次 submit 前写 partition-specific preflight，核对 GPU 型号、显存、CUDA、PyTorch、extension、checkpoint、input/output/config hash。正式训练依赖使用 `afterok`；覆盖所有 started attempts 的 finalizer 使用 `afterany`。

长等待使用 `htzhulab` 与 `a100-gpu` isolated mirror race；记录相同 code/config/split/checkpoint hash、各自 job id、submit/start/end、atomic winner lock、loser cancellation 与 zero-credit。`volta-gpu` 只在 exact preflight 通过且不改变 batch、precision、model、patch、steps、accumulation 或 metric semantics 时运行；否则记录 incompatibility receipt，不得静默缩小任务。排队、monitor、submitted-only、running、awaiting accounting 均不是完成；scheduler 连续阻塞 24 小时后返回 `NEEDS_MONITOR`，不伪造科学结论。

禁止 smoke 冒充正式训练；禁止 validator 只查文件存在；禁止 pending/monitor/undertrained 早退；禁止旧 wrapper 绕过 Round04 namespace；禁止旧 B3 field 控制新 flow；禁止 bootstrap/EMA 冒充 OOF bank；禁止 no-T2 edema-negative；禁止 fake CineMA、unmatched random control、direct velocity warp、proxy Jacobian、pair-as-case、unconsumed temporal fields、frame0-only temporal、stale metric、local proxy 冒充 official。

Validator 必须解析 completion semantics、运行 known-bad fixtures、核对 hash/provenance/denominator/field consumption，并对任一 nonterminal accounting、missing output 或 retry lineage gap 返回非零。

## 8. Completion tokens 与 Reviewer draft

Controller 只能写以下 terminal operational states：

```text
ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW
ROUTE_B_ROUND04_NEEDS_MONITOR
ROUTE_B_ROUND04_NEEDS_EVIDENCE
ROUTE_B_ROUND04_NEEDS_REVISION
ROUTE_B_ROUND04_EXTERNAL_RESOURCE_BLOCKED
```

Stage-specific sufficient-runtime miss 必须写清 stage、runtime adequacy、失败点与 downstream blocking；只有 independent Reviewer 能将完整 packet 判为：

```text
ROUTE_B_ROUND04_REVIEW_EVIDENCE_COMPLETE
ROUTE_B_ROUND04_REVIEW_ADEQUATE_NEGATIVE
ROUTE_B_ROUND04_REVIEW_NEEDS_REVISION
ROUTE_B_ROUND04_REVIEW_NEEDS_EVIDENCE
ROUTE_B_ROUND04_REVIEW_NEEDS_MONITOR
```

Reviewer 固定到 Controller local packet commit，只读核对：B0-B2 inheritance、B3A/B3B gate semantics、B4-B10 formal runtime、same-split nnU-Net、case-wise help/harm、subgroups、Cine seven-control ablation、all-attempt accounting、strict known-bad、mapper receipts 与 authority boundary。Runtime roles 不得写 `review.md`，不得 push。

## 9. Authority boundary 与下一步

本计划及配套 prompt、controller contract、executor YAML、critic request、planner audit 仍处于 `DRAFT_FOR_ROUND04_CRITIC_REVIEW`。独立 Critic 必须绑定包含六个文件的 exact main commit、记录 SHA256、运行仓库原生 validator 与扫描，并在无 blocking finding 时写 `ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER`。在该 token 出现前，Controller 不得启动。

本轮不授权 validation upload、route promotion、M11、cross-route merge、hosted metric claim 或 final scientific decision。