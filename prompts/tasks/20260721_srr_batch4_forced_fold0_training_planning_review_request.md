# Batch 4 独立规划审查请求

## 审查对象

请固定到包含以下文件的最新 `origin/main`：

```text
docs/plans/laneB_round04_active_srr_batch4_forced_fold0_training_execution.md
configs/srr_production/myops_batch4.yaml
prompts/tasks/20260721_srr_batch4_forced_fold0_training_controller.md
prompts/tasks/20260721_srr_batch4_forced_fold0_training_executor_plan.yaml
prompts/routes/handoffs/CURRENT.md
configs/srr_production/entrypoints.yaml
```

这是独立 GPT 规划审查，不是执行者、controller、mapper 或运行后 reviewer。不得修代码、训练、提交 Slurm、写 runtime `review.md`、上传 validation 或启动 Batch 4。

## 背景结论

Batch 3A 已建立真实 MyoPS 模型在环完整体积诊断，但当前只使用零步、小模型和少病例原型/记忆；Batch 3B 是三例强度阈值解剖代理和二维光流诊断。用户已明确授权 Batch 4 进行一次真实 fold0 训练，并允许等待过长时使用三个兼容分区的同逻辑运行竞速。

## 必须审查的问题

1. 是否完整保留 SRR-v2/v2.5/v3 的路线目标，而没有退化成普通 nnU-Net 后处理。
2. 模型是否固定为 `m10_d3_hierarchical_memory_propref + full_4scale + anchor_bounded_srr_correction`。
3. 是否明确修复训练 checkpoint 与 Batch 3A 推理 schema 不兼容的问题。
4. 是否要求同一训练 checkpoint 支持 identity、anchor-bounded、no-anchor 三模式。
5. identity 是否必须从模型 logits 导出，而不是 raw label 覆盖。
6. 原型/记忆是否覆盖全部 176 个 fold0 训练病例，并禁止验证泄漏和无 T2 水肿伪负例。
7. 训练预算是否不可被 smoke 代替：至少 1800 optimizer steps、1800 秒、3 次完整 44 例评价。
8. 当前采样配额是否能够覆盖 176 例，同时给 T2 水肿、LGE-only scar 和 hard negative 足够训练机会。
9. checkpoint 选择是否真正使用 Dice、HD95、远端假阳性和病例级 help/harm，而不是 patch loss。
10. `htzhulab -> a100-gpu -> volta-gpu` race 是否满足同一配置、隔离目录、原子 winner lock、取消 loser 和 `afterany` finalizer。
11. 是否禁止控制者用 submitted、pending、running、`NEEDS_MONITOR`、启动失败或 undertrained token结束本应继续的训练。
12. 任务图、write scope、required outputs、known-bad、终止条件和 reviewer 通过标准是否足够精确，没有把科学选择留给 Codex。
13. mapper/wiki/fingerprint、controller no-push 和独立 reviewer 边界是否符合当前协议。
14. 本轮冻结 Cine、只训练 MyoPS 是否合理。

## 输出路径与决定

请只写：

```text
prompts/tasks/20260721_srr_batch4_forced_fold0_training_planning_review.md
```

通过时必须包含：

```text
planning_review_decision: AUDITED_GO
planning_review_token: BATCH4_PLANNING_AUDITED_GO
reviewed_commit: <exact main SHA>
```

发现任何计划留白、训练可被短跑代替、checkpoint/评价不公平、分区竞速不安全、Cine 混入本轮、输出路径缺失或 reviewer 边界错误时，写：

```text
planning_review_decision: NEEDS_PLANNING_REVISION
```

并逐项给出阻断修改。