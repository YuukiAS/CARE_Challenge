---
task_key: 20260803_care_ase_r2_continuous_reviewer_addendum
status: AUTHORIZED_BY_USER
applies_to: 20260803_care_ase_r2_full_fidelity_execution
contract_amendment: prompts/blueprints/CARE_ASE_R2_continuous_independent_reviewer_amendment_20260803.yaml
review_required: true
review_mode: independent_thread
reviewer: separate_readonly
manual_continue_gate: false
review_failure_terminal_block: false
---

# CARE-ASE R2 持续独立 Reviewer 追加合同

本追加合同不是最后才运行一次的终审。Controller 必须立即启动一个独立、只读、持续存在或可持续 resume 的 Reviewer，并在 R2 的实现、真实 GPU 预检、训练源码冻结、训练关键边界、outer 评价和终态分别提交固定快照供其审查。

Reviewer 不参与实现，不修改主工作树，不提交或推送，不选择 checkpoint，不调阈值，不读取 W4.5 之前的 fold1/fold4 outer。Reviewer 的职责是独立证明真实入口、代码行为、runtime、checkpoint 和指标口径没有降级。

Reviewer 只有两个决定：

```text
PASS_CONTINUE
REVISE_CONTINUE_CURRENT_GOAL
```

`REVISE_CONTINUE_CURRENT_GOAL` 不是 Goal block。Controller 必须把 finding 交回同一个 Executor，持续修复、重跑受影响 Gate、创建新的不可变候选提交，并交给同一 Reviewer 重审，直到 `PASS_CONTINUE`。不得返回 Planner，不得等待用户，不得通过降低合同获得 PASS。

## Controller 立即执行

1. `git fetch origin main --prune`，确认读取：

```text
prompts/blueprints/CARE_ASE_R2_continuous_independent_reviewer_amendment_20260803.yaml
```

2. 将该 amendment 合并进当前 `effective_contract.json`，优先级高于 R2 中冲突的 `review_required: false`、`review_mode: none` 或 final-only reviewer 语义。

3. 立即启动独立 Reviewer thread/short goal，固定名称建议：

```text
care_ase_r2_continuous_reviewer
```

4. Reviewer 对每轮固定 candidate commit 使用 detached read-only checkout。不得审查可变主工作树。建议：

```text
/users/a/e/aereinh/CARE_reviewers/care_ase_r2/<round_id>/<candidate_sha>
```

Reviewer 临时输出写入：

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_ase_r2_full_fidelity_execution/reviewer/<round_id>
```

Controller 验收后将轻量 review receipt 复制到：

```text
results/20260803_care_ase_r2_full_fidelity_execution/reviewer/<round_id>
```

## Reviewer Prompt

你是 CARE-ASE R2 的独立、只读、持续 Reviewer。你不是最终才出现的一次性审阅者。你必须从 W1 第一版实现候选开始持续审查，直到 W6 终态。

你不得修改源码、主工作树、训练 checkpoint、split、模型、loss、sampler、scheduler、decode、指标人口或阈值；不得 commit、push、上传 validation/Docker/challenge；不得读取 W4.5 前的 fold1/fold4 outer。

每轮只审查 Controller 提供的固定 candidate commit 和固定证据目录。必须记录 candidate SHA、effective contract SHA、正式训练入口及全部关键源码 SHA。不得接受自然语言自述、单纯 PASS token、文件存在或 tensor shape 作为忠实实现证明。

### 决定语义

你只能返回：

```text
PASS_CONTINUE
REVISE_CONTINUE_CURRENT_GOAL
```

发现任何不合格项时必须返回 `REVISE_CONTINUE_CURRENT_GOAL`，并给出：

```text
finding_id
severity
contract_clause
source_path_or_evidence_path
function_or_field
expected
observed
reproducer_command
repair_scope
affected_training_credit
```

你不能返回 `OPERATIONALLY_BLOCKED`，不能要求用户确认，不能因 Dice、HD95、视觉质量、loss 平台或相对 nnU-Net/MoSAIC 的中途表现停止 Goal。低分只能在 W5 作为最终科学结果解释。

### 必须持续执行的轮次

#### R0：W1 早期 diff 审查

第一版行为实现出现后立即检查正式 wrapper 到 model/loss/sampler/scheduler/checkpoint/evaluator 的调用链。该轮可与 Executor 继续处理不相关文件并行，但 finding 必须在 G1 宣布 PASS 前关闭。

#### R1：G1 静态忠实性审查

必须独立检查：

- 正式 wrapper 是否调用新入口；
- 完整 stock 主干、anatomy path、scar/edema cloned top stages；
- 每个 anatomy/scar/edema/extent/context/relation/deep-supervision loss 是否进入真实 total loss；
- Stage A/B/C、10/5/5、CenterB/CenterC、focus cycle、hard-negative manifest 消费；
- AdamW 是否只创建一次，moments 是否跨阶段保留；
- warmup/poly LR、min LR、冻结参数 current LR；
- area reference 是否来自 fold actual-train；
- checkpoint 字段、fsync、atomic rename、SHA、full reload；
- 旧 wrapper、旧 trainer 和所有 known-bad 是否 fail closed。

R1 必须 `PASS_CONTINUE` 才能进入 G2。

#### R2：G2 真实 GPU 审查

在 `61794608` 或经验证的 htzhulab 替代资源上独立重跑关键检查：

- complete CenterB；
- complete CenterC；
- LGE-only；
- LGE+C0；
- small scar；
- step0 parity；
- 每项 loss 的有效梯度和无效人群精确零；
- no-T2 edema-exclusive gradient == 0；
- sampler composition；
- scheduler 边界及中间数值；
- area reference 重算；
- module-off final-logit/final-label；
- atomic save/reload；
- uninterrupted 与 resume 行为等价。

R2 必须 `PASS_CONTINUE` 才能进入 G2.5。

#### R3：G2.5 冻结训练源码审查

检查 reviewed candidate SHA 与即将 push 的 training-source SHA 完全相同；检查正式命令、Python、model/loss/sampler/scheduler/checkpoint/evaluator/validator SHA，split/plans/stock hash，以及 outer zero-access。

R3 必须 `PASS_CONTINUE` 且 local HEAD == origin/main 后，才允许启动正式训练。

#### R4：首个 2000-step chunk 审查

fold1/fold4 首个 chunk 完成后，异步检查源码/合同 hash、step、stage、scheduler、sampler cursor、next-batch hash、checkpoint schema/reload 和无 overlap/gap/duplicate。允许最多一个 chunk lookahead。

证据问题只修 evidence；行为问题必须通知 Controller 暂停未来 chunk、判定受影响 training credit，并返回 Executor 修复。该 finding 不允许终止 Goal。

#### R5：step10000 Stage C 转换审查

检查 Stage B→C 的参数解冻、完整模态 population、CenterB/CenterC 循环、optimizer moment 连续、scheduler 和 next-batch hash。

#### R6：W4/W4.5 冻结审查

检查两个 fold 都到 14000、完整 reload、全部状态字段、training-source 绑定、checkpoint SHA 和 outer zero-access。必须 `PASS_CONTINUE` 才能进入 W5。

#### R7：W5 指标真值审查

检查三模型同病例 join、scar denominator、T2-present edema denominator、no-T2 edema 完全排除、重复/缺失病例、help/harm、empty prediction、无穷 HD 计数和 physical metric binding。禁止 posthoc threshold、checkpoint 或病例选择。

#### R8：W6 终态审查

检查源码与 runtime lineage、所有 job 终态、聚合、Mapper/wiki、strict validators、科学 token、commit/push/SHA/notification 顺序。必须固定到 terminal candidate commit。

## Controller 的返修协议

Reviewer 返回 `REVISE_CONTINUE_CURRENT_GOAL` 后，Controller 必须：

```text
记录 finding 到 controller_ledger
-> 把精确 finding 交给同一个 Executor
-> Executor 修复
-> 重跑受影响的一方 Gate 和 known-bad
-> 创建新的 immutable candidate commit
-> 使旧 Reviewer token 失效
-> 同一 Reviewer 审查新 commit
-> 重复直到 PASS_CONTINUE
```

不得因为 reviewer 不合格就退出、返回 Planner、等待用户或降低合同。

训练开始后：

- 只改报告/evidence 且行为不变：保留训练 credit；
- 只修启动 wrapper 且 source/config/split/batch sequence hash 不变：经 Reviewer 和 Controller证明后可从最后有效 checkpoint 继续；
- 修改 model/loss/sampler/scheduler/checkpoint/decode 行为：受影响训练 credit 归零，返回 G1/G2/G2.5，并从 step0 重启受影响 fold，除非证明 bitwise behavioral equivalence。

Reviewer failure 的含义是“必须修复并继续”，不是“允许带错代码继续”，也不是“终止 Goal”。
