# CARE-PRISM v2 W1/W2 修复 Controller Prompt

你是 CARE Challenge 项目的 Controller / Coordinator。当前任务不是继续 W3，而是修复并重新验收 CARE-PRISM v2 的 W1/W2。

仓库：

```text
/users/a/e/aereinh/CARE
remote: YuukiAS/CARE_Challenge
branch: main
```

开始前同步 `origin/main`，确认包含：

```text
a76f3fd639ce09b900ce232bf65550fa4be37120
71717f0d7c6232cb8b68dd4d6442f8a5223ce297
```

按优先级读取：

```text
prompts/tasks/20260730_care_prism_w1_w2_critic_repair_amendment.md
prompts/tasks/20260729_care_prism_v2_backbone_and_w1_repair_amendment.md
prompts/tasks/20260729_care_prism_v2_backbone_repair_executor_plan.yaml
prompts/tasks/20260729_care_prism_v2_backbone_repair_controller.md
prompts/tasks/20260729_care_prism_execution_hardening_amendment_v2.md
prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md
prompts/routes/handoffs/CURRENT.md
wiki/README.md
以及全部 CARE、Slurm、Mapper 协议。
```

验收结论已冻结为 `NEEDS_REPAIR_BEFORE_W3`。禁止使用当前 step400 checkpoint继续 W3；禁止访问 fold0 outer、fold1 outer。

Controller必须把以下问题退回同一Executor修复，并亲自检查真实diff与可执行证据：

1. 标签语义：`edema_zone=(label==4)|(label==5)`，`scar=label==5`，`myocardium_union in {1,4,5}`；统一 dataset/loss/decode/evaluator/export，并添加错误语义 known-bad。
2. Proposal/negative loss不得detach后再进入总loss；分别证明直接目标梯度到 proposal_head 与 negative_head。
3. 修复双零初始化的 anatomy exchange 死分支；单独证明 exchange on/off、gate/projection梯度和一次step后的final-logit变化，同时阻断 pathology→anatomy梯度。
4. 实现真正的 component/lesion-level scar监督和双侧距离/表面loss；当前全病例max BCE与近似单侧距离不合格。
5. 对四类negative做病例内类别平衡或采样，分别报告有效体素、loss、梯度；no-T2不得产生edema negative。
6. 从canonical metadata读取真实center，实现center→burden/positive/safe-negative→case采样；当前round-robin和未使用safe_negative bucket不合格。
7. 实现正式`--resume`，恢复optimizer/scheduler/scaler/stage/step/sampler/augmentation/RNG/prototype/hard-negative；证明next case、增强、LR、loss和更新精确一致。
8. 实现A/B/C/D阶段状态机、阶段LR与active losses；当前一次性W3 optimizer不能满足合同。
9. 实现actual-train/inner-select/outer三分、all-checkpoint inner评价、freeze receipt和one-time outer lock。
10. 扩展 evaluator：scar/edema-zone Dice、HD95、exact HD、lesion recall、remote FP、component count、volume ratio、empty/infinite HD、help/harm、同划分nnU-Net比较。单个no-T2 empty case不算验收。
11. 扩展 W2 validator：summary不得无条件PASS；必须验证400步真实病例、两病理active loss前后窗口下降>=30%、finite/nonnegative、真实病例机制梯度、采样平衡、exact resume和checkpoint reload。
12. known-bad至少覆盖：wrong edema union、wrong myocardium union、detached direct loss、dead exchange、fake W2 PASS、missing inner split/outer lock、unsafe no-T2 negative、missing center/burden sampling、random/unbound evaluator checkpoint。

修复后，从 fold0 stock nnU-Net checkpoint重新运行 W1，再重新运行 W2 400-step zero-credit；旧 W2只保留诊断。生成并校验：

```text
critic_repair_receipt.json
label_semantics_report.json
direct_loss_gradient_report.json
anatomy_exchange_report.json
sampler_balance_report.json
exact_resume_report.json
w2_adequacy_report.json
w1_w2_strict_validator_report.json
```

只有这些文件内容全部通过、validator非零失败语义正确、CURRENT/wiki同步后，才写中间修复提交。当前 goal 不自动启动 W3；修复完成后返回用户验收。

继续复用既有 allocation `61220581`；若仍运行，GPU命令只能串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

禁止 `sbatch`、`salloc`、新Slurm job、并行GPU、写 `/overflow/htzhu/CARE`、runtime push、validation/Docker upload。普通代码、数据、OOM、cache、sampler、loss、resume、evaluation或validator问题必须在同一goal内持续修复，不得再次包装成科学失败或资产阻塞。

最终报告必须先用中文说明修复是否真实闭环，再给出：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
w1_repair_status:
w2_rerun_status:
label_semantics_status:
direct_loss_gradient_status:
anatomy_exchange_status:
sampler_balance_status:
exact_resume_status:
inner_outer_lock_status:
evaluator_status:
validator_status:
w3_authorized: NO
next_required_action: RETURN_TO_PLANNER
```