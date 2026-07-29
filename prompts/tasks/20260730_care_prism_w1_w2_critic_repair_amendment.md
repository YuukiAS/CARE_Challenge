# CARE-PRISM v2 W1/W2 验收修复案

**日期：** 2026-07-30  
**状态：** ACTIVE_HIGHEST_AUTHORITY  
**适用任务：** `20260729_care_prism_v2_backbone_repair_and_resume`  
**验收结论：** `NEEDS_REPAIR_BEFORE_W3`  
**优先级：** 本修复案 > `20260729_care_prism_v2_backbone_and_w1_repair_amendment.md` > PRISM v2 hardening/base blueprint > 当前中间 packet

## 1. 结论

当前 W1/W2 中间包已正确解决同折 stock nnU-Net 主干定位和移植问题，但不能授权 W3。问题不是指标失败，而是标签语义、损失梯度、解剖交换、采样、恢复、评价和 validator 仍存在会让 6500-step 训练失真的实现缺口。现有 W2 `PASS` 只证明 400 步循环跑完，不证明预训练充分或机制正确。

W3、fold0 outer、W4 均保持禁止，直到本修复案全部通过。已有 400-step W2 作为 zero-credit 诊断保留；修复后必须从同折 nnU-Net 初始化重新运行 W1 和 W2，旧 step400 checkpoint 不得续接正式 W3。

## 2. 已通过且必须保留

- fold0/fold1 checkpoint 当前文件和 SHA256 已核验；
- stock `PlainConvUNet` 按 plans 恢复；
- encoder 参数字节覆盖率 1.0，FP32 各尺度误差 0；
- shared encoder 输入为 `[LGE,T2,C0]`，availability 不追加输入；
- prototype 默认关闭，slice correspondence 冻结 identity；
- no-T2 输出概率和 mask 为零的前向语义已建立；
- pathology top-down decoder 的 level1–3 干预可改变最终 logit。

## 3. 必须修复的阻断问题

### 3.1 Edema-zone 与 myocardium-union 标签语义错误

Dataset501 紧凑标签中 `4` 是 pure edema，`5` 是 scar。PRISM 的直接 edema-zone 目标必须是：

```python
edema_zone = (seg == 4) | (seg == 5)
scar = seg == 5
pure_edema = edema_zone & ~scar
myocardium_union = (seg == 1) | (seg == 4) | (seg == 5)
```

当前 `edema_zone_target = (seg == 4)`，同时 anatomy union 使用 `seg > 0`，把 LV/RV blood pool 也并入 myocardium band。这会使 scar–edema soft relation 与像素监督直接冲突，并放宽病理到血池。必须统一 dataset、loss、decode、evaluation、known-bad 和 export 语义。

### 3.2 Proposal/negative 直接监督被 detach

当前 `pathology_refiner_loss` 把 proposal/negative loss 放入 detached parts，外层再把 detached tensor 加入总损失。因此这些数值会出现在日志里，但不会把目标梯度传给 proposal/negative head。必须：

- 保留未 detach 的 `proposal_loss`、`negative_loss` 参与总损失；
- 只在 logging payload 中 detach；
- 用 `torch.autograd.grad(L_proposal, proposal_head)` 与 `torch.autograd.grad(L_negative, negative_head)` 证明直接监督梯度非零；
- known-bad 必须能拒绝“日志有 loss 但参数无直接梯度”。

### 3.3 Anatomy exchange 是双零初始化死分支

当前 exchange 同时把 scalar gate 和 projection 权重置零，导致两者梯度都为零，模块永远无法启动。现有 intervention 关闭的是完整 anatomy guidance，不是 exchange 本身。必须改为以下二者之一并冻结选择：

```text
A. gate=0，projection 使用非零稳定初始化；或
B. projection=0，gate 固定/初始化为1。
```

必须单独报告 exchange on/off、gate/projection 梯度和一次 optimizer step 后的 final-logit delta；pathology gradient 仍不得进入 anatomy decoder。

### 3.4 Loss 仍未达到合同语义

当前所谓 lesion MIL 只是全病例最大概率 BCE，不是 lesion/component-level supervision；所谓 generalized surface loss 也不是正确的双侧边界/距离监督。必须实现：

- scar：component-adaptive Tversky 或逐 GT component lesion-MIL；
- scar/edema：基于真实 signed/bidirectional distance map 的 surface loss；
- Stage C 启用前 fail closed；
- 单独 small-lesion、empty-GT、single-component 和远端 false-positive known-bad。

### 3.5 Negative-space 未做类别平衡

四类 mask 已生成，但当前 full-volume BCE 会被 `outside_union` 的巨大体素数支配。必须按病例内类别做采样或归一化加权，分别记录正常心肌、血池、远端背景和 artifact 的有效体素数、loss 与梯度。Edema negative 仍只允许 T2-present；no-T2 myocardium 不能进入任何 edema negative。

### 3.6 正式采样器没有执行 center × burden × safe-negative 合同

当前 training loop 只是按 index 循环 scar/edema eligible cases；`safe_negative` bucket 统计后未被使用，center 和 burden 也没有参与选择。必须从 canonical case metadata 读取真实中心，不得用 case ID 首位数字伪造中心。每 step 保持 scar-focused 与 T2-present edema-focused 两个串行 micro-batch，但每个 focus 内必须：

```text
先等概率选择 eligible center
→ 再选择 positive burden tertile 或 safe-negative stratum
→ 再选择病例
```

W2 receipt 必须报告各中心、各 burden、positive/safe-negative 实际抽样次数和最大偏差。

### 3.7 Checkpoint/resume 只有 key-presence，没有真实恢复

当前 runner 没有正式 `--resume`，loader 只恢复 model，W1 receipt 只检查 checkpoint keys 存在。必须恢复 optimizer、scheduler、scaler、stage、step、sampler、augmenter、Python/NumPy/Torch/CUDA RNG、prototype 与 hard-negative state；证明中断前后 next case、增强参数、loss、LR 和模型更新一致。W3 不能依赖当前 resume 证据。

### 3.8 W3 stage schedule 尚未真实实现

当前 optimizer 在启动时只按字符串 `W3` 建一次，A/B/C/D 不改变学习率、冻结范围或 active loss；Stage D 低学习率没有生效。必须实现可恢复的阶段状态机：

```text
A 1–1000: transplant preservation + anatomy/evidence
B 1001–2500: proposal + balanced safe-negative
C 2501–5000: refinement；第3001步后启用 component/surface
D 5001–6500: encoder/new heads 低学习率 joint calibration
```

阶段切换必须调整 optimizer param-group LR 与 active losses，并写入 training log/checkpoint。

### 3.9 Inner selection、outer lock 与正式评价尚不存在

当前 dataset 只有 `train/val`，evaluator 只支持少量病例 Dice；没有 train-side inner split、checkpoint selection、freeze receipt、one-time outer lock，也没有 nnU-Net 同划分比较。W3 前必须补齐：

- deterministic actual-train / inner-select / outer 三分；
- 每500步在 inner 上重载 checkpoint 评价；
- scar 与 edema-zone 分别报告 Dice、HD95、exact HD、lesion recall、remote FP、component count、volume ratio、empty/infinite HD、case-wise help/harm；
- same-split nnU-Net comparator；
- checkpoint/decode/threshold freeze receipt；
- freeze 后 outer 只允许一次。

当前 `eval_probe` 的单个 no-T2 empty case 不具备任何性能验收价值。

### 3.10 W2 PASS 与 validator 是假充分

当前 training summary 无条件写 `status: PASS`，没有验证 finite loss、两病理 loss 下降、机制梯度或 resume；strict validator 只支持 W1，known-bad 仅两项。必须扩展 W2 validator并至少检查：

- 400 optimizer steps、2 micro-batches/step、真实病例；
- scar 与 active T2-present edema 的前/后窗口 loss 各下降至少30%，或明确失败；
- 全程 finite/nonnegative，无 silent NaN；
- router/anatomy/exchange/proposal/negative/burden 的真实病例梯度与 on/off；
- no-T2 exact zero；
- exact resume；
- label semantics；
- sampler balance；
- checkpoint SHA 与 reload；
- fake PASS summary、detached loss、dead exchange、wrong edema union、missing inner split 等 known-bad 必须被拒绝。

## 4. 修复后的执行顺序

```text
R3 semantic/data/loss/exchange/sampler/resume/evaluator repair
→ rerun W1 on real + synthetic known-bad
→ rerun W2 from fold0 stock checkpoint for 400 zero-credit steps
→ Planner-facing repair packet and strict W1/W2 validator
→ only after explicit PASS: continue W3 6500 steps
```

不得在修复期间访问 fold0 outer 或 fold1 outer。不得以现有 W2 step400 checkpoint 直接进入 W3。

## 5. 必须新增/更新的证据

```text
results/20260729_care_prism_v2_backbone_repair_and_resume/critic_repair_receipt.json
results/20260729_care_prism_v2_backbone_repair_and_resume/label_semantics_report.json
results/20260729_care_prism_v2_backbone_repair_and_resume/direct_loss_gradient_report.json
results/20260729_care_prism_v2_backbone_repair_and_resume/anatomy_exchange_report.json
results/20260729_care_prism_v2_backbone_repair_and_resume/sampler_balance_report.json
results/20260729_care_prism_v2_backbone_repair_and_resume/exact_resume_report.json
results/20260729_care_prism_v2_backbone_repair_and_resume/w2_adequacy_report.json
results/20260729_care_prism_v2_backbone_repair_and_resume/w1_w2_strict_validator_report.json
```

Controller完成修复后只提交新的中间验收包，不得自行启动 W3，除非用户在同一 goal 中明确要求“修复通过后自动继续 W3”。