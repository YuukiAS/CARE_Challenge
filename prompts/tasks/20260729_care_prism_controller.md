# CARE-PRISM Controller Contract

## Execution Contract

```yaml
task_key: 20260729_care_prism_fold0_fold1
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
executor_plan_path: prompts/tasks/20260729_care_prism_fold0_fold1_executor_plan.yaml
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

你是 CARE Challenge 项目的 Controller / Coordinator。当前任务是停止旧 CARE-ARC W3 线并执行新的 CARE-PRISM 系统重设计。你不是被动转发 Executor 总结；你是实现验收、同范围修复、Slurm 连续性和终态 packet 的责任人。

仓库：

```text
/users/a/e/aereinh/CARE
remote: YuukiAS/CARE_Challenge
branch: main
```

开始前同步 `origin/main`，确认包含：

```text
00c2d44cb2670063ce56846beec4ae4f3b70d3f6
5981803ccbc27891da3b599e2388c0e7b47f0921
```

按优先级读取：

```text
prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md
prompts/tasks/20260729_care_prism_fold0_fold1_executor_plan.yaml
prompts/tasks/20260729_care_prism_controller.md
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

严格按 executor plan 的 W0–W5 顺序执行，只启动一个 Executor和一个 Mapper，禁止并行。

### Controller必须亲自关闭的旧W3问题

在任何训练前，逐项从真实代码和可执行测试确认：

1. same-fold nnU-Net encoder/anatomy decoder权重确实移植，覆盖率按参数字节>=90%，不得随机初始化后写“兼容”；
2. scar/edema router权重真实乘到多尺度特征并改变最终logit，不能只返回审计张量；
3. anatomy feature和soft union真实进入每个病理decoder尺度；
4. coarse proposal真实调制soft ROI/refiner，不能只是auxiliary loss；
5. prototype margin只进入proposal且有正负安全语义；
6. 所有loss非负、有限，禁止旧SDF logvar负值捷径；
7. 数据增强、中心×病灶负荷采样和每step scar+edema双micro-batch真实执行；
8. train/deploy使用同一slice-correspondence模式；
9. no-T2 edema probability、mask、loss和gradient均exact zero，而不只是logit=0；
10. checkpoint selection评价所有预注册checkpoint，不得只用terminal step。

任一项失败，Controller必须把精确symbol、diff和失败fixture退回同一Executor修复，不能进入W3，也不能把实现错误写成科学失败。

### 正式网络边界

唯一模型是 CARE-PRISM：

```text
LGE/T2/C0 + availability
→ one same-fold nnU-Net-initialized shared ResEnc backbone
→ lightweight modality-private pyramids
→ real pathology-specific soft retrieval
→ internal anatomy decoder and anatomy-pathology exchange
→ scar/edema proposal + safe positive/negative prototype margins
→ one soft myocardium-neighborhood ROI per pathology
→ scar/edema independent full-lesion refiners
→ direct edema-zone → scar priority → pure edema
```

禁止：第二个完整backbone、MoSAIC runtime/weights、MMRD teacher、nnU-Net pathology residual、DPR component utility、ADD/REVISE、完整SRR dictionary/SIP/top-k router、hard myocardium crop、独立不连接最终mask的SDF head。

### 训练和评价

W2 400-step preflight是zero credit，只验证实现和学习能力。

W3 fold0固定6500 steps：A 1000、B 1500、C 2500、D 1500；必须从fold0 nnU-Net初始化重新开始。checkpoint每500步，全部在train-side inner选择；outer只在freeze receipt后评价一次。

只有W3全部机制门通过才进入W4。W4 fold1固定8000 steps，从fold1 nnU-Net初始化重新训练；fold1 inner冻结checkpoint/decode，outer atomic lock只评价一次。不得读取fold1 outer调参。

普通OOM、cache、import、loss、sampler、resume、evaluation和validator错误属于同范围执行修复，Controller必须继续修复而不是提前结束。真正机制未过门时，写明 proposal、negative-space、refinement、routing、anatomy exchange各自差距，返回Planner做下一次完整设计；不得输出项目放弃或恢复nnU-Net-only为研究终态。

### 资源

唯一GPU资源：

```text
jobid 61220581
partition htzhulab
node g1807htzh01
```

所有GPU命令只能串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

禁止 `sbatch`、`salloc`、新Slurm job、并行GPU进程、写`/overflow/htzhu/CARE`、runtime push、validation/Docker upload。allocation终止时只记录精确resume point并返回`OPERATIONALLY_BLOCKED`，不得新建job。

### 终态

Controller负责到全部已启动GPU进程terminal、aggregation、strict validator、Mapper final、CURRENT/wiki更新和lightweight local commit完成。不得push runtime。

最终必须生成 executor plan 声明的全部W5文件，并在自然中文结论后写：

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

全部结束后，复用现有 notifier 向 `1155246312@link.cuhk.edu.hk` 发送中文短邮件。不得在 submitted、running、monitor、未完成aggregation或未commit时发送。
