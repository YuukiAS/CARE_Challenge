# CARE 架构 Wiki

architecture_version: `care-myops-batch10-deadline-rescue-ready`
latest_verified_runtime: `Batch9 repair direct and teacher complete; Wave6 control/distill stopped by user after epoch25`
latest_scientific_status: `CARE-MMRD remains below nnU-Net under current evaluator; fair inference/export and training semantics still require repair before final judgment`
latest_controller_task: `20260724_care_myops_batch10_deadline_rescue`
route_status: `MAIN_ONLY_BATCH10_READY_FOR_CONTROLLER`

本页是 GPT、Controller、Executor、Mapper 和 Planner 读取当前架构状态的根入口。当前任务不是再增加模型复杂度，而是在两到三天内确认 CARE-MMRD 是否还有真实提交价值：先修复公平推理和空间恢复，重评全部现有 checkpoint，再决定是否允许一次25 epoch定向续训以及是否形成paper或Docker候选。

## 当前判断

```text
Batch7: 操作完成，scar失败、edema小增益，BR2/SIP机制闭环不完整
Batch8: 未执行，历史诊断合同
Original Batch9: 运行完成，因实现缺陷不能作为干净科学否定
Batch9 repair: Wave0–5代码已推送，Wave6由用户在epoch25后终止
Batch10: READY_FOR_CONTROLLER
旧SRR/BR2/SIP: 不进入Batch10
nnU-Net: 只作同划分评价基线，不进入CARE-MMRD forward或fallback
```

当前任务入口：

```text
results/srr_production/code_maturity/batch10_deadline_rescue_planner_decision_20260724.md
configs/care_mm/batch10_deadline_rescue.yaml
prompts/tasks/20260724_care_myops_batch10_deadline_rescue_controller.md
prompts/tasks/20260724_care_myops_batch10_deadline_rescue_executor_plan.yaml
results/20260724_care_myops_batch10_deadline_rescue/
```

## CARE-MMRD 部署前向保持不变

```text
[LGE,T2,C0] + availability
-> 3 independent modality stems
-> hard mask immediately after each stem
-> concatenate stem features and availability channels
-> ResidualEncoderUNet M-level backbone
-> shared decoder feature
-> anatomy head + scar head + edema head
-> direct six-class logits
-> argmax
```

模型类仍为：

```text
src/care_myocardium/models/care_mm_reliable_distill.py
CAREMMReliableDistillResEnc
```

Batch10不恢复：

```text
SRRProposeRefineMyoPS
prototype / semantic memory
BR2 / SIP
proposal / refiner
source arbiter / production gate
bounded nnU-Net correction
```

## Batch 9 repair 到 epoch25 的真实含义

人工提供的 Wave6 epoch25 结果：

```text
seed20260723 control: scar 0.4743, edema 0.3188
seed20260723 distill: scar 0.4754, edema 0.3316
seed20260724 control: scar 0.4291, edema 0.3354
seed20260724 distill: scar 0.4221, edema 0.3576
```

蒸馏相对control平均约为 scar `-0.0030`、edema `+0.0175`。因此完整视图蒸馏对edema有可重复信号，但对scar不稳定；当前仍没有超过nnU-Net的证据。用户已终止原Wave6后续运行，Batch10不得自动恢复到epoch100。

## 为什么当前分数还不能作为最终结论

远端提交 `3705a37bf4519144ea52155a2a7a3d2d118e3776` 已补正式Trainer、plans、augmentation、deep supervision、loss归一化和周期性验证，但进一步审计发现：

```text
1. evaluator使用一次全体积forward，不是plans滑窗推理；
2. prediction只做shape-only nearest-neighbor zoom；
3. 没有使用nnU-Net v2正式crop/transpose/resampling逆变换；
4. checkpoint评价用默认模型构造，不从checkpoint plans重建；
5. ResEnc M plans与硬编码preprocessed目录可能不一致；
6. student空间增强未同步到natural/teacher view；
7. pathology coverage只检查任意类别confidence；
8. sampler没有落实center-first均衡；
9. clean checkout可能缺少被import的case_metadata.py；
10. Wave0–5轻量证据和CURRENT/wiki未与本地runtime闭合。
```

这些问题既可能压低checkpoint的真实分数，也可能让distillation接受错误的逐体素监督。因此Batch10先修评价和数据语义，再决定是否训练。

## Batch 10 数据流

```text
freeze Batch9 runtime and checkpoint lineage
-> clean-checkout import audit
-> plans / preprocessing fingerprint
-> checkpoint-plans model reconstruction
-> nnU-Net v2 sliding-window + Gaussian + mirror TTA
-> official inverse preprocessing and NIfTI export
-> 8 existing checkpoints + same-evaluator nnU-Net baseline
-> bounded ensemble and calibration/audit postprocessing
-> near-baseline gate
-> optional synchronized 25-epoch matched continuation
-> paper / Docker go-no-go
```

## 公平评价边界

标准nnU-Net只允许读取现有fold0 prediction NIfTI和轻量metrics，用同一评价器重算baseline、HD95、remote FP和case-wise help/harm。禁止将nnU-Net checkpoint、logits、概率或预测作为CARE-MMRD输入、ensemble source、anchor或fallback。

必须重评：

```text
2 direct selected checkpoints
2 complete-view teacher selected checkpoints
2 control epoch25 checkpoints
2 distill epoch25 checkpoints
```

完整三模态teacher必须作为独立候选，因为官方validation/test输入为完整三模态。

## 有限 ensemble 与后处理

只允许六个冻结候选：direct、teacher、control、distill各自two-seed probability mean，best-two mean，以及一个pathology-specific probability compositor。不得做无界子集搜索，不得混入nnU-Net概率。

44例按center和病种阳性状态分层，再按case hash交替分成calibration/audit。后处理只在calibration选择，audit只用于独立检验。允许的小网格仅包含anatomy support阈值、5/10 mm物理距离限制和scar/edema最小连通域阈值。

## 条件式短续训

只有最佳非nnU-Net候选在audit半集满足：scar距baseline不超过0.04、edema不超过0.03、无阳性空预测、no-T2 edema为0、HD95恶化不超过10%，才允许短续训。

短续训从repaired direct selected checkpoint重新开始，不恢复旧Wave6 optimizer。两个seed各运行matched control/distill 25 epoch、6250 steps。必须先修复：

```text
student/natural/teacher共享空间变换
独立强度增强但完整记录seed
先target、再eligible center、再case、再patch的采样
scar/edema各自teacher margin confidence mask
训练集阈值校准
无法满足coverage/precision的病种distillation权重置0
```

任一seed、任一病种distill低于matched control都必须明确失败。

## Paper 与 Docker 门

Paper候选要求audit split两病种基本不低于nnU-Net，完整44例至少一项提高0.005、另一项非负，同时通过help/harm、HD95、remote FP、空预测和no-T2安全门。

Docker候选可以略宽，但必须是非nnU-Net CARE-MMRD，完整44例两病种均不低于baseline超过0.01，至少一项不低于baseline，并通过确定性重复推理和端到端容器dry-run。Batch10只允许本地构建和submission-ready manifest；上传仍由用户决定。

若完成全部授权救援后scar仍低于baseline超过0.03或edema低超过0.02，停止本次CARE-MMRD竞赛路线，不启动Batch11。

## 时间边界

```text
paper deadline: 2026-07-27
docker deadline: 2026-08-03
7月24–25日: 正确推理、重评、ensemble、后处理
7月25日晚: go/no-go
7月25–26日: 仅在near-baseline时短续训
7月26日: 冻结paper科学内容
7月27日: 只提交paper
7月28日–8月3日: 仅对通过Docker门的候选做容器QA
```

## 当前图

![当前模型](figures/model-current.png)

![当前差距](figures/model-gap.png)

![执行流程](figures/execution-flow.png)

部署forward未改变，因此Batch10不重画模型主图。Mapper需要更新真实推理/export、训练语义、runtime和状态证据。

## 入口

- [MODEL.md](MODEL.md)
- [EXECUTION.md](EXECUTION.md)
- [COMPONENTS.csv](COMPONENTS.csv)
- [LINEAGE.md](LINEAGE.md)
- [architecture.yaml](architecture.yaml)
- [current_state.yaml](current_state.yaml)
- [history/README.md](history/README.md)
