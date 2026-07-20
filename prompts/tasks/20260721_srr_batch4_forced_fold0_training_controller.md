---
task_key: 20260721_srr_batch4_forced_fold0_training
task_kind: scientific_milestone
task_type: mainline_batch_training
controller_mode: slurm_continuous
milestone_number: null
milestone_id: null
status: DRAFT_FOR_PLANNING_REVIEW
risk_level: high
route_change: false
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260721_srr_batch4_forced_fold0_training_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: independent_thread
reviewer: separate_readonly
review_required: true
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: blocked
experiment_adequacy_gate: batch4_minimum_effective_training
route_negative_gate: independent_review_required
scientific_completion_gate: independent_review_required
diagnostic_publication_gate: independent_review_required
diagnostic_publication_scope: lightweight_batch4_packet_only
blocked_after_diagnostic_publication: validation_upload,hosted_metric_claim,fold_expansion,route_promotion,m11
planning_review_required: true
planning_reviewer: separate_gpt_thread
planning_review_path: prompts/tasks/20260721_srr_batch4_forced_fold0_training_planning_review.md
planning_review_token: PENDING
planning_reviewed_commit: PENDING
---

## Execution Contract

本任务只执行 CARE SRR Batch 4：修复训练 checkpoint 与推理接口的最后断点，构建完整 fold0-train 原型/记忆资产，强制完成一次 1800 步 MyoPS fold0 训练，并在 step 600、1200、1800 对完整 44 例做同划分评价。

权威输入：

```text
prompts/routes/handoffs/CURRENT.md
docs/plans/laneB_round04_active_srr_batch4_forced_fold0_training_execution.md
configs/srr_production/myops_batch4.yaml
prompts/tasks/20260721_srr_batch4_forced_fold0_training_executor_plan.yaml
```

运行仓库和分支固定为：

```text
/users/a/e/aereinh/CARE
main
```

禁止写入 `/overflow/htzhu/CARE` 和 Route A/B/C worktree。禁止训练 Cine、上传 validation、生成 hosted 主张、启动 M11 或 push。

开始执行前必须存在独立规划审查文件，并包含精确 token：

```text
BATCH4_PLANNING_AUDITED_GO
```

否则停止为 `BLOCKED_HANDOFF_REVIEW`，不得实现、提交 Slurm 或写运行结果。

### Minimum effective training

```yaml
min_optimizer_steps: 1800
min_train_loop_seconds: 1800
min_validation_events: 3
min_eval_cases: 44
require_one_batch_overfit: true
require_prediction_sanity: true
require_loss_decrease: true
require_same_split_baseline: true
require_cache_isolation: true
require_all_train_cases_loaded: 176
require_all_train_cases_sampled: 176
require_same_checkpoint_three_modes: true
```

短 smoke、预检和失败启动均为零正式训练 credit。

## Controller Prompt

你是 CARE main-only Batch 4 controller。你必须绑定当前 `origin/main` 精确 SHA，验证工作树干净，并读取任务、配置、Slurm skill、mapper skill、Agent-Flow v2、HANDOFF gate 和当前机器真值。不要使用旧 Route controller。

在执行科学任务前，强制执行 hard-gate policy：精确任务图、agent-flow v2 合同、strict validator、completion-check-before-final-audit、minimum effective training、known-bad regression、mapper/wiki/fingerprint gate、SRR 图读取证据。任一门失败时返回 `NEEDS_REVISION` 或 `NEEDS_EVIDENCE`；不要继续 final audit。

本任务的有序任务图固定如下：

```text
B4-00 bootstrap and planning-review gate
B4-01 training/inference checkpoint interface repair
B4-02 full 176-case frozen prototype-memory asset build
B4-03 one-batch overfit and GPU/environment preflight
B4-04 Slurm routing race and forced 1800-step fold0 training
B4-05 step-600/1200/1800 44-case full-volume inference/evaluation
B4-06 selected checkpoint reload and same-checkpoint three-mode controls
B4-07 failure diagnosis and scientific status classification
B4-08 mapper final, strict validation, terminal accounting and local packet commit
controller stops
independent reviewer runs later
```

所有 B4-00 至 B4-08 都是 blocking。不得用相似文件、历史结果或自然语言说明代替。

### Durable continuity

使用 `slurm_dependency`。训练提交后，必须通过 `scripts/ops/submit_care_dependency_finalizer.py` 或仓库当前等价的一方 helper，为全部 race attempt IDs 提交 `afterany` finalizer。训练阶段内部依赖使用 `afterok`。

finalizer 必须记录：

```text
all attempt job IDs
partition/state/exit/elapsed/node
winner job ID and winner lock
cancelled losers
runtime output and log paths
aggregation commands and exit codes
strict validator commands and exit codes
post-completion tracked files
```

任何 pending、running、submitted、`NEEDS_MONITOR` 或 `AWAITING_SACCT` 状态都不是完成。控制者必须保留终态责任，不得提交 job 后退出。

### Slurm race

按照 `configs/srr_production/myops_batch4.yaml`：先 `htzhulab`；900 秒仍 pending 时提交 `a100-gpu`；首次提交后 1800 秒前两者仍 pending 时，仅在同配置 V100 显存预检通过后提交 `volta-gpu`。所有尝试使用同一 logical run、相同代码/配置/split/asset hash、隔离目录和原子 winner lock。

### Operational retry

同一语义下的环境、导入、路径、OOM 启动、preemption 修复允许 bounded retry：

```yaml
max_startup_retries: 2
max_preemption_retries: 2
max_unknown_retries: 0
```

失败启动不得计入 optimizer steps 或训练时间。若修复会改变模型、patch、loss、步数、划分、配置语义或科学选择，停止并返回 `NEEDS_GPT_PLANNER`。

### Controller ending

`controller_report.md` 必须以这些字段结束：

```text
controller_run_status:
operational_completion_status:
experiment_adequacy_decision:
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision:
git_commit_decision:
git_push_decision: NO_PUSH
published_files:
blocked_actions:
next_required_action: INDEPENDENT_READONLY_REVIEW
reason_if_not_published:
reason_if_no_route_promotion:
```

## Executor Worker Contract

执行者只有一个，写入范围由 executor plan 固定。不得增加第二执行者或将 MyoPS/Cine 并行。

### B4-01 必须修复

1. `scripts/training/run_srr_propref_myops_fold0.py` 写 schema v2 checkpoint，而不是只含 `model_state_dict` 的旧字典。
2. 同一训练 checkpoint 可在运行时切换三种模式，final-output mode 不再导致重新初始化或 checkpoint 结构不匹配。
3. `scripts/srr_production/infer_myops.py` 的 identity 输出必须来自模型 logits，禁止 raw label 覆盖。
4. checkpoint 选择改为 44 例完整体积证据；patch loss 只作诊断。
5. 增加完整训练集覆盖采样和 176 例冻结原型/记忆构建。
6. 为正式入口增加 config、split、anchor、prototype、checkpoint hash 检查。

### B4-02 资产

只从 fold0 的 176 个训练病例构建。资产 `.pt` 保持 ignored，tracked manifest 必须完整记录病例和哈希。验证病例出现在资产 manifest 中必须失败。

### B4-03 预检

使用正式 Python 和相同配置。60-step one-batch overfit 必须至少相对下降 5%，目标模块梯度非零、无 T2 水肿严格为零、schema v2 reload 输出差不超过 `1e-6`。

### B4-04 训练

必须完成 1800 optimizer steps 和至少 1800 秒训练循环。不得启用提前停止。训练读取全部 176 例，最终采样清单也必须覆盖 176 例。

### B4-05/B4-06 评价

step 600、1200、1800 均对 44 例运行 anchor-bounded 模式。按配置中的固定字典序选择 checkpoint，重新加载后用相同权重运行 identity、anchor-bounded 和 no-anchor。评价输入必须是 NIfTI prediction/GT。

### B4-07 诊断

不得根据性能临时启动第二训练。按计划固定类别解释：优化失败、候选召回不足、细化无效、修正门过闭、修正过度、远端假阳性或数据/标签/评价问题。结果差但足额训练时写 `BATCH4_TRAINED_NEGATIVE_OR_REPAIR_REQUIRED`，不能写 undertrained。

### B4-08 提交边界

只提交轻量 Markdown/CSV/JSON、源代码、配置、测试和 wiki。不得提交 checkpoint、原型 `.pt`、预测 NIfTI、完整日志、锁、secret 或 upload package。执行者不得写 `review.md`。

## Mapper Contract

Mapper 必须在实现快照后写 draft，在所有训练、推理和聚合完成后重读最终 SHA 并写 final。它必须核对：

- 实际训练模型是否为 M10 D3 full-4scale；
- 176/44 数据流；
- 原型/记忆来源和查询策略；
- schema v2 checkpoint 到推理入口；
- 同 checkpoint 三模式；
- proposal、refiner、correction 对 final labels 的影响；
- 当前 wiki 中 stale 的 M9/M10/Batch3 描述。

Mapper 可以更新 root `wiki/` 和 D2/SVG/PNG，但不能训练、提交 Slurm、作科学判断或写 `review.md`。final mapper 后必须运行：

```bash
python scripts/architecture/validate_care_architecture_wiki.py --strict
python scripts/architecture/generate_care_architecture_wiki.py --check
```

## Reviewer Prompt

这是独立只读 reviewer session。不要修代码、补证据、训练、提交 Slurm、打包 validation、上传或启动下一批。固定到控制者本地结果包 commit，独立检查：

1. 规划审查 token 是否匹配当前任务。
2. 是否真实完成一个 official winner 的 1800 步、1800 秒训练。
3. 是否存在 3 个完整 44 例评价事件。
4. checkpoint 是否 schema v2 且重载后用于同一三模式。
5. 原型/记忆是否来自全部 176 例且无验证泄漏。
6. identity 是否模型 logits 精确恢复 anchor，而不是导出绕过。
7. no-T2、安全、几何、标签和 hash 门是否通过。
8. Slurm attempts、winner、losers、terminal accounting、聚合是否自洽。
9. 结果是否按候选、强信号或足额负结果诚实分类。
10. controller/mapper/finalizer 是否未自审、未 push、未作 hosted 主张。

只写：

```text
results/20260721_srr_batch4_forced_fold0_training/review.md
```

通过操作和证据审查时使用 token：

```text
BATCH4_TRAINING_PACKET_AUDITED_GO
```

如果只是 pending/monitor、训练不足、缺 44 例评价、旧 checkpoint 格式、identity 绕过、资产泄漏或 receipt 冲突，返回对应 `NEEDS_MONITOR`、`NEEDS_EVIDENCE` 或 `NEEDS_REVISION`，不得给 audited-go。