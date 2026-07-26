# Codex Goal — MoSAIC Hosted-Gap Forensics and Final Blueprint

你是 CARE 的 Controller/Coordinator 和 acceptance owner。同步最新 `origin/main` 后，严格执行以下三个文件，优先级从高到低：

1. `prompts/tasks/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint_amendment.md`
2. `prompts/tasks/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint_controller.md`
3. `prompts/tasks/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint_executor_plan.yaml`

用户已确认 scar Dice `0.6965` 属于 MoSAIC submission；不要重新裁决模型家族归属。你需要查清 exact ZIP/checkpoint/inference recipe，并彻底解释 clean OOF 与 hosted 排名翻转。

只允许使用现有 Slurm allocation `60657290`，所有 GPU 命令串行运行。禁止 `sbatch`、`salloc`、新 Slurm job、validation 上传、Docker 上传和 runtime git push。

完整执行核心 W0–W7。W3D matched training 仅在修订文件的资源门通过时运行，不能挤占 W4–W7。

Controller 不得在第一次代码、缓存、几何、标签、checkpoint、评价器、测试、聚合、validator 或 wiki 错误时停止。所有可修复缺口必须记录到 `repair_ledger.csv`，退回同一 Executor 做最小修复，检查真实 diff/hash，并重跑受影响命令和 validators。不得把普通可修复问题包装成需要用户确认，也不得用短 smoke、component F1、full-data contaminated 指标或 unresolved exact recipe 代替结论。

终态必须明确回答：

1. exact hosted package/checkpoint/recipe 是否已绑定；
2. 目标模态结构、validation 域、full-data inclusion/selection、推理配方、15-case 波动和 metric/export 各解释多少；
3. Batch7、MMRD、Cascade 哪些部件有独立增量价值；
4. 旧 SafeScar Step3 gate 是否具备最终分割科学证据；
5. 两份 CARE-SER 蓝图保留、删除和修改什么；
6. 最终 Docker 应执行哪个唯一架构及其病种独立 fallback。

完成严格 validator、Mapper、CURRENT/wiki、aggregation 和本地轻量 commit 后才能返回 `VERIFIED_COMPLETE`。运行角色不得 push。