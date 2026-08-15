# CARE-ASE Hierarchical Pathology Rescue Blueprint

**日期：2026-08-15**  
**状态：DEFERRED_BLUEPRINT_ONLY；仅记录下一轮设计，不授权实现、训练、outer、Docker、validation 或 hosted submission**  
**目的：保存 CARE-ASE faithful long-run 的负结果、已定位失败机制，以及下一次 Agent-Flow v3 重启时必须遵守的唯一 rescue 方向。**

## 0. 结论先行

当前 CARE-ASE 不应继续按原 formulation 调参或续训。faithful implementation 已有 Planner PASS，后续 provenance 与只读机制诊断没有发现新的 model/loss/sampler/decode 语义 regression；真正失败的是系统设计：Stage B 解冻共享表示后，anatomy myocardium logit 在 GT scar 位置持续增强，最终平坦六类竞争把仍然存在的 scar signal 压掉。fold3 no-T2/partial scar 因此从“会分”退化到大量乃至全空预测。

下一版只保留 CARE-ASE 已经证明合理的资产：成熟 nnU-Net trunk、scar/edema 独立高分辨率病理分支、LGE/T2 角色分工、可靠标签/no-T2 safety、full-volume reconstruction、软解剖上下文。必须删除或重构：

1. anatomy myocardium 与 scar/edema 的平坦六类直接竞争；
2. Stage B 大范围解冻 shared low/mid decoder 与 upper encoder；
3. scar 与 pure-edema 作为三个独立 logits 和 healthy myocardium 同场竞争的最终语义。

新的核心形式是：

```text
frozen / strongly protected mature nnU-Net representation
                    ↓
           soft anatomy / wall context
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
LGE-driven scar specialist   T2-driven injury-zone specialist
        ↓                       ↓
      scar S              injury Z = scar ∪ edema
        └───────────┬───────────┘
                    ↓
     hierarchical pathology composition
       scar has pathology authority
       pure edema = injury minus scar
       healthy myocardium = wall minus pathology
                    ↓
     background / healthy MYO / LV / RV / edema / scar
```

这不是新建 CARE-XYZ，也不是再叠模块，而是对 CARE-ASE 的 final authority 和优化结构做一次最后的、最小但结构性的修正。

---

## 1. 当前证据与来源边界

### 1.1 当前仓库状态

本蓝图写入 `main`，但 2026-08-12 至 2026-08-15 的 faithful formal-training 与 outer diagnostic 证据当前主要保存在远端 `develop`。后续 Planner 重启时必须先同步远端并重新核对；不得把本蓝图中的数字当作替代机器真值。

关键 develop snapshot：

```text
develop HEAD at blueprint time:
184cc16bc00dbb4edce80e2c848bdaabae4f782e

faithful Planner PASS:
results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_009_final.json

mechanism diagnostic:
results/agent_flow_v3/care-ase-faithful-formal-training-20260812/stage_b_forgetting_diagnostic/DIAGNOSTIC_REPORT_FOR_GPT.md

outer diagnostic evidence:
results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/
```

`main` 上的 `prompts/routes/handoffs/CURRENT.md` 与 `wiki/README.md` 在本蓝图写入时仍未包含这轮 develop formal-training 终态，因此它们对该轮 CARE-ASE 结果是 stale evidence；未来正式重启前必须先做状态 reconciliation，不能静默假设已同步。

### 1.2 图像视觉依据

本蓝图写入前已视觉读取 ChatGPT Project 背景中的：

```text
SRR-v2
SRR-v2.5
SRR-v3
CARE-ASE
```

恢复的有效思想是：availability-aware evidence、病种专属证据角色、anatomy-guided pathology formation、scar/edema 非对称处理、negative-space、安全监督、成熟 nnU-Net 表示保护。明确不恢复 SRR dictionary / prototype / SIP / free router / hard ROI，也不恢复 SRR-v3 的 bounded anchor correction。

---

## 2. faithful run 到底证明了什么

### 2.1 实现层面

此前 Agent-Flow v3 Planner 最终返回 `PLANNER_PASS`，没有剩余 blocking implementation finding。后续 formal-training checkpoint provenance 继续绑定同一 frozen contract/source manifest；Stage-B 只读诊断也没有发现 no-T2 availability、decode、sampler fallback 或 runtime semantic bug。

因此下一轮默认假设必须是：

```text
IMPLEMENTATION_FIDELITY_OF_OLD_ASE = sufficiently established for scientific diagnosis
```

除非未来重新审计发现精确反证，否则不得再次把主要失败原因笼统归为“Codex 没实现对”。

### 2.2 科学失败机制

fold3 Stage-B 诊断最关键的现象：

```text
GT scar voxel margin z_scar - z_myo
step2000: +4.432
step4000: -0.878
step6000: -24.560
```

与此同时 scar half/full signal 并未归零；step6000 仍可见 scar half/full/z_scar signal，而 myocardium logit 上升到压倒性水平。actual-train partial 也出现同方向 collapse，因此不是单纯 held-out overfit。

Stage-B sampler 有大量真实 partial-scar events，bad fallback rate 约为 0；`disable_extent_wall` 不能救回 fold3 empty predictions。因此主要机制判断是：

```text
PRIMARY:
FINAL_CLASS_COMPETITION_COLLAPSE_WITH_SHARED_REPRESENTATION_DRIFT

SECONDARY:
PARTIAL_MODALITY_TRAINING_DYNAMICS_COLLAPSE

WEAK / RULED OUT AS PRIMARY:
SAMPLER_EFFECTIVE_SUPERVISION_GAP
EXTENT_WALL_NEGATIVE_BIAS
NO_T2_DECODE_OR_AVAILABILITY_RUNTIME_BUG
```

### 2.3 outer 结果说明的不是“全部机制无效”

已访问 outer 只能作为 retrospective diagnostic，后续不得用于正式 checkpoint selection。

大致趋势：

```text
early pair (fold2 5k / fold3 4k):
complete tri-modal scar ≈ 0.6793 vs nnU-Net ≈ 0.6725
pure edema ≈ 0.4503 vs nnU-Net ≈ 0.4751

late pair (fold2 12k / fold3 11k):
complete tri-modal scar ≈ 0.6465 vs nnU-Net ≈ 0.6725
pure edema ≈ 0.4808 vs nnU-Net ≈ 0.4752
```

含义：scar mechanism 和 edema mechanism 分别出现过正信号，但没有在同一稳定 checkpoint 共存。问题更像 shared optimization / final composition 冲突，而不是所有 pathology branch 都完全没有学习能力。

---

## 3. 必须修改的最终语义：从 flat competition 改为 hierarchical composition

### 3.1 Anatomy 不再拥有 pathology exclusion authority

旧版 anatomy target 将 label4/5 remap 为 myocardium class1，同时最终又让 class1 与 class4/5 直接 softmax 竞争。这在同一病灶 voxel 上制造了相互冲突的优化目标。

新版 anatomy 只输出：

```text
background/anatomy support
wall union probability
LV
RV
soft geometry
```

anatomy 仍可把 scar/edema 视为 wall union 的一部分，但 **anatomy myocardium logit 不得再直接与 scar/edema 做 final argmax 竞争**。

### 3.2 分层标签组合

最终语义必须显式分两层：

第一层：是否属于心肌壁 / cavity / background。

第二层：在 wall 内由 pathology specialist 决定 healthy / scar / edema。

建议固定组合：

```text
S = scar specialist binary decision
Z = injury-zone specialist binary decision, target = scar ∪ pure-edema
E = Z and not S
H = wall and not S and not E
```

最终输出优先级只表达病理语义，不允许 anatomy 去覆盖 pathology：

```text
scar -> label5
else injury -> label4
else wall -> label1
LV -> label2
RV -> label3
else background -> label0
```

具体 cavity/wall 冲突规则必须在下一次 Planner contract 中冻结并由 Critic 审核；Controller/Executor 不得自行发明。

### 3.3 Scar specialist authority

scar branch 继续使用 LGE 主导、C0 弱结构支持，不引入 T2 adapter。其 binary logit `z_scar` 必须成为真正的 pathology authority，而不是只作为六类 softmax 中一个候选通道。

最先做的零成本因果诊断：

```text
existing checkpoint
same full-volume inference
same cases
compare:
A. old flat six-class decode
B. canonical binary scar decode: z_scar > 0
C. hierarchical composition using existing wall/injury tensors when available
```

如果 B/C 能显著恢复 fold3 partial empty scar，同时不造成 catastrophic remote FP，才允许进入新训练实现。

### 3.4 Edema 改为 injury-zone factorization

不再让 pure-edema 与 scar 完全平行独立竞争。

新版 edema path 主目标：

```text
injury-zone Z = scar ∪ pure-edema
```

T2-present 时训练 injury-zone specialist；最终：

```text
pure edema = injury-zone minus scar
```

no-T2 时 injury/edema graph继续严格关闭，不把 no-T2 当 edema negative。

旧版 `edema_injury` auxiliary head 可作为初始化/代码资产，但下一轮不得仅把它保留为 auxiliary；它必须进入正式 final composition 或被删除。

---

## 4. 训练策略：保护成熟表示，不再大范围 Stage-B 解冻

旧 Stage B 在 step2000 后同时解冻 shared low/mid decoder、upper encoder、anatomy decoder；参数漂移与 scar-vs-myo margin collapse 同期出现。

新版第一阶段必须：

```text
FROZEN:
stock encoder
stock bottleneck
shared low/mid decoder

TRAINABLE:
scar top-two pathology decoder
injury top-two pathology decoder
modality adapters
必要的 pathology-specific heads
必要的 final hierarchical compositor parameters（若有）
```

禁止一开始重塑 shared representation。

若后续必须解冻，只能作为第二阶段小范围实验，并要求：

```text
very low LR
explicit stock-feature preservation / distillation
predeclared stop gate
no outer tuning
```

具体 LR、step 数和可解冻层必须由下一轮 Planner 明确写死，经 Critic freeze 后才能执行。

---

## 5. 明确保留与删除

### 保留

- stock-compatible nnU-Net encoder/bottleneck/shared decoder初始化；
- highest-two-resolution scar/injury specialist decoder；
- availability hard masking；
- scar: LGE primary + C0 weak support；
- injury/edema: T2 primary + C0/LGE context；
- no-T2 edema zero-gradient语义；
- full-volume continuous reconstruction；
- scar component / center / negative-space 可作为辅助监督；
- soft wall / LV / RV / distance / rho context；
- case-wise help/harm、HD95、volume ratio、empty prediction审计。

### 删除或禁止

- flat six-class pathology/anatomy competition；
- anatomy class1 对 scar/edema 的最终覆盖权限；
- 旧 Stage-B broad unfreeze；
- 新 dictionary / prototype / SIP / router；
- hard ROI / bbox / local-only refiner；
- bounded nnU-Net residual correction；
- center ID 输入；
- post-hoc largest-component 作为主要救火机制；
- 根据已经看过的 outer 选择 checkpoint/threshold；
- 再增加第二 backbone、Transformer、Mamba、foundation model。

---

## 6. 下一轮执行顺序：必须先证明“值得救”，再实现

### Gate R0 — zero-cost decode rescue

不训练。仅对现有 faithful checkpoints做只读 intervention：

1. old flat decode；
2. `z_scar > 0` binary scar decode；
3. hierarchical wall + scar + injury composition；
4. case-wise Dice / sensitivity / precision / HD95 / volume ratio / remote FP / empty count；
5. 重点 fold3 partial/no-T2 collapse cases + complete tri-modal control cases。

硬门：如果 scar branch 独立 authority 仍不能恢复 meaningful scar signal，则停止本 rescue，不进入重新训练。

### Gate R1 — architecture-only implementation

实现 hierarchical compositor、scar authority、injury-zone final path，但不改 shared trunk。

必须通过：

```text
real-case forward
loss finite
expected gradients only
no-T2 edema graph hard-off
intervention changes final labels
save/reload exactness
stock/shared trunk frozen proof
final-label authority trace
```

### Gate R2 — bounded single-fold training

只跑一个预先冻结 fold，不访问新 outer。

目标不是追求 headline，而是确认：

```text
partial scar no longer catastrophically collapses
complete scar remains >= stock-near baseline
injury/edema does not collapse
scar-vs-wall margin remains stable
```

### Gate R3 — second-fold replication

只有 R2 机制成功才复制到第二 fold。两个 fold 都必须通过后才讨论更大训练。

### Stop rule

如果 hierarchical rescue 仍不能稳定保持 scar 且同时保住 edema，则 CARE-ASE 架构探索终止。不得再通过新增模块延长路线。

---

## 7. 未来 Agent-Flow v3 重启合同

用户后续明确授权时，重新走完整 v3：

```text
GPT Planner
-> GPT Critic repair/freeze contract
-> persistent Codex Controller
-> isolated Verifier
-> isolated Executor
-> deterministic CI
-> GPT Planner implementation review
-> repair loop until PLANNER_PASS
-> HUMAN GATE
-> only then diagnostic/training authorization
```

本蓝图本身 **不等于** 新 task 已激活，也不授权 Controller/Executor 现在执行任何代码或 Slurm。

未来 Planner 必须重新读取当前：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/AGENT_FLOW_V3_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
```

并视觉读取 Project 背景 SRR-v2/v2.5/v3、CARE-ASE，以及当时可用的最新架构图。

若继续采用当前 v3 `develop` integration exception，必须在新 task 中显式声明；否则仍遵循 main-only 默认。不得由本蓝图提前授权 develop 写入、训练或 outer access。

---

## 8. TODO（未来人工启动时）

- [ ] 先 reconcile main 与 develop 的 CARE-ASE faithful-run 终态证据；更新 CURRENT/wiki 前须另行授权。
- [ ] Planner 重新审计旧 CARE-ASE code、loss、sampler、outer contamination boundary。
- [ ] 执行 R0：existing-checkpoint zero-cost hierarchical decode rescue。
- [ ] 若 R0 FAIL：记录最终 negative conclusion，停止 CARE-ASE rescue。
- [ ] 若 R0 PASS：Planner 写新的 v3 frozen contract。
- [ ] Critic 重点审查 final authority、hierarchical labels、frozen-trunk boundary、no-T2 semantics、evaluation contamination。
- [ ] Controller/Verifier/Executor 实现 R1，不训练。
- [ ] Planner implementation review 返回 PLANNER_PASS 后，再由用户授权 R2。
- [ ] R2 只跑单 fold bounded training；不使用已看过 outer 做选择。
- [ ] R2 成功后才允许 R3 second-fold replication。
- [ ] 两 fold 不能同时稳定保住 scar/edema，则终止架构探索。

---

## 9. 一句话设计原则

> **不要再问“还能加什么模块”，先保证 pathology specialist 真正拥有病理标签的最终决定权；anatomy 负责定位和结构，不再负责把 pathology 否决掉。**
