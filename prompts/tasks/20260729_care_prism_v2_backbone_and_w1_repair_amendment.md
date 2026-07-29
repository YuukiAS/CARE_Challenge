# CARE-PRISM v2 主干资产与 W1 实现修复案

**日期：** 2026-07-29  
**状态：** ACTIVE_HIGHEST_AUTHORITY  
**适用任务：** `20260729_care_prism_v2_backbone_repair_and_resume`  
**优先级：** 本修复案 > PRISM v2 hardening amendment > PRISM base blueprint > 旧 executor/controller > ARC 与历史路线

## 1. Planner 判断

当前阻塞不是本地没有可用同折强模型，而是旧合同把“强同折 nnU-Net 初始化”错误收窄成“必须存在 ResidualEncoderUNet checkpoint”。仓库历史资产清单已经证明 Dataset501 的标准 `nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres` 在 fold0–4 均存在 `checkpoint_best.pth` 与 `checkpoint_final.pth`，并记录了路径、大小和 SHA256。该标准模型正是本地公平 baseline 的来源，因此使用它作为 PRISM 共享主干初始化比随机 ResEnc 更可信，也保持同划分公平性。

正式修改为：**共享主干不再限定 ResidualEncoderUNet；必须从实际存在、同折、已绑定 hash 的标准 nnU-Net checkpoint 和对应 `nnUNetPlans.json` 动态恢复其真实 network class，并把该网络的 encoder 作为 PRISM 唯一共享主干。** 这只是更换初始化/主干实现，不改变 PRISM 的病种检索、解剖交换、proposal、negative-space 或 refiner 科学假设。

## 2. 冻结主干资产

主结果根：

```text
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres
```

W3 fold0 固定：

```text
checkpoint: fold_0/checkpoint_final.pth
sha256: 8bceb20cae8920e87d43b14665a0db9dfd4f1204533d25a3cd6e40ad9de74111
size_bytes: 357381749
plans: data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json
```

W4 fold1 固定：

```text
checkpoint: fold_1/checkpoint_final.pth
sha256: 5310569ff62f2f9a6ff2bc7dd3754404140071427a2025caf5e25d2916cfe400
size_bytes: 357381813
plans: data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json
```

来源证据：

```text
results/20260727_care_dg_dual_pathology_validation/nnunet_oof_anchor_manifest.json
results/20260722_care_myops_batch9_reliable_label_distillation/standard_nnunet_baseline_contract.json
```

Controller 必须对真实本地文件重新执行 `stat` 与 SHA256；历史 manifest 只作为定位和预期 hash，不能替代当前文件存在。若 repo 相对路径未解析，依次检查 repo 内路径、`NNUNET_RESULTS`/`nnUNet_results` 环境变量和 repo-local symlink 目标；不得只按目录名包含 `resenc` 搜索。

禁止使用 Batch9/MMRD 自定义 checkpoint 冒充标准 nnU-Net 主干，因为它们包含不同模型头与训练语义。也禁止下载外部 checkpoint 或从零训练一个新的 ResEnc 来绕过当前任务。

## 3. 动态主干恢复与奇偶校验

删除 `CAREPRISMConfig.from_resenc_plans`、`ResidualEncoderUNet` 硬编码和 `find_same_fold_resenc_checkpoints` 作为正式入口。实现计划驱动恢复：

1. 读取 checkpoint payload 中的 trainer/configuration/plans 信息，并与冻结 `nnUNetPlans.json` 核对；
2. 使用 nnU-Net v2 官方 network construction path 或 plans 中 `network_class_name + arch_kwargs` 构造源网络；
3. 加载 `network_weights`；
4. 直接复制或加载源网络的 `encoder` 到 PRISM `shared_encoder`；
5. 按参数字节覆盖率要求 `>=0.99`，不是旧的 `>=0.90`；
6. CARE modules 关闭、同一 FP32 实例、eval mode 时，源 encoder 与 PRISM shared encoder 每尺度最大绝对误差 `<=1e-6`；
7. 记录每个未匹配 key、shape、bytes；不得用 `strict=False` 后只看没有抛异常。

输入仍固定 `[LGE,T2,C0]` 三通道，availability 不进入 shared encoder。

## 4. W1 必须继续修复的实现漏洞

发现合法 checkpoint 后仍不得直接进入 W2。当前部分代码存在以下未闭环问题，Controller 必须退回同一 Executor 修复并以可执行 known-bad 验收：

### 4.1 多尺度主干被实际绕过

当前 `CAREPRISM.forward` 虽计算四层 routed/anatomy features，但 scar/edema refiner 只消费 level0；深层 encoder、router 和 anatomy exchange 对最终 mask 没有贡献。必须实现真实 top-down pathology decoders，消费冻结的全部正式尺度；逐尺度 on/off 干预要改变最终 logits。不得用“计算后放进输出字典”冒充多尺度使用。

### 4.2 anatomy decoder 不是 decoder

当前实现只是逐尺度 1×1 projection，并只从 level0 产生 anatomy logits。必须改为与共享主干尺度对应的 top-down anatomy decoder，融合深层上下文；病理只接收 `stopgrad` anatomy features/probabilities，病理梯度不得进入 anatomy decoder。

### 4.3 slice correspondence 是 no-op

当前 flag 被读取后丢弃。正式默认冻结 `identity`，W1/W2 不要求实现 correspondence 才能继续；但 API、receipt 与报告必须诚实写 `identity_disabled`。只有以后真实实现、干预和独立门通过后才能启用，禁止 no-op 写 enabled。

### 4.4 数据入口仍是 synthetic-only

`care_prism_dataset.py` 当前只有 synthetic W1 fixture。必须接入 Dataset501 真实预处理病例、fold/inner/actual-train 排除、完整 z、center×burden×positive/safe-negative 采样、共享空间增强和模态独立强度增强。Synthetic 只保留为 known-bad/单元测试，不得用于 W2 400-step credit。

### 4.5 正式脚本缺失

必须实现并验证：

```text
scripts/training/run_care_prism.py
scripts/evaluation/evaluate_care_prism.py
scripts/evaluation/validate_care_prism_packet.py
```

不得由临时 Python 片段代替正式训练、checkpoint selection、outer lock、聚合或 validator。

### 4.6 loss 仍是 placeholder

当前 `generalized_surface_placeholder` 与 `lesion_mil_placeholder` 不是合同要求的真实损失。必须实现真实 Generalized Surface Loss 与 lesion/component-aware 项，或在 Stage C 启用前 fail closed；不得用 L1 概率误差冒充 surface loss。

### 4.7 negative-space 监督错误

当前四通道 negative logits 的 target 全为零，未使用正常心肌、血池、union 外背景和伪影类别。必须由 batch 提供四类互斥/可重叠安全负空间 masks，并按病种监督；edema negative 只来自 T2-present。Matched `disable_negative` 必须减少远端 FP 且不显著损失病灶召回，才能证明该机制有效。

### 4.8 burden 仍是 auxiliary-only

当前 burden heads 不调制 proposal 或 refiner。必须通过零初始化 FiLM/conditional affine 同时进入 proposal 与 final refiner；on/off 必须改变 final logits。若不实现，就从方法和损失中删除，不能保留装饰性 head。

### 4.9 prototype 状态尚不完整

Prototype 保持默认关闭。若以后启用，必须实现 read-before-update、当前病例排除、source case hashes、正负安全语义和完整 resume；当前 W1/W2 不得因为 prototype 未完成而阻塞核心模型。

## 5. 新的 W1/W2 授权门

W1 只有在以下全部通过后才能进入 W2：

```text
stock same-fold checkpoint actual file + exact SHA PASS
plan-driven source network construction PASS
encoder parameter-byte coverage >=0.99
FP32 per-scale parity <=1e-6
real multi-scale pathology decoders consume all declared scales
real top-down anatomy decoder and one-way stop-gradient exchange
proposal and four-category negative-space change final logits
real Dataset501 patient sampler and augmentations
formal train/eval/validator scripts exist and run
formal losses finite, nonnegative, non-placeholder
burden either causally connected or removed
no-T2 edema probability/mask/loss/gradient exact zero
checkpoint/resume restores next case, augmentation, LR and all states
known-bad and strict validator PASS
```

W2 仍为 400-step zero-credit real-case preflight。W3/W4 预算、inner selection、one-time outer lock和性能门保持 PRISM v2 原合同不变。

## 6. Controller 修复责任

该问题已由 Planner 明确授权为同一科学主线内的合同修复。Controller 不得再次以“没有 ResEnc checkpoint”结束；应使用冻结 stock nnU-Net 资产继续 W1。若真实文件与冻结 hash 不匹配，先调查 symlink/mount/环境与历史 manifest，只有所有合法定位均失败才返回 `OPERATIONALLY_BLOCKED_ASSET_MISSING`。

所有普通代码、数据、OOM、cache、sampler、loss、resume、evaluation和validator错误继续属于同范围修复。禁止启动新 Slurm job、runtime push、validation/Docker upload或 fold1 outer 访问。