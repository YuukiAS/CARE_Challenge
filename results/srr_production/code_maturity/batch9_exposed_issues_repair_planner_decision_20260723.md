# Batch 9 暴露问题修复：Planner 决定

## 结论

本轮不接回 nnU-Net 作为模型主体，不加载其 logits、checkpoint 或预测，也不允许 baseline fallback。继续保留 `CAREMMReliableDistillResEnc` / CARE-MMRD 的三模态独立 stem、availability hard mask、anatomy/scar/edema 分头和可靠标签逻辑。当前唯一授权工作是修复 Batch 9 已暴露的训练、采样、解码、蒸馏和验收缺陷，再按同一模型公平重跑；这不是 Batch 10，也不是恢复旧 SRR 长链。

原 Batch 9 不能作为干净科学负结果，因为实际实现不仅有 loss 归一化、学习率、采样、no-T2 解码和 validator 问题，还缺少合同要求的正式 CARE-MMRD Trainer、plans 绑定、成熟数据增强、深监督、独立 overfit、全过程 matched receipt、蒸馏有效覆盖率和 loss 冲突审计。

## 必须修复的完整问题

1. `masked_mean` 只除以病例数，没有按有效体素数归一化。
2. direct 与 warm-start continuation 使用恒定高学习率，后者容易把已有能力训崩。
3. patch sampler 固定按 `edema -> scar -> anatomy` 取第一个前景点，没有平衡 scar、可靠 edema、anatomy 和 background。
4. no-T2 只把 edema logit 设为 `-20`，不能保证 argmax 不输出 edema。
5. 正式训练没有每 25 epoch 的固定 44 例验证、候选 checkpoint 保存和 reload 选择。
6. known-bad 只是自报 `injected/rejected=true`，finalizer 还能用跨 seed 平均掩盖单 seed 塌缩。
7. terminal PASS 字段未完全由真实 Slurm accounting、aggregation 和 validator 派生。
8. 合同要求的 `src/care_myocardium/training/nnUNetTrainerCAREMMReliableDistill.py` 未实现；正式优化循环实际仍在自写脚本中。
9. 正式训练没有使用 nnU-Net v2 的成熟空间/强度增强与深监督；小病灶训练语义不完整。
10. fixed-case overfit 的三种模态模式共用同一模型顺序训练，且优化器与正式训练不同，不能证明各模式独立可学。
11. control/distill manifest 只抽样保存部分步骤，不能证明全部 25000 步的病例、patch、增强、mask、学习率和 teacher 输入完全匹配。
12. ResEnc M 结构和 patch 使用硬编码近似，没有由 `PlansManager` / `ConfigurationManager` 从正式 plans 解析；`20x128x128` 不能继续冒充正式 plans patch。
13. 蒸馏只证明 teacher forward 被调用，没有证明置信阈值后实际有多少病理体素和 batch 获得非零蒸馏信号。
14. anatomy Dice 把 background 一起平均，且 anatomy、scar、edema、final-six losses 是否梯度冲突或某项支配训练没有审计。

## 唯一修复范围

保持部署时的 CARE-MMRD 输入、三 stem、availability hard mask、三类输出头和最终六类输出定义不变，只允许完成以下修复：

- 实现 `nnUNetTrainerCAREMMReliableDistill`，正式优化循环必须由该 Trainer 持有；旧 runner 只可调度和做诊断。
- 使用官方 nnU-Net v2 plans 管理器解析 ResEnc M 的 patch、kernel、stride、stage channels 和 deep-supervision scales；解析失败必须停止，禁止硬编码 fallback。
- 使用 nnU-Net v2 的空间与强度增强，并冻结 transform 配置和随机种子；matched control/distill 必须复用同一增强参数。
- 启用训练期深监督，在各尺度应用下采样后的可靠标签 mask；推理仍只使用最高分辨率最终输出。
- 所有 masked loss 按真实有效体素归一化；anatomy Dice 排除 background。
- 在 32 个真实 batch 上记录各 loss 的加权梯度范数和两两 cosine；若 `loss_final_six_class_reliable` 与 scar/edema loss 的 cosine 小于 `-0.25` 的 batch 比例超过 `0.25`，其权重固定置零；否则保留。其他冲突或任一 weighted gradient norm 超过其他项 10 倍且无法由该规则消除时，preflight 失败。
- 实现 scar 0.35、可靠 edema 0.35、anatomy 0.20、background 0.10 的显式采样。
- 在 inference/evaluation argmax 前 hard mask no-T2 的 class 4。
- 每 25 epoch 固定评价 44 例并保存 checkpoint，按两病种最低 Dice、平均 Dice、正例 HD95 的词典序选择和 reload。
- fixed overfit 对 full、LGE+C0、LGE-only 分别创建全新 model/optimizer/scheduler，使用与 formal direct 相同的 loss、优化器和学习率日程，禁止状态继承。
- control/distill 每一步都写 runtime manifest；tracked evidence 保存覆盖全 25000 步的 streaming hash，字段至少包括 step、case、patch bounds、augmentation seed/parameters、student mask、learning rate、teacher checkpoint/hash。每 seed mismatch 必须为 0。
- teacher 训练后先做蒸馏覆盖 gate：feature distillation 非零 batch 比例至少 0.95；logit 和 anatomy distillation 各至少 0.50；scar 与 edema GT-positive 体素进入 teacher confidence mask 的比例各至少 0.05。未通过不得启动 control/distill。
- known-bad 必须真实篡改 packet 或 runtime receipt，并证明 validator 非零退出；finalizer 只能从真实 accounting、aggregation 和 validator 结果生成终态。

这里允许复用 nnU-Net v2 的 Trainer、plans、augmentation 和 deep-supervision 基础设施，但它们只是 CARE-MMRD 的训练引擎。禁止加载标准 nnU-Net 模型权重、预测、logits，禁止 anchor correction 或 baseline fallback。

## 执行顺序

先完成 Trainer、plans、augmentation、deep supervision、loss、sampler、decode 和 validator 修复。随后完成三种模态模式彼此独立的 fixed overfit。只有全部 preflight 通过，才重跑两个 repaired direct seed，各 500 epoch / 125000 optimizer steps。

只有两个 direct seed 均无 GT-positive 空预测、no-T2 edema 精确为零、selected checkpoint 已 reload，且 scar 与 edema 都相对原 Batch 9 同 seed 改善，才允许训练 teacher。Teacher 的蒸馏覆盖 gate 通过后，才允许继续 matched moddrop/control 和 distill。任一 seed、任一病种失败不得被跨 seed 平均掩盖。

## 状态边界

```text
task_key: 20260723_care_myops_batch9_exposed_issues_repair
status: READY_FOR_CONTROLLER
inference_architecture_change: false
training_system_repair: required
nnunet_model_or_anchor: forbidden
baseline_fallback: forbidden
batch10_authorized: false
```
