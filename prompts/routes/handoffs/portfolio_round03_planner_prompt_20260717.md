---
portfolio_round: round03
date: 2026-07-17
role: gpt_planner_prompt
status: DRAFT_READY_FOR_GPT_PLANNER
remote_baseline_main: 28c8aac80b7f18f3441c495dc9f2625fc10c460f
remote_baseline_route_A: 73d90a71482913b8e798a784454c1de90489a9be
remote_baseline_route_B: f01427e72134d5e5be1bfd51b93bdefdd5f3126c
remote_baseline_route_C: 469265ad999c3a568e2e40198f200e4ce7523f7c
round02_route_A_token: ROUTE_A_ROUND02_PLANNING_NEEDS_REVISION
round02_route_B_token: ROUTE_B_ROUND02_PLANNING_NEEDS_REVISION
round02_route_C_token: ROUTE_C_ROUND02_PLANNING_NEEDS_REVISION
controller_start_authorized: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
server_shell_required: false
---

# CARE Route Portfolio Round03 Planner Prompt

你是 CARE GPT Planner。当前任务是基于 Round02 三条 route 的 Critic 结果、Round02 历史证据分析和 deep research，制定 Round03 的 controller-forward 规划。只做规划和规划期 handoff，不执行代码、不训练、不提交 Slurm、不启动 controller、不写 runtime `review.md`、不上传 validation、不做 route promotion、不启动 M11、不跨 route merge、不声明 hosted metric 或最终科学结论。

## 0. 重要边界：不要访问服务器

不要尝试 SSH、shell、访问 `/users/a/e/aereinh/CARE` 服务器、运行 `git fetch`、运行 Python、读取本地未提交文件，或要求自己进入 Codex/tmux。上一版 Round03 prompt 的主要问题就是要求 GPT 访问服务器，导致失败。

你应使用 GitHub/项目材料中可读的远端仓库文件、当前对话提供的状态、以及本 prompt 列出的证据入口来规划。如果 GitHub connector 或项目材料无法读取某个文件，明确列出缺失文件并请求用户或 Codex coordinator 提供内容；不要伪造已经读取，也不要因为不能访问服务器而直接放弃规划。若你不能写入 GitHub，请输出 copy-ready 的文件内容；若你有 GitHub 写入能力，才可以按下面的分支/文件要求提交。

当前 Codex coordinator 已同步远端，基线为：

```text
origin/main    28c8aac80b7f18f3441c495dc9f2625fc10c460f
origin/route_A 73d90a71482913b8e798a784454c1de90489a9be
origin/route_B f01427e72134d5e5be1bfd51b93bdefdd5f3126c
origin/route_C 469265ad999c3a568e2e40198f200e4ce7523f7c
```

## 1. 必读文件

先读取这些通用规则和当前入口：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/README.md
prompts/routes/route_portfolio_planner_prompt.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
```

涉及 Slurm、partition、routing race、pending/monitor、finalizer、scheduler block 时，还必须读取：

```text
.agents/skills/slurm-routing-partition/SKILL.md
```

涉及模型结构、loss、dataflow、export、Cine temporal、mapper/fingerprint 时，还必须读取：

```text
.agents/skills/care-mapper/SKILL.md
```

必须读取 Round02 新增分析：

```text
wiki/history/ROUND02_SRR_EVIDENCE_AND_CONTROLLER_FORWARD_ANALYSIS_20260718.md
docs/notes/deep_research/care_2026_myocardium_round02_targeted_deep_research_cleaned.md
```

还要读取三条 Round02 Critic review：

```text
origin/route_A:prompts/routes/route_A_round02_critic_review.md
origin/route_B:prompts/routes/route_B_round02_critic_review.md
origin/route_C:prompts/routes/route_C_round02_critic_review.md
```

继续视觉读取 ChatGPT Project 背景材料中的 SRR-v2、SRR-v2.5、SRR-v3。仓库 `images/SRR-v2.png`、`images/SRR-v2.5.png`、`images/SRR-v3.png` 只是版本引用，不替代 Project 背景图视觉读取。不能视觉读取时，输出 `BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE`，不要写 route plan。

## 2. 当前 Round02 事实

Round02 三条 route 的 Critic 结果全是 planning revision：

```text
Route A: ROUTE_A_ROUND02_PLANNING_NEEDS_REVISION
Route B: ROUTE_B_ROUND02_PLANNING_NEEDS_REVISION
Route C: ROUTE_C_ROUND02_PLANNING_NEEDS_REVISION
```

当前可启动 controller 数量为 0。Round02 的 contract blob / executor plan blob 在各 route critic review 中已经匹配 handoff；问题不是 stale handoff，而是 planning hard gates 没过。Round03 必须生成新的 planner revision、新的 route commit/blob 绑定、新的 critic handoff 或 critic-ready request。Round02 token 不能复用。

## 3. Round03 总策略

Round03 不要继续三条 route 平均投入。根据 `wiki/history/ROUND02_SRR_EVIDENCE_AND_CONTROLLER_FORWARD_ANALYSIS_20260718.md` 和 deep research：

1. Route B 是主模型路线。它应吸收 deep research 的完整 SRR-v3 设计，冻结为唯一新模型主线。
2. Route C 是 M10/follow-up/follow-up2 forensic evidence + Cine fidelity 路线。它不是新模型设计路线，不能被 Route B 替代。
3. Route A 暂停 active GPU/controller 路线，保留为条件 fallback。只有 Route B 在 implementation gate 前出现不可修复 blocker，才允许启动一次最多 24 小时的 compressed fallback；否则 Route A 保持 reviewed negative/fallback，不再单独迭代。

你仍必须为 A/B/C 都给出 controller-forward 结果，但 A 的结果应是明确的 fallback contract，而不是继续消耗主资源的平行路线。

## 4. 共同 hardening 要求

Round03 必须继续继承 `ROUTE_HARD_REQUIREMENTS_MATRIX.md`。不要把 Round02 hardening 当作一次性补丁。

每条 route 都必须围绕 CARE Myocardium 三个主指标：

```text
myops_scar
myops_edema
myocardium_cinemyops
```

禁止用 `foreground_mean`、empty-GT average、compact-label proxy、local proxy-only metric、validator pass、smoke pass 或工程 runnable 状态代替三主指标。

每条 route plan 必须写清：

- target metrics 和 expected gain mechanism；
- 同一划分 nnU-Net baseline；
- case-wise help/harm matrix；
- T2-present edema、no-T2 safety、scar-positive、CenterB/CenterC、remote FP、component count、`Dice`、`HD95`、volume ratio；
- exact controller task graph；
- machine-readable `executor_plan.yaml`；
- exact write scopes、result/runtime/log/lock roots；
- exact required files 和 schema；
- exact commands、Slurm submit/monitor/finalizer/aggregation commands；
- validator semantics、known-bad fixtures、expected failing keys；
- completion tokens、non-ready states、retry/monitor/return-to-previous-phase states；
- reviewer input path、reviewed commit、allowed reviewer tokens 和 pass/fail criteria；
- local commit/no-push boundary。

禁止把这些留给 Codex/controller 自行决定：模型结构、loss、训练预算、输入输出路径、Slurm 策略、routing race、validator、known-bad、completion state、reviewer pass/fail。`TBD`、`optional`、`as appropriate`、`if needed`、`choose best`、`Codex decide`、`controller decide`、`视情况`、`按需`、`补一个稳健实现` 等都是 hard-gate failure，除非同一小节给出触发条件、默认值、允许范围、证据要求和失败分支。

## 5. Slurm 与 GPU routing 要求

所有正式 Slurm wrapper 必须使用验证过的 CARE Python，例如：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python
```

禁止裸 `python`。每个正式 GPU job 前必须有 compute-node preflight，记录 Python executable/version、`torch` import/version、CUDA visibility/device、关键 package、optimizer construction、`--print-contract` 或等价 contract print、output/log/lock writability、code/config/split/case hash。

默认 partition 顺序：

```text
htzhulab -> a100-gpu -> volta-gpu
```

Round03 必须显式规划 `volta-gpu` 的用途，但不能为了 V100 16GB 偷改科学语义。推荐规则：

- `htzhulab` 是默认训练 partition。
- `a100-gpu` 是语义等价 mirror/fallback。
- `volta-gpu` 必须用于明确 V100-compatible 的独立任务，例如 Route C fresh replay shards、CineMA per-frame inference/provenance smoke、validator/aggregation、lightweight registration probes、或 batch/shape 已证明等价的小型 bounded jobs。
- 若把 `volta-gpu` 用于训练，必须写明显存约束、batch/patch/precision 是否改变；任何改变科学语义、loss、case/frame set、augmentation、budget、selection rule 的 V100 fallback 都禁止。

Routing race 要求：

- 单个关键路径 job 在 `htzhulab` 长时间 pending，且 `a100-gpu` 语义等价时，可以 `htzhulab` + `a100-gpu` race。
- `volta-gpu` 只有在同一任务 V100-compatible 且语义完全等价时才加入 race；否则作为独立 V100-safe shard/fallback，不和大模型训练强行 race。
- race 必须有 isolated attempt output、atomic winner lock、started-loser exit、pending-loser cancellation、job id/partition/state/取消命令/log path receipt。
- pending、submitted-only、running、awaiting-accounting、monitor packet 不是完成。
- finalizer/accounting dependency 使用 `afterany`；training-to-training dependency 使用 `afterok`。
- 对目标任务内 operational startup/runtime defect，允许 same-scope retry，但必须保持 command semantics、scientific variant、budget、split、config meaning、executor id、write scope 不变；失败 attempt 训练 credit 为 0。

## 6. Route A：条件 fallback，不再作为 active 主线

Round03 对 Route A 的建议状态：

```text
ROUTE_A_ROUND03_RECOMMENDATION=DEFERRED_FALLBACK_NOT_ACTIVE
```

原因：

- 旧 Route A 正式 run 已 terminal 且训练 adequacy 通过，但 44/44 MyoPS rows 的 route-owned final-label effect 为 0。
- `myops_scar` 约 0.0227，唯一 T2-present edema-positive case 的 edema Dice 为 0。
- 继续修 Route A 会接近 Route B 的压缩子集，重复消耗时间。

你仍要写 Route A fallback contract，但不得让它自动启动。该 fallback 只有在 Route B implementation gate 前出现不可修复 blocker 时才可由后续 GPT/user 明确启用。

Route A fallback 必须保留：

- 两尺度 compressed live-evidence SRR；
- no interaction experts、no online memory；
- LGE/C0/T2 evidence + availability；
- anatomy-guided scar/edema proposal；
- scar 小 ROI、高 precision refiner；
- edema 大 ROI、T2-present-only supervision、no-T2 zero correction；
- bounded anchor correction；
- real CineMA 或诚实 blocker；
- real multi-frame registration/temporal，不能 frame0/postprocess-only。

Route A candidate-ready 必须同时满足：

```text
myops_changed_case_count > 0
myops_changed_voxels > 0
myops_gate_open_voxels > 0
proposal_to_final_retention_pass == true
temporal_on_off_changed_cases >= 8
```

Cine gain 不能掩盖 MyoPS zero effect。若再次 44-case zero-effect，只能形成 reviewed negative/fallback packet。

## 7. Route B：Round03 主模型路线

Route B 必须成为完整 SRR-v3 主线，不得降级成 Route A。

根据 deep research，Route B 设计必须冻结为：

1. 四尺度 architecture，每尺度含 modality-specific encoder、shared expert、private expert、interaction expert。
2. 输入顺序固定 `[LGE, T2, C0]`，availability 同序。不可用模态不得作为 zero-filled observed image 进入私有/交互路径。
3. Scar route 允许 shared + LGE-private + LGE-T2 + LGE-C0。
4. Edema route 允许 shared + T2-private + LGE-T2 + T2-C0。
5. Anatomy route 允许 shared + C0-private + LGE-C0 + T2-C0。
6. Proposal 使用 anatomy-guided conservative cascade + prototype similarity-difference augment。
7. Prototype memory 使用 fold-safe、OOF-fitted、inference-frozen prototype bank；training-only hard-negative queue 只用于训练/replay，不能作为 validation/test online memory。
8. Scar/edema refiner 分开：scar 小 ROI、高精度、强负空间；edema 大 ROI、T2-present recall、uncertainty-aware boundary。
9. Final output 使用 anchored bounded correction，但 proposal/refiner 必须改变 SRR logits，并经 gate 体现在 final logits/final labels。
10. Pattern-SIP 必须是 pattern-conditioned integrativeness，不是 uniform coverage 表格。

必须写入 exact tensor contracts。至少包括：

```text
x shape: [B,3,H,W,D]
availability shape: [B,3]
per-scale modality features
shared/private/interaction expert output shapes
scar/edema routed feature shapes
proposal logits/probability shapes
soft ROI function and thresholds
refiner input/output shapes
bounded final composition formula
```

Prototype bank 必须写清：

- scar positive prototype 来源；
- scar negative categories：normal myocardium、blood pool、outside myocardium、hard FP、artifact；
- edema positive 只来自 T2-present edema-positive voxels；
- edema safe negative 只来自 T2-present safe regions；
- 禁止 no-T2 myocardium、unknown edema tissue、validation/test labels 进入 edema negative；
- 每尺度每病种 `K_pos=8`、`K_neg=12`，或给出更具体的冻结值；
- bank tensor、source manifest SHA、fit script commit、OOF split receipt、category counts、empty-class fallback flag；
- deterministic/bootstrap prototype 只能是 control，不能进入正式 final path。

Route B 训练应分阶段，不允许直接长训掩盖实现缺口：

1. evidence warmup：router/retrieval/anatomy 稳定，过 router sensitivity 和 invalid-slot mask；
2. proposal stage：冻结 refiner，过 proposal recall/precision、positive-case nonempty、proposal-to-final retention；
3. refiner stage：冻结 proposal 主体，只小学习率调 temperature/gate，过 changed-component/HD95 direction；
4. joint fine-tune：低学习率连接 proposal/refiner/gate/bounded correction；
5. fresh eval + clean selected-checkpoint reload + final-output interventions。

Route B 必须修复 Round02 critic blocker：

- `executor_plan.yaml` 必须有 schema-valid top-level `executors`；
- 每个 B0-B10 或新版 wave 必须有 exact `result_dir`、required files、commands、validator、success token、failure states、next transition；
- 冻结 MyoPS/Cine manifests、hash、case IDs、CenterB/CenterC floors、T2-positive edema-positive floor；
- 冻结 sampler strata、overlap precedence、replacement policy、seed、per-step proportions、runtime count receipt；
- 冻结 Pattern-SIP equation、loss coefficients、warmup schedule、source symbols；
- 枚举可编辑 first-party paths/symbols；发现新 shared-source edit 必须回 planning；
- exact CineMA adapter file/symbol、feature hook、4D-to-frame assembly、orientation/spacing/normalization、entropy formula、temporal schema；
- matched pretrained/random control 必须有 shared downstream initialization artifact SHA 和 parameter comparison；
- exact known-bad fixtures under `tests/route_B/known_bad/`；
- exact non-ready states 和 continuation obligations；
- exact compute-node preflight、durable finalizer、aggregation、mapper-final、strict validator、heavy-artifact check、local commit boundary；
- exact reviewer tokens 和 candidate-ready / adequate-negative / needs-evidence / needs-monitor / needs-revision criteria。

## 8. Route C：M10 forensic evidence + Cine fidelity

Route C 必须完整继承 M10 / follow-up / follow-up2，不得裁剪。Route C 不做新 MyoPS 科学设计，目标是证明旧 M10 到底哪些 evidence 可以可信继承，并关闭 Cine fidelity 证据链。

Round03 Route C 必须修成五个 serial waves：

```text
C0  lane=tooling wave=1
C0B lane=myops   wave=2
R1  lane=myops   wave=3
R2  lane=cine    wave=4
R3  lane=cine    wave=5
```

每个 executor 必须有：

```text
id
lane
wave
prompt_path
result_dir
runtime_output_root
slurm_job_namespace
lock_path
log_path
merge_order
write_scope
required_completion_file
required_completion_token
slurm_required
preflight
retry_policy
dependency_policy
retry_ledger_path
```

Route C 必须修复 Round02 critic blocker：

1. `executor_plan.yaml` 必须通过 `scripts/ops/validate_executor_plan.py`，Planner audit 必须记录真实 exit 0。
2. 旧 M10/follow-up/follow-up2 required evidence 必须逐项进入 machine plan，或提供 `old_requirement -> new_file -> required_fields -> validator` 映射。至少覆盖 per-checkpoint replay receipt、all-checkpoint subgroup metrics、eligibility/selector recalculation、selected reload、D2/D3 deterministic baselines、D2/D3 intervention manifests、component-state classification、hard-subgroup help/harm、no-T2 safety、per-executor validator/known-bad/completion receipts。
3. 增加 exact runtime reviewer tokens，至少包括 positive、adequate registration negative、external-resource blocker、undertrained、needs-monitor、needs-evidence、needs-revision，并为每个 token 定义 required evidence、validator state、拒绝条件和禁止授权。

Route C 的 scientific requirements 仍包括：

- fresh all-checkpoint replay，必须 `--evaluate --force`；
- 44-case raw manifests；
- checkpoint SHA、state-dict SHA、code/config/split/case/label/preprocess/decode/metric hashes；
- immutable anchor；
- anchor-relative selector；
- selected checkpoint clean reload；
- D2/D3 deterministic baselines、no-op controls、positive/negative swaps、replacement final-path interventions；
- `OOF memory -> similarity -> proposal -> refiner -> probability composition -> final labels` 机制链；
- failed/timeout/partial/submitted-only/old copied metrics zero-credit。

## 9. CineMA / registration / temporal 共同合同

CineMA 是 Round03 硬要求，尤其 Route C 不允许再拖延、表面接入或 future-work 化。

官方 CineMA 资产冻结点：

```text
repo: mathpluscode/CineMA
license: MIT
code commit: c10daa1d93f0ea28d8b9ad9206b0f673d25805c1
HF revision: b1251ee50423bceeca84c080782fc3bc7756dea6
weight: finetuned/segmentation/acdc_sax/acdc_sax_0.safetensors
SHA256: c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f
model class: cinema.segmentation.convunetr.ConvUNetR
```

Planner 必须要求 first-party adapter 输出：

```text
multiclass anatomy logits
probabilities
last decoder feature before pred_head_dict['sax']
normalized predictive entropy / uncertainty
affine/header/provenance
```

CARE Cine 4D 数据必须 per-frame inference，不得把 4D stack 直接喂给单 time-frame CineMA。必须冻结 axis/orientation/spacing/intensity normalization、ED/reference frame selector、frame set、label mapping、output tensor shapes。

Matched pretrained/random control 必须同 architecture、config、adapter/head、cases、frames、preprocessing、augmentation draws、optimizer、budget、validation cadence、checkpoint schedule、selection rule、downstream initialization artifact。唯一区别只能是上游 CineMA segmentation weights：official safetensors vs same config random initialization。必须记录 parameter names、trainable/frozen sets、shapes、counts、initial hashes。

Faithful registration 必须是 first-party SVF：

```text
stationary velocity v [B,3,Z,H,W]
phi = exp(v) via 7-step scaling-and-squaring
phi_inv = exp(-v) via 7-step scaling-and-squaring
trilinear warp for image/feature/probability
nearest warp for labels
Jacobian determinant receipt
folding rate
inverse-composition error
smoothness loss
warped feature/probability/label SHA
case-level and aggregate receipts
real ANTsPy SyN control
```

Temporal model 必须消费 registered evidence：

```text
reference CineMA logits/features/uncertainty
registered non-reference logits/features/uncertainty
registered anatomy
displacement magnitude / velocity
Jacobian
motion quality
texture residual
temporal position
frame quality
```

必须有 controls：reference-only、unregistered multi-frame、registered temporal、temporal-off、motion-off、anatomy-off、pretrained-vs-random。Temporal on/off 必须改变 final logits/final labels；否则不能 candidate-ready。

## 10. Evidence selector 与 validator

Round03 不能只按 mean Dice 选 checkpoint。使用 lesion-centric selector，至少包含：

```text
0.40 * delta Dice on scar-positive
0.25 * delta Dice on T2-present edema-positive
0.15 * negative clipped scar-positive HD95 delta
0.10 * negative clipped T2-present edema HD95 delta
0.10 * negative clipped remote-FP delta
```

只有硬门都过才计算 selector：

```text
proposal_recall_pass
changed_voxels > 0
changed_components > 0
no_T2_edema_correction == 0
fresh_evaluation_receipt_complete
case_manifest_sha bound
prediction_sha bound
checkpoint_sha bound
evaluator_commit bound
selected_checkpoint_clean_reload_pass
```

Known-bad fixtures 必须覆盖：

- copied old metrics；
- missing `--evaluate --force`；
- compact/local proxy 冒充 official metric；
- submitted-only/pending/running/awaiting-accounting packet；
- no-op candidate 冒充 nonidentity；
- zero MyoPS effect plus Cine-only improvement；
- nnU-Net-only / wrapper-only / postprocess-only；
- fake/binary/frame0 CineMA；
- unmatched pretrained/random control；
- direct velocity as displacement；
- proxy Jacobian/inverse/SyN；
- pair-level result mislabeled as case-level；
- temporal inputs not consumed；
- R3 source edit；
- stale receipts；
- heavy artifacts/checkpoints/NIfTI staged；
- runtime push/review；
- upload/promotion/M11/hosted/final scientific claim。

## 11. 输出要求

如果你能写入 GitHub，按分支提交：

Route A branch:

```text
prompts/routes/route_A.md
prompts/routes/route_A_executor_plan.yaml
prompts/routes/route_A_critic_request.md
prompts/routes/route_A_planner_audit.md
```

Route B branch:

```text
prompts/routes/route_B.md
prompts/routes/route_B_executor_plan.yaml
prompts/routes/route_B_critic_request.md
prompts/routes/route_B_planner_audit.md
```

Route C branch:

```text
prompts/routes/route_C.md
prompts/routes/route_C_executor_plan.yaml
prompts/routes/route_C_critic_request.md
prompts/routes/route_C_planner_audit.md
```

Main branch:

```text
prompts/routes/portfolio_round03_planner_plan_20260717.md
prompts/routes/handoffs/CURRENT.md
prompts/routes/handoffs/route_A_round03_critic_handoff_20260717.md
prompts/routes/handoffs/route_B_round03_critic_handoff_20260717.md
prompts/routes/handoffs/route_C_round03_critic_handoff_20260717.md
```

若不能写 GitHub，输出上述文件的 copy-ready 内容，并明确哪些文件应放在哪个分支。

所有 route executor plans 必须在 planner audit 中声明：

```text
scripts/ops/validate_executor_plan.py prompts/routes/route_X_executor_plan.yaml
```

对对应 plan exit 0；否则不得请求 Critic ready。

## 12. Critic tokens for Round03

Round03 Critic ready tokens：

```text
ROUTE_A_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_C_ROUND03_PLANNING_READY_FOR_CONTROLLER
```

Round03 Critic revision tokens：

```text
ROUTE_A_ROUND03_PLANNING_NEEDS_REVISION
ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
ROUTE_C_ROUND03_PLANNING_NEEDS_REVISION
```

Ready token 只授权对应 route controller 启动，不授权 validation upload、route promotion、M11、cross-route merge、hosted metric claim 或最终科学决定。

## 13. 最终回答格式

最后用中文汇报：

- 读了哪些文件；
- 当前远端基线和 Round02 三条 critic token；
- Round03 对 A/B/C 的 route decision；
- 每条 route 写入/建议写入哪些文件；
- 每条 route 的 controller task graph 摘要；
- executor plan 是否 schema-valid；
- Critic 应读哪个 handoff；
- 哪些内容明确禁止 controller 自行决定；
- Slurm routing 如何使用 `htzhulab`、`a100-gpu`、`volta-gpu`；
- CineMA 在 A/B/C 中如何真实使用、验证或阻塞解除；
- 哪些 action 仍被禁止。
