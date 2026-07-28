---
task_key: 20260728_care_dpr_fold0_global_redesign
task_kind: scientific_milestone
task_type: care_dpr_dual_pathology_global_redesign_fold0
status: READY_FOR_CONTROLLER
risk_level: high
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260728_care_dpr_fold0_global_redesign_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
planning_review_required: false
review_required: false
review_mode: none
reviewer: none
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
validation_packaging_authorized: false
validation_upload_authorized: false
docker_local_build_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
fold_expansion_authorized: false
new_model_training_authorized: true
new_slurm_allocation_authorized: false
route_promotion_authorized: false
---

# CARE-DPR Fold0 全局重设计 Controller

## Execution Contract

本任务不是对 Gate B-R2 的 scale、threshold 或单个 head 继续打补丁。当前冻结 CARE-DG 已经证明病例外错误信号存在，但逐体素 correction 无法把信号稳定转化为完整病灶。新的唯一方法是：

```text
CARE-DPR
= one compact availability-aware CARE encoder
+ scar proposal/refiner/component-utility branch
+ edema-zone proposal/refiner/component-utility branch
+ frozen nnU-Net context/fallback
```

方法真值：

```text
prompts/blueprints/CARE_DPR_dual_pathology_proposal_refine_arbitrate_20260728.md
```

执行图：

```text
prompts/tasks/20260728_care_dpr_fold0_global_redesign_executor_plan.yaml
```

必须读取并执行这两个文件，不得自行简化架构、预算、数据划分、监督、评价或失败分支。

## 启动与真值

工作位置固定：

```text
/users/a/e/aereinh/CARE
branch: main
remote: YuukiAS/CARE_Challenge
```

先 `git fetch origin`，确认 `origin/main` 至少包含：

```text
prompts/blueprints/CARE_DPR_dual_pathology_proposal_refine_arbitrate_20260728.md
prompts/tasks/20260728_care_dpr_fold0_global_redesign_executor_plan.yaml
prompts/tasks/20260728_care_dpr_fold0_global_redesign_controller.md
```

然后读取：

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/FINAL_OUTPUT_READABILITY_POLICY.md`
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`
- `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`
- `prompts/routes/handoffs/CURRENT.md`
- `routes/README.md`
- `wiki/README.md`
- `.agents/skills/slurm-routing-partition/SKILL.md`
- `.agents/skills/care-mapper/SKILL.md`
- CARE-DG Gate B-R1/R2 最新结果与源码。

`CURRENT.md` 和 wiki 当前仍可能停留在旧 baseline-only 终态。它们是 stale evidence，不能覆盖本任务；只有 W5 完成后才更新。

视觉交接已经由 Planner 完成：

```text
diagram_versions_read:
  SRR-v2
  SRR-v2.5
  SRR-v3
  CARE-MMRD
  CARE-SRR-Cascade
visual_read_status: PASS_PROJECT_BACKGROUND_IMAGES_VISUALLY_READ
```

恢复的核心设计是：一个 availability-aware multimodal encoder，双病理独立 proposal，anatomy-guided local refinement，component utility arbitration，bounded per-pathology anchor fallback。

## 绝对资源边界

唯一允许的 GPU allocation：

```text
job_id: 60657290
```

所有 GPU 命令必须串行使用：

```bash
srun --jobid=60657290 --overlap --ntasks=1 bash -lc '<command>'
```

严格禁止：

- `sbatch`
- `salloc`
- 新 Slurm job
- 同时运行两个 GPU 训练/推理进程
- 写 `/overflow/htzhu/CARE`
- validation upload
- Docker upload
- runtime git push

每个 GPU wave 前检查 `squeue`、`scontrol show job`、`nvidia-smi`、剩余 walltime、现存 CARE 进程和 task-local GPU lock。Allocation 终止只能写 operational block 和精确 resume 点，不得写科学失败或项目放弃。

## 架构硬要求

### 1. 只有一个共享主体

实现一个 compact three-scale CARE encoder：

- LGE stem
- T2 stem
- C0 stem
- availability-aware masked fusion
- anchor context stem
- shared encoder

禁止第二个完整 U-Net、第二个 nnU-Net、MoSAIC coarse/fine、MMRD teacher、prototype/dictionary、多个 expert encoder。

nnU-Net 只作为：

- frozen probabilities/logits；
- anatomy and uncertainty context；
- exact fallback。

它不得成为唯一输出主体。

### 2. Scar 与 edema-zone 对称但独立

每条分支必须真实实现：

- FN proposal head；
- FP proposal head；
- local refinement head；
- component utility / accept head。

Scar 使用 LGE-dominant small-ROI refinement；edema-zone 使用 T2-conditioned larger-context refinement。两条分支 loss 权重、采样槽和科学 gate 对称，不得用 scar 结果掩盖 edema。

### 3. 可靠标签与 no-T2 安全

继承 CARE-MMRD 的可靠标签规则：

- scar：所有 scar-reliable 病例；
- edema-zone：T2-present 病例；
- no-T2：edema loss、gradient、proposal、refinement、utility、final write-back 均严格为零。

不得生成伪 T2、伪 edema 标签，也不得把无 T2 病例当 edema negative。

### 4. Proposal 不直接写回

继承 Batch7 的病理 decomposition 和 proposal/refinement，但修复其过度写回问题：

- q_fn/q_fp 只定义候选错误区域；
- local refiner 负责完整局部病灶重建；
- component utility head 决定是否接受 refined component；
- 未接受组件必须完整 fallback 到 anchor。

### 5. 双病理组合

顺序固定：

```text
edema-zone arbitration
-> scar arbitration
-> scar priority
-> pure edema = accepted zone - accepted scar
```

Anatomy channels 0–3 默认保持 anchor。只允许被接受的 pathology component bounded write-back。

## Controller Task Graph

严格按 executor plan 顺序执行 W0–W5，不得跳过，也不得让 Executor 自行决定新结构。

### W0：机制上限与失败分类

使用当前 CARE-DG fold0 train-side selected checkpoint 和 fixed train-side inner cases，生成：

- scar/edema FN component recall；
- scar/edema FP component recall；
- q_fn/q_fp AUCPR；
- soft ROI GT coverage；
- oracle component acceptor gain；
- oracle local replacement gain；
- current realized gain。

Outer fold0 不得用于 threshold、模型、loss、ROI 或结构选择。

必须输出 machine-readable classification：

- `EXECUTION_FAILURE`
- `PROPOSAL_LIMITED`
- `REFINEMENT_LIMITED`
- `ARCHITECTURE_CEILING_LOW`

`EXECUTION_FAILURE` 必须先修复；其他分类不得阻止 W1–W4。`ARCHITECTURE_CEILING_LOW` 也不允许项目终止，只要求 W4 后返回 Planner 做下一次全局设计。

### W1：实现

新文件固定：

```text
src/care_myocardium/models/care_dpr.py
src/care_myocardium/data/care_dpr_dataset.py
src/care_myocardium/training/care_dpr_trainer.py
src/care_myocardium/inference/care_dpr_predictor.py
scripts/training/run_care_dpr.py
scripts/inference/run_care_dpr_inference.py
scripts/evaluation/analyze_care_dpr_mechanism_ceiling.py
scripts/evaluation/evaluate_care_dpr.py
scripts/evaluation/validate_care_dpr_packet.py
configs/care_dpr/care_dpr_v1.yaml
tests/care_dpr/
```

Component utility target 只能从 actual-train GT 构建；inner 只用于 checkpoint/threshold selection；outer fold0 只用于最终一次评价。

### W2：真实病例 preflight

必须通过：

- real-case forward/backward；
- scar/edema proposal、refiner、utility 全部非零梯度；
- no-T2 edema 全路径零梯度和零输出；
- scar priority；
- component target 与 image/label/feature 对齐；
- zero accepted component = exact anchor；
- checkpoint save/reload/resume exact；
- bfloat16 finite；
- 300-step anti-empty-shell overfit：scar 与 edema active loss 各下降至少 30%。

所有 smoke/preflight scientific credit = 0。

### W3：Fold0 正式训练

初始化：

- 从现有 fold0 CARE-DG train-side selected `checkpoint_step04000.pt` 读取 stems、anchor context、shared encoder、q_fn/q_fp compatible weights；
- new local refiner 与 utility heads 随机初始化；
- 初始化映射、遗漏参数和 shape 必须有 receipt。

Stage A：

```text
2500 steps
actual-train reliable cases
encoder lr 2e-5
proposal/refiner/utility lr 1e-4
```

Stage B：

```text
1500 steps
complete-trimodal actual-train only
freeze stems/shared encoder/q proposal
train only scar+edema refiners and utility heads
lr 5e-5
```

共同设置：

```text
seed 20260728
batch size 4
patch 8x128x128
AdamW
weight decay 1e-4
bfloat16
grad clip 1.0
checkpoint every 500 steps
```

采样严格八槽循环：

```text
scar_FN
scar_FP
scar_hard_negative
scar_pathology
edema_FN
edema_FP
edema_hard_negative
edema_pathology
```

Hard negative 至少含 blood pool、outside-support bright island、remote anchor FP、高强度无病灶区域。No-T2 不得进入 edema 槽。

### W4：Fold0 评价与诊断

Checkpoint、utility threshold 与任何 component 参数只允许 fixed train-side inner selection。Outer fold0 评价一次，禁止根据 outer 指标重选。

Complete16 主结果，outer44 robustness。分别报告：

- scar；
- edema-zone；
- pure-edema；
- Dice、HD95、exact HD、precision、recall；
- remote FP、component count、volume ratio；
- per-pathology help/harm；
- proposal recall；
- refiner oracle vs realized gap；
- utility calibration；
- accepted/rejected component audit；
- no-T2 identity；
- exact fallback。

Fold0 candidate gate 完全按 blueprint，不得修改。

如果未通过，禁止写 `NO_CARE_DG_CANDIDATE_SAFE_FOR_VALIDATION` 或任何项目放弃终态。必须给出：

```text
execution_gap
proposal_gap
refinement_gap
arbitration_gap
oracle_ceiling
next_global_redesign_target
```

Controller 只能返回 Planner，不得自行引入下一架构。

### W5：Packet、Mapper 与状态

必须生成：

- controller report；
- completion check；
- MANIFEST；
- strict validator；
- mapper report；
- notification brief；
- local lightweight commit。

只有 W4 通过 candidate gate 时，报告可以建议后续五折扩展，但不得自动开始 folds 1–4。若未通过，状态必须是“本轮结构未达标，已定位下一全局重设计方向”，不是“放弃”。

## 失败处理原则

### 执行不到位

包括 wiring、mask、loss application、gradient、ROI alignment、checkpoint、resume、sampler、evaluation、selection leakage、nonfinite、empty component target。全部属于同范围 repair，必须修复并重跑，不得用负科学结果结束。

### 当前设计仍可提高

如果执行正确但 gate 未通过，必须根据 W0/W4 的 proposal/refinement/arbitration/oracle 证据判断瓶颈。不得只改一个 loss 或 scale 后继续；下一轮必须重新检查整个 input→proposal→ROI→refiner→utility→composition 链路，由 Planner 给出新的整体合同。

### 明确禁止放弃

本任务不得输出：

```text
ABANDON_CARE
STOP_ALL_CUSTOM_RESEARCH
NO_FURTHER_REDESIGN
```

也不得把 `NO_CANDIDATE` 作为 CARE 项目终态。当前架构不通过只表示需要下一次整体设计。

## Controller 终态字段

Controller report 必须以自然中文说明：发生了什么、执行是否可信、设计信号在哪里、下一步全局目标是什么。然后包含：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status:
experiment_adequacy_decision:
contract_compliance_status:
required_outputs_complete:
validators_passed:
all_jobs_terminal:
aggregation_complete:
fold0_candidate_gate:
failure_classification:
next_global_redesign_target:
git_commit_decision:
git_push_decision: NOT_AUTHORIZED
blocked_actions:
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```

Batch 完全结束、所有 GPU 命令 terminal、aggregation/validator/local commit 确认后，写：

```text
results/20260728_care_dpr_fold0_global_redesign/notification_brief.json
```

并复用已有 `controller_notifications/notify_goal_watcher.py` / `care_watchboard:Notify` 向 `1155246312@link.cuhk.edu.hk` 发送中文短邮件。不得新建 notifier，也不得在 running/monitor 阶段发送完成邮件。
