# CARE-ASE 忠实重实现冻结合同

## 0. 机器绑定与执行边界

```text
task_id: care-ase-faithful
request_nonce: care-ase-20260806T090955Z
integration_branch: develop
planner_draft_commit_sha: abf549e57452e0047a767332e786ea3a06c214cb
planner_draft_sha256: d945b065c656fa26b1b661e135195ac3e5934ff21649ee748cff716260409649
planner_visual_receipt_commit_sha: 0e4030ed92ea6d72bc3b5e37e9fc97253b690d85
planner_visual_receipt_sha256: 69577e8e5dc09e12f4cc1eca02131e47b2164ac111abb0539244a140af9848e1
```

本合同只授权在 `develop` 上重建、验证并多轮审阅 CARE-ASE 的实现忠实性。它不授权正式训练、访问 outer、合并 `develop` 到 `main`、构建或上传 Docker、提交 validation/challenge、发送组织方邮件或作出科学优越性结论。实现探针只能是零信用、有限步、不可计入任何正式训练或性能证据的确定性检查。

成功条件仅为：独立 Verifier 冻结能够击穿降级实现的验证体系，独立 Executor 完成唯一实现，Controller 集成后由 Scheduled Planner 对精确提交和真实运行证据审阅，直至 `PLANNER_PASS`，随后停止在人工决策门。

## 1. 权威来源与冲突消解

优先级从高到低如下：

1. 本冻结合同、Agent-Flow v3 角色隔离与本任务边界；
2. `CARE_ASE_final_model_blueprint_20260801.md`、`CARE_ASE_exact_implementation_contract_20260801.yaml` 和 CARE-ASE 架构图；
3. `CARE_ASE_R2_effective_contract_v8_20260803.yaml`、`CARE_ASE_R2_effective_contract_v9_20260803.yaml` 中关于运行正确性的更严格修订；
4. 当前 R2 源码、历史 PASS receipt、step6000 诊断和其他历史架构，仅作待审计实现或反例，不具设计权威。

确定性冲突统一为：

- edema 弱 LGE gate 初始输出为 `0.05`；step0 pathology parity 由其后的独立、具名、零初始化 evidence projection 保持。
- modality adapter 必须活初始化；禁止 adapter 与下游 projection 同时零初始化造成死梯度。
- no-T2 行完全不执行 edema-owned 子图，class 4 不进入 softmax/argmax 分母，target 4 为 ignore，不映射为背景。
- 单窗口与滑窗使用同一 canonical full-volume 路径；全局 extent/wall bias 仅在 tile 聚合后施加一次。
- 活动分支为 `develop`；旧 `main`、结果目录和 permit 路径必须参数化并绑定当前 nonce、合同和提交。
- scheduler 唯一为 stage-local warmup + polynomial decay，power `0.9`；Stage C 无 warmup。
- 本合同不签发 formal training permit，也不允许启动 14,000-step 训练。

## 2. 固定任务、标签和部署函数

```text
dataset: Dataset501_CAREMyoPS
input order: [LGE, T2, C0]
availability: manifest-provided 3-bit mask
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

部署函数必须严格为 `f(images, availability)`。center、source、case ID、outer 信息、其他模型输出或推理时 selector 均不得进入 forward。center 仅可用于训练采样和分组报告。

scar 与 anatomy 使用全部可靠病例；pure-edema、injury、edema boundary、edema context 和 edema extent 仅在真实 T2-present 且标签可靠的病例上监督。no-T2 病例绝不作为 edema 阴性。

## 3. 唯一完整主干与三条高分辨率路径

必须实现一个完整、stock-compatible 的 3D nnU-Net trunk：

- 加载同 fold 的 `nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres` checkpoint；
- encoder、bottleneck、全部 decoder stages 和 deep-supervision heads 参数字节覆盖率至少 `0.99`；
- 通道、stride、kernel、stage 数量由 plans 与真实模块 introspection 决定，禁止猜测、缩宽或缩层；
- 新证据关闭时，各尺度 FP32 stock-compatible logits 最大绝对误差不超过 `1e-6`，argmax changed voxels 为 `0`；
- encoder 与 shared low/mid decoder 只运行一次；
- Stage A 后完整 shared decoder 与规定 encoder stages 必须按日程解冻，禁止永久冻结；
- stock class-4/class-5 normal-forward logits仅可用于权重初始化和 parity audit，不得进入正常 forward 的 final add、fallback、teacher、distillation 或 residual。

最高两个 decoder resolution 必须分成三条独立路径：

```text
AnatomyContextBranch
ScarBranch
EdemaBranch
```

scar 和 edema 各自 clone/继承最高两个 stock decoder stages，拥有独立参数和单行 classifier；禁止 D0 后浅层两层卷积冒充独立 decoder。建议唯一模块化真值位于 `src/care_myocardium/models/care_ase/`、`training/care_ase/` 和 canonical inference 文件。旧 import 只能是薄转发层，不能保留第二套可运行实现。

分类器初始化固定为：

- scar half/full classifier：对应尺度 stock class-5 row；
- pure-edema half/full classifier：对应尺度 stock class-4 row；
- injury classifier：shape-compatible stock class-4/class-5 row 均值；
- boundary 最终层可零初始化，但上游和 loss 路径必须可学习。

## 4. 模态角色、证据投影与梯度活性

最高两尺度的每个允许模态 adapter 固定为：

```text
Conv3d(1,16,3,padding=1)
InstanceNorm3d(16,affine=True)
SiLU
Conv3d(16,C_scale,1)
```

规则：

- adapter 非零 Kaiming/nnU-Net-compatible 初始化；
- 缺失输入与 adapter 输出按病例硬清零；
- scar：LGE mandatory primary，C0 auxiliary，T2 forbidden；
- edema：T2 mandatory primary，C0 auxiliary，LGE weak context；
- scar/edema C0 gate 初始输出 `0.2`；
- edema LGE tanh gate 初始输出 `0.05`；
- 每个 evidence source 必须有独立、具名、零初始化 `1x1` residual projection；
- 共享多源 projection、自由 router、top-k mixture、center-conditioned gate 禁止。

必须运行两阶段零信用梯度活性探针：

1. 第一次 backward：每个 required residual projection 梯度非零且有限；
2. 在临时克隆状态执行一次确定性更新后再次 backward：对应 adapter、gate、dilation/context 上游梯度非零且有限。

探针不得写入正式 checkpoint，不得产生科学指标，不得计入训练。

## 5. 解剖与软心肌壁上下文

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

要求：

- anatomy target 将 labels 4/5 remap 为 1；
- EDT 使用真实 spacing，clip 到 `[-10mm,10mm]` 后除以 10；
- `rho = d_endo / (d_endo + d_epi + 1e-6)`；
- 异常拓扑切片只 mask distance/rho regression；
- 所有 context 输入 pathology branch 前 `detach()`；
- 只可作为软通道或软 logit bias；
- hard multiply、hard crop、hard clipping、wall-space transform、geometry fail-stop 禁止；
- rotation/scale 后的物理 target 必须从变换后的 segmentation 与有效 spacing 重算，不得只插值旧距离场。

anatomy deep supervision 必须同时覆盖 full 与 half scale，总权重 `0.50`；尺度权重从 stock trainer 获取并重新归一化。

## 6. ScarBranch

ScarBranch 同时承担全图候选形成和最高两尺度直接重建：

- `ScarCoarseProposalHead` 在 1/4 与 1/2 尺度分别输出 occupancy logit 与 component-center heatmap；
- 保留所有 GT scar components，26-connectivity；
- center Gaussian：in-plane `4mm`，z 为 `1 slice`；
- proposal 只作软证据，禁止 bbox、hard ROI 和 crop；
- 最高两尺度 decoder 必须真实消费 shared feature、stock skip、LGE/C0 adapter、proposal occupancy/center 和 detached soft-wall/context；
- 直接输出 `z_scar`；
- 4 类 context classifier 为 scar、normal myocardium、blood-pool-adjacent、remote/background，其 logits 必须进入 final scar reconstruction path，不能只是旁路 auxiliary head。

Scar sampler 固定：

```text
35% GT scar component-centered
20% small scar (<1000 mm3) component-centered
20% canonical OOF scar FN / low-overlap
15% canonical OOF remote or blood-pool-adjacent FP
10% random wall/background
```

component-adaptive Tversky 权重固定为：

```text
clip(sqrt(1000 mm3 / component_volume_mm3), 1, 4)
```

OOF 必须来自该病例未训练过的 stock nnU-Net，绑定精确预处理网格、病例、预测 artifact 与实际 checkpoint SHA。空 pool 时必须改变 resolved category 并记录，禁止用普通中心冒充 requested category。

## 7. EdemaBranch

EdemaBranch 只对 T2-present 行执行，采用全体积连续区域重建：

- 禁止 proposal bbox、hard ROI、局部 crop、largest-component target 和 compactness；
- 最高两尺度独立 decoder；
- T2 evidence 为 mandatory primary；
- full path 包含真实 dilation `1/2/4` residual blocks，不能以孤立标量或旁路命名冒充；
- 输出 `z_pure_edema`、injury auxiliary、boundary；
- edema context classifier 必须进入 final reconstruction evidence。

Edema sampler 仅从 T2-present eligible pool 取样：

```text
35% pure-edema positive
20% canonical OOF low-volume/FN
20% edema boundary
15% safe FP or blood-pool-adjacent
10% random wall/background
```

complete-case 内 CenterB/CenterC 以 `1:1` 循环，不足时有放回抽样。不得从 no-T2 组抽 edema event。

boundary degenerate 语义固定：

- empty edema：`target=0, raw=0, valid=0`；
- full edema 且真实外边界不可观察：`target=0, raw=0, valid=0`；
- 只有可观察真实边界时才从有效 full-case segmentation 计算 signed distance，patch 外框不得充当病灶边界。

## 8. SliceExtentHead 与全体积语义

scar 与 edema 各自拥有独立 1/4-scale extent head：

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

统计函数固定为：

```text
0.5 * wall_weighted_mean + 0.5 * masked_max
```

presence 输入为 probability，使用 clamped probability 的 BCE。presence validity 与 area validity 分开；padding、all-invalid slice 和 partial-H/W slice 的 bias、loss 与 gradient 必须为零，禁止 fallback 读取无效像素。

target 来自 full-case profile，不得由裁剪 patch 局部重定义：

- presence：原始物理切片是否有病灶；
- area：pathology voxels / wall-union voxels。

最终软偏置系数固定：

```text
scar: 0.30 presence + 0.20 area + 0.15 wall
edema: 0.35 presence + 0.30 area + 0.10 wall
```

extent/wall bias 全局 ramp 固定为：

```text
r(s) = 0                              , s < 500
r(s) = (s - 500) / 1500               , 500 <= s < 2000
r(s) = 1                              , s >= 2000 或部署推理
```

训练与推理调用同一 `compute_slice_extent_statistics`。tile 只输出 base logits、wall 与 extent evidence；全体积聚合后只施加一次 global bias。单 tile 与多 tile 必须走同一代码路径。

## 9. 条件类别竞争与 no-T2

T2-present 行：

```text
logits = [z0,z1,z2,z3,z_edema,z_scar]
loss/decode classes = [0,1,2,3,4,5]
```

T2-absent 行：

```text
logits = [z0,z1,z2,z3,z_scar]
loss/decode classes = [0,1,2,3,5]
```

对 no-T2 行，class 5 在局部五类张量中可临时 reindex 为 4，decode 后必须映射回官方 label 5；原 class-4 target 设为 ignore。class 4 必须从 softmax、Dice 和 argmax 分母中完全移除，禁止仅将 class-4 logit置零或置负后仍参加六类计算。

mixed batch 必须按 eligible row 子集执行并安全 scatter：

- no-T2 行任一 edema-owned module call count 为 `0`；
- edema-exclusive losses 和参数梯度严格为 `0`；
- T2-present 与 T2-absent 的 final competition 分别计算；
- 每项 loss 按自身 eligible rows/voxels 归一化，禁止被全 batch 稀释；
- 无固定 scar-priority、per-case threshold 或 post-hoc overwrite。

## 10. 固定损失与数值语义

唯一允许的损失及权重：

```text
1.00 conditional final DiceCE
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

只对 eligible T2-present rows 计算。context CE reduction 固定为 `valid_voxel_mean`；所有敏感 reduction 使用 FP32。每项损失必须报告有效分母、有效病例/体素数、目标模块直接梯度和 on/off intervention。禁止 distillation、prototype、SIP、compactness、全局 HD surrogate 或其他损失。

## 11. 数据、增强与采样顺序

每个 optimizer step 恰好包含 4 个独立、有放回 microbatch。唯一正式数据路径必须完整覆盖：

```text
eligible pool
-> stage group schedule
-> pathology/focus category
-> case draw
-> coordinate draw
-> case load
-> initial patch
-> stock augmentation
-> synchronized target build
-> forward/backward
-> finite checks
-> accumulation
-> clipping
-> optimizer/scheduler
```

Stage A/B 的 20-event group cycle 固定为 10 complete、5 LGE-only、5 LGE+C0；Stage C 只使用 complete tri-modal。complete pathology cursor 固定 `[scar, edema]`；partial events 只执行 scar event，且不推进 complete pathology cursor。

空间 target 与图像必须使用 stock nnU-Net runtime transform 的同一空间变换。离散 component metadata 不得连续插值。padding value `-1` 不进入 loss 或物理 target。所有 rotation/scale 后的 signed distance、rho、context、boundary 和 scar center target 必须从最终 segmentation/effective spacing 重建。

每病例 manifest 至少绑定 case ID、image/segmentation/properties/plans path 与 SHA256、shape、spacing、cache schema 和完整 cache payload SHA256。

## 12. 优化器、日程与 step 语义

optimizer 为 AdamW，weight decay `1e-4`，physical batch 1，gradient accumulation 4，effective batch 4，gradient clip 12 且 `error_if_nonfinite=true`。optimizer 在 step0 只建立一次，stage transition 只更新 LR/`requires_grad`，不得丢失 optimizer state。

所有区间为左闭右开；`global_optimizer_step` 表示即将执行的 optimizer step：

### Stage A `[0,2000)`

- freeze stock encoder/shared decoder；
- train new branches/context/adapters/extent；
- new modules LR `5e-4`；
- cloned pathology blocks LR `1e-4`；
- cloned classifiers LR `2e-4`；
- warmup 200；
- minimum LR `5e-6`。

### Stage B `[2000,10000)`

- unfreeze complete shared decoder + upper two encoder stages；
- new modules LR `3e-4`；
- shared/anatomy/cloned pathology blocks/classifiers LR `1e-4`；
- upper two encoder LR `5e-5`；
- warmup 500；
- minimum LR `1e-6`；
- case mixture 50% complete / 25% LGE-only / 25% LGE+C0。

### Stage C `[10000,14000)`

- complete tri-modal only，CenterB/CenterC `1:1`；
- all layers trainable；
- new modules LR `1e-4`；
- shared decoder、anatomy decoder、cloned pathology blocks/classifiers、upper encoder LR `5e-5`；
- lower encoder/bottleneck LR `1e-5`；
- warmup 0；
- minimum LR `1e-6`。

每阶段使用 stage-local warmup + polynomial decay，power `0.9`。checkpoint 每 1000 completed optimizer steps；full-volume inner evaluation 每 2000 completed steps。checkpoint 保存的是 post-step 状态，`last_completed_optimizer_step` 与 next-step descriptor 必须无歧义。任何 stage 不得因早期指标差而跳过。当前任务只实现和验证该日程，不执行正式训练。

## 13. Checkpoint schema v4 与 exact resume

checkpoint 必须自包含、可部署，并绑定：

- fold、model config fold、同 fold stock checkpoint path/SHA；
- split、actual-train cases、hard-negative manifest、target manifest；
- 本冻结合同 SHA、critical source manifest SHA、environment determinism manifest SHA；
- model、optimizer、scheduler、stage、step、extent ramp；
- Python/NumPy/Torch/CUDA、augmentation、sampler、micro-patch RNG；
- 4 个 microbatch descriptor 和 next-step descriptor SHA；
- logical chunk start/end、last completed step、resume invocation start、completed steps in logical chunk、checkpoint reason；
- 所有 cursor 与 parameter-owner registry。

schema 1/2/3、cross-fold resume、placeholder、合同漂移、manifest 漂移、环境漂移必须 fail closed。reload 后下一 optimizer step 的 4 个 microbatch、loss、梯度、参数更新和 scheduler 必须与 uninterrupted 路径一致。checkpoint reload 验证不得推进训练 RNG。deployment loader 不得再打开 stock checkpoint。

所有 micro-loss、trainable gradients、更新后参数和 Adam state 必须有限；任一非有限值禁止 optimizer commit 与 checkpoint 保存。

## 14. Canonical full-volume inference 与评价接口

唯一推理入口必须：

- 单 tile 与 sliding-window 走同一路径；
- tile 内禁用 local extent/wall final bias；
- 聚合 base logits、wall 和 extent evidence 后一次性施加 global bias；
- 使用 checkpoint 保存的精确 step/ramp/schedule，禁止 early checkpoint 使用 final-step 值；
- self-contained deployment load，不依赖未跟踪 host asset；
- CARE 与 baseline 使用相同病例、TTA、decode 和 metric population。

实现必须提供 Dice、HD95、exact HD、precision、sensitivity、lesion recall、小病灶 recall、component count、remote FP count/volume、blood-pool-adjacent FP、volume ratio、casewise help/harm、CenterB/CenterC subgroup 和指定 sentinel case 接口。本任务只验证接口与语义，不产生性能或 promotion 结论。

## 15. Verifier-first 冻结门

Executor 开始前，Verifier 必须提交并由 Controller 冻结：

```text
verification_contract.json
public_test_manifest.json
protected_known_bad_manifest.json
verifier_fingerprint.json
verifier_session_receipt.json
```

Verifier 只能修改 tests、validators 和授权 receipt。每个 protected known-bad 必须真实使 validator 非零退出，至少覆盖：

1. role session/worktree/CODEX_HOME 重叠；
2. encoder-only inheritance、decoder reset、缩小 channels、永久冻结 trunk；
3. D0 shallow head 冒充最高两尺度 decoder；
4. stock class4/5 normal-forward shortcut；
5. required module 存在但不影响目标中间量或 final logits；
6. 双零初始化死梯度；
7. scar 使用 T2 或 edema 不消费真实 T2；
8. no-T2 行调用 edema graph、收到 supervision/negative/gradient，或 class4 仍参与竞争；
9. context/extent/soft-wall 只有 auxiliary loss 而无 final authority；
10. hard wall、hard ROI、bbox crop、local refiner、prototype/dictionary/query、fixed scar-priority；
11. full-case extent 被 patch-local profile替代，invalid/padding/partial-HW 产生 bias；
12. tile 内重复 extent 或单/multi tile路径分叉；
13. declared loss 未进入 total，分母为零仍称覆盖；
14. hard-negative 无真实 mask/坐标/checkpoint/grid binding；
15. requested/resolved category 不一致未记录；
16. checkpoint 状态不完整、cross-fold可恢复、reload/next-step不一致；
17. early checkpoint inference 使用 final-step ramp；
18. canned receipt 在未执行真实 forward/backward/inference 时通过；
19. patch proxy 冒充 full-volume evaluator或评价不公平；
20. under-14000、跳过Stage B/C、startup/pending/preempted job计入训练；
21. outer 用于阈值、系数、checkpoint或source选择；
22. hidden host asset/旧 wrapper绕过新实现；
23. monolith与模块化实现同时可运行形成双真值；
24. required metrics/sentinel接口缺失。

公共测试可公开接口，但 protected mutation 细节不得泄露给 Executor。Verifier 不得替 Executor修实现。

## 16. Executor、Controller 与 Planner 循环

Executor 只能在独立 session/worktree/local branch 修改实现范围，不得修改 tests、validators、蓝图、冻结合同或状态机。必须建立唯一模块化真值，完成模型、loss、sampler、augmentation、checkpoint/resume、canonical inference，并输出 architecture signature、source manifest、implementation fingerprint、parameter owners 和真实运行 receipts。只允许运行零信用实现探针。

Controller 只协调、集成、push `develop`、运行确定性门和路由返修，不得编辑实现或验证源码。顺序固定：

1. 证明三个独立持久 session；
2. 启动 Verifier 并冻结其 commit/fingerprint；
3. 启动 Executor；
4. 集成 Verifier 与 Executor commits；
5. 运行本地与 server-local protected tests；
6. push `develop` 并等待 GitHub Actions；
7. 绑定 nonce、合同 SHA、integration SHA、implementation/verifier fingerprints、CI、runtime receipt manifest 和 review round；
8. 将 CURRENT 最后更新为 `READY_FOR_PLANNER_REVIEW`；
9. Planner 返回修订时只恢复指定 exact session，`BOTH` 时先 Verifier 后 Executor；
10. 每轮重新集成并重跑全部门，最多 12 轮；同一阻断缺口连续 3 轮未关闭则停止。

Planner 每轮必须先审完整当前实现，再审旧 finding closure。只能返回 `PLANNER_REVISE_EXECUTOR`、`PLANNER_REVISE_VERIFIER`、`PLANNER_REVISE_BOTH` 或 `PLANNER_PASS`。

## 17. 终止边界

`PLANNER_PASS` 仅表示精确 `develop` 实现与本冻结合同一致，无剩余阻断性降级证据。随后必须：

```text
CURRENT -> AWAIT_HUMAN_DECISION
stop Controller/Verifier/Executor
commit/push lightweight receipts to develop
send existing notifier
```

始终禁止自动正式训练、outer、validation/challenge upload、Docker build/upload、organizer email、`develop -> main` 合并和科学优越性结论。
