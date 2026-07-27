# Codex Goal — CARE-DG Fold0 语义修复后再继续五折

你是 CARE-DG 当前任务的 Controller/Coordinator 和 acceptance owner。同步最新 `origin/main` 后，优先执行：

1. `prompts/tasks/20260727_care_dg_w2_fold0_critic_repair_amendment.md`
2. `prompts/blueprints/CARE_DG_dual_pathology_blueprint_20260727.md`
3. `prompts/tasks/20260727_care_dg_dual_pathology_validation_controller.md`
4. `prompts/tasks/20260727_care_dg_dual_pathology_validation_executor_plan.yaml`

立即暂停新的 folds 1–4；若后续 fold 已运行，保存最近 checkpoint 后停止该 CARE-DG 进程，但不要终止 interactive allocation `60657290`。将已有 fold0 标记为 `PRE_REPAIR_INVALID_SEMANTICS_DIAGNOSTIC_ONLY`，不得计入正式 OOF。

必须修复 amendment 中的全部语义问题，尤其是：

- edema decoder 改为预测 scar∪edema 的 edema zone，pure edema 由 zone−scar 得到；
- FP margin loss 必须降低 pathology margin，不能和 FN 同方向；
- magnitude 必须有界，禁止用巨大 magnitude 绕过接近零的 gate；
- scar competitor 必须能包含 edema，修正、loss、evaluation 的 margin 定义一致；
- partial-label/T2 supervision 必须逐病例 mask，禁止 `t2.mean()` 乘全 batch loss；
- remote penalty 使用 pre-support raw delta；
- formal runner、sampler、evaluator、validator 源码必须本地 commit 且 hash 可审；
- nnU-Net probability 必须明确转换为 log-prob/logit，禁止把 raw probability 当 logit；
- formal mode 不得静默补缺 uncertainty/support/distance；
- 绑定最终 package 所需的 15-case frozen Cine prediction tree。

修复后先跑新增 unit/known-bad tests，再重跑 300-step real-case overfit，随后从原 seed 完整重跑 fold0 `5000 + 3000` steps。只有 repaired fold0 的语义、gate/magnitude calibration、sampler quota、no-T2 safety、mechanism activation、source/hash 和 strict validator 全部通过，才继续 folds 1–4。

不得因为 repaired fold0 暂时低于 nnU-Net 而科学性早停；但不得在语义错误、gate bypass、partial-label leakage、raw-probability-as-logit、remote loss vacuous 或源码不可审的情况下继续烧卡。

所有 GPU 工作仍只允许使用 `60657290`；禁止 `sbatch`、`salloc`、新 Slurm job、validation/Docker upload 和 runtime push。所有可修复错误必须进入 `repair_ledger.csv` 并由同一 Executor 修复、重跑和验证。