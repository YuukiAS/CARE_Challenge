# Codex Goal — CARE-SER Target-Domain Validation Sprint

你是 CARE 的 Controller/Coordinator 和 acceptance owner。同步最新 `origin/main` 后，按以下优先级执行：

1. `prompts/tasks/20260727_care_ser_lite_target_domain_submission_amendment.md`
2. `prompts/tasks/20260727_care_ser_lite_owned_final_candidate_controller.md`
3. `prompts/tasks/20260727_care_ser_lite_owned_final_candidate_executor_plan.yaml`

用户确认 official MyoPS validation/test 目标是完整 `C0+LGE+T2`。Clean OOF 本身无泄漏且公平，但 all-220 mixed-modality 均值不能继续作为唯一 deployment 选择标准。完整三模态 80-case OOF 是 competition primary estimand；all-220 是 robustness/limitation estimand。两者都必须报告。

历史 target-matched fold0 已显示 Batch7 与 SCR scar 距 nnU-Net 约 `-0.008/-0.007`，SCR edema Dice/HD95 有小幅正信号。因此不得再把过去 CARE 路线整体视为无目标域潜力，也不得用 `NNUNET_ONLY_DOCKER` 提前终止。

本轮必须优先产出一个真实 CARE-owned scar-first validation candidate：

```text
nnU-Net anchor
+ nnU-Net/MoSAIC/可用 Batch7 多来源 scar proposals
+ CARE-MMRD frozen evidence
+ SRR positive/negative retrieval
+ CARE suppress/recover component gate
+ Cascade-style bounded correction and exact fallback
```

至少完成 amendment 的 P0-P4：评价器 parity、target-matched reanalysis、真实多候选 dataset、病例外检索与 suppress/recover gate、complete80 nested OOF、final full-data gate、15-case validation inference 和本地 package。Scar 候选通过 exploratory target-domain gate 后，不得因 edema 未完成而阻塞包装；可生成 `CARE-SER-TD-Scar = CARE scar + nnU-Net edema`。Edema/Cascade-TD 是后续优先级。

只允许使用现有 Slurm allocation `60657290`，所有 GPU 命令串行。禁止 `sbatch`、`salloc`、新 Slurm job、validation/Docker 自动上传和 runtime push。

Controller 对代码、缓存、几何、标签、checkpoint、特征、评价器、nested-CV、mask reconstruction、package 或 validator 问题必须执行 repair loop：记录 `repair_ledger.csv`，退回同一 Executor 最小修复，检查真实 diff/hash，重跑受影响命令与 validators。不得用旧 component F1、两行 CSV、人工结论、all-220 单一结果或文件存在代替执行。

终态必须明确：

1. 当前训练比较为什么在统计上公平但对 complete-target 不充分；
2. complete80 上 T0-T7 每个候选的 Dice、HD95、exact HD、remote FP、help/harm；
3. SRR retrieval、MMRD evidence、Batch7/Cascade evidence分别增加了什么；
4. 哪个 CARE variant通过 paper gate、哪个只通过 exploratory validation gate；
5. 推荐上传的唯一 CARE-owned ZIP 路径；若无候选，写 `NO_CARE_TARGET_DOMAIN_CANDIDATE_SAFE_FOR_VALIDATION`。

只有真实 CARE mechanism 在 held-out 和 validation inference 中非零激活、严格 validator/Mapper/CURRENT/wiki/aggregation/local commit 完成后，才允许返回 `VERIFIED_COMPLETE`。运行角色不得 push。