# Codex Goal — CARE-SER Dual-Pathology Target-Domain Validation Sprint

你是 CARE 的 Controller/Coordinator 和 acceptance owner。同步最新 `origin/main` 后，按以下优先级执行：

1. `prompts/tasks/20260727_care_ser_dual_target_domain_submission_amendment.md`
2. `prompts/tasks/20260727_care_ser_lite_target_domain_submission_amendment.md`
3. `prompts/tasks/20260727_care_ser_lite_owned_final_candidate_controller.md`
4. `prompts/tasks/20260727_care_ser_lite_owned_final_candidate_executor_plan.yaml`

最高优先级硬要求：第一版 validation candidate 必须同时处理 scar 和 edema，且两个病种都由独立 CARE-owned learned gate 决定最终 mask。禁止 scar-only primary、nnU-Net-only edema primary、纯 nnU-Net、纯 MoSAIC 或两者确定性拼接。

当前固定模型是 `CARE-SER-TD-Dual-v1`：

```text
5-fold nnU-Net anatomy/pathology anchor
+ final/full-data MoSAIC raw scar proposals only
+ CARE-MMRD real frozen embeddings
+ SRR positive/negative retrieval
+ CARE ScarSuppress/ScarRecover
+ CARE EdemaSuppress/EdemaRecover with T2-present reliable supervision
+ Cascade-style bounded correction
+ protected anatomy and pathology-specific exact fallback
```

Official validation/test 是完整 `C0+LGE+T2`，因此 complete-80 OOF 是 competition primary estimand，all-220 是 robustness/limitation estimand。两者都报告，但不得再用 all-220 单独终止 target-domain candidate。

完整执行 dual amendment 的 P0-P7。先完成双病理 candidate dataset、真实 MMRD embeddings、病例外正负 retrieval、scar/edema nested OOF reconstructed final-mask metrics、最终 gate freeze和 full-data proposal calibration。

Submission 1 固定为：

```text
CARE-SER-TD-Dual-FD-v1
```

只有 scar 和 edema 都通过 exploratory target-domain gate、两个 CARE branch 在 held-out 和 validation inference 中非零激活、FD proposal calibration stress PASS，才允许生成本地 upload-ready ZIP。

Submission 2 优先为：

```text
CARE-Cascade-TD-Dual-v1
```

仅当 matched C0 zero-retrieval 与 C1 real-retrieval full-data target-weighted shallow Cascade 能在现有 allocation 内完整运行，且 C1 对两个病种均通过 gate并相对 C0有增量时生成。否则使用同一双病理 CARE gate和 clean five-fold MoSAIC scar proposals生成：

```text
CARE-SER-TD-Dual-CF-v1
```

Submission 1 不等待 Submission 2。

只允许使用现有 Slurm allocation `60657290`，GPU 命令串行。禁止 `sbatch`、`salloc`、新 Slurm job、自动 validation/Docker 上传和 runtime push。

Controller 遇到代码、缓存、几何、标签、checkpoint、feature、nested-CV、mask reconstruction、package、validator 或 wiki 缺口时必须执行 repair loop：写 `repair_ledger.csv`，退回同一 Executor 最小修复，检查 diff/hash，重跑受影响命令和 validators。不得使用空表、两行 candidate、component F1、纯模型对比、文件存在或预写结论冒充完成。

终态必须明确：

1. scar 和 edema 各自 complete-target OOF Dice/HD95/exact-HD/remote-FP/help-harm；
2. SRR retrieval 和 MMRD evidence 对两个病种的独立增量；
3. 两个 CARE branch 的 held-out/validation activation；
4. Submission 1 ZIP 路径和期待超过当前 MoSAIC hosted score的依据；
5. Submission 2 ZIP路径或未生成的精确原因；
6. 哪些结果 paper-ready，哪些仅 exploratory validation；
7. all-220 robustness limitations。

只有 real dual-pathology final masks、真实指标、双病种 CARE action、package audit、strict validator、Mapper、CURRENT/wiki、aggregation和本地轻量 commit全部完成后，才可返回 `VERIFIED_COMPLETE`。运行角色不得 push。