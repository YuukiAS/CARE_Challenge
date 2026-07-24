---
task_key: 20260725_care_myops_srr_cascade_runtime_closure_repair
parent_task_key: 20260724_care_myops_srr_cascade_submission_rescue
task_kind: runtime_closure_repair
task_type: srr_cascade_formal_runtime_repair
status: READY_FOR_CONTROLLER_RUNTIME_CLOSURE_REPAIR
repair_id: SCR-R1-RC1
risk_level: high
route_change: false
scientific_decision_scope: none_runtime_closure_only
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260725_care_myops_srr_cascade_runtime_closure_repair_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: component_runtime_alignment
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
---

## Execution Contract

本任务修复 SCR-R1 的运行闭环，不新开 SCR-R2、Batch11 或 milestone。Controller 此前因真实 W3 formal runtime 缺失而阻塞是正确结论；现在用户授权在同一科学合同内补齐生产实现，并复验 W0–W2 中不能支持正式训练的合成或元数据证据。

唯一机器权威是：

```text
results/srr_production/code_maturity/scr_r1_runtime_block_critic_and_repair_20260725.md
configs/care_mm/srr_cascade_runtime_closure_repair.yaml
prompts/tasks/20260725_care_myops_srr_cascade_runtime_closure_repair_executor_plan.yaml
```

上述修复文件在冲突时覆盖旧 preexecution amendment、base config、旧 executor plan 和旧 Controller 生成的 `resolved_execution_contract.json`。不允许改变科学假设、seed、6250-step 预算、22/22 split、retention gate、Cine 边界或上传权限。

## Controller Prompt

你是 SCR-R1-RC1 的唯一 Controller、协调者和最终验收人。先同步最新 `origin/main`，确认包含本修复提交，读取治理文件、三份修复权威、旧 SCR-R1 合同、当前 Controller ledger、source-cache job receipts、Slurm skill 和 Mapper skill。不要继续使用绑定在 `6b9834c6...` 的旧上下文。

继续监督一个 Executor。修复不是让 Executor临场发明算法：anchor/cache/model/prototype/sampler/augmentation/loss/training/resume/validation/selection/audit/package/validator的结构、参数、文件路径和失败分支已经写入修复 config。Executor 只能实现并修复这些固定合同。

先执行 RC0：

1. 绑定最新 main 并记录所有 authority SHA；
2. 分类现有工作树和旧 untracked 文件，不得静默混入；
3. 刷新旧 cache jobs `60450660/60451021/60451022` 的真实 `squeue/sacct`；
4. 保留旧 receipts，但将 W0 标为条件复验、W1 标为原位修复、W2 标为正式授权前重跑、W3 标为零 formal credit；
5. 检查 runtime 目录至少 45 GiB 可用空间。

随后按 RC1–RC6 连续执行。每个 Wave 后必须亲自检查真实 diff、测试、cache/hash、预测、Slurm和required outputs。实现错误、cache格式错误、训练错误、评价/selection错误、打包错误、validator错误和Mapper错误均属于同范围修复，必须退回同一 Executor；不得再次仅以“当前仓库没有实现”为由终止，因为本任务已经显式授权实现。

特别检查以下旧问题是否真正消失：

- `--formal-job` 不再主动返回 `NEEDS_REPAIR_FORMAL_ENTRYPOINT_MISSING`；
- orchestrator 不再硬编码 job ID，也不再在 cache PASS 后强制 NEEDS_REPAIR；
- scar 与 edema 是独立 trainable trunks，active pathology之外的病种通道精确等于 anchor；
- prototype 保留病例×负类别向量，不再合并类别或取 mask前 N 个 voxel；
- anchor全220例完成真实 probability/grid/official-export roundtrip；
- source cache使用checkpoint/plans解析和滑窗，不用默认构造器整幅捷径；
- fiducial真实调用增强函数，overfit使用真实32通道cache/OOF anchor/标签；
- known-bad通过真实注入和validator非零退出，而不是“该阶段未运行所以PASS”；
- control/SRR读取同一冻结schedule与initial state；
- 训练支持signal/resume，但只有完整6250+6250 steps才有formal credit；
- W4六候选、audit、W5五折anchor package与W6 validator入口在W3前就已存在并通过dry-run。

只有以下情况可写 `OPERATIONALLY_BLOCKED`：服务器资产确实不存在且不能由授权代码生成；45 GiB存储门无法满足；两个授权GPU partition均在记录所有允许尝试后不可用；或外部集群故障阻止任何运行。普通代码缺陷不得写成 operational block。

Controller 必须持续负责到四个 logical run 全部 terminal、post-completion aggregation、calibration freeze、audit、条件式本地package、strict validator、Mapper/wiki/CURRENT/fingerprint和本地轻量commit完成。Submitted、pending、running、resume checkpoint和monitor packet均不是完成。

最终仍只允许：

```text
CUSTOM_SUBMISSION_CANDIDATE_READY_PENDING_USER_UPLOAD
PARTIAL_CUSTOM_SUBMISSION_CANDIDATE_READY_PENDING_USER_UPLOAD
NO_CUSTOM_RESCUE_USE_BASELINE_ONLY
OPERATIONALLY_BLOCKED
```

不得 push runtime、上传 validation/Docker、扩 fold、训练 Cine、恢复旧 Wave6 或启动下一轮。

## Executor Worker Contract

Executor严格执行修复 executor plan。每个 Wave 返回真实diff、命令、测试、asset/hash、job ID、terminal accounting和证据路径。不能自行改设计、门槛、候选、seed、budget、split、上传权限，也不能把dry-run、smoke或partial runtime称为formal complete。

## Mapper Contract

Mapper核对真实生产调用图，而不是规划图：OOF anchor builder、tiled frozen source cache、independent pathology trunks、category-aware cross-fit prototypes、matched schedule、active-pathology losses、resume、calibration/audit decode、five-fold package anchor、official export和fallback。最终更新 `wiki/README.md`、`wiki/current_state.yaml`、`wiki/architecture.yaml`、`wiki/COMPONENTS.csv`、CURRENT和fingerprint；本轮不要求新PNG。
