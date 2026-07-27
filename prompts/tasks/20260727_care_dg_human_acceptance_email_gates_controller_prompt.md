# CARE-DG Controller Prompt — 人工验收邮件门

本文件是正在执行的 `20260727_care_dg_dual_pathology_validation` 任务的最高优先级运行补充。它不改变 CARE-DG 的网络、数据划分、训练预算、指标和修复合同，只增加四个明确的人工验收节点，避免在实现语义仍有问题时继续进行高成本训练。

继续遵守：

1. `prompts/tasks/20260727_care_dg_w2_fold0_critic_repair_amendment.md`
2. `prompts/blueprints/CARE_DG_dual_pathology_blueprint_20260727.md`
3. `prompts/tasks/20260727_care_dg_dual_pathology_validation_controller.md`
4. `prompts/tasks/20260727_care_dg_dual_pathology_validation_executor_plan.yaml`

所有 GPU 工作仍只允许使用 interactive allocation `60657290`。禁止 `sbatch`、`salloc`、新 Slurm job、validation/Docker 自动上传和 runtime push。

## 总原则

Controller 到达下面四个节点时，必须先完成该节点的全部证据、validator 和 GPU terminal accounting，再使用仓库已有的 `controller_notifications/notify_goal_watcher.py` / `care_watchboard:Notify` notifier 向 `1155246312@link.cuhk.edu.hk` 发送一封中文短邮件。

不得新建 SMTP 脚本或新的 notifier。每个节点只能发送一次；在

```text
results/20260727_care_dg_dual_pathology_validation/checkpoint_notifications/
```

保存节点 JSON、发送 receipt、发送时间和去重状态。邮件发送失败是同范围 operational repair，不得跳过，也不得重复轰炸。

邮件发出后，Controller 必须进入相应的 `AWAITING_HUMAN_ACCEPTANCE_*` 状态，暂停下一高成本阶段。此状态是用户明确要求的人工验收门，不是 `OPERATIONALLY_BLOCKED`，也不是任务完成。Controller 应保留当前代码、日志、checkpoint 和 allocation，不得删除或重置；允许做只读核查和整理证据，但不得开始下一训练阶段。只有用户在同一 Controller 会话中明确回复 `APPROVE_<GATE>`，才继续。

不得因为平均分暂时不高而自行终止；人工门主要审查语义、实现、训练健康、泄漏和安全性。用户可在验收后决定继续、修复或终止。

## Gate A — 修复实现可进入正式 Fold0

触发条件：critic amendment 中所有确定性语义修复完成，并重新通过 unit tests、known-bad tests、真实病例 forward/backward、no-T2 梯度/推理恒等、checkpoint/resume、augmentation alignment 和 300-step anti-identity overfit。

在开始 repaired fold0 的 5000+3000 steps 之前发送邮件：

```text
Subject: [CARE-DG][A/4] 修复实现完成，等待正式 Fold0 验收
State: AWAITING_HUMAN_ACCEPTANCE_GATE_A
Approval token: APPROVE_GATE_A
```

邮件必须包含：

- 修复 commit/diff 摘要和源码 hash；
- edema-zone 标签与 pure-edema composition 的实现证据；
- FN 与 FP margin 方向测试；
- bounded magnitude 无法绕过 gate 的测试；
- scar competitor 包含真实最高非-scar竞争类别的测试；
- 逐病例 reliable-label/T2 masking 测试；
- pre-support raw-delta remote penalty 测试；
- raw probability 到 calibrated logit 的审计；
- 300-step loss、gate/magnitude 分布、changed voxels；
- known-bad 与 strict validator 结果；
- 关键证据路径。

只有收到 `APPROVE_GATE_A` 才允许从头运行 repaired fold0。

## Gate B — 修复后 Fold0 可扩展到 Folds 1–4

触发条件：repaired fold0 已从原 seed 完整运行 Stage A 5000 + Stage B 3000 steps；所有 GPU 进程 terminal；完成 44 例 outer-held-out 推理和评价。旧 pre-repair fold0 必须继续标为 `PRE_REPAIR_INVALID_SEMANTICS_DIAGNOSTIC_ONLY`，不得混入任何正式指标。

在开始 folds 1–4 之前发送邮件：

```text
Subject: [CARE-DG][B/4] 修复后 Fold0 完成，等待五折扩展验收
State: AWAITING_HUMAN_ACCEPTANCE_GATE_B
Approval token: APPROVE_GATE_B
```

邮件和证据包必须包含：

- 44-case all-fold0 与 16-case complete-trimodal 分项；
- nnU-Net A0、direct residual A1、CARE-DG A2、无 Stage B A3 的可用 matched fold0 对照；
- scar、edema-zone、pure-edema 的 Dice、HD/HD95、exact HD、precision、recall、remote FP、component count、volume ratio；
- case-wise help/harm；
- FN/FP error recall 和 correct-direction correction；
- q_FN/q_FP 与 m_FN/m_FP 的均值、分位数、相关性，证明 gate 未被 magnitude 绕过；
- changed voxels、fallback、no-T2 identity；
- inner checkpoint selection 未读取 outer-held-out 的证据；
- repaired fold0 checkpoint、config、source、split 和 prediction hashes；
- 是否存在 NaN、OOM、identity collapse、support collapse、远端组件或 exact-HD 灾难病例。

Gate B 的重点是确认实现和训练机制正确。即使 fold0 Dice 暂时低于 nnU-Net，Controller 也不能自行取消五折；是否继续由用户验收后决定。

只有收到 `APPROVE_GATE_B` 才允许运行 folds 1–4。

## Gate C — 五折 OOF 可进入 All-data Deployment Fit

触发条件：五折正式训练全部 terminal，W3 OOF aggregation、A0/A1/A2/A3 ablation、anti-identity、help/harm、exact-HD tail 和 remote-FP audit 全部完成。不得只在 W2 训练完成时发邮件，必须等 W3 指标形成。

在开始 W4 all-data deployment training 之前发送邮件：

```text
Subject: [CARE-DG][C/4] 五折 OOF 与消融完成，等待部署训练验收
State: AWAITING_HUMAN_ACCEPTANCE_GATE_C
Approval token: APPROVE_GATE_C
```

邮件必须用自然中文先给结论，并附：

- complete-80 主结果与 all-220 robustness；
- scar、edema-zone、pure-edema 对 nnU-Net 的差值；
- 各 fold 稳定性；
- A1 vs A2：显式 FN/FP gate 是否优于旧式直接 residual；
- A2 vs A3：完整三模态 Stage B 是否有增量；
- help/harm、exact-HD 95% tail、remote FP；
- anti-identity 和机制激活结果；
- paper-ready gate、exploratory validation gate 的逐项 PASS/FAIL；
- 推荐继续 all-data fit、需要修复，或 `NO_CARE_DG_CANDIDATE_SAFE_FOR_VALIDATION` 的理由；
- 关键 CSV/JSON/Markdown 路径。

未经 `APPROVE_GATE_C`，不得运行 all-data 5000+3000 steps，也不得生成 CARE-DG validation package。若科学结果为负，仍需把完整证据交给用户决定，不得自动换成纯 nnU-Net 或历史模型。

## Gate D — Validation 本地包待人工上传 / 无候选终态

触发条件：用户批准 Gate C 后，W4 all-data fit 和 W5 validation inference/package 全部完成，或者严格 gate 得出无安全候选。所有 GPU 命令必须 terminal，determinism、geometry、label、fallback、runtime 和 Docker-equivalent smoke 已完成。

发送终态邮件之一：

```text
Subject: [CARE-DG][D/4] Validation 本地包完成，等待人工上传
State: CARE_DG_VALIDATION_CANDIDATE_READY_PENDING_USER_UPLOAD
```

或：

```text
Subject: [CARE-DG][D/4] 未形成安全 CARE-DG 候选
State: NO_CARE_DG_CANDIDATE_SAFE_FOR_VALIDATION
```

候选邮件必须包含：

- ZIP 路径和 SHA256；
- source/config/checkpoint hashes；
- validation 15 例 scar/edema mechanism activation、changed voxels 与 fallback rate；
- 两次推理 hash equality；
- geometry/label/export/Docker-equivalent smoke；
- 峰值显存和运行时间；
- 明确写 `validation_upload_performed: false`、`docker_upload_performed: false`；
- 用户下一步的手动上传命令或页面动作。

无候选邮件必须精确写明失败的是哪一个科学门，不能推荐纯 nnU-Net、MoSAIC、Batch7 或旧 Cascade 替代。

Gate D 后继续完成 Mapper、CURRENT/wiki、strict validator、本地轻量 commit 和终态 accounting。若 Gate D 邮件先于 W6 完成，则 W6 完成后只发送仓库既定的最终 completion email；两封邮件用途必须区分，且不得重复发送相同内容。

## 恢复规则

用户每次验收后会在 Controller 会话中发送以下精确 token 之一：

```text
APPROVE_GATE_A
APPROVE_GATE_B
APPROVE_GATE_C
```

Controller 收到 token 后必须：

1. 记录批准时间、当前 git SHA、任务/blueprint hash 和批准前证据 hash；
2. 验证自邮件发送后科学代码和冻结合同未被未审修改；
3. 若发生变化，重新生成差异并再次请求验收，不能沿用旧批准；
4. 继续下一阶段并保持相同 Executor、相同 allocation 和 repair loop。

不得将聊天中的普通“继续”“好的”自行解释为批准 token。