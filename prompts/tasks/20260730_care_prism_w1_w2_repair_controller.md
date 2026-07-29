# CARE-PRISM v2 W1/W2 Repair and Auto-Continue Controller

你是 CARE Challenge 项目的 Controller / Coordinator。当前 goal 不是修复后返回人工验收，而是在同一 goal 中持续完成：

```text
W1 修复与独立复核
→ W2 从 fold0 stock nnU-Net 重新运行并独立复核
→ 全部门通过后自动 W3
→ W3 通过后自动 W4
→ W5 终态聚合、验证、Mapper、提交、推送与通知
```

仓库：

```text
/users/a/e/aereinh/CARE
remote: YuukiAS/CARE_Challenge
branch: main
```

开始或恢复前：

1. 同步 `origin/main`；
2. 读取最新 `prompts/routes/handoffs/CURRENT.md`；
3. 以更新后的 `prompts/tasks/20260729_care_prism_controller_v2.md` 为持续 Controller 总合同；
4. 继续读取 `prompts/tasks/20260730_care_prism_w1_w2_critic_repair_amendment.md`、主干修复案、PRISM hardening、blueprint、executor plan、CARE/Slurm/Mapper 协议；
5. 复用当前 Controller/Executor/runtime，禁止另开重复 goal。

用户已明确授权：修复后的 W1/W2 经 Controller 独立验收通过后自动继续 W3，不再等待 Planner 中间确认。旧 W2 step400 checkpoint 仍为 zero-credit，W3 必须从 fold0 stock nnU-Net 初始化重新开始。

## 强制修复项

必须逐项修复并由 Controller 独立检查真实代码、直接梯度、known-bad 和重算证据：

1. `edema_zone=(label==4)|(label==5)`、`scar=label==5`、`myocardium_union∈{1,4,5}`，统一 dataset/loss/decode/evaluator/export；
2. proposal/negative 未 detach 的直接 loss 进入总损失，分别对对应 head 产生非零直接梯度；
3. anatomy exchange 不得 gate/projection 双零死锁，必须可学习、单向 stop-gradient，并通过独立 on/off 与一步更新验证；
4. scar 使用真实 component/lesion-level 监督，scar/edema 使用真实双侧 surface/distance loss；
5. 四类 safe-negative 病例内平衡，分别记录有效体素、loss 与梯度；no-T2 不得产生 edema negative；
6. canonical metadata 驱动 center→burden/positive/safe-negative→case 采样；不得按 case ID 猜中心；
7. 正式 `--resume` 精确恢复 optimizer/scheduler/scaler/stage/step/sampler/augmentation/RNG/prototype/hard-negative，并对照 uninterrupted run；
8. A/B/C/D 状态机真实改变 active loss、冻结范围和 LR；
9. actual-train/inner-select/outer 三分、all-checkpoint inner evaluator、freeze receipt、one-time outer lock；
10. evaluator 实现 Dice、HD95、exact HD、lesion recall、remote FP、component count、volume ratio、empty/infinite HD、help/harm 与同划分 nnU-Net 比较；
11. W2 summary 不得无条件 PASS；必须验证 400 步真实病例、两病理 active loss 前后窗口下降 `>=30%`、finite/nonnegative、真实病例机制梯度、采样平衡、exact resume、checkpoint reload；
12. known-bad 至少拒绝 wrong edema/myocardium union、detached direct loss、dead exchange、fake W2 PASS、unsafe no-T2 negative、错误中心/负荷采样、missing inner split/outer lock、unbound evaluator checkpoint。

必须生成并严格校验：

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

## 持续修复责任

Controller 不得把 Executor 的 `PASS`、字段存在或同一实现自产 validator 当作通过。每个 gate 必须同时有：

```text
代码语义审计 + executable known-bad + 独立重载/重算
```

任何同范围实现、数据、OOM、cache、sampler、augmentation、loss、resume、evaluation、validator 或 notifier 问题，都必须退回同一 Executor 修复并重跑受影响证据。标签、loss、sampler、architecture 或 stage 语义发生改变时，受污染训练必须从同折 nnU-Net 初始化重跑；只有纯启动/环境故障允许 exact resume。

W1/W2 全部独立通过后，直接采用 `20260729_care_prism_controller_v2.md` 中的 W3/W4/W5 规则继续，不写“中间包待用户验收”，不暂停 Controller。

## 资源与终态

复用既有 allocation `61220581`；若仍运行，GPU 命令只能串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

禁止 `sbatch`、`salloc`、新 Slurm job、并行 GPU、写 `/overflow/htzhu/CARE`、validation/Docker upload。Runtime 期间禁止 push。

目标完整达到时，在所有进程终态、aggregation、strict validator、Mapper、CURRENT/wiki、轻量 commit 均确认后，将轻量代码和结果推送到 `origin/main`，核对远端 SHA，再发送一次中文完成邮件。不得推送 checkpoint、NIfTI、raw data、大日志或上传包。

只有真实资源/权限阻塞、必须改变冻结科学设计，或忠实充分训练后的机制失败，才允许结束为 block；写好稳定阻塞 packet 后发送一次中文阻塞邮件。普通修复中间态不得通知。

最终报告字段：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
w1_repair_status:
w2_rerun_status:
w3_status:
w4_status:
contract_compliance_status:
all_jobs_terminal:
aggregation_complete:
strict_validators_passed:
mapper_final_status:
git_commit_decision:
git_push_decision: PUSHED_VERIFIED_COMPLETE | NOT_PUSHED
remote_head_sha:
email_notification_status:
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```
