---
route_id: route_B
portfolio_round: round04
date: 2026-07-19
role: independent_planning_critic_rereview
status: PLANNING_NEEDS_REVISION
requested_main_commit: 6c8d6f26ed4907ee59023795265ee4e1c53fb2b8
initial_main_target_match: true
post_write_origin_main_observed: b312cef72ec37c0e06686e2dc783dafd12060713
post_write_main_target_match: false
post_write_disallowed_descendant_path: prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md
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
all_bound_planning_blobs_match: true
coordinator_receipt_status_pass: true
coordinator_all_required_exit_codes_zero: true
coordinator_working_tree_clean: true
critic_local_users_worktree_available: false
critic_local_fetch_exit_code: 1
critic_used_bound_coordinator_receipt: true
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_CURRENT_CONVERSATION_PROJECT_MATERIALS
scientific_contract_preserved: true
round03_b3_only_interpretation_pass: true
b4_b5_b6_progression_pass: true
b7_b8_b9_mandatory_cine_lane_pass: true
b10_terminal_accounting_structure_pass: true
per_executor_validator_structure_pass: true
slurm_hardening_pass: true
hard_blockers:
  - CONCURRENT_MAIN_MOVEMENT_OUTSIDE_HANDOFF_ALLOWLIST
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

## 1. Scope

本轮只做 Route B Round04 规划复审。没有实现代码、运行模型、训练、提交或监控 Slurm、启动 Controller/tmux、写 runtime `review.md`、准备或上传 validation、路线晋级、启动 M11、主张 hosted metric、跨路线合并或作出最终科学决定。

## 2. Initial exact binding and coordinator receipt

首次写入前，远端绑定满足用户给定目标：

```text
origin/main:    6c8d6f26ed4907ee59023795265ee4e1c53fb2b8
origin/route_B: b9c7664da7cb1f1892fff37a4497722f31a0a96d
origin/route_C: 17062b00edc3443aacefe8583568797a9f2655ba
```

Handoff、coordinator receipt及六个 planning blob全部 byte-identical。六个 planning blobs为：

```text
planner plan:       e6e31f772e2766ec79c466660fe8f56f14350d6f
planner prompt:     030c4ae0cb97bae1d661b40786bf3d7be78d930d
controller contract:fdb74c49634ba02a30b96979f185bd71fcf085c4
executor plan:      505b3a64d83b3d17cbc28ea7c0837d098665f821
critic request:     9911593bef8d8381e0df620bf22ca8c759e24186
planner audit:      6a9881f3eba630ec51ffed2b9ecb0ca0367262ed
```

本 ChatGPT runtime 未挂载 `/users/a/e/aereinh/CARE`，本地 fetch尝试 exit `1`，随后 status/rev-parse exit `128`。Current handoff明确允许独立 Critic核对绑定 coordinator receipt。Receipt blob `e5d9a479db918a63fcdf8fd56e6106629ab1199b`满足：

```text
status: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
working_tree_clean: true
all_required_exit_codes_zero: true
completion_token: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
```

Receipt记录 fetch、branch/status、refs、executor-plan validator、PyYAML结构/B10/validator-binding assertions、`git diff --check`、空白授权、禁止工作区、正式解释器、Cine non-deferral和clean-tree检查全部 exit `0`。

## 3. Concurrent main movement after the final pre-write check

在最终 pre-write compare 时，`origin/main`仍精确等于要求的 `6c8d6f26ed4907ee59023795265ee4e1c53fb2b8`。写入本 rereview 后重新比较发现 main 同时新增：

```text
prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md
```

该文件不是本 Critic写入，不属于 handoff声明允许的以下 descendant classes：

```text
CURRENT/handoff/coordinator receipt
docs/figures/round03_route_architecture/*
controller_notifications/*
watchboard scripts/tests
```

因此，写入后的 origin/main不再等于用户给定 target，并且相对 planning commit包含一个未列入 allowlist的 Route C planning文件。即使六个 Route B planning blobs仍未改变，当前 handoff的“仅声明非规划 administrative/observability descendant”条件已经不满足。

这是独立 stale-parent blocker。Planner必须读取该并发 Route C文件，决定它是否应加入新的 portfolio binding；随后重新发布 CURRENT/handoff并重新取得 coordinator receipt。不能由 Route B Critic自行把一个新的 portfolio planning文件归类为纯 administrative change。

## 4. Visual and scientific rereview

SRR-v2、SRR-v2.5和SRR-v3已从当前对话视觉材料独立读取。完整 Route B目标仍为：

```text
observed [LGE,T2,C0] with explicit availability
-> four-scale modality-specific encoding
-> shared/private/interaction retrieval
-> optimized Pattern-SIP and fold-safe OOF prototypes
-> anatomy-guided scar and edema proposals with safe hard negatives
-> pathology-specific soft ROI and separate refiners
-> bounded final correction over nnU-Net anchor/context/safety evidence
-> official-label reconstruction and real final-output interventions
```

Cine目标仍为：

```text
official CineMA logits/features/probabilities/uncertainty
-> ED/reference and fixed key frames
-> seven-step SVF plus independently produced real SyN
-> registered anatomy/features/motion/Jacobian/quality evidence
-> registered temporal aggregation and same-case controls
```

科学合同通过，没有 Route A、nnU-Net-only、postprocess-only、wrapper-only、validator-only、two-scale或single-frame proxy降级。以下要求均保留：

- four scales `[32,64,128,256]`；
- canonical `[LGE,T2,C0]`和explicit availability；
- sixteen shared/private/interaction experts per scale；
- spatial/pathology-conditioned two-pass routing；
- optimized Pattern-SIP；
- four-shard fold-safe OOF-fitted inference-frozen banks；
- safe hard-negative queues和no-T2 edema exclusion；
- separate scar/edema proposal、soft ROI和refiner；
- bounded correction与真实final-output intervention；
- same-split nnU-Net baseline、case-wise help/harm和困难子组；
- official CineMA provenance和matched-random control；
- seven-step SVF、true Jacobian、inverse consistency和real SyN；
- registered temporal aggregation与完整controls；
- fixed budgets和selected-checkpoint clean reload。

## 5. Round03 interpretation and mandatory continuation

Round03 Reviewer token只支持旧B3 gate的adequate negative。B3达到`43003` steps、`1800.7964860140346`秒和`22`次validation，sampler、finite loss、loss decrease、invalid-slot zero和no-T2 zero通过，但`anatomy_union_overfit=false`；B4–B9没有执行。

修订后的stage语义正确：

- B3只能是representation readiness，不能full-route stop；
- valid B3必须进入B4；
- valid weak B4必须通过conservative-ROI control进入B5；
- faithful weak B5必须进入B6；
- B6是第一个MyoPS full-route judgment；
- B7/B8/B9在B2后仍mandatory，不因B3或Route C completion消失。

Route C只作为context；本轮没有给Route C写critic/reviewer/controller任务。

## 6. Previous mechanical blockers now closed

上一轮四项 blocker 中，以下内容已经被正确修复：

1. CURRENT已进入Round04并绑定handoff、receipt、六个blobs和rereview path。
2. B10已成为controller-level terminal finalizer，`depends_on: []`，不依赖B6/B9成功merge receipt，使用controller registry/ledger和all-attempt `afterany`。
3. B0–B10均机器绑定exact strict validator、known-bad matrix、expected validator exit `1`和exact failure keys。
4. Coordinator receipt记录最终检查全部exit `0`和clean tree。

B10 static scenarios覆盖B1 failure、B2 external blocker、B7 blocker、B8 registration blocker without B9、timeout、preemption、failed startup、cancelled/started race loser和successful B6/B9。

## 7. Remaining controller-forward blockers

### 7.1 Route B worktree lacks the bound planning files

Future Controller被要求运行于：

```text
branch: route_B
worktree: /users/a/e/aereinh/CARE_worktrees/route_B
```

但精确`origin/route_B=b9c7664da7cb1f1892fff37a4497722f31a0a96d`中：

```text
prompts/routes/route_B_round04_controller_contract.md -> 404 Not Found
```

六个planning文件只在main。B0却声明：

```text
prompt_path: prompts/routes/route_B_round04_controller_contract.md
exact command argument: --contract prompts/routes/route_B_round04_controller_contract.md
```

Plan没有定义从exact planning commit使用`git show`读取、materialize只读snapshot、使用absolute main input，或将planning snapshot合法发布到route_B的机械步骤。因此Controller切到route_B后无法从声明路径读取contract/executor plan，B0 exact command也无法使用声明的contract path。

Required repair：新增机器可解析的`controller_planning_materialization`合同，固定source commit、六个blobs、critic rereview blob、materialization command、read-only target、hash validator、clean-tree规则和failure token；或者将exact planning snapshot发布到route_B并重新绑定。不得让Controller自行决定复制/cherry-pick/读取方式。

### 7.2 B0 exact inputs bind the superseded critic review

`prompts/routes/route_B_round04_executor_plan.yaml`的B0 `exact_inputs`仍包含：

```text
prompts/routes/route_B_round04_critic_review.md
```

这是上一轮negative planning review。B0没有包含当前`prompts/routes/route_B_round04_critic_rereview.md`，也没有把current handoff和coordinator receipt列为exact inputs。

Required repair：B0必须将old review标记为superseded historical input，机器绑定current rereview、current handoff、coordinator receipt及其blob/commit，并在`STALE_PLANNING_BINDING` known-bad中验证。

### 7.3 Receipt ancestor policy contradicts frozen controller entry rules

CURRENT和handoff允许coordinator receipt测试一个ancestor，只要后继差异限于声明路径且六个planning blobs不变。但六个frozen planning files仍要求strict equality：

- controller contract要求`coordinator tested commit == current origin/main`；
- critic request要求receipt测试current `origin/main`，否则拒绝。

Receipt测试`aea169e65e19c674b8c6cdba74fc1cab7a07713f`；initial target main为`6c8d6f26ed4907ee59023795265ee4e1c53fb2b8`，写入review后main还会继续前进。按controller contract literal equality，future Controller会在任何code/Slurm前判stale，即使handoff明确允许祖先关系。

Required repair：把controller contract和critic request统一为CURRENT/handoff的ancestor+allowlist+six-blob policy，或采用不会产生self-reference矛盾的外部immutable receipt。不能保留两套互斥规则。

## 8. Slurm, continuity and authority

Slurm合同本身通过：

- `htzhulab` default；
- long compatible wait使用isolated `htzhulab+a100-gpu` race；
- identical scientific hashes、isolated roots、atomic winner lock、pending-loser cancellation、loser zero credit和all-attempt accounting；
- V100仅在unchanged config且peak memory `<=14.5 GiB`时记credit；
- training dependency为`afterok`，finalizer为`afterany`；
- pending/submitted/running/awaiting-accounting/monitor/undertrained/timeout/preemption/partial都不是completion；
- Controller必须作为Codex goal/goal resume持续到accounting、aggregation、mapper final、packet commit和reviewer handoff。

本轮不授权Controller、validation upload、route promotion、M11、hosted metric claim、cross-route merge或final scientific decision。

## 9. Required planner revision

Planner必须：

1. 处理并重新绑定写入期间出现的`prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md`并发main变动；
2. 为main planning snapshot进入route_B Controller worktree定义immutable、hash-verified bootstrap/materialization；
3. 将B0 exact inputs切换到current rereview + handoff + coordinator receipt；
4. 统一receipt ancestor规则；
5. 重新生成六个blobs、planning commit、CURRENT/handoff和coordinator exit-zero receipt；
6. 再请求独立planning critic。

ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION