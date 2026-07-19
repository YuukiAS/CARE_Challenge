---
route_id: route_B
portfolio_round: round04
date: 2026-07-19
role: independent_planning_critic_rereview
status: PLANNING_NEEDS_REVISION
reviewed_main_commit: 6c8d6f26ed4907ee59023795265ee4e1c53fb2b8
planning_commit: 755e5919d472e3033c23ff7a848cac618aca1d34
planning_parent_main: 30098813522cecd98e60bcb99e2676b28c1a5461
reviewed_route_B_evidence_commit: b9c7664da7cb1f1892fff37a4497722f31a0a96d
route_C_context_commit: 17062b00edc3443aacefe8583568797a9f2655ba
route_C_reviewed_controller_commit: 1e663cfa64f00413f005bef26310290fd43ec8ab
handoff_blob: 9223849b7ca1aa22e6b9af036178628d4b6caec1
coordinator_receipt_blob: e5d9a479db918a63fcdf8fd56e6106629ab1199b
planner_plan_blob: e6e31f772e2766ec79c466660fe8f56f14350d6f
planner_prompt_blob: 030c4ae0cb97bae1d661b40786bf3d7be78d930d
controller_contract_blob: fdb74c49634ba02a30b96979f185bd71fcf085c4
executor_plan_blob: 505b3a64d83b3d17cbc28ea7c0837d098665f821
critic_request_blob: 9911593bef8d8381e0df620bf22ca8c759e24186
planner_audit_blob: 6a9881f3eba630ec51ffed2b9ecb0ca0367262ed
all_bound_blobs_match: true
current_main_allowed_descendant: true
coordinator_receipt_status_pass: true
coordinator_all_required_exit_codes_zero: true
coordinator_working_tree_clean: true
critic_local_users_worktree_available: false
critic_local_fetch_exit_code: 1
critic_used_bound_coordinator_receipt: true
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_CURRENT_CONVERSATION_PROJECT_MATERIALS
scientific_contract_preserved: true
b3_stage_interpretation_pass: true
b4_b5_b6_progression_pass: true
b7_b8_b9_mandatory_cine_lane_pass: true
b10_terminal_accounting_structure_pass: true
per_executor_validator_structure_pass: true
slurm_hardening_pass: true
hard_blockers:
  - CONTROLLER_ROUTE_B_WORKTREE_LACKS_BOUND_PLANNING_FILES_AND_HAS_NO_MATERIALIZATION_CONTRACT
  - B0_EXACT_INPUT_BINDS_OLD_CRITIC_REVIEW_INSTEAD_OF_CURRENT_REREVIEW
  - COORDINATOR_RECEIPT_ANCESTOR_POLICY_CONTRADICTS_CONTROLLER_ENTRY_GATE
controller_start_authorized: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
---

# Route B Round04 Independent Planning Critic Rereview

## 1. Scope and binding

本轮只做 Route B Round04 规划复审。没有实现代码、运行模型、训练、提交或监控 Slurm、启动 Controller/tmux、写 runtime `review.md`、准备或上传 validation、路线晋级、启动 M11、主张 hosted metric、跨路线合并或作出最终科学决定。

远端精确绑定通过：

- `origin/main` 等于 `6c8d6f26ed4907ee59023795265ee4e1c53fb2b8`；
- `origin/route_B` 等于 `b9c7664da7cb1f1892fff37a4497722f31a0a96d`；
- `origin/route_C` 等于 `17062b00edc3443aacefe8583568797a9f2655ba`；
- handoff blob、coordinator receipt blob 和六个 planning blobs 全部 byte-identical。

当前 main 是 planning commit `755e5919d472e3033c23ff7a848cac618aca1d34` 的后继。后继修改仅涉及 CURRENT/handoff/receipt、watchboard/notifier 和 Round03 architecture documentation 等已声明 administrative/observability 路径；六个 planning blobs 没有变化，因此 handoff 本身不 stale。

## 2. Coordinator executable receipt

本 ChatGPT runtime 没有挂载 `/users/a/e/aereinh/CARE`。实际本地尝试结果为：

```text
git fetch attempt exit: 1
git status exit after missing cwd: 128
git rev-parse exit after missing cwd: 128
```

当前 handoff 明确允许复审者核对绑定的 Codex coordinator receipt。该 receipt 满足：

```text
status: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
working_tree_clean: true
all_required_exit_codes_zero: true
completion_token: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
```

Receipt 记录的全部要求均为 exit `0`：fetch、branch/status、refs、executor-plan validator、PyYAML/B10/validator-binding assertions、`git diff --check`、空白授权扫描、禁止工作区扫描、正式解释器扫描、Cine 非延期扫描和 clean-tree 检查。

Receipt 测试 commit `aea169e65e19c674b8c6cdba74fc1cab7a07713f` 是当前 main 的祖先；其后的差异只包含 handoff/receipt/CURRENT、watchboard 和允许的 ops 路径，符合 current handoff 的 ancestor allowance。此 receipt 足以关闭上一轮“没有 `/users` exit-zero 收据”的 blocker。

## 3. Visual and scientific rereview

SRR-v2、SRR-v2.5 和 SRR-v3 已从当前对话提供的视觉材料独立读取。恢复出的 Route B 不变量是：

```text
observed [LGE,T2,C0] with explicit availability
-> four-scale modality-specific encoding
-> shared/private/interaction retrieval
-> Pattern-SIP and fold-safe OOF prototype evidence
-> anatomy-guided scar and edema proposals
-> pathology-specific soft ROI and separate refiners
-> bounded final correction over nnU-Net anchor/context/safety evidence
-> official-label reconstruction and real final-output interventions
```

Cine 不变量是：

```text
official CineMA logits/features/probabilities/uncertainty
-> ED/reference and fixed key frames
-> seven-step SVF plus independently produced real SyN
-> registered anatomy/features/motion/Jacobian/quality evidence
-> registered temporal aggregation
-> same-case controls and ED-space final-output interventions
```

修订后的科学合同通过，不存在 Route A、nnU-Net-only、postprocess-only、wrapper-only、validator-only、two-scale 或 single-frame proxy 降级。以下要求均保留并数值化：

- 四尺度 `[32,64,128,256]`；
- canonical `[LGE,T2,C0]` 与 explicit availability；
- 每尺度 sixteen shared/private/interaction experts；
- spatial/pathology-conditioned two-pass entmax routing；
- optimized Pattern-SIP；
- four-shard fold-safe OOF-fitted inference-frozen prototype banks；
- training-only safe hard-negative queues 和 no-T2 edema exclusion；
- scar/edema 分开的 proposal、soft ROI 和 refiner；
- bounded correction 与 same-checkpoint final-output interventions；
- same-split nnU-Net baseline、case-wise help/harm 和困难子组；
- official CineMA provenance 与 architecture-matched random control；
- seven-step scaling-and-squaring、true Jacobian、inverse consistency 和 real SyN；
- registered temporal aggregation 与完整 controls；
- fixed training budgets 和 selected-checkpoint clean reload。

## 4. Round03 interpretation and stage progression

Round03 Reviewer token只支持旧 B3 evidence-warmup gate 的 adequate negative：B3 达到 `43003` optimizer steps、`1800.7964860140346` 秒和 `22` 次 validation，sampler、finite loss、loss decrease、invalid-slot zero 和 no-T2 zero 通过，但 `anatomy_union_overfit=false`。B4–B9 没有执行。

修订后的 progression 正确：

- B1 保留严格 anatomy target/optimization micro-overfit implementation gate；
- B3 只能做 representation readiness，不能成为 full-route stop；
- valid B3 必须进入 B4；
- valid weak B4 通过 conservative-ROI control 进入 B5；
- faithful weak B5 必须进入 B6；
- B6 是第一个 MyoPS full-route judgment；
- B7/B8/B9 在 B2 后仍为 mandatory Cine lane，不因 B3 或 Route C completion 消失。

Route C 只作为 portfolio context。其 reviewed controller repair 和 `EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION` 状态已核对；本轮未给 Route C 写任何任务。

## 5. Previously reported mechanical blockers

上一轮四项 blocker 的修订状态如下：

### 5.1 CURRENT Round04 binding: closed

`CURRENT.md` 已进入 Round04，绑定 planning commit、Route B evidence、六个 blobs、current critic handoff、coordinator receipt、rereview output path、允许 token 和 authority boundary。

### 5.2 B10 early-terminal reachability: structurally closed

Executor plan 中 B10 已变为 controller-level terminal finalizer：

```text
depends_on: []
controller_terminal_finalizer: true
launch_owner: controller
prepare_wave_helper_exempt: true
depends_on_successful_merge_receipts: false
finalizer_dependency_policy: afterany_all_started_attempts
no_started_attempt_backend: local_deterministic
```

`terminal_finalizer_contract` 和 B10 known-bad matrix覆盖 B1 failure、B2 external blocker、B7 blocker、B8 registration blocker without B9、timeout、preemption、failed startup、cancelled/started race loser 和 successful B6/B9。该部分不再依赖 B6/B9 成功 merge receipt。

### 5.3 Per-executor validators: closed

B0–B10 每个 executor 均有 exact machine-readable：

```text
validator.script_path
validator.command
validator.input_path
validator.report_file
validator.expected_exit_code: 0
validator.success_token
known_bad_contract.matrix_path
known_bad_contract.matrix_command
known_bad_contract.report_file
known_bad_contract.runner_expected_exit_code: 0
known_bad_contract.validator_expected_exit_code_per_fixture: 1
known_bad_contract.expected_failure_keys
known_bad_contract.all_keys_required: true
known_bad_contract.unexpected_pass_is_failure: true
```

所有正式 validator/known-bad 命令使用 `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`。Failure keys覆盖 nnU-Net bypass、B3 premature stop、OOF leakage、unsafe no-T2 negatives、proposal/refiner disconnect、fake CineMA、unmatched random control、proxy registration、temporal fallback、monitor-as-completion、uncovered finalizer branches 和 authority violation。

### 5.4 Coordinator executable receipt: closed

绑定 receipt 的 required commands 和 exits 全部为 `0`，working tree clean，六个 blob hashes匹配。

## 6. Remaining controller-forward blockers

尽管前述四项旧 blocker 已关闭，当前规划仍有三个互相相关的启动级机械冲突。

### 6.1 Bound planning files do not exist in the required Route B Controller worktree

Controller contract要求未来 Controller：

```text
current branch == route_B
worktree == /users/a/e/aereinh/CARE_worktrees/route_B
```

Executor plan也声明：

```text
branch: route_B
B10 worktree_path: /users/a/e/aereinh/CARE_worktrees/route_B
```

但六个 bound Round04 planning 文件仅存在于 main。对精确 `origin/route_B=b9c7664da7cb1f1892fff37a4497722f31a0a96d` 读取：

```text
prompts/routes/route_B_round04_controller_contract.md -> 404 Not Found
```

B0 的 `prompt_path` 和 `exact_command` 又使用 route_B worktree 内的相对路径：

```text
prompt_path: prompts/routes/route_B_round04_controller_contract.md
--contract prompts/routes/route_B_round04_controller_contract.md
```

当前合同没有定义以下任何一种机械 bootstrap：

- 从 exact planning commit 通过 `git show <commit>:<path>` 读取并校验六个文件；
- 将六个文件 materialize 到一个 route-local immutable/read-only input directory；
- 在不改变 Route B scientific branch 的前提下，将 exact planning snapshot 合法带入 Route B worktree；
- 将 absolute main-worktree input paths及其 clean/hash requirements写入 B0。

因此，future Controller 按合同切到 `route_B` 后，不能从声明路径读取自己的 controller contract/executor plan，B0 exact command也不能使用声明的 contract path。这是 controller-start hard failure。

Required Planner repair：选择并机器绑定一种 exact bootstrap。建议新增 `controller_planning_materialization` contract，固定 source commit、六个 blob、critic rereview blob、materialization command、目标只读路径、hash validator、clean-tree语义和失败 token；或者把 exact planning snapshot发布到 Route B branch并重新绑定。不能让 Controller自行选择复制、cherry-pick或读取方式。

### 6.2 B0 exact inputs bind the superseded critic review

Executor plan 的 B0 `exact_inputs` 当前包含：

```text
prompts/routes/route_B_round04_critic_review.md
```

这是上一轮 `PLANNING_NEEDS_REVISION` 文件。B0没有包含当前要求的：

```text
prompts/routes/route_B_round04_critic_rereview.md
```

也没有把 current handoff和coordinator receipt列为 B0 exact inputs。即使未来存在正向 rereview，B0仍会冻结旧 negative review而不是当前授权来源。

Required Planner repair：B0 exact inputs必须删除或明确标注 superseded old review，并绑定 current rereview、current handoff、coordinator receipt及其 blob/commit。B0 `STALE_PLANNING_BINDING` known-bad应验证这些 exact inputs。

### 6.3 Receipt ancestor policy contradicts the frozen controller entry gate

Current `CURRENT.md` 和 critic handoff明确允许：coordinator receipt测试一个 ancestor，只要后继差异限于声明的 receipt/handoff/docs/ops路径，且六个 planning blobs不变。这也是当前 receipt能够通过复审的依据。

但六个 frozen planning files仍包含严格 equality规则：

- `prompts/routes/route_B_round04_controller_contract.md` 要求 `coordinator tested commit == current origin/main`；
- `prompts/routes/route_B_round04_critic_request.md` 要求 receipt测试 current `origin/main`，否则拒绝。

当前 receipt测试 `aea169e65e19c674b8c6cdba74fc1cab7a07713f`，当前 main为 `6c8d6f26ed4907ee59023795265ee4e1c53fb2b8`。写入本 rereview 后 main还会再前进一个 review commit。按 frozen controller contract 的 literal equality，未来 Controller会在任何 code/Slurm前返回 stale，即使 handoff明确允许该祖先关系。

Required Planner repair：将 controller contract和critic request统一为 CURRENT/handoff 的 exact ancestor policy，机器绑定允许路径、ancestor check、six-blob equality和forbidden planning-file changes；或者在不产生自引用矛盾的外部 immutable receipt机制中测试最终 controller target。不能同时保留“receipt commit之后允许 administrative descendants”和“必须等于当前 main”两套互斥规则。

## 7. Slurm, continuity and authority review

Slurm科学语义通过：

- `htzhulab` default；
- materially long compatible wait必须 isolated `htzhulab+a100-gpu` race；
- identical scientific hashes、isolated output/log/checkpoint/cache roots、atomic winner lock、pending-loser cancellation、loser zero credit和all-attempt accounting；
- `volta-gpu`仅在 unchanged configuration 且 measured peak memory `<=14.5 GiB`时记 credit；
- training dependencies为 `afterok`，terminal accounting为 `afterany`；
- submitted、pending、running、awaiting-accounting、monitor、undertrained、timeout、preemption和partial均不是 completion；
- Controller必须作为 Codex goal/goal resume持续负责到 terminal accounting、aggregation、mapper final、packet commit和reviewer handoff。

所有下游权限保持禁止。

## 8. Required next revision

Planner需要修改并重新绑定六个 planning files，至少完成：

1. 为 main planning snapshot进入 Route B Controller worktree定义不可变、可验证、无需Controller决策的 bootstrap/materialization；
2. 将 B0 `exact_inputs` 从旧 critic review改为 current rereview + handoff + coordinator receipt；
3. 统一 CURRENT/handoff/receipt与controller contract/critic request的 receipt-ancestor规则；
4. 重新生成六个 blob、planning commit、CURRENT/handoff和coordinator exit-zero receipt；
5. 再请求独立 planning critic。

本轮不授权 Controller启动。

ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION