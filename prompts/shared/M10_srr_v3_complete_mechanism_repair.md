---
task_key: 20260711_srr_v3_m10_complete_mechanism_repair
task_kind: scientific_milestone
task_type: controller
controller_mode: true
milestone_number: 10
milestone_id: M10
status: DRAFT_FOR_PLANNING_REVIEW
risk_level: high
route_change: true
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 3
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: independent_thread
reviewer: separate_readonly
review_required: true
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: independent runtime reviewer plus later GPT planner; M10 cannot promote itself
experiment_adequacy_gate: all formal runs must satisfy per-run and aggregate real-training, validation, full-case, stability, provenance, and cache-isolation minima
route_negative_gate: M10 cannot declare scientific stop; negative adequate evidence remains no-promotion and scientifically unresolved
scientific_completion_gate: L1-L3 mechanism fidelity, adequate training, exact final packet, strict validators, and independent runtime review
diagnostic_publication_gate: local lightweight reviewed packet only
diagnostic_publication_scope:
- md
- csv
- json
blocked_after_diagnostic_publication:
- runtime_role_push
- validation_packaging
- validation_upload
- hosted_metric_claim
- fold_expansion
- route_promotion
- scientific_stop
- M11_execution
planning_review_required: true
planning_reviewer: separate_gpt_thread
planning_review_path: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_planning_review.md
planning_review_token: ''
planning_reviewed_commit: ''
---

# M10：SRR-v3 完整机制修复、Dictionary 设计竞赛、MyoPS 因果归因与成熟 Cine 时序路线

本文件是 `planner` GPT 写出的 **规划草案**，不是 Codex 执行授权。当前状态必须保持
`DRAFT_FOR_PLANNING_REVIEW`。另一个独立 GPT/ChatGPT `critic` 必须先审查本文件和 executor
plan，计算当前合同的 SHA256，并按
`prompts/schemas/planning_review.schema.yaml` 写入
`prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_planning_review.md`。
只有 critic 给出 `PLANNING_CRITIC_READY_FOR_CODEX_MERGE`，且本文件的
`planning_review_token`、`planning_reviewed_commit` 与被审合同完全一致后，Codex
maintenance/validator 才能把本暂存内容合并到共享提示词并启动 controller。

本里程碑不授权 validation packaging、validation upload、hosted metric claim、fold expansion、
route promotion、scientific stop 或 M11。它的目标是把 SRR-v2/v2.5/v3 图中要求的机制真正实现、
充分训练、逐模块归因，并建立能冲击 leaderboard 的一方系统基础。**“能运行”不是成功标准；
结构忠实、训练充分、困难子组不被掩盖、最终输出真实受机制影响，才是完成标准。**

## Execution Contract

```yaml
task_key: 20260711_srr_v3_m10_complete_mechanism_repair
task_kind: scientific_milestone
task_type: controller
controller_mode: true
milestone_number: 10
milestone_id: M10
status: DRAFT_FOR_PLANNING_REVIEW
risk_level: high
route_change: true
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 3
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: independent_thread
reviewer: separate_readonly
review_required: true
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
planning_review_required: true
planning_reviewer: separate_gpt_thread
planning_review_path: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_planning_review.md
planning_review_token: ""
planning_reviewed_commit: ""
```

### 1. 当前角色图与权限边界

当前 agent-flow 共有八个正式角色：

1. `planner`：用户监督的 GPT/ChatGPT 规划线程；本文件由它编写。它选择科学路线、确定公式、任务图、训练预算、角色数、证据门与审阅合同。
2. `critic`：另一个独立 GPT/ChatGPT 规划审查线程；在 Codex 执行前审查本草案，不运行代码、不提交作业、不写 runtime `review.md`。
3. `controller`：顶层 Codex continuity goal；只执行本合同，负责落盘重读、三 executor 波次、Slurm 连续性、mapper/finalizer/validator 和本地轻量 final packet。
4. `executor`：Codex 实现/训练工作线程；本任务固定三个、串行波次，禁止 controller 自行增加、删减、合并职责或发明变体。
5. `mapper`：controller 内部只读架构/证据映射线程；只能在授权时更新 root `wiki/`，不训练、不做科学结论。
6. `finalizer`：确定性 `FINALIZER_A`/`FINALIZER_B` 脚本阶段，不是 LLM；完成终态核算、聚合、mapper-final handoff、validator 和单次本地轻量提交。
7. `validator`：一方 fail-closed 脚本；发现错误必须非零退出，不能把 warning 当通过。
8. `reviewer`：final packet 本地提交后启动的独立只读 Codex 线程；只写 `review.md`，不能修包、训练、监控或启动后续里程碑。

高风险流程固定为：

```text
planner GPT
  -> separate GPT critic
  -> Codex merge/validator
  -> controller
       -> wave 1 shared-architecture executor
       -> mapper draft
       -> wave 2 MyoPS training/evidence executor
       -> wave 3 Cine temporal executor
       -> FINALIZER_A
       -> mapper final
       -> FINALIZER_B + local lightweight commit
     controller stops
  -> separate Codex reviewer
  -> later GPT planner/user decision
```

任何角色都不得在 controller runtime 中 push。planner 草案的仓库发布不构成 scientific/runtime
授权。

### 2. 前置审阅关口与读取凭据

执行前必须精确验证：

```text
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md:
M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY
```

同时必须验证：

```text
results/20260711_agent_flow_generic_protocol_repair/review.md:
AGENT_FLOW_GENERIC_PROTOCOL_REPAIR_AUDITED_GO
```

若 token、planning critic hash、当前合同 hash、executor plan、route-diagram bootstrap、工作树隔离、
Slurm skill、mapper skill、root wiki/current-state fingerprint 任一不匹配，只允许产生最小 blocked
packet，状态为 `M10_BLOCKED_PREREQUISITE` 或 `M10_NEEDS_REVISION`；不得实现或训练。

视觉读取凭据：

```yaml
diagram_source: ChatGPT Project background materials
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
canonical_repo_paths:
  - images/SRR-v2.png
  - images/SRR-v2.5.png
  - images/SRR-v3.png
visual_read_status: READ_FROM_PROJECT_BACKGROUND
later_project_diagrams_found: []
```

从图中恢复出的不可降级目标是：

```text
真实 availability-aware 模态处理
 -> 多尺度 shared/private/interaction semantic representation dictionary
 -> lesion-conditioned spatial retrieval
 -> train/OOF + online safe prototype memory
 -> union/LV/RV anatomy prior
 -> scar/edema pathology-specific proposal
 -> pathology-specific soft-ROI refinement
 -> SRR 自身 final logits
```

`nnU-Net` 只能作为 same-split control、detached teacher/context、uncertainty 或显式 safety
comparator，不能作为 formal candidate 的 final-logit base。Cine 次线必须从 ED/reference、成熟
registration、非参考帧、CineMA 表示、motion/anatomy/texture dictionary 和 learned temporal
aggregation 形成最终输出，不能继续使用 frame0 或 deterministic union proxy 冒充时序模型。

### 3. history_files_read

本次 system-level 设计已读取以下当前与历史材料；controller、critic、mapper、reviewer 均需按需复核：

```text
wiki/current_state.yaml
wiki/README.md
wiki/MODEL.md
wiki/COMPONENTS.csv
wiki/architecture.yaml
wiki/history/README.md
wiki/history/COMPARISON.md

wiki/history/M08/README.md
wiki/history/M08/ORIGINAL_ANALYSIS.md
wiki/history/M08/snapshot.yaml
wiki/history/M08/COMPONENTS.csv
wiki/history/M08/components/availability-no-t2.md
wiki/history/M08/components/retrieval-dictionary.md
wiki/history/M08/components/prototype-memory.md
wiki/history/M08/components/anatomy-prior.md
wiki/history/M08/components/proposal.md
wiki/history/M08/components/refiner.md
wiki/history/M08/components/arbitration.md
wiki/history/M08/components/losses.md
wiki/history/M08/components/checkpoint-selection.md
wiki/history/M08/components/cine-temporal.md
wiki/history/M08/components/training-evidence.md

wiki/history/M09/README.md
wiki/history/M09/ORIGINAL_ANALYSIS.md
wiki/history/M09/snapshot.yaml
wiki/history/M09/COMPONENTS.csv
wiki/history/M09/components/availability-no-t2.md
wiki/history/M09/components/retrieval-dictionary.md
wiki/history/M09/components/prototype-memory.md
wiki/history/M09/components/anatomy-prior.md
wiki/history/M09/components/proposal.md
wiki/history/M09/components/refiner.md
wiki/history/M09/components/arbitration.md
wiki/history/M09/components/losses.md
wiki/history/M09/components/checkpoint-selection.md
wiki/history/M09/components/cine-temporal.md
wiki/history/M09/components/training-evidence.md

TODO-dictionary.md
prompts/shared/M10_srr_v3_complete_mechanism_repair.md
prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml
```

最近提交检查至少覆盖：

```text
925a001 Add agent-flow generic protocol repair review
1300caa Generalize agent-flow policy schemas and validators
fa4e50b Harden M10 planning handoff validation
48353e7 Complete pre-M10 controller continuity repair
b62580b Initialize M10 controller packet
7c7b78e Add M10 single-executor controller plan
e26895b Add M10 complete SRR-v3 mechanism repair milestone
20650aa Finalize agent-flow v2 pre-M10 repair
d82c647 Add agent-flow v2 history and parallel continuity follow-up
10878dc Repair executable agent-flow v2 controller continuity
```

其中 `1300caa`/`925a001` 增加并审计了 generic schema、`critic` 角色、动态 history 与
planning-review hash；`fa4e50b` 明确把旧 M10 草案和旧 executor plan 保留为必须失败的反例。
本文件和新 plan 必须替换该反例，而不是绕过 validator。

### 4. 当前架构问题清单：M10 必须逐项修复

以下问题是代码和 M8/M9 证据共同指出的，不允许通过重命名、增加 CSV 或延长旧训练回避：

1. 当前 `RetrievalRouter` 以全局池化特征、availability 和 anchor summary 输出病例级权重，不能在病灶位置形成空间选择。
2. shared/private/interaction bank 骨架存在，但尚未证明 representer 学到 lesion-forming 表示；旧 Lite 的 `[fused,fused,fused]` 路径不得进入正式模型。
3. 当前所谓 Pattern-SIP 与 `dict_loss`/entropy/coverage 发生 alias，主要是手写 slot family prior 和事后汇总，不是真正按 availability/style/hard subgroup 优化的 integrativeness。
4. `ProposalDictionary` 的正式原型仍可能来自 deterministic axis buffer；`SafePrototypeMemoryBank` 类别少、像孤立 helper，没有完成 memory→similarity→proposal→refiner→final label 闭环。
5. hard-negative 主要来自旧表或一次性统计，未完成“当前模型误报→安全过滤→memory refresh→继续训练→前后比较”。
6. proposal 公式对 nnU-Net anchor/component context 权重过大，dictionary 可能只在 teacher 附近修补。
7. refiner 当前更像小 crop residual，且可回退到图像中心 seed；这会产生与 anatomy/proposal 无关的伪 lesion formation。
8. M8 anchor-residual 把 nnU-Net 变成主角；M9 改成 SRR-main 后，scar/edema 均未形成稳定 segmentation basis。M10 不能简单在两者间来回切换。
9. anatomy prior 有 union/LV/RV/distance/uncertainty 接口，但尚未证明真实改善 proposal recall、ROI coverage 和 final logits。
10. M9 loss wiring 修过，但 Pattern-SIP/memory 仍为 alias，Cine loss 仍是零占位；任何 alias/placeholder 都不能作为完成证据。
11. patch-centric checkpoint 选择仍可能由 patch loss 主导；M10 必须在 scheduled checkpoints 上做完整病例、challenge-facing 指标选择。
12. 既往 `ablation_matrix`、`refiner_causal_effect` 等文件名强于实际内容；M10 若写 causal，必须是真正同 checkpoint intervention 或匹配预算重训。
13. Cine 当前只用 classical SyN/Demons、少量 frame pairs、CineMA frame-wise proxy 和 deterministic union；没有成熟 learned registration 与 temporal model。
14. 当前 formal capacity 仍偏小；正式模型不能继续以 `tiny_3scale`、`base_channels=10` 作为 leaderboard 级候选。
15. 当前实现没有把“结构完成”“运行激活”“最终输出影响”“科学增益”分层，容易再次把 wiring 缺陷误判为路线失败。

### 5. 组件评估顺序：先完整实现，再谈作用

每个组件必须依次通过四层审查：

```text
L1 structural_fidelity
  按本合同实现了真实代码路径，不是名字、wrapper、静态表或零占位。

L2 runtime_activation
  使用真实数据时有合法输入、非零梯度/更新、非平凡空间输出、正确 availability 与 provenance。

L3 final_output_effect
  预先定义的 intervention 会在 intended cases 中改变 proposal/refiner/final logits 或 labels，
  且不靠 GT-aware decode。

L4 scientific_contribution
  在完整系统、充分训练、同一 split、匹配 control 下改善 challenge-facing 指标或给出可信 trade-off。
```

只有 L1-L3 全部通过，才允许评估 L4。允许的组件结论仅为：

```text
NECESSARY_SIGNAL
COMPLEMENTARY_SIGNAL
ACTIVE_BUT_NOT_BENEFICIAL
REDUNDANT_UNDER_CURRENT_CHECKPOINT
INCONCLUSIVE_NEEDS_MATCHED_RETRAIN
INCOMPLETE_FIDELITY_BLOCKER
```

同 checkpoint toggle 可以证明运行因果影响，不能单独证明“可替代”；除本合同明确要求的匹配重训
control 外，不得临时增加/删除变体或宣布组件科学无效。

### 6. M10 正式 MyoPS 架构合同

#### 6.1 Availability、模态顺序与编码器

唯一模态顺序是：

```text
[LGE, T2, C0]
```

令：

$$
m=(m_{\mathrm{LGE}},m_{\mathrm{T2}},m_{\mathrm{C0}})\in\{0,1\}^3.
$$

占位存储可以为零，但缺失模态不能借卷积 bias、normalization 或 interaction 泄漏进入语义计算。
每个带 bias/normalization 的 block 后必须再次施加 mask：

$$
F_{q,0}=m_q S_q(x_q),\qquad
F_{q,\ell+1}=m_q\left(E_\ell(F_{q,\ell})+A_{q,\ell}(F_{q,\ell})\right),
$$

其中 $$E_\ell$$ 是可共享 stage，$$A_{q,\ell}$$ 是模态适配器。正式候选必须使用四尺度
`balanced_4scale` 或等价容量，通道下限为 `[24,48,96,192]`；`tiny_3scale` 只允许 mechanism
smoke。所有正式 D0-D3 变体参数量需在共同参考的 $$\pm10\%$$ 内；若显存不足，使用 gradient
accumulation/checkpointing，不得偷偷降成小模型。

#### 6.2 多尺度 semantic representation dictionary

至少在三个 decoder-relevant scales 上建立：

$$
\mathcal D_\ell=
\mathcal D_\ell^{sh}\cup
\mathcal D_\ell^{LGE}\cup
\mathcal D_\ell^{T2}\cup
\mathcal D_\ell^{C0}\cup
\mathcal D_\ell^{LGE,T2}\cup
\mathcal D_\ell^{LGE,C0}\cup
\mathcal D_\ell^{T2,C0}.
$$

每尺度至少有四个 shared representers、每模态两个 private representers、每合法 pair 两个
interaction representers。representer 必须有独立参数，建议使用 residual depthwise-separable
`Conv3d + pointwise Conv3d + normalization + GELU/LeakyReLU` adapter；禁止把同一个 fused tensor
复制成伪模态输入。

输入规则：

$$
X^{sh}_\ell=\operatorname{concat}
\left(
\operatorname{mean}_{q:m_q=1}F_{q,\ell},
\operatorname{var}_{q:m_q=1}F_{q,\ell}
\right),
$$

$$
X^q_\ell=F_{q,\ell},
$$

$$
X^{a,b}_\ell=
\psi_\ell^{a,b}\left[
F_{a,\ell},
F_{b,\ell},
|F_{a,\ell}-F_{b,\ell}|,
F_{a,\ell}\odot F_{b,\ell}
\right].
$$

private slot 只在对应模态存在时运行；interaction slot 只在 pair 全部存在时运行。invalid slot
forward value、gate weight、gradient 和 memory update 均必须为零，数值容差 $$10^{-7}$$。

#### 6.3 四种必须分别实现和报告的 dictionary 设计

所有设计共享相同 encoder、anatomy head、proposal/refiner 容量、sampler、训练时长、评估病例和
decode 规则；Codex 不得自行改名、删减或增加第五个 formal design。

```text
D0_STATIC_MATCHED_PROPREF
  参数量匹配 control。保留同样数量的 expert adapters，但使用预先声明的合法静态混合，
  无内容路由、无 Pattern-SIP、无 prototype similarity；保留 conv proposal + refiner。
  作用：排除“只是多参数/多卷积”的解释。

D1_SPATIAL_BR2_PROPREF
  使用 shared/private/interaction bank 和单尺度局部空间 router；
  无跨尺度 feedback、无 prototype memory。
  作用：检验 spatial BR2 retrieval 本身。

D2_HIERARCHICAL_BR2_PSIP_PROPREF
  在 D1 上加入 coarse-to-fine 两遍 router、跨尺度 proposal feedback 和真正 Pattern-SIP；
  无 prototype memory。
  作用：检验层级 lesion-conditioned retrieval 与 integrativeness。

D3_HIERARCHICAL_BR2_MEMORY_PROPREF
  在 D2 上加入 train/OOF + EMA + learnable-residual prototype memory、
  safe hard-negative refresh、病种专属 proposal/refiner、条件 feature alignment。
  这是 M10 formal candidate；nnU-Net 仍只作 detached teacher/context/control。
```

D0-D3 均必须分别输出参数量、FLOPs/patch、峰值显存、训练秒数、steps、loss 稳定性、
proposal/refiner 指标、最终指标和困难子组。只训练 D3 或把 D0-D2 写成 inference toggle 均为
hard failure。

#### 6.4 Lesion-conditioned 两遍空间 router

router 必须输出空间权重图：

$$
\alpha_{t,\ell,k}(x)\in[0,1],\qquad
\sum_{k\in V(m)}\alpha_{t,\ell,k}(x)=1,
$$

而不是每个病例一个向量。第一遍产生 coarse routing 和 proposal seed；第二遍 query 至少包含：

$$
q_{t,\ell}(x)=\phi_{t,\ell}\left[
F_\ell^{avail}(x),
e(m),
P_{t,\ell}^{(0)}(x),
P_{union,\ell}(x),
P_{LV,\ell}(x),
P_{RV,\ell}(x),
d_{myo,\ell}(x),
U_\ell(x),
s^+_{t,\ell}(x),
s^-_{t,\ell}(x),
h^{style}_\ell
\right].
$$

$$h^{style}_\ell$$ 由当前图像特征产生；center ID 只可用于审计分组，不得作为推理输入。logit 与
masked normalization 为：

$$
a_{t,\ell,k}(x)=w_{t,\ell,k}^{\top}q_{t,\ell}(x)+b_{t,\ell,k},
$$

$$
\alpha_{t,\ell,k}(x)=
\frac{v_k(m)\exp(a_{t,\ell,k}(x)/\tau)}
{\sum_j v_j(m)\exp(a_{t,\ell,j}(x)/\tau)}.
$$

训练前 20% 使用完整 masked softmax，20%-70% 使用温度退火加 top-4，后 30% 使用 top-2
straight-through 或等价可微稀疏门；不得一开始 hard top-k。必须记录 spatial standard deviation、
effective slots、invalid max/mean、per-group usage、梯度与 final-logit intervention。

#### 6.5 Pattern-conditioned SIP

分组 $$g$$ 至少覆盖 availability pattern、train-only style cluster、scar/edema positive、
small/large lesion、remote-FP hard group；center 只作报告维度。对 ROI 权重 $$r_i(x)$$：

$$
u_{t,\ell,k,g}=
\frac{\sum_{i\in g}\sum_x r_i(x)\alpha_{t,\ell,k}^{(i)}(x)}
{\sum_{i\in g}\sum_x r_i(x)+\epsilon}.
$$

使用 participation-ratio 近似软 integrativeness：

$$
\gamma_{t,\ell,k}=
\frac{\left(\sum_{g\in G_k}u_{t,\ell,k,g}\right)^2}
{\sum_{g\in G_k}u_{t,\ell,k,g}^2+\epsilon}.
$$

其中 $$G_k$$ 只包含 slot 合法的组。独立优化项为：

$$
\mathcal L_{\mathrm{PSIP}}=
\lambda_{\mathrm{int}}\sum_{k\in D^{sh}}
\left[\max(0,\gamma_{\min}-\gamma_{t,\ell,k})\right]^2
+\lambda_{\mathrm{lb}}\sum_g
\mathrm{KL}(\bar u_{t,\ell,g}\Vert\pi_{t,\ell,g})
+\lambda_{\mathrm{sp}}\mathbb E_x H(\alpha_{t,\ell}(x))
+\lambda_{\mathrm{collapse}}\mathcal L_{\mathrm{collapse}}.
$$

$$\pi$$ 只在合法 slot 上定义，且不是所有 slot 的 uniform target。该项必须有独立函数、独立 raw
value、独立权重、独立梯度测试；其张量值或计算图与旧 `dict_loss` 相同即 fail。Pattern-SIP
不能只在 aggregator 中计算。

#### 6.6 Cross-fitted prototype memory 与 proposal

scar、edema 分别维护多原型正类和安全负类。正式初始化必须来自同一训练 split 的三折
cross-fitted features；任何用于当前病例 proposal 的原型不得由该病例标签直接构造。形式为：

$$
p_{t,c,j}=
\operatorname{normalize}\left(
\operatorname{sg}(\mu^{EMA}_{t,c,j})+\delta_{t,c,j}
\right),
$$

其中 $$\mu^{EMA}$$ 保存 source cases、count、age、assignment 和 update ledger，
$$\delta$$ 是有正则的可学习残差。禁止 deterministic axis prototype 进入正式 run；若 OOF bank
缺失或空，必须 fail closed。

类别至少包括：

```text
scar positive:
  core, boundary
scar safe negative:
  normal myocardium, blood pool, outside myocardium,
  LGE bright artifact, remote FP island
edema positive:
  T2 lesion core, T2 lesion boundary
edema safe negative:
  T2-present normal myocardium, blood pool, outside myocardium,
  T2 texture noise, T2-present remote FP island
```

no-T2 myocardium 对 edema negative 的 accepted count、梯度和 memory update 必须恒为零。

使用平滑多原型相似度：

$$
s^+_t(x)=\tau_p\log\sum_j
\exp\left(\frac{\cos(e_t(x),p^+_{t,j})}{\tau_p}\right),
$$

$$
s^-_t(x)=\tau_p\log\sum_j
\exp\left(\frac{\cos(e_t(x),p^-_{t,j})}{\tau_p}\right).
$$

proposal logit 为：

$$
z_t^{prop}(x)=
r_t(x)
+\beta_{t,1}\left(s_t^+(x)-s_t^-(x)\right)
+\beta_{t,2}z_t^{evid}(x)
+\beta_{t,3}\operatorname{logit}A_t(x)
-\beta_{t,4}d_{remote}(x)
-\beta_{t,5}U_t(x)
+\beta_{t,6}C_t^{teacher}(x).
$$

$$\beta_{t,1:5}$$ 为 `softplus` 约束的可学习非负系数；teacher/context 系数
$$0\le\beta_{t,6}\le0.15$$，teacher 张量必须 detached。每项必须单独导出贡献图统计。scar proposal
LGE-dominant、偏 precision；edema proposal T2-conditioned、偏 recall。no-T2 时 edema proposal
从 loss、memory、decode、export 四处阻断。

#### 6.7 Anatomy、soft ROI、refiner 与 final logits

anatomy decoder 输出 background、myocardium-union、LV、RV；scar/edema 标签训练 anatomy 时
折叠进 myocardium-union。它同时输出 uncertainty 和到 union/LV/RV 的软距离支持。

soft ROI：

$$
G_t(x)=
\sigma(z_t^{prop}(x)/T_t)
(1-U_t(x))
\left[\epsilon+(1-\epsilon)A_t(x)\right]
\exp(-\kappa_t d_{remote}(x)).
$$

scar 使用较紧的 myocardium-neighborhood crop 和高分辨率 refiner；edema 使用更大 dilation、
T2 feature、boundary uncertainty 和更大感受野。crop 只是计算边界，真正作用必须是 soft gate；
proposal 为空时只能退回 anatomy-union ROI，并记录 `ANATOMY_FALLBACK`，禁止退回图像中心 seed。

最终 pathology logits：

$$
z_t^{final}(x)=z_t^{prop}(x)+G_t(x)\Delta z_t^{ref}(x),
\qquad t\in\{scar,edema\}.
$$

最终六类 logits：

$$
z^{6}=
[z_{bg},z_{myo},z_{LV},z_{RV},z_{edema}^{final},z_{scar}^{final}].
$$

formal output 必须记录：

```text
final_output_base: SRR_PROPOSAL_REFINEMENT
nnunet_role: DETACHED_CONTEXT_TEACHER_CONTROL_ONLY
```

禁止 `anchor_logits + delta`、静默 fallback、用 anchor label 替换 formal output，或只在 CSV 中声称
refiner 影响输出。允许单独导出 `nnunet_safety_comparator`，但它不参与 formal candidate decode。

#### 6.8 条件 feature alignment expert

D3 必须实现可审计的 LGE-reference feature alignment expert，但只能在 pair 合法时运行。它至少在
LGE-T2 和 LGE-C0 的中低尺度预测位移并 warp feature，采用局部 NCC/feature similarity、
anatomy consistency、smoothness 和 Jacobian-fold penalty。其输出进入 interaction dictionary，不得
改写原始数据或标签。

alignment 必须有：

```text
unaligned D3 control
aligned D3 intervention
pair-valid mask
registration quality matrix
Jacobian fold rate
before/after scar and T2-present edema metrics
```

如果成熟 alignment 不改善 formal checkpoint，可保持 formal gate 关闭，但实现、训练和因果报告仍
是 blocking；不能把“未使用”伪装成“已完成”。

### 7. 损失、优化与训练稳定性合同

总损失必须由独立实现的真实项构成：

$$
\begin{aligned}
\mathcal L={}&
\lambda_{ana}\mathcal L_{ana}
+\lambda_{full}\mathcal L_{full}^{6cls}
+\lambda_{sp}\mathcal L_{scar}^{prop}
+m_{T2}\lambda_{ep}\mathcal L_{edema}^{prop}\\
&+\lambda_{sr}\mathcal L_{scar}^{ref}
+m_{T2}\lambda_{er}\mathcal L_{edema}^{ref}
+\lambda_{proto}\mathcal L_{proto}
+\lambda_{mem}\mathcal L_{memory}\\
&+\lambda_{hn}\mathcal L_{hardneg}
+\lambda_{psip}\mathcal L_{PSIP}
+\lambda_{inv}\mathcal L_{invalid-slot}
+\lambda_{roi}\mathcal L_{ROI}\\
&+\lambda_{bd}\mathcal L_{boundary}
+\lambda_{hd}\mathcal L_{HD-surrogate}
+\lambda_{align}\mathcal L_{align}
+\lambda_{teach}\mathcal L_{detached-teacher}.
\end{aligned}
$$

要求：

- anatomy：DiceCE，包含 union/LV/RV；
- scar：DiceCE + precision-aware Focal-Tversky + boundary/HD surrogate；
- edema：所有 dense/proposal/refiner/boundary 项均乘 T2-present mask，使用 recall-aware
  Focal-Tversky；无 T2 batch 返回带合法计算图的 masked NA，而不是负类；
- full-output：六类 DiceCE，edema channel 对 no-T2 样本屏蔽；
- prototype：正负 margin/InfoNCE，edema negative 仅 T2-present；
- hard-negative：当前模型 remote/component FP 的安全 margin；
- ROI：GT coverage、outside-myocardium ratio、uncertainty calibration；
- teacher：只约束 context/representation，不把 nnU-Net logits变成 final base。

每个 loss 必须在 `loss_component_contract.csv` 标记为：

```text
real_optimized_loss
diagnostic_metric_only
disabled_with_reason
```

禁止 `alias_loss` 和 `placeholder_zero_loss`。known-good 测试把任一 active 权重从 $$0$$ 改为
$$10$$ 时，total loss 和 intended parameter group 梯度必须改变；任意两个不同 loss 的 tensor identity、
数值全程相同或 gradient target 完全相同必须由 validator 拒绝。

优化固定要求：

```text
optimizer: AdamW
mixed_precision: true
gradient_clip_norm: 5.0
warmup_fraction: 0.05
scheduler: cosine_with_floor
early_stop_before_minimum_budget: forbidden
```

训练分四阶段：

```text
A  anatomy/evidence + soft router warmup
B  dictionary/proposal + Pattern-SIP + OOF memory
C  refiner/full-output + boundary/HD optimization
D  current-model hard-negative refresh + low-LR joint calibration
```

loss 稳定性最低门：

- 所有 loss/gradient 必须 finite；无 NaN/Inf；
- one-batch overfit 必须使目标 Dice 上升且总 loss 相对初始下降至少 30%；
- formal run 最后 25% 的总 loss EMA 不得比中间 25% 高超过 10%，否则分类
  `DIVERGED_OR_UNSTABLE`；
- 任一 weighted component 连续三个 validation windows 占总绝对 weighted loss 超过 70%，或
  active component 连续三个 windows 低于 0.5% 且非 masked NA，必须触发
  `LOSS_DOMINANCE_NEEDS_REVISION`；
- 记录每项 raw/weighted value、实际权重、gradient norm、目标参数组、EMA 与 masked denominator；
- 不得通过 sleep、空 step、重复缓存评估、synthetic batch 或减少病例来满足训练秒数/steps。

### 8. 多设计训练预算与 challenge-facing checkpoint 选择

正式训练只使用授权训练 split 与 fold0 same-split 44-case full-case evaluation。challenge validation、
held-out test、hosted metric 或 GT-aware decode 不得用于训练、阈值、选择或 calibration。

aggregate 最低真实训练预算：

```yaml
aggregate_min_train_loop_seconds: 72000
aggregate_target_controller_runtime_hours: 22
formal_eval_cases: 44
T2_present_edema_positive_cases_min: 16
CenterB_cases_min: 7
CenterC_cases_min: 9
```

每个单一 Slurm job walltime 不得超过 8 小时。训练秒数只统计真实 forward/backward/optimizer 和
预定 validation，不含排队、sleep、文件拷贝或等待 accounting。

| 运行 | 最低 train-loop 秒 | 最低 optimizer steps | validation events | full-case events | eval cases |
|---|---:|---:|---:|---:|---:|
| D0 static matched control | 7200 | 20000 | 12 | 4 | 44 |
| D1 spatial BR2 | 9000 | 25000 | 15 | 5 | 44 |
| D2 hierarchical BR2 + PSIP | 9000 | 25000 | 15 | 5 | 44 |
| D3 full memory PropRef | 14400 | 40000 | 20 | 8 | 44 |
| D3 hard-negative refresh | 5400 | 15000 | 10 | 4 | 44 |
| retrained no-nnU-Net-context control | 5400 | 15000 | 10 | 4 | 44 |
| alignment train/control | 3600 | 8000 | 8 | 3 | 44 |
| CineMA CARE adapter | 3600 | 5000 | 8 | 3 | ≥12 |
| learned Cine registration | 7200 | 10000 | 12 | 4 | ≥12 |
| learned Cine temporal dictionary | 7200 | 8000 | 12 | 4 | ≥12 |

达到 steps 但未达到真实 train-loop seconds，或达到 seconds 但未达到 steps，都只能标
`SCIENTIFIC_UNDERTRAINED`。OOM、divergence 或 plateau 可终止 job，但不能补写 adequate。

scheduled checkpoints 必须直接运行 full-case evaluation。patch loss 只作 sanity，不能决定 formal
best。每个 checkpoint 先执行硬约束：

```text
no-T2 edema output == 0
label/export semantics valid
all 44 cases present
T2-present/edema-positive and CenterB/CenterC rows complete
no cache/checkpoint collision
finite Dice/HD95/remote-FP/component metrics
```

随后建立 scar/edema Pareto frontier。联合 checkpoint 选择采用预先声明的 lexicographic 规则：

1. 最大化 scar 与 T2-present edema 的最差病例组 Dice delta；
2. 在第一项容差 $$0.002$$ 内，最大化两项 mean Dice；
3. 在前两项容差内，最小化 scar+edema HD95；
4. 再最小化 remote-FP ratio 与 median component count；
5. 若没有 checkpoint 同时满足 non-catastrophic guard，选择最小 harm checkpoint并明确
   `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`，不得改阈值追分。

阈值和 component decode 只能在 train/inner-validation 中校准，必须固定后再运行 44-case
same-split evaluation。

### 9. 真实 component causal audit

完整 D3 通过 L1-L3 和训练充分门后，在同一 selected checkpoint、同一 44 cases、同一 decode 上
执行：

```text
full_system
static_mixture_intervention
spatial_router_to_global
Pattern-SIP_stateless_intervention
prototype_similarity_off
memory_pre_refresh_vs_post_refresh
anatomy_prior_off
scar_refiner_off
edema_refiner_off
both_refiners_off
nnunet_context_off
alignment_off
```

每行必须记录：

```text
component, intervention, checkpoint, case_id, subgroup,
proposal_logit_l1_delta, refiner_logit_l1_delta, final_logit_l1_delta,
changed_label_voxels, Dice_delta, HD95_delta, remote_fp_delta,
component_count_delta, intended_role, L1_status, L2_status, L3_status,
interpretation
```

另外只有以下匹配训练 control 可以用于 L4：

```text
D0 vs D1 vs D2 vs D3
D3 vs retrained no-nnU-Net-context control
D3 before vs after bounded hard-negative refresh
```

组件尚未完整实现时，不得先跑负 ablation；必须返回
`INCOMPLETE_FIDELITY_BLOCKER` 并回到 wave 1 修复，而不是继续训练掩盖缺陷。

### 10. Cine：CineMA、成熟 registration 与 learned temporal dictionary

Cine 是 blocking 次线，不可跳过，也不能为 MyoPS 负结果背书。

#### 10.1 CineMA 完整使用

必须使用当前仓库/批准缓存中许可证、来源、commit/model identifier、文件 SHA256 和 preprocessing
可核验的 CineMA 资产。若资产或许可不可验证，状态为 `RESOURCE_BLOCKED_CINEMA_PROVENANCE`，
不得临时 clone 未审依赖或用随机 backbone 冒充。

CineMA 的正式用途不是只导出 frame0 mask，而是：

- 作为每帧 anatomy feature backbone；
- 在 CARE train 上训练 segmentation adapter，并至少解冻/低学习率适配最后两个 block 或使用明确
  LoRA/adapter；
- 输出每帧 LV/RV/MYO logits、feature maps 和 uncertainty；
- 记录 frozen/trainable 参数、权重 checksum、label map、方向/spacing/time-axis QA；
- 与随机初始化同容量 adapter 做至少一个匹配 control。

#### 10.2 Learned diffeomorphic registration

ED/reference frame 为 $$I_0$$。每例至少使用 ED、ES 和六个均匀/运动显著帧；有足够帧时总数至少
8，不能只用一个 non-reference pair。registration network：

$$
v_t=R_\theta(I_0,I_t,P_0,P_t),\qquad
\phi_t=\exp(v_t),
$$

通过 scaling-and-squaring 得到可微 diffeomorphic warp。损失：

$$
\mathcal L_{reg}=
\lambda_{ncc}(1-\mathrm{LNCC}(I_0,W_{\phi_t}I_t))
+\lambda_{ana}\mathcal L_{Dice}(P_0,W_{\phi_t}P_t)
+\lambda_{sm}\|\nabla v_t\|_2^2
+\lambda_{inv}\|\phi_t\circ\phi_t^{-1}-Id\|_2^2
+\lambda_{jac}\operatorname{ReLU}(-\det J_{\phi_t}).
$$

ANTsPy SyNOnly 和 Demons 只作 classical controls。formal registration 必须报告所有 case/frame 的
before/after anatomy Dice、HD95、NCC、folding voxel fraction、displacement magnitude、失败原因和
fallback；失败 case 保留在 denominator，不能静默删除。成熟门要求在 safe subset 上多数
non-reference pairs 的 anatomy Dice/NCC 改善，folding rate 受控，并且至少优于 frame0/no-warp control
中的一个明确指标；否则 Cine 返回诚实 blocker。

#### 10.3 Temporal representation dictionary

将每帧 feature、warped anatomy、texture、displacement/Jacobian/strain proxy 和 registration quality
送入 cue-specific bank：

$$
\mathcal D^{cine}=
\mathcal D^{anchor}\cup
\mathcal D^{anatomy}\cup
\mathcal D^{texture}\cup
\mathcal D^{motion}\cup
\mathcal D^{quality}.
$$

$$
R_{cine}(x)=
\sum_{t\in T}\sum_k
\beta_{t,k}(x)
E_k\left[
W_{\phi_t}F_t(x),
W_{\phi_t}P_t(x),
\phi_t(x),
J_{\phi_t}(x),
q_t
\right],
$$

其中 $$\beta$$ 由 frame quality、phase、motion saliency、registration uncertainty 和局部 anatomy
生成并归一化。最终输出是 learned reference-space myocardium segmentation，不是 deterministic union。

Cine 总损失：

$$
\mathcal L_{cine}=
\mathcal L_{seg}^{ED}
+\lambda_{reg}\mathcal L_{reg}
+\lambda_{temp}\mathcal L_{temporal-consistency}
+\lambda_{cycle}\mathcal L_{cycle}
+\lambda_{dict}\mathcal L_{temporal-dictionary}
+\lambda_{qual}\mathcal L_{quality-calibration}.
$$

同一不少于 12-case 的安全 subset 必须比较：

```text
frame0 CineMA/adapter control
classical SyN/Demons warped control
learned registration + simple averaging
M9 deterministic temporal proxy
M10 learned temporal dictionary final output
```

报告 `myocardium_cinemyops` 本地 proxy（myocardium Dice/HD95）、LV/RV sanity、temporal jitter、
registration failure matrix 和 final compact-label manifest。不得声称 hosted readiness。

### 11. 精确任务图和 required outputs

以下所有节点均为 blocking，并按依赖顺序执行。缺任一目录或 required file，completion check 必须
失败。

1. `20260711_srr_v3_m10_architecture_fidelity`
   - `results/20260711_srr_v3_m10_architecture_fidelity/`
   - required: `result.md`, `architecture_fidelity_contract.md`,
     `dictionary_design_contract.csv`, `component_activation.csv`,
     `loss_component_contract.csv`, `invalid_slot_runtime.csv`,
     `prototype_provenance.json`, `nnunet_role_audit.md`,
     `commands_run.md`, `MANIFEST.md`.
2. `20260711_srr_v3_m10_mechanism_smoke`
   - `results/20260711_srr_v3_m10_mechanism_smoke/`
   - required: `result.md`, `one_batch_overfit.csv`, `gradient_effect.csv`,
     `loss_alias_selftest.csv`, `proposal_refiner_sanity.csv`,
     `no_t2_safety.csv`, `known_bad_selftest.csv`,
     `commands_run.md`, `MANIFEST.md`.
3. `20260711_srr_v3_m10_myops_d0_control`
   - required: `result.md`, `training_budget_ledger.csv`, `loss_stability.csv`,
     `checkpoint_selection.csv`, `same_split_metrics.csv`,
     `hard_subgroup_metrics.csv`, `commands_run.md`, `MANIFEST.md`.
4. `20260711_srr_v3_m10_myops_d1_spatial_br2`
   - 同 D0 required，另加 `dictionary_runtime.csv`, `spatial_router_metrics.csv`.
5. `20260711_srr_v3_m10_myops_d2_hierarchical_psip`
   - 同 D1 required，另加 `pattern_sip_metrics.csv`, `pattern_group_usage.csv`.
6. `20260711_srr_v3_m10_myops_d3_full_propref`
   - 同 D2 required，另加 `prototype_memory_ledger.csv`,
     `proposal_metrics.csv`, `refiner_metrics.csv`, `final_output_effect.csv`.
7. `20260711_srr_v3_m10_hard_negative_refresh`
   - required: `result.md`, `hard_negative_mining_ledger.csv`,
     `memory_update_ledger.csv`, `refresh_before_after.csv`,
     `training_budget_ledger.csv`, `loss_stability.csv`,
     `commands_run.md`, `MANIFEST.md`.
8. `20260711_srr_v3_m10_no_nnunet_context_control`
   - required: `result.md`, `training_budget_ledger.csv`,
     `checkpoint_selection.csv`, `same_split_metrics.csv`,
     `nontrivial_signal_check.csv`, `commands_run.md`, `MANIFEST.md`.
9. `20260711_srr_v3_m10_alignment_control`
   - required: `result.md`, `registration_quality.csv`,
     `alignment_on_off.csv`, `jacobian_report.csv`,
     `commands_run.md`, `MANIFEST.md`.
10. `20260711_srr_v3_m10_component_causal_audit`
    - required: `result.md`, `component_interventions.csv`,
      `component_contribution.csv`, `refiner_true_toggle.csv`,
      `dictionary_router_interventions.csv`, `anatomy_prior_intervention.csv`,
      `memory_intervention.csv`, `final_label_effect.csv`,
      `commands_run.md`, `MANIFEST.md`.
11. `20260711_srr_v3_m10_cinema_adapter`
    - required: `result.md`, `cinema_provenance.json`, `label_geometry_qa.csv`,
      `adapter_training_budget.csv`, `framewise_anatomy_metrics.csv`,
      `commands_run.md`, `MANIFEST.md`.
12. `20260711_srr_v3_m10_cine_registration`
    - required: `result.md`, `registration_training_budget.csv`,
      `cine_registration_pair_metrics.csv`, `cine_registration_failure_matrix.csv`,
      `jacobian_report.csv`, `commands_run.md`, `MANIFEST.md`.
13. `20260711_srr_v3_m10_cine_learned_temporal`
    - required: `result.md`, `cine_training_budget.csv`,
      `cine_frame_usage.csv`, `cine_temporal_dictionary_runtime.csv`,
      `cine_frame0_vs_controls_vs_learned.csv`,
      `cine_case_metrics.csv`, `cine_final_output_manifest.csv`,
      `commands_run.md`, `MANIFEST.md`.
14. `20260711_srr_v3_m10_completion_check`
    - required: `decision.md`, `required_output_check.csv`,
      `training_adequacy_check.csv`, `loss_stability_check.csv`,
      `stale_status_scan.csv`, `validator_report.md`,
      `known_bad_selftest.csv`, `MANIFEST.md`.
15. 主 controller packet：
    - `results/20260711_srr_v3_m10_complete_mechanism_repair/`
    - required: `result.md`, `controller_context.json`, `controller_ledger.csv`,
      `controller_bootstrap_snapshot.md`, `implementation_snapshot.md`,
      `finalizer_state.json`, `mapper_report_draft.md`,
      `architecture_delta_draft.md`, `mapper_report_final.md`,
      `architecture_delta_final.md`, `m10_system_summary.md`,
      `m10_dictionary_design_comparison.csv`,
      `m10_component_contribution.csv`, `m10_myops_decision_matrix.csv`,
      `m10_cine_decision_matrix.csv`, `completion_check.md`,
      `review_request.md`, `MANIFEST.md`, `subagents/reviewer_prompt.md`.

最低表结构：

```text
training_budget_ledger.csv:
variant,job_id,partition,state,exit_code,train_loop_seconds,optimizer_steps,
validation_events,full_case_events,eval_cases,checkpoint,stop_reason,adequacy

loss_stability.csv:
variant,stage,step,component,classification,raw_value,configured_weight,
actual_weight,weighted_value,ema_value,gradient_norm,target_parameter_group,
masked_denominator,finite,dominance_fraction,status

dictionary_runtime.csv:
variant,case_id,subgroup,task,scale,slot_id,slot_group,valid,
gate_mean,gate_max,gate_spatial_std,expert_output_norm,gradient_norm,
proposal_logit_delta,final_logit_delta,status

checkpoint_selection.csv:
variant,checkpoint,eval_cases,scar_dice,scar_hd95,scar_remote_fp,
edema_t2_positive_dice,edema_t2_positive_hd95,edema_remote_fp,
CenterB_delta,CenterC_delta,no_t2_violation_count,pareto_status,selected,reason

component_interventions.csv:
component,intervention,checkpoint,case_id,subgroup,proposal_logit_l1_delta,
refiner_logit_l1_delta,final_logit_l1_delta,changed_label_voxels,
dice_delta,hd95_delta,remote_fp_delta,component_count_delta,
L1_status,L2_status,L3_status,interpretation

cine_registration_pair_metrics.csv:
case_id,fixed_frame,moving_frame,method,before_dice,after_dice,
before_hd95,after_hd95,before_ncc,after_ncc,folding_fraction,
mean_displacement,quality_pass,failure_reason
```

### 12. Known-bad fixtures 和 fail-closed 要求

validator 至少必须拒绝：

```text
旧无 frontmatter M10 staging
旧 invalid-lane/missing-completion-token executor plan
缺 planning critic hash/token 却标 READY_FOR_CODEX_MERGE
global pooled router 冒充 spatial router
missing-modality private/interaction slot weight 非零
Pattern-SIP 与 dict_loss alias
deterministic axis prototype 进入 formal run
prototype 无 train/OOF provenance
no-T2 myocardium 被接受为 edema negative
memory 不影响 proposal similarity
proposal/refiner 不改变 final logits
proposal 空时中心 seed fallback
formal output 仍是 anchor_logits + delta
loss weight 0/10 不改变目标梯度
Cine temporal/ref-warp loss 为零占位
patch-loss-only checkpoint selection
proxy summary 冒充 causal effect
训练未达 seconds/steps/cases/events
submitted/pending/monitor packet 冒充 completion
Cine frame0-only、单 pair registration 或 deterministic union 冒充 learned temporal
Cine registration 失败 case 被移出 denominator
stale wiki/fingerprint/figures
```

### 13. 科学判定门

M10 operational completion 不要求必然赢，但要求所有 blocking 机制、训练、证据和 Cine 路线完整。
允许的 mechanism-signal 条件：

- D1 相对 D0 显示 spatial retrieval 对 intended region 有非平凡 final-logit effect；
- D2 相对 D1 显示 hierarchical router/Pattern-SIP 的独立信号，不发生 gate collapse；
- D3 相对 D2 显示 prototype/memory/proposal/refiner 对 lesion-wise recall、HD95、remote FP 或
  component burden 有可信贡献；
- scar gate：Dice 不低于 anchor，HD95/remote FP 不恶化，且至少一个严格改善；
- edema gate：T2-present/edema-positive Dice 和 HD95 不低于 anchor，CenterB/CenterC 无未解释
  severe harm，no-T2 violation 为零；
- no-context control 仍存在非平凡 lesion signal，证明 SRR 不是 nnU-Net identity；
- Cine learned temporal 在同一 subset 相对 frame0 和至少一个 control 有可解释改善，registration
  failure matrix 完整。

若结构保真或训练充分性失败：`M10_NEEDS_REVISION` 或 `M10_NEEDS_EVIDENCE`。

若实现、训练和证据完整但指标为负：

```text
M10_COMPLETE_NO_PROMOTION_SCIENTIFIC_UNRESOLVED
```

不得宣布 SRR/Cine 科学失败，不得自动回退 nnU-Net，不得启动 M11。

## Controller Prompt

你是 M10 唯一顶层 Codex controller。你没有科学设计权，只能执行本合同。启动前从磁盘重新读取
本 staging、planning critic review、executor plan、当前 HEAD、`AGENTS.md`、全部 handoff schemas、
Slurm skill、mapper skill、root wiki、M8/M9 history 和两个前置 review token；不要依赖聊天摘要。

先运行并记录：

```text
python scripts/validation/validate_handoff_policy.py --policy --warnings-as-errors
python scripts/validation/validate_handoff_policy.py --candidate prompts/shared/M10_srr_v3_complete_mechanism_repair.md
python scripts/ops/validate_executor_plan.py prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml
python scripts/validation/validate_handoff_policy.py --repository-readiness --warnings-as-errors
```

生成 `controller_context.json`、bootstrap snapshot 和 append-only ledger。若 planning critic 的
`reviewed_contract_sha256` 与当前 staging 不一致，立即停止。

严格按 executor plan 启动三个串行 wave：

```text
wave 1: m10_shared_architecture_executor
merge by controller
mapper draft
wave 2: m10_myops_training_executor
merge by controller
wave 3: m10_cine_temporal_executor
merge by controller
```

不得把三个 executor 合成一个，不得并行 MyoPS/Cine，不得修改 variant 数量或训练预算。每个
executor 必须在独立 worktree/branch 内写自己的 completion file/token；只有 controller 可按
`merge_order` 合并。任何 executor 返回 `NEEDS_REVISION`、`NEEDS_EVIDENCE`、`NEEDS_MONITOR`、
`BLOCKED` 时，不得伪造 ready token。

Slurm 默认 `htzhulab`，只按 skill 允许顺序使用 `a100-gpu`、`volta-gpu` 或隔离 routing race。
每个 training/eval job walltime ≤8h。训练链可以由多个 jobs 构成；必须记录全部 job IDs。使用
`scripts/ops/submit_care_dependency_finalizer.py` 提交 `afterany` finalizer，依赖 **所有**
training/registration/temporal job IDs，而不是只依赖链末尾。若 dependency finalizer 失败，才允许
namespace-local tmux watcher fallback，并记录 session/PID/command/log/lock/result dir。

`PENDING`、`RUNNING`、`CONFIGURING`、`COMPLETING`、`AWAITING_SACCT` 都是
`NEEDS_MONITOR`。不得把 submission receipt、watcher setup、pending `squeue` 或 monitor packet
当 completion；scheduler block 只按连续 12 次、每次间隔 2 小时、累计 24 小时无任何 routing job
启动的门槛判定。

`FINALIZER_A` 必须：

1. 收集所有 job terminal state、exit code、elapsed、log/runtime paths；
2. 验证所有 runtime output 存在；
3. 运行 MyoPS/Cine aggregators、completion check 和 strict packet validator；
4. 写 `finalizer_state.json`，只有全部 terminal/aggregated 才能到 `READY_FOR_MAPPER_FINAL`。

mapper final 后，`FINALIZER_B` 必须运行 strict validators、known-bad、Toolkit healthcheck、
wiki history/current figures check、`git diff --check`，再做一次本地轻量 packet commit。禁止提交
checkpoint、prediction、NIfTI、zip、大日志、raw data、secret/env dump。

controller report 写在 reviewer 前，只能使用：

```text
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
git_push_decision: SKIP_PUSH
next_required_action: separate reviewer writes review.md
```

写完 controller report 后停止。不得写 `review.md`、不得启动 M11、不得 push。

## Executor Worker Contract

三个 executor 必须分别遵守以下固定职责。

### Wave 1：shared architecture executor

只负责完整实现和 fidelity/smoke，不跑正式长训练。必须：

- 逐 symbol 审计当前 `srr_blocks.py`、`srr_propref.py`、`srr_dictionary_memory.py`、
  `srr_losses.py`；
- 实现 D0-D3 共用的四尺度 encoder、semantic bank、两遍 spatial router、Pattern-SIP、
  cross-fitted/EMA/learnable-residual memory、proposal/refiner final base、alignment hooks；
- 删除正式路径的 deterministic prototype、center seed fallback、anchor-final base、alias/zero loss；
- 写 unit tests、one-batch overfit、gradient/weight 0-vs-10、invalid-slot、no-T2、final-output-effect、
  known-bad fixtures；
- 只在全部 fidelity/smoke 通过时写 `READY_FOR_CONTROLLER_MERGE`。

若发现公式无法在现有代码中忠实实现，不得自行简化；写
`NEEDS_GPT_PLANNER`/`NEEDS_REVISION` 和精确 blocker。

### Wave 2：MyoPS training/evidence executor

只使用 wave 1 已合并且冻结的 architecture source。不得修改 `src/care_myocardium/models/` 或
`losses/` 来追分；若正式训练暴露 wiring bug，停止并返回 wave 1 repair，不得热补后继续。

必须按 D0→D1→D2→D3→hard-negative refresh→no-context retrain→alignment control 顺序提交真实
Slurm jobs，满足每项 seconds/steps/events/cases。每个变体使用隔离 checkpoint/prediction/cache/log/
lock path。必须执行 scheduled full-case checkpoint selection、困难子组、proposal/refiner、loss 稳定性和
真实 component interventions。不得用旧 checkpoint、旧 CSV、synthetic/smoke 或 inference-only toggle
替代匹配训练。

### Wave 3：Cine temporal executor

必须完整使用可核验 CineMA 资产，实现 CARE adapter、learned diffeomorphic registration 和 learned
temporal dictionary。Classical registration、frame0 和 M9 union 只作 controls。至少处理 12 个安全病例、
每例足够 non-reference frames，失败病例保留 denominator。若外部资产/许可/几何不合格，诚实写
resource/evidence blocker；不得 clone 随机代码、降级 single-frame 或把 deterministic union 包装成完成。

所有 executor 共同行为：

- 只写各自 executor plan `write_scope`；
- 每次提交 job 前重读 Slurm skill；
- 写完整 `commands_run.md`、MANIFEST、provenance 和 completion file；
- 不写 runtime `review.md`，不自审，不 push，不启动下一 wave；
- 不允许 Codex 自行制定科研计划、改变公式、缩短预算或选取更容易的病例。

This is an executor/controller session for one milestone only. Stop after writing
`completion_check.md` and `review_request.md`, force-add/commit the lightweight required result
files, then stop. Do not push automatically. Do not write `review.md` and do not start the next
milestone. The milestone must be reviewed by a separate read-only Codex session before continuation.

## Mapper Contract

你是 controller 内部独立 mapper。使用 `.agents/skills/care-mapper/SKILL.md`。draft 阶段在 wave 1
merge 后从 source/config/tests/fidelity evidence 建立架构映射；未有 runtime 证据的组件必须保持
`partial/unverified`，不能因类或文件存在而标 verified。

final 阶段在全部 jobs terminal 且 `FINALIZER_A` 聚合成功后重新从当前 source 和结果 grounding。
更新：

```text
wiki/README.md
wiki/MODEL.md
wiki/EXECUTION.md
wiki/COMPONENTS.csv
wiki/LINEAGE.md
wiki/architecture.yaml
wiki/figures/model-current.{d2,svg,png}
wiki/figures/model-gap.{d2,svg,png}
wiki/figures/execution-flow.{d2,svg,png}
wiki/history/README.md
wiki/history/COMPARISON.md
```

M8/M9 历史不可改写。按当前动态 history 规则生成/验证 M10 snapshot 与
`delta-from-M09.{d2,svg,png}`；若 runtime review 尚未发生，M10 snapshot 必须明确 pre-review，
不能伪造 review token。

每个组件记录 source/symbol、inputs/outputs、loss、final-output effect、runtime evidence、code
fingerprint、L1-L4 状态。运行：

```bash
AI_RESEARCH_TOOLKIT_ROOT=/overflow/htzhu/mingcheng_new/AI_Research_Toolkit \
  python scripts/architecture/run_toolkit_healthcheck.py --check
python scripts/architecture/generate_care_architecture_wiki.py
python scripts/architecture/generate_care_architecture_wiki.py --check-all
python scripts/architecture/validate_care_architecture_wiki.py --strict --history
```

mapper 不训练、不提交 Slurm、不改模型代码、不写 `review.md`、不做 route promotion/scientific
stop。

## Reviewer Prompt

你是 final packet 本地提交后启动的独立只读 M10 reviewer。读取本 staging/merged contract、
planning critic review、executor plan、三个 executor completion receipts、十五个 blocking result
directories、一方 source/config/helper/test、root wiki、M8/M9 history、前置 review tokens 和
finalizer/controller receipts。可以运行只读 strict validators；不得修文件、训练、恢复 job、生成缺失
wiki、打包、upload、push 或启动 M11。

逐项审查：

1. planning critic hash/token、当前 prompt hash、executor plan、三个串行 worktree/merge receipts；
2. 所有 exact result dirs/files、终态 Slurm accounting、post-job aggregation；
3. aggregate real train-loop seconds ≥72000，且每个 formal run 达到自身 seconds/steps/events/cases；
4. D0-D3 是真实匹配训练设计，不是同 checkpoint 开关、改名或 CSV；
5. router 是空间两遍路径，invalid slot 在 forward/gate/gradient/update 中严格为零；
6. Pattern-SIP 是独立训练目标，不与旧 dict loss alias；
7. prototype 有 cross-fitted provenance、EMA+learnable residual、safe-negative 和 refresh 闭环；
8. proposal/refiner/anatomy/memory 真正影响 final logits，formal output 不是 nnU-Net identity；
9. no-T2 edema 在 supervision、memory、decode、export 四处阻断；
10. loss 无 alias/placeholder/miswire，曲线和梯度满足稳定性门；
11. checkpoint 来自 scheduled 44-case full-case metric selection，困难子组齐全；
12. causal 文件是真 intervention，within-checkpoint 结论没有越界称 replaceable；
13. CineMA provenance、adapter 训练、至少 8 frames/case、learned registration、learned temporal
    dictionary、same-subset controls 和 failure denominator 完整；
14. validator 严格拒绝所有 known-bad；
15. mapper/wiki/fingerprint/figures 与最终代码和 runtime evidence 一致。

以下任一情况必须拒绝 audited-go：缺文件；monitor/pending；训练不足；运行输出未聚合；D0-D3
未分别重训；global router；Pattern-SIP alias；deterministic/no-provenance prototype；no-T2 负样本；
proposal/refiner 对 final 输出无影响；anchor final base；patch-loss checkpoint；proxy causal 表；
Cine frame0/单 pair/classical-only/union-only；Cine failure case 被排除；validator 或 wiki stale。

允许 decision：

```text
M10_AUDITED_GO_MECHANISM_SIGNAL
M10_AUDITED_COMPLETE_NO_PROMOTION_SCIENTIFIC_UNRESOLVED
M10_AUDITED_NEEDS_REVISION
M10_AUDITED_NEEDS_EVIDENCE
M10_AUDITED_NEEDS_MONITOR
```

`M10_AUDITED_GO_MECHANISM_SIGNAL` 只允许 later GPT planner 设计下一里程碑，不授权 route promotion、
fold expansion、validation packaging/upload、hosted claim 或 M11 自动执行。完整实现和训练充分但指标
仍负时，必须使用
`M10_AUDITED_COMPLETE_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`，不得宣布科学失败。

This is a separate read-only reviewer session. Do not fix code, do not generate missing artifacts,
do not train, and do not start the next milestone. Review only the completed result directory, write
`review.md` with the controlled milestone decision, then force-add/commit `review.md`. Do not push
automatically.
