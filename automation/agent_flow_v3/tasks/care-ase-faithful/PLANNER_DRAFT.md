# CARE-ASE 忠实重实现：Planner 完整规划草案

## 0. 精确绑定与本轮结论

本规划只处理 `care-ase-faithful`，绑定如下机器真值：

```text
task_id: care-ase-faithful
request_nonce: care-ase-20260806T090955Z
integration_branch: develop
request_path: automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json
request_git_blob_sha: 230b121ce8a2a448d38f695ee9769b902742b384
current_path: automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json
current_git_blob_sha_before_planning: 22f3a6f550b0bfb3c07fc8d2c2a4e90c85f9027b
visual_manifest_path: automation/agent_flow_v3/tasks/care-ase-faithful/VISUAL_SOURCES.json
visual_manifest_git_blob_sha: 1387c29faa65fcd9efdfb9d52172b0da8fd2ae14
planner_visual_receipt: results/agent_flow_v3/care-ase-faithful/planner_visual_receipt.json
planner_visual_receipt_sha256: 69577e8e5dc09e12f4cc1eca02131e47b2164ac111abb0539244a140af9848e1
```

Planner 的结论是：**必须重建并验证 CARE-ASE 的实现忠实性，但不得在本任务中再次训练模型或用 step6000 结果修改科学架构。** 当前 R2 代码、历史 PASS receipt 和训练 checkpoint 只作为待审计的既有实现与反例来源，不能自动继承为正确证据。

本任务的唯一成功含义是：独立 Verifier 先冻结足以击穿降级实现的验证体系，独立 Executor 再完成与本规划及后续 Critic 冻结合同一致的实现，最后由 Planner 对精确提交、指纹、CI 和真实运行 receipt 做多轮审阅，直至无阻断性实现偏差。成功后停在人工决策门；不自动训练、访问 outer、合并 `main`、构建 Docker 或上传。

## 1. 权威层级与冲突消解

Critic 冻结时必须把以下来源吸收到一个自包含合同中，不能让 Executor 自行选择版本：

1. **任务与角色边界最高优先级**
   - `prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_loop.md`
   - `prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_controller.md`
   - `prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_role_plan.json`
   - `prompts/AGENT_FLOW_V3_PROTOCOL.md`

2. **科学拓扑权威**
   - `prompts/blueprints/CARE_ASE_final_model_blueprint_20260801.md`
   - `prompts/blueprints/CARE_ASE_exact_implementation_contract_20260801.yaml`
   - CARE-ASE 架构图及本任务视觉 receipt。

3. **后续代码正确性修订**
   - `prompts/blueprints/CARE_ASE_R2_effective_contract_v8_20260803.yaml`
   - `prompts/blueprints/CARE_ASE_R2_effective_contract_v9_20260803.yaml`
   - 这些版本中关于活初始化、命名证据投影、no-T2 五类语义、全体积 extent、checkpoint schema v4、精确恢复、目标缓存、采样和运行隔离的更严格规则覆盖早期冲突字段。

4. **仅作诊断而非设计权威**
   - 当前 `src/care_myocardium/models/care_ase.py` 及 R2 runtime；
   - 所有历史内部 PASS receipt；
   - step6000 held-out diagnostic；
   - MoSAIC、SRR、MMRD、Cascade、DG、ARC、PRISM、MyoWall 的源码与结果。

明确冲突消解如下：

- edema 弱 LGE gate 初始输出固定为 `0.05`，不是早期草案的 `0`；该值只打破死梯度，最终 step0 pathology logit parity 由下游零初始化的**独立命名证据投影**保持。
- 模态 adapter 使用非零 Kaiming/nnU-Net 兼容初始化；不得 adapter 输出与下游投影同时为零。
- no-T2 不把 class 4 映射为背景；应忽略 class-4 target、完全不调用该行 edema-owned 子图，并在最终竞争中只保留 `[0,1,2,3,5]`。
- 单窗口与滑窗推理必须走同一 canonical full-volume 路径；extent 只在聚合完基础 logits、wall 和全局 extent evidence 后施加一次。
- 当前任务运行于 `develop`；旧合同中写死的 `main`、旧结果目录和旧 permit 路径不得照搬。相关路径必须参数化并绑定当前任务、当前提交和当前 nonce。
- 本任务不签发 formal training permit。14,000-step 日程、恢复和全体积评价必须被实现和验证，但不得实际启动正式训练。

## 2. 已知结果的正确解释

step6000 同口径诊断显示：88 例 scar Dice 为 `0.441313`，较 nnU-Net 低 `0.125983`；32 个 T2-present 病例 pure-edema Dice 为 `0.400175`，较 nnU-Net 低 `0.003587`。最佳早期观察点分别是 scar step500 和 edema step3000，之后 scar 尤其在 fold4 明显恶化。

这些结果只支持以下判断：

- 当前实现或优化过程没有保持成熟 scar 能力；
- scar 与 edema 的最佳时间尺度不同；
- 当前实现可能存在分支 authority、梯度所有权、初始化、损失耦合、stage 解冻、采样、checkpoint/inference step 语义或全体积 extent 方面的问题；
- 不能据此判定 CARE-ASE 科学架构必然失败，也不能据此调新阈值、改损失系数、选 outer 病例或新增组件。

Verifier 必须把当前 R2 代码当作一个**未被证明忠实的候选**，而不是从历史 PASS 状态继续补 receipt。

## 3. 冻结的科学模型合同

### 3.1 输入、标签与部署函数

```text
dataset: Dataset501_CAREMyoPS
input order: [LGE, T2, C0]
availability: manifest-provided three-bit mask
compact labels:
  0 background
  1 healthy myocardium
  2 LV cavity
  3 RV cavity
  4 pure edema
  5 scar
wall union: labels 1|4|5
injury auxiliary: labels 4|5
```

部署模型必须是 `f(images, availability)`，不得读取 center ID、source ID、病例 ID、outer 信息或其他模型输出。center 只允许用于训练采样和分组报告。

scar/anatomy 使用全部可靠病例；pure-edema、injury、edema boundary、edema context 与 edema extent 只在真实 T2-present 且标签可靠的病例上监督。no-T2 病例不得作为 edema 阴性。

### 3.2 唯一完整主干

实现一个完整 stock-compatible 三维 nnU-Net trunk：

- 加载同 fold 的 `nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres` checkpoint；
- encoder、bottleneck、全部 decoder stages 和 deep-supervision heads 的参数字节覆盖率至少 `0.99`；
- 通道、stride、kernel、stage 数量全部由 plans 与真实模块 introspection 决定，禁止猜测或缩小；
- 新证据关闭时，FP32 各尺度 stock-compatible logits 最大误差不超过 `1e-6`，argmax changed voxels 为 `0`；
- encoder 与低/中分辨率 decoder 只运行一次；
- Stage A 后完整 shared decoder 与规定的 encoder stages 必须可训练，禁止永久冻结主干；
- stock class-4/class-5 normal-forward logits只可用于初始化/parity audit，绝不能进入 CARE-ASE 最终 pathology logits、fallback、teacher 或 residual add。

### 3.3 分叉结构与文件边界

在最高两个 decoder resolution 分成三条真正独立路径：

```text
AnatomyContextBranch
ScarBranch
EdemaBranch
```

不得仅在 D0 后接两层卷积。scar 与 edema 必须各自 clone/继承最高两个 stock decoder stages，并拥有独立参数和单行 classifier。

Executor 应把当前巨型单文件拆成可审查模块，至少形成：

```text
src/care_myocardium/models/care_ase/__init__.py
src/care_myocardium/models/care_ase/model.py
src/care_myocardium/models/care_ase/stock_trunk.py
src/care_myocardium/models/care_ase/modality_adapters.py
src/care_myocardium/models/care_ase/anatomy_context.py
src/care_myocardium/models/care_ase/scar_branch.py
src/care_myocardium/models/care_ase/edema_branch.py
src/care_myocardium/models/care_ase/slice_extent.py
src/care_myocardium/training/care_ase/losses.py
src/care_myocardium/training/care_ase/sampler.py
src/care_myocardium/training/care_ase/trainer.py
src/care_myocardium/inference/care_ase_full_volume.py
```

旧 import 路径需要时可保留薄兼容层，但兼容层不得包含另一套实现或绕过新路径。不能同时保留两个可运行 CARE-ASE 真值。

### 3.4 模态角色适配与证据注入

每个最高两尺度的每个允许模态使用：

```text
Conv3d(1,16,3,padding=1)
InstanceNorm3d(16,affine=True)
SiLU
Conv3d(16,C_scale,1)
```

规则：

- adapter 非零初始化；
- 缺失输入和输出按病例硬清零；
- scar：LGE mandatory primary，C0 auxiliary，T2 forbidden；
- edema：T2 mandatory primary，C0 auxiliary，LGE weak context；
- scar/edema C0 gate 初始输出 `0.2`；
- edema LGE tanh gate 初始输出 `0.05`；
- 每个 evidence source 有独立、具名、零初始化的 `1x1` residual projection；
- 共享多源投影、自由 router、top-k mixture、center-conditioned gate 均禁止。

必须用两阶段梯度 liveness 证明：第一次反向时每个 required residual projection 有非零有限梯度；在临时克隆状态做一次零信用确定性更新后，第二次反向时相应 adapter、gate、dilation/context 上游获得非零有限梯度。该探针不进入任何训练 checkpoint、不产生科学指标、不得被算作 formal training。

### 3.5 解剖与软心肌壁上下文

`AnatomyContextBranch` 输出：

```text
anatomy_logits_0_3
p_wall_union
p_lv
p_rv
signed_endo_distance
signed_epi_distance
wall_depth_rho
```

- anatomy target 将 labels 4/5 remap 为 1；
- 物理 EDT 使用真实 spacing，clip 到 `[-10mm,10mm]` 后除以 10；
- `rho = d_endo / (d_endo + d_epi + 1e-6)`；
- 异常拓扑切片只 mask distance/rho regression；
- 输入 pathology branch 前全部 `detach()`；
- 只能作为软通道或软 logit bias；
- hard multiply、hard crop、hard clipping、wall-space transform 和 geometry fail-stop 禁止。

所有旋转/缩放后物理 target 必须从变换后的 segmentation 与有效 spacing 重新计算，不能只插值旧距离场。

### 3.6 ScarBranch

ScarBranch 必须同时实现“全图候选形成”和“最高两尺度直接重建”：

- `ScarCoarseProposalHead` 在 1/4 与 1/2 尺度分别产生 occupancy logit 和 component-center heatmap；
- 保留所有 GT scar components，26-connectivity；
- center Gaussian：in-plane `4mm`，z 方向 `1 slice`；
- proposal 只作软证据，禁止 bbox、hard ROI 或 crop；
- 最高两尺度 decoder 真实消费 shared feature、stock skip、LGE/C0 adapters、proposal occupancy、center、detached soft-wall/context；
- classifier 从 shape-compatible stock class-5 row 初始化；
- 最终直接输出 `z_scar`；
- 4 类 context classifier：scar、normal myocardium、blood-pool-adjacent、remote/background；其 logits 必须进入 scar final path，不得只是有 loss 的旁路头。

Scar sampler 固定比例：

```text
35% GT scar component-centered
20% small scar (<1000 mm3) component-centered
20% canonical OOF scar FN / low-overlap
15% canonical OOF remote or blood-pool-adjacent FP
10% random wall/background
```

OOF 必须来自该病例未训练过的 stock nnU-Net、精确预处理网格和逐病例 checkpoint/provenance 绑定。空 pool 时必须明确改变 resolved category，不得用普通中心冒充 requested category。

### 3.7 EdemaBranch

EdemaBranch 只对 T2-present 行执行，采用全体积连续区域重建：

- 不使用 proposal bbox、hard ROI、局部 crop、largest-component target 或 compactness；
- 最高两尺度独立 decoder；
- T2 evidence 为 mandatory primary；
- full path 包含真实 dilation `1/2/4` residual blocks，而不是三个孤立标量/旁路卷积名称；
- 输出 `z_pure_edema`、injury auxiliary、boundary；
- injury classifier 从 stock class4/5 shape-compatible mean 初始化；
- boundary 最终层可零初始化，但其上游和 loss 路径必须可学习；
- edema context classifier 必须进入 final reconstruction evidence。

Edema sampler 只从 T2-present eligible pool 取样：

```text
35% pure-edema positive
20% canonical OOF low-volume/FN
20% edema boundary
15% safe FP or blood-pool-adjacent
10% random wall/background
```

complete-case 内 CenterB/CenterC 以 `1:1` 循环；不足时有放回抽样。不得从 no-T2 组抽任何 edema event。

### 3.8 SliceExtentHead 与全体积语义

scar、edema 各自拥有独立 1/4-scale extent head：

```text
masked average + masked max over H/W
Conv1d(C,64,3,padding=1)
GroupNorm(8,64)
SiLU
Conv1d(64,64,3,padding=1)
SiLU
presence Conv1d(64,1,1)
area Conv1d(64,1,1) + sigmoid
```

target 来自 full-case profile，不允许从裁剪 patch 局部重新定义：

- presence：该原始物理切片是否有病灶；
- area：pathology voxels / wall-union voxels；
- presence validity 与 area validity 分开；
- padding、全无效切片和 partial-H/W 不得产生 area/wall bias、loss 或梯度；
- hard slice zeroing 禁止。

最终固定软偏置：

```text
scar: 0.30 presence + 0.20 area + 0.15 wall
edema: 0.35 presence + 0.30 area + 0.10 wall
```

训练与推理调用同一 `compute_slice_extent_statistics`。滑窗时各 tile 只输出 base logits、wall 与 extent evidence；在全体积聚合后只施加一次 global extent bias。单 tile 与多 tile 必须走同一代码路径。

### 3.9 最终类别竞争与 no-T2

T2-present：

```text
final_logits = concat(anatomy 0..3, z_edema, z_scar)
final = argmax over [0,1,2,3,4,5]
```

T2-absent：

- 该行任何 edema-owned module call count 为 `0`；
- 所有 edema-exclusive loss 与参数梯度严格为 `0`；
- class 4 target 为 ignore，不映射为背景；
- decode 固定对 `[0,1,2,3,5]` argmax；
- 不得通过把 class-4 logit简单置零后仍参加六类竞争来冒充；
- mixed batch 必须对子集执行并安全 scatter，不得让 absent 行经过 edema graph。

无固定 scar-priority、无 per-case threshold、无 post-hoc overwrite。

## 4. 固定损失、采样和日程实现

只允许原合同列出的损失及固定权重：

```text
1.00 final six-class DiceCE
0.50 anatomy deep-supervision DiceCE
0.25 wall DiceBCE
0.10 distance/rho masked SmoothL1
1.00 scar binary Dice+Focal(alpha=.25,gamma=2)
0.25 scar component-adaptive Tversky(alpha=.3,beta=.7)
0.10 scar center focal BCE
0.15 scar extent BCE+SmoothL1
0.10 scar context CE
T2-present only:
  1.00 edema binary Dice+Focal(alpha=.35,gamma=2)
  0.40 injury Dice+BCE
  0.10 edema boundary SmoothL1
  0.20 edema extent BCE+SmoothL1
  0.10 edema context CE
  0.05 relation loss
```

relation 固定为：

```text
relu(max(stopgrad(p_scar), stopgrad(p_edema)) - p_injury)
```

每项必须报告有效分母、有效病例/体素数、目标模块直接梯度和 on/off intervention。禁止新增 distillation、prototype、SIP、compactness、全局 HD surrogate 或其他损失。

训练日程必须完整实现但本任务不执行正式训练：

```text
optimizer AdamW, weight_decay 1e-4
physical batch 1
gradient accumulation 4
effective batch 4
gradient clip 12, error_if_nonfinite=true
checkpoint every 1000 optimizer steps
full-volume inner evaluation every 2000 steps

Stage A: 0–2000
  freeze stock encoder/shared decoder
  train new branches/context/adapters/extent
Stage B: 2000–10000
  unfreeze complete shared decoder + upper two encoder stages
  case mixture 50% complete / 25% LGE-only / 25% LGE+C0
Stage C: 10000–14000
  complete tri-modal only
  CenterB/CenterC 1:1
  all layers trainable with lower-encoder low LR
```

optimizer 在 step0 建立一次，stage transition 只能更新参数组 LR/`requires_grad`，不得丢 optimizer state。scheduler 固定 stage-local warmup+poly/cosine语义，由 Critic 统一选择当前 v8/v9 已实现并验证的 `stage_local_warmup_poly(power=.9)`，不得由 Executor混用两套 scheduler。任何 stage 不得因早期指标差跳过。

## 5. 数据、增强、checkpoint 与恢复合同

### 5.1 全病例目标与增强

必须冻结逐病例 manifest，至少绑定：

```text
case_id
image/segmentation/properties/plans path and SHA256
shape_zyx
spacing_zyx
cache schema
full cache payload SHA256
```

target 包括软壁距离、rho、context、boundary、scar component center、slice presence/area。stock nnU-Net runtime transform 必须对所有空间 target 保持同一变换；离散 component metadata 不得作连续插值。padding value 为 `-1`，不得进入 loss 或物理 target。

### 5.2 正式数据路径唯一性

同一正式函数必须拥有完整数据路径：eligible pool → case draw → coordinate draw → case load → initial patch → augmentation → target build → forward/backward → finite checks → accumulation → clipping → optimizer/scheduler。测试、resume oracle 与未来 formal run 不得使用预构造 batch 绕过前半段。

所有 micro-loss、trainable gradient、更新后参数与 Adam state 必须有限；任何非有限值禁止保存 checkpoint。

### 5.3 checkpoint schema v4

checkpoint 必须自包含、可部署，并绑定：

- fold、model config fold 与同 fold stock checkpoint path/SHA；
- split、actual-train cases、hard-negative manifest、target manifest；
- 当前冻结合同 SHA、critical source manifest SHA、环境确定性 manifest；
- model、optimizer、scheduler、stage、step；
- Python/NumPy/Torch/CUDA、augmentation、sampler 与 micro-patch RNG；
- 四个 microbatch descriptor 与 next-step descriptor SHA；
- logical chunk start/end、已完成 step、checkpoint reason；
- extent ramp 和所有 cursor。

cross-fold resume、旧 schema、placeholder、合同漂移、manifest 漂移、环境漂移必须 fail closed。reload 后下一 optimizer step 的四个 microbatch、loss、梯度、参数更新和 scheduler 必须与 uninterrupted 路径一致。deployment loader 不得再打开 stock checkpoint。

## 6. Verifier-first 冻结合同

Verifier 在 Executor 开始前必须提交并由 Controller冻结：

```text
verification_contract.json
public_test_manifest.json
protected_known_bad_manifest.json
verifier_fingerprint.json
verifier_session_receipt.json
```

Verifier 只能改 `tests/**`、`validators/**` 和其授权 receipt 路径。至少覆盖以下真实失败族，每个 known-bad 必须实际让 validator 非零退出：

1. 角色 session/worktree/CODEX_HOME 重叠。
2. 只继承 encoder、重置 decoder、缩小 channels 或永久冻结 trunk。
3. D0 后浅层 pathology head 冒充最高两尺度独立 decoder。
4. stock class4/5 normal-forward logits进入 final add/fallback。
5. 分支、adapter、proposal、context、extent、injury、boundary存在但不改变目标中间量或 final logits。
6. 双零初始化造成 projection/adapter/dilation 死梯度。
7. scar 使用 T2，或 edema 不消费真实 T2。
8. no-T2 行调用 edema graph、收到 edema supervision/negative、产生 edema-exclusive gradient，或 class4 仍参与竞争。
9. context/extent/soft-wall只有辅助 loss但不进入 final path。
10. hard wall、hard ROI、bbox crop、local-only refiner、prototype/dictionary/query、fixed scar-priority 被恢复。
11. full-case extent 被 patch-local profile替代；padding/partial-HW/all-invalid slice产生 bias。
12. tile 内重复施加 extent，或单 tile/多 tile代码路径不同。
13. declared loss未进入 `L_total`，有效分母为零仍声称覆盖。
14. hard-negative只有字符串/shape proof，没有真实 mask、坐标、checkpoint和预处理网格绑定。
15. requested category 与 resolved fallback 不一致却未记录。
16. checkpoint未保存完整状态、cross-fold可恢复、reload输出/下一步不一致。
17. early checkpoint inference使用最终 step 的 ramp/schedule。
18. static/canned receipt在未执行 forward/backward/inference时通过。
19. patch proxy冒充full-volume evaluator；CARE与baseline使用不同 TTA、decode、病例或metric population。
20. under-14000、跳过Stage B/C、startup/pending/preempted job计入训练。
21. outer被用于阈值、系数、checkpoint或source选择。
22. hidden host asset/旧 wrapper 绕过新实现。
23. current R2 monolithic implementation与新模块化实现同时可运行，形成双真值。
24. sentinel cases、HD95/exact HD、precision/sensitivity、volume ratio、remote FP、help/harm等接口缺失。

公共测试可告诉 Executor接口与合同，但 protected mutation 细节不得泄露。Verifier 不得替 Executor修源码。

## 7. Executor 实现合同

Executor 只能在独立 session/worktree/local branch 中修改实现范围。开始时读取冻结合同、public test manifest和当前代码，但不得读取 protected known-bad具体实现。

Executor 必须：

1. 建立唯一模块化 CARE-ASE 真值并删除/降级旧重复实现；
2. 保持必要的旧 import compatibility，但所有入口指向新真值；
3. 完成模型、loss、sampler、augmentation、checkpoint/resume、canonical full-volume inference和validator要求的 runtime；
4. 对所有 required modules注册明确 parameter owner；
5. 输出 architecture signature、source manifest、implementation fingerprint；
6. 用真实计划和同 fold stock checkpoint完成 parity、forward/backward、mixed-availability、save/reload和full-volume smoke；
7. 只运行零信用实现探针，不启动连续训练、Slurm formal job或outer评价；
8. 不得改测试、validator、蓝图、冻结合同或状态机。

当前 step6000代码不得通过“尽量少改”的理由保留不符合冻结合同的结构。重写优先于为历史 monolith继续叠加 conditional branches。

## 8. Controller 集成与审阅循环

Controller 只负责协调，不得编辑实现或验证源码。

顺序固定：

1. 创建并核验三个独立持久 session receipt；
2. 启动 Verifier；
3. 机械检查 Verifier scope，冻结其 commit与fingerprint；
4. 启动 Executor；
5. 集成 Verifier commit，再集成 Executor commit；
6. 运行本地确定性检查和 server-local protected tests；
7. push `develop`，等待 GitHub Actions；
8. 生成精确 review request，至少绑定：
   - 当前 nonce；
   - Critic 冻结合同 SHA256；
   - integration commit SHA；
   - implementation/verifier fingerprints；
   - CI run ID/status；
   - runtime receipt manifest SHA256；
   - review round；
9. 将 CURRENT 最后更新为 `READY_FOR_PLANNER_REVIEW`；
10. Planner 返回修订时，只恢复指定 exact session；`BOTH` 时先 Verifier 后 Executor；
11. 每轮重新集成、重新运行全部门并绑定新 SHA；
12. 最多 12 轮；相同阻断缺口连续三轮未关闭则停止。

## 9. Planner 后续审阅准则

每次 `READY_FOR_PLANNER_REVIEW`，Planner 必须先审完整当前实现，再看旧 finding closure。至少核验：

- 合同、集成、Verifier和Executor指纹是否精确绑定；
- 当前代码是否只有一个 CARE-ASE真值；
- 图中每个 required module是否有真实张量路径、loss、梯度和 final-output intervention；
- no-T2是否是按行图排除与五类竞争；
- current source是否仍保留 stock pathology shortcut、旁路头、patch-local extent或静态 receipt；
- CI 与 protected runtime tests是否真实执行；
- 当前轮是否改变冻结科学合同或削弱验证门。

只能返回：

```text
PLANNER_REVISE_EXECUTOR
PLANNER_REVISE_VERIFIER
PLANNER_REVISE_BOTH
PLANNER_PASS
```

## 10. 本任务完成边界

`PLANNER_PASS` 仅表示精确 `develop` 实现与冻结合同一致，没有剩余阻断性降级证据。随后必须：

```text
CURRENT -> AWAIT_HUMAN_DECISION
stop Controller/Verifier/Executor
commit and push lightweight receipts to develop
send existing notifier
```

本任务始终禁止：

- 正式训练或把实现探针计为训练；
- outer access；
- validation/challenge upload；
- Docker build/upload；
- organizer email；
- `develop -> main` 合并；
- 科学优越性、训练充分性或提交就绪结论。

## 11. Critic 必须直接审查和冻结的焦点

Critic 应在同一次运行中直接修订并重新完整审计，不因可确定问题退回 Planner。重点检查：

1. 上述源权威层级是否足以消除原始合同、v8、v9和当前代码的冲突；
2. `stage_local_warmup_poly(power=.9)` 是否应作为唯一 scheduler，若不同则直接冻结唯一选择；
3. 模块化文件迁移与旧 import compatibility 是否会产生双真值；
4. 零信用两阶段梯度探针是否不违反“禁止正式训练”；
5. no-T2 mixed-batch scatter、loss和parameter-gradient门是否完整；
6. full-case extent、augmentation后物理target和global inference应用是否无歧义；
7. Verifier protected tests是否能够识别当前R2式“模块存在但authority不足”的降级；
8. 所有路径、receipt、fingerprint、停止条件和人工门是否已闭合。

若视觉与来源可用且不存在真正需要用户选择的科学分歧，Critic应直接生成自包含冻结合同和 freeze receipt，将 CURRENT 最后更新为 `PLAN_FROZEN`。
