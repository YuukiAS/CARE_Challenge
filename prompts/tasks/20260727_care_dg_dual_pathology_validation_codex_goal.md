# Codex Goal — CARE-DG 双病理 validation 冲刺

你是 CARE 的 Controller/Coordinator 和 acceptance owner。同步最新 `origin/main` 后，严格执行：

1. `prompts/blueprints/CARE_DG_dual_pathology_blueprint_20260727.md`
2. `prompts/tasks/20260727_care_dg_dual_pathology_validation_controller.md`
3. `prompts/tasks/20260727_care_dg_dual_pathology_validation_executor_plan.yaml`

这是对此前 `NNUNET_ONLY_DOCKER`、CARE-SER-Lite、MoSAIC proposal fusion 和复杂多模型蓝图的正式覆盖。当前唯一目标方法是 `CARE-DG`：冻结五折 nnU-Net 锚点，加一个紧凑共享编码器和两个独立 scar/edema 错误修正 decoder。禁止在 runtime 中引入 MoSAIC、完整 MMRD、prototype/dictionary、SIP、多个专家或旧 Cascade。

用户明确授权本任务实现新网络、修复代码、完成五折 OOF 正式训练、all-data deployment training、validation 15 例本地推理、upload-ready ZIP 和 Docker-equivalent smoke。不得自动上传 validation 或 Docker。

所有 GPU 工作只允许使用现有 interactive allocation：

```text
60657290 / htzhulab / g1807htzh01 / CAREInteractive3d
```

如果当前进程不在 allocation 内，只能用 `srun --jobid=60657290 --overlap ...` 进入。禁止 `sbatch`、`salloc`、新 Slurm job、并行 GPU 训练、写入 `/overflow/htzhu/CARE` 和 runtime push。

Controller 必须持续监督同一个 Executor 至全部 GPU 命令 terminal、aggregation、strict validator、Mapper、CURRENT/wiki、本地轻量 commit和终态 email完成。遇到代码、缓存、环境、几何、标签、checkpoint、loss、gradient、training、评价器、package、validator或wiki错误，不得随意 block：先写入 `repair_ledger.csv`，退回同一 Executor 做最小修复，检查真实 diff/hash，重跑失败命令及受影响的 aggregation/validators。不得因 fold0 暂时未超过 nnU-Net、运行中状态、负科学结果或第一次可修复错误提前结束。

必须真实完成 W0–W6：评价器 parity；CARE-DG 实现和真实病例 forward/backward；300-step anti-identity overfit；五折每 fold Stage A 5000 + Stage B 3000 optimizer steps；220-case OOF 与 complete-80 主评价；A0/A1/A2/A3 final-mask ablation；scar/edema-zone/pure-edema Dice、HD95、exact HD、remote FP、help/harm和机制激活；all-data deployment fit；validation 双病理推理；两次 deterministic hash equality；本地 ZIP；Docker-equivalent smoke；Mapper和strict validator。

终态只允许：

```text
CARE_DG_VALIDATION_CANDIDATE_READY_PENDING_USER_UPLOAD
CARE_DG_LOCAL_PAPER_READY_AND_VALIDATION_CANDIDATE_READY
NO_CARE_DG_CANDIDATE_SAFE_FOR_VALIDATION
OPERATIONALLY_BLOCKED_EXISTING_ALLOCATION_OR_REQUIRED_ASSET
```

禁止用纯 nnU-Net、历史 Batch7/Cascade 或其他外部模型替代失败的 CARE-DG。完成后写 `results/20260727_care_dg_dual_pathology_validation/notification_brief.json`，并使用既有 notifier 向 `1155246312@link.cuhk.edu.hk` 发送一封中文短邮件；不得创建新 notifier，也不得在 submitted、pending、running、monitor 或 aggregation 未完成阶段通知。运行角色不得 git push。