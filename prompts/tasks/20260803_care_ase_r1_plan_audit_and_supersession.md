# CARE-ASE R1 计划审计与 R2 取代说明

## 结论

R1 的方向是正确的：它识别了上一轮 CARE-ASE 的主要实现降级，并要求在新折重训。但 R1 仍含有会再次制造“不完整实现或不完整训练”的计划漏洞，因此不得直接启动。R2 已把这些漏洞全部改成机器可检查的 Gate，并取代 R1 成为唯一活动 Goal。

## 已视觉恢复的方法目标

本次重新视觉检查了 SRR-v2、SRR-v2.5、SRR-v3、CARE-MMRD、CARE-SRR-Cascade、CARE-DG、CARE-ARC、CARE-PRISM、CARE-MyoWall-IF、MoSAIC 和 CARE-ASE。

CARE-ASE 的真实方法边界是：

```text
完整保留 stock nnU-Net 成熟 encoder-decoder 能力
-> 在最高两级分别复制 scar / edema 解码路径
-> scar 使用 LGE 驱动的候选、中心、负空间和小病灶监督
-> edema 使用 T2 驱动的 injury、boundary、extent、负空间和多尺度上下文监督
-> 解剖和心肌壁只作 detached soft context
-> no-T2 完全排除 pure-edema 监督与竞争
-> 单一端到端 checkpoint、固定 argmax、无 selector、无 threshold search
```

## R1 中发现的计划漏洞

1. **人为十二小时终止线。** R1 允许在时间不足时形成阻塞或只完成一个 fold。这与用户要求的完整忠实执行冲突，也可能再次把排队或实现修复时间压力转化为降级实现。

2. **旧 allocation 写死。** R1 仍使用 `61220581`，而用户已指定主要使用 `61794608`。继续沿用旧 job 会导致 Controller 静默使用错误资源或在找不到旧 job 后自行改路由。

3. **代码修复与并行训练的顺序不够硬。** R1 虽提到预检后提交，但没有把“所有科学代码串行完成并 push 后，才允许任何额外 sbatch”写成独立机器 Gate。

4. **两折完成不是终态硬条件。** R1 的 one-fold fallback 会降低新折复现证据，无法支持稳定超过 nnU-Net/MoSAIC 的结论。

5. **scheduler 仍有执行空白。** R1 没有冻结每个参数组的 min LR 和逐步公式，Controller 仍可实现成近似 warmup/poly，甚至在阶段切换重建 optimizer。

6. **sampler 百分比仍有执行空白。** R1 没有给出 35/20/20/15/10 的离散确定性 cycle，也没有规定某类样本为空时如何 fallback；Controller 仍可能退化成普通病例循环。

7. **正式训练缺少逐 chunk Gate。** R1 没有明确规定每个 2000-step chunk 必须先完成 checkpoint full reload、source hash、scheduler、sampler cursor 和 next-batch hash 验证，才允许下一 chunk。

8. **success 与完整评价边界不足。** R1 没有把同病例三方连接、no-T2 edema 排除、无穷 HD 计数和 prediction-level physical metric 重算写成足够严格的 Gate。

## R2 的修复

R2 新增以下不可跳过 Gate：

```text
G0  source/split/allocation/outer-zero-access freeze
G1  full static behavioral implementation gate
G2  real-GPU fidelity and exact-resume gate
G2.5 immutable training-source commit/push gate
W3  per-2000-step chunk continuity gate
G4  both-fold step14000 full-state reload gate
G4.5 pre-outer immutable snapshot gate
G5  same-case three-way metric-truth gate
G6  mapper/validator/controller/push/notify terminal gate
```

R2 还固定：

- 只有一个 Executor，科学代码串行编写；
- G2.5 前禁止正式训练和额外 sbatch；
- fold1 主要使用 interactive job `61794608`；
- G2.5 后才允许额外向 `htzhulab` 提交 fold4 chunk chain；
- fold1/fold4 都必须完成 14,000 步，无 one-fold fallback；
- 只允许 `htzhulab`，不自动转其他 partition；
- 没有人为十二小时终止线；
- 不能保证训练前的数值胜出，但保证实现不再降级、比较口径不再失真。

## 唯一活动文件

```text
prompts/blueprints/CARE_ASE_R2_full_fidelity_execution_contract_20260803.yaml
prompts/tasks/20260803_care_ase_r2_full_fidelity_controller.md
```

R1 和旧 metric-truth Goal 仅保留为 provenance，不得单独启动。
