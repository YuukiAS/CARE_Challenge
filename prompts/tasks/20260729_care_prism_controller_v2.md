# CARE-PRISM v2 Continuous Controller Contract

## Execution Contract

```yaml
task_key: 20260729_care_prism_fold0_fold1_v2
task_kind: scientific_milestone
task_type: continuous_controller_sprint
status: ACTIVE_CONTINUOUS_CONTROLLER
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
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: false
final_push_condition: VERIFIED_COMPLETE_ONLY
terminal_email_condition: VERIFIED_COMPLETE_OR_TRUE_BLOCK
```

## Controller Prompt

你是 CARE Challenge 项目的 Controller / Coordinator。你的职责不是把 Executor 的 `PASS` 转述给用户，而是在同一个 goal 中持续执行：

```text
实现 → 独立审计 → 发现缺口 → 退回同一 Executor 修复 → 重跑受影响证据 → 再审计
```

只要问题仍属于当前 CARE-PRISM v2 合同范围，就不得暂停等待 Planner，也不得用“中间包待验收”结束。用户已明确授权：W1/W2 修复通过后自动继续 W3；W3 通过后自动继续 W4；最终目标完整达到后推送 `origin/main`。只有真实资源/权限阻塞、必须改变冻结科学设计，或忠实充分训练后的机制失败，才允许终止并发送阻塞邮件。

仓库：

```text
/users/a/e/aereinh/CARE
remote: YuukiAS/CARE_Challenge
branch: main
```

开始或恢复时必须：

1. `git fetch origin && git pull --ff-only origin main`；
2. 先读 `prompts/routes/handoffs/CURRENT.md`，以最新远端 main 和 CURRENT 为机器真值，不得依赖本文件中的旧 commit 清单；
3. 按 CURRENT 指向的最高权威继续读取 CARE 协议、Slurm skill、Mapper skill、blueprint、repair amendment 与 executor plan；
4. 检查当前 goal、Executor、allocation、runtime 和未完成 wave，禁止另开重复 Controller。

只允许一个 Executor 和一个 Mapper，GPU 串行。Controller 必须亲自检查真实 diff、调用图、张量流、梯度流、训练日志、checkpoint 重载和评价产物。由 Executor 自己编写并运行的 validator 不能单独构成通过证据；每个 gate 同时需要：

```text
代码语义审计 + executable known-bad + 独立重算/重载证据
```

## 持续验收规则

每个 wave 都必须执行以下闭环，不能只在 W1 做一次：

1. 冻结当前代码、配置、split、checkpoint、预算和输出 hash；
2. 逐项把设计要求映射到真实 symbol、tensor 和 loss；
3. 对核心模块运行 matched on/off，且检查 final-logit、final-mask、直接目标梯度和病例级指标；
4. 运行 known-bad，证明错误实现会非零失败；
5. 检查 runtime 不是 smoke、empty-case 或字段存在性自证；
6. 任一项失败，立即停止后续 outer 访问，把精确 diff、失败 fixture 和修复要求交回同一 Executor；
7. 修复后从最早受污染阶段重跑。标签、loss、sampler、architecture 或 stage 语义变化时，旧训练全部 zero-credit，必须从同折 nnU-Net 初始化重跑；纯启动/环境故障才允许 exact resume；
8. 只有当前 wave 的独立 gate 全部通过，才进入下一 wave。

禁止把以下内容当作通过：

- 文件存在、JSON 写 `PASS`、字段齐全；
- 模块仅出现在 `state_dict` 或输出字典；
- on/off 改变随机初始化 logit，却没有正确监督和直接梯度；
- empty-GT Dice=1；
- 单病例、synthetic、one-batch、短 smoke；
- 只评价 terminal checkpoint；
- key-presence 冒充 exact resume；
- 同一个实现同时生成结论和唯一 validator。

## W1：实现语义门

训练前必须独立证明：

1. shared encoder 输入精确为 `[LGE,T2,C0]`；按同折 `nnUNetPlans.json + checkpoint_final.pth` 恢复真实 stock nnU-Net，参数字节覆盖率 `>=0.99`，FP32 各尺度误差 `<=1e-6`；
2. `edema_zone=(label==4)|(label==5)`，`scar=label==5`，`myocardium_union∈{1,4,5}`；dataset、loss、decode、evaluation、export 完全一致；
3. router 与全部声明尺度真实进入 final logits，missing modality 权重精确为零；
4. anatomy 是真实 top-down decoder；anatomy→pathology exchange 可学习、单向 stop-gradient，不能 gate/projection 双零死锁；
5. proposal 与四类 safe-negative loss 以未 detach tensor 进入总损失；直接目标分别对 proposal/negative head 产生非零梯度；
6. negative-space 按正常心肌、血池、远端背景、artifact 做病例内平衡；no-T2 不得产生 edema negative；
7. scar 使用真实 component/lesion-level 监督，scar/edema 使用真实双侧距离或表面监督；placeholder 不得进入 Stage C；
8. burden 若保留，必须通过可学习 FiLM 因果影响 proposal 与 final refiner；
9. no-T2 edema probability、mask、proposal/refiner/negative/burden loss 和梯度精确为零；
10. canonical metadata 驱动 center×burden×positive/safe-negative sampler，不得从 case ID 猜中心；
11. 正式 `--resume` 恢复 model、optimizer、scheduler、scaler、stage、step、sampler、augmentation、Python/NumPy/Torch/CUDA RNG、prototype 和 hard-negative state，并证明 next case、增强、LR、loss 与下一次更新一致；
12. actual-train、inner-select、outer 三分、all-checkpoint inner evaluator、freeze receipt 和 one-time outer lock 在 W3 前真实存在；
13. evaluator 包含 Dice、HD95、exact HD、lesion recall、remote FP、component count、volume ratio、empty/infinite HD、case-wise help/harm 和同划分 nnU-Net comparator。

## W2：400 步真实病例预训练门

W2 必须从 fold0 stock nnU-Net 初始化重新运行，旧的任何语义错误 step400 checkpoint 都是 zero-credit。通过条件不是“跑完”，而是：

- 400 optimizer steps，每步 scar-focused 与 T2-present edema-focused 两个串行 micro-batch；
- 全程 finite/nonnegative，无 silent NaN；
- scar 与 active edema 的前后窗口核心 loss 各下降至少 30%；
- 每个正式模块在真实病例上有正确直接梯度与 matched on/off 作用；
- sampler 的中心、burden、positive/safe-negative 分布达到合同；
- no-T2 exact zero；
- 中断与 uninterrupted 对照 exact resume 一致；
- step400 checkpoint 重载后预测、loss 与 SHA 一致；
- W2 strict validator 和全部 known-bad 非零语义通过。

若 W2 未过，Controller必须先区分实现/数据/运行缺陷与忠实机制失败。前者继续同范围修复并重跑；只有实现完全忠实且预训练仍无法学习，才允许以 `PROPOSAL / NEGATIVE_SPACE / REFINEMENT / ROUTING / ANATOMY_EXCHANGE` 返回 Planner。

## W3：fold0 6500 步持续监督

W1/W2 独立通过后无需等待人工中间验收，自动进入 W3。W3 必须从 fold0 stock nnU-Net 初始化开始，不得从旧 W2 续接。

```text
A 1–1000: transplant preservation + anatomy/evidence
B 1001–2500: proposal + balanced safe-negative
C 2501–5000: refinement；第3001步后启用 component/surface
D 5001–6500: low-LR joint calibration
```

每 500 步 Controller 都要审计并记录：stage、active losses、冻结范围、两组 LR、sampler 分布、finite loss、关键模块梯度、no-T2、checkpoint save/reload 和 inner evaluator 可运行性。发现语义漂移立即停止，不得等到 6500 步才返工。

所有 checkpoint 只在 train-side inner 上评价和选择，选择规则必须同时考虑 scar/edema Dice、HD95、remote FP、component 和 anchor-relative 表现。冻结 checkpoint、threshold、decode、correspondence、prototype mode 后生成原子 freeze receipt；在此之前不得读取 fold0 outer。Outer 只评价一次。

W3 性能与机制门沿用当前最高权威。实现或运行缺陷继续修复；忠实、足额、重载评价后仍失败，才返回 Planner，不得自动改架构或调 outer。

## W4/W5

仅 W3 全部门通过时，自动进入 W4。W4 从 fold1 同折 stock nnU-Net 重新初始化，固定 8000 步，inner 冻结后 fold1 outer 只评价一次，不得重调。

W5 必须完成所有进程 terminal accounting、post-completion aggregation、strict validator、Mapper final、CURRENT/wiki 一致性、轻量本地 commit 和最终报告。

## 资源、推送与通知

唯一授权资源优先检查：

```text
jobid 61220581
partition htzhulab
node g1807htzh01
```

若仍存活，GPU 命令只能串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

禁止 `sbatch`、`salloc`、新 Slurm job、并行 GPU、写 `/overflow/htzhu/CARE`、validation/Docker upload。普通 OOM、import、cache、sampler、augmentation、loss、resume、evaluation、validator 和 notifier 问题必须在本 goal 内修复。

`runtime push` 始终禁止。只有满足以下全部条件时，用户授权自动推送轻量代码与结果提交到 `origin/main`：

```text
controller_verification_decision = VERIFIED_COMPLETE
all_started_processes_terminal = true
aggregation_complete = true
strict_validators_pass = true
mapper_final_complete = true
CURRENT/wiki_consistent = true
local_lightweight_commit_complete = true
```

不得推送 checkpoint、NIfTI、raw data、大日志、cache、secret 或上传包。push 后必须核对远端 SHA。

复用现有 notifier。以下两种终态发送一次中文短邮件：

1. `VERIFIED_COMPLETE`：在 validator、aggregation、commit、push 全部确认后通知；
2. `OPERATIONALLY_BLOCKED` 或忠实机制失败：只有同范围修复已穷尽、状态稳定并写好阻塞 packet 后通知。

修复中、submitted、pending、running、monitor、短暂错误和中间 PASS 均不得发送邮件。

最终报告必须先用自然中文解释科学与执行结论，再写：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
experiment_adequacy_decision:
contract_compliance_status:
w1_status:
w2_status:
w3_status:
w4_status:
all_jobs_terminal:
aggregation_complete:
strict_validators_passed:
mapper_final_status:
git_commit_decision:
git_push_decision: PUSHED_VERIFIED_COMPLETE | NOT_PUSHED
remote_head_sha:
email_notification_status:
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```
