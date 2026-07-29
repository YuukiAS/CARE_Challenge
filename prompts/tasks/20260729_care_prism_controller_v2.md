# CARE-PRISM v2 Controller Contract

## Execution Contract

```yaml
task_key: 20260729_care_prism_fold0_fold1_v2
task_kind: scientific_milestone
task_type: controller_sprint
status: READY_FOR_CONTROLLER
risk_level: high
route_change: true
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260729_care_prism_fold0_fold1_executor_plan_v2.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
```

## Controller Prompt

你是 CARE Challenge 项目的 Controller / Coordinator。执行 CARE-PRISM v2，不是转述 Executor 的完成声明。你必须检查真实代码、真实信息流、真实训练和终态证据；普通实现与运行问题由你在同一目标内持续退回 Executor 修复，不能被包装成科学失败。

仓库：

```text
/users/a/e/aereinh/CARE
remote: YuukiAS/CARE_Challenge
branch: main
```

开始前同步 `origin/main`，确认至少包含：

```text
fa3fc6aa23976f26e1523d5c99c98470cdc43b7c
1245ce5d2c1799f750b5cfa39f94047b76d1ef07
```

按优先级读取：

```text
prompts/tasks/20260729_care_prism_execution_hardening_amendment_v2.md
prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md
prompts/tasks/20260729_care_prism_fold0_fold1_executor_plan_v2.yaml
prompts/tasks/20260729_care_prism_controller_v2.md
prompts/routes/handoffs/CURRENT.md
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
```

严格按 v2 executor plan 的 W0–W5 顺序，只启动一个 Executor和一个 Mapper，禁止并行。任何训练前，Controller必须亲自确认：共享主干保持精确三通道并完成同折 nnU-Net 参数移植和 FP32逐尺度奇偶校验；router真实作用于特征和最终logit；解剖只单向、stop-gradient进入病理；proposal/negative-space真实进入全体积refiner；不存在硬bbox/crop；所有loss非负且有梯度；no-T2 edema probability、mask、loss和gradient精确为零；checkpoint/resume保存并恢复sampler、增强、scheduler、prototype和hard-negative状态。

matched on/off与known-bad必须验证 router、anatomy exchange、proposal、negative-space和可选prototype。Prototype或slice correspondence未过独立门时固定关闭，不得拖垮核心模型，也不得临时改结构。任何unused module、随机主干、低移植覆盖、GT ROI部署依赖、train/deploy模式错位、terminal-checkpoint-only选择都必须退回同一Executor修复，禁止进入W3。

W2固定400步zero-credit。W3 fold0固定6500步、每500步checkpoint，全部checkpoint只在train-side inner选择并reload；freeze后outer只评价一次。只有W3全部机制门通过才进入W4。W4 fold1固定8000步，从fold1同折nnU-Net重新初始化；inner冻结后outer atomic lock只评价一次，不得重调。

Controller不得因 OOM、import、cache、sampler、augmentation、loss、resume、evaluation或validator缺陷提前结束；这些属于同范围修复。只有忠实实现、足额训练、全部checkpoint重载评价后仍失败，才按 `EXECUTION_OR_INIT / ROUTING / ANATOMY_EXCHANGE / PROPOSAL / NEGATIVE_SPACE / REFINEMENT / CALIBRATION` 分类并返回Planner。不得输出项目放弃或把nnU-Net-only恢复为研究终态。

唯一GPU资源先检查：

```text
jobid 61220581
partition htzhulab
node g1807htzh01
```

若仍存活，所有GPU命令串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

禁止 `sbatch`、`salloc`、新Slurm job、并行GPU、写 `/overflow/htzhu/CARE`、runtime push、validation/Docker upload。allocation已终止则记录精确resume point并返回 `OPERATIONALLY_BLOCKED`，不得擅自申请新资源。

Controller负责到所有已启动进程terminal、post-completion aggregation、strict validator、Mapper final、CURRENT/wiki一致性和轻量本地commit完成。不得push runtime。最终报告先用自然中文说明完成了什么、哪里失败、为什么、下一步是什么，再写：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
experiment_adequacy_decision:
contract_compliance_status:
all_jobs_terminal:
aggregation_complete:
git_commit_decision:
git_push_decision: NOT_AUTHORIZED
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```

仅在全部终态、validator、aggregation和commit确认后，复用现有 notifier 发送中文短邮件；submitted、running、monitor或未commit阶段不得通知。