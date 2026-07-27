# Codex Goal — CARE-SER-Lite 自有机制最终候选

你是 CARE 的 Controller/Coordinator 和 acceptance owner。同步最新 `origin/main` 后，严格执行：

1. `prompts/tasks/20260727_care_ser_lite_owned_final_candidate_controller.md`
2. `prompts/tasks/20260727_care_ser_lite_owned_final_candidate_executor_plan.yaml`

这是对前一任务 `NNUNET_ONLY_DOCKER` 结论的明确覆盖。用户禁止最终 submission 只包含 nnU-Net、MoSAIC 或两者的确定性拼接。nnU-Net 和 MoSAIC只能是冻结 evidence sources；最终至少一个病种必须由 CARE 自有机制真实修改 mask 并通过 strict nested OOF final-mask safety gate。

必须实现并验证 CARE-SER-Lite：

```text
SRR positive/negative selective retrieval
+ MMRD frozen teacher evidence and reliable-label/no-T2 semantics
+ scar suppress/recover component gate
+ T2-conditioned edema-zone region gate
+ Cascade-style bounded pathology correction and exact fallback
```

只允许使用现有 Slurm allocation `60657290`，GPU 命令串行运行。禁止 `sbatch`、`salloc`、新 Slurm job、validation 上传、Docker 上传和 runtime push。

完整执行 W0–W7。前一 Controller 没有真正完成的内容——多来源多阈值 candidate dataset v2、真实 CARE-MMRD embeddings、病例外正负 prototype、真实 remove/add counterfactual、case-grouped nested CV、scar/edema reconstructed final-mask Dice/HD95/exact-HD/remote-FP/help-harm、CF/FD proposal-source stress test——本次必须真实运行，不能再用文件存在、人工结论、纯模型对比或 component F1 代替。

Controller 遇到代码、缓存、几何、标签、checkpoint、特征、评价器、测试、聚合、validator 或 wiki 缺口时，必须记录 `repair_ledger.csv`，退回同一 Executor 做最小修复，检查真实 diff/hash，并重跑受影响命令与 validators。不得在第一次可修复错误时停止，也不得把负科学结果当成操作阻塞。

终态只允许：

```text
CARE_SER_LITE_DUAL_READY
CARE_SER_LITE_SCAR_READY_NNUNET_EDEMA
CARE_SER_LITE_EDEMA_READY_NNUNET_SCAR
NO_CARE_OWNED_CANDIDATE_DO_NOT_UPLOAD
OPERATIONALLY_BLOCKED_EXISTING_ALLOCATION_OR_REQUIRED_ASSET
```

禁止输出或推荐 `NNUNET_ONLY_DOCKER`、纯 MoSAIC 或纯外部 deterministic hybrid 作为本任务 submission。只有至少一个 CARE-owned pathology branch 通过并在 validation inference 中产生非零机制激活时，才允许生成本地 upload-ready ZIP；否则明确不提交。

完成 strict validator、Mapper、CURRENT/wiki、aggregation 和本地轻量 commit 后，才可返回 `VERIFIED_COMPLETE`。运行角色不得 push。