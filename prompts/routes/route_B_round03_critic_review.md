---
route_id: route_B
portfolio_round: round03
date: 2026-07-18
role: independent_planning_critic
status: PLANNING_NEEDS_REVISION
reviewed_branch: route_B
reviewed_commit: a282007ecab44274699ab49a389ba107ac04d5b2
route_head_at_binding_check: a282007ecab44274699ab49a389ba107ac04d5b2
route_head_match: true
handoff_path: prompts/routes/handoffs/route_B_round03_critic_handoff_20260718.md
handoff_blob_sha: cfe69bbd597d6cdd80f3b27bc42f577f8dce122a
contract_path: prompts/routes/route_B.md
expected_contract_blob_sha: 2d82b8bb5d05e521adb87281a663fd7fe38582c6
observed_contract_blob_sha: 2d82b8bb5d05e521adb87281a663fd7fe38582c6
contract_blob_match: true
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
expected_executor_plan_blob_sha: 83494fbf40df7b79c26c3be3c00d51e23830208c
observed_executor_plan_blob_sha: 83494fbf40df7b79c26c3be3c00d51e23830208c
executor_plan_blob_match: true
critic_request_path: prompts/routes/route_B_critic_request.md
expected_critic_request_blob_sha: 50fba61a5512e4ba7b124fd2355ca84c2a688ed8
observed_critic_request_blob_sha: 50fba61a5512e4ba7b124fd2355ca84c2a688ed8
critic_request_blob_match: true
planner_audit_path: prompts/routes/route_B_planner_audit.md
expected_planner_audit_blob_sha: 3a0d422ed81695f77750f59ebfdca38700c69516
observed_planner_audit_blob_sha: 3a0d422ed81695f77750f59ebfdca38700c69516
planner_audit_blob_match: true
deep_research_commit: 28c8aac80b7f18f3441c495dc9f2625fc10c460f
deep_research_blob_sha: 05f35a6843a0f14247cd40e5cfdd3a837c03c8d3
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_PROJECT_BACKGROUND_CURRENT_CONVERSATION
required_users_worktree_available: false
git_fetch_exit_code: 128
executor_plan_validator_exit_code: 1
pyyaml_executor_count_check_exit_code: 1
git_diff_check_exit_code: 1
partition_race_executable_check_status: UNAVAILABLE_REQUIRED_LOCAL_CHECK
remote_prompt_path_count: 11
remote_prompt_paths_all_exist: true
remote_scientific_contract_review: PASS_STATIC_CONTENT
remote_partition_race_review: PASS_STATIC_FIELDS_WITH_FINALIZER_GRAPH_BLOCKERS
decision_token: ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
controller_start_authorized: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
prompts_shared_modified: false
---

# Route B Round03 Independent Planning Critic Review

## 1. Scope and decision

本轮只进行了 Route B Round03 规划审查。没有实现代码、训练模型、提交或监控 Slurm、写 runtime `review.md`、启动 controller、创建或启动 tmux、准备 validation、晋级路线、启动 M11、跨路线合并或作出最终科学判断。

最终决定为：

`ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION`

该决定首先由 handoff 规定的 executable hard gate 强制产生：当前工具运行环境没有挂载 `/users/a/e/aereinh/CARE`，因此规定的真实仓库命令均未能在绑定 commit 上获得 exit `0`。此外，远端静态审查还发现三个独立的机器合同问题：B10 finalizer 不能覆盖中途科学失败、B10 引用了不存在且不在允许创建范围内的 mapper 脚本，以及规划文件中的 ancestry metadata 不一致。

## 2. Exact binding

在写入本审查文件前，远端 `route_B` 与绑定 commit 完全一致，ahead `0`、behind `0`。所有 handoff 指纹均匹配：

| binding | expected | observed | result |
| --- | --- | --- | --- |
| route head | `a282007ecab44274699ab49a389ba107ac04d5b2` | `a282007ecab44274699ab49a389ba107ac04d5b2` | MATCH |
| `route_B.md` blob | `2d82b8bb5d05e521adb87281a663fd7fe38582c6` | `2d82b8bb5d05e521adb87281a663fd7fe38582c6` | MATCH |
| executor-plan blob | `83494fbf40df7b79c26c3be3c00d51e23830208c` | `83494fbf40df7b79c26c3be3c00d51e23830208c` | MATCH |
| critic-request blob | `50fba61a5512e4ba7b124fd2355ca84c2a688ed8` | `50fba61a5512e4ba7b124fd2355ca84c2a688ed8` | MATCH |
| planner-audit blob | `3a0d422ed81695f77750f59ebfdca38700c69516` | `3a0d422ed81695f77750f59ebfdca38700c69516` | MATCH |

因此 handoff 本身不是 stale；本轮进入了实质审查。

## 3. Mandatory executable checks

实际执行结果如下。退出码均为真实 shell 退出码，不是根据远端内容推测：

```text
CHECK=git_fetch
git -C /users/a/e/aereinh/CARE fetch --all --prune
stderr: fatal: cannot change to '/users/a/e/aereinh/CARE': No such file or directory
EXIT=128

CHECK=executor_plan_validator
cd /users/a/e/aereinh/CARE && \
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python \
  scripts/ops/validate_executor_plan.py \
  prompts/routes/route_B_executor_plan.yaml
EXIT=1
reason: required worktree was unavailable before the validator could run

CHECK=pyyaml_executor_count
cd /users/a/e/aereinh/CARE && \
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python <required PyYAML script>
EXIT=1
reason: required worktree was unavailable before PyYAML could run

CHECK=git_diff_check
cd /users/a/e/aereinh/CARE && git diff --check
EXIT=1
reason: required worktree was unavailable before git diff could run

CHECK=required_users_path
test -d /users/a/e/aereinh/CARE
EXIT=1
```

这些结果不证明 executor plan 内容本身一定无效；它们证明本轮 Critic 无法满足 handoff 明确要求的“exact bound commit 上真实 exit `0`”。`CURRENT.md` 与 route handoff 都规定任何 nonzero 或 unavailable check 必须返回 planning revision，不能把验证推迟给 Controller。远端 GitHub 读取也不能确认本地是否存在未推送提交，因此本轮不能发 controller-ready token。

Critic-equivalent partition/race 检查只能进行远端人工静态检查，没有产生可接受的本地 executable exit code，状态为 `UNAVAILABLE_REQUIRED_LOCAL_CHECK`。

## 4. Required sources read

已读取 main 的治理和证据文件：

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/routes/README.md`
- `prompts/routes/route_portfolio_planner_prompt.md`
- `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`
- `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`
- `prompts/routes/handoffs/CURRENT.md`
- `prompts/routes/handoffs/route_B_round03_critic_handoff_20260718.md`
- `.agents/skills/slurm-routing-partition/SKILL.md`
- `.agents/skills/care-mapper/SKILL.md`
- `routes/README.md`
- `wiki/README.md`
- `wiki/history/ROUND02_SRR_EVIDENCE_AND_CONTROLLER_FORWARD_ANALYSIS_20260718.md`
- `docs/notes/deep_research/care_2026_myocardium_round02_targeted_deep_research_cleaned.md` at commit `28c8aac80b7f18f3441c495dc9f2625fc10c460f`
- `prompts/routes/route_B_round02_critic_review.md`

已读取精确 Route B revision 的：

- `prompts/routes/route_B.md`
- `prompts/routes/route_B_executor_plan.yaml`
- `prompts/routes/route_B_critic_request.md`
- `prompts/routes/route_B_planner_audit.md`
- B0–B10 的全部 executor prompts

## 5. Independent SRR visual review

SRR-v2、v2.5、v3 均从当前 Project/current-conversation visual channel 独立视觉读取，没有依赖 Planner 摘要或 GitHub PNG metadata。

- SRR-v2 定义 availability-aware modality evidence、shared/private/interaction retrieval、解剖引导的 scar/edema proposal、pathology-specific soft-ROI refinement，以及 reference-space Cine temporal path。
- SRR-v2.5 明确分离 scar 与 edema 的 proposal decoder、ROI 几何与 refiner。
- SRR-v3 引入 nnU-Net logits/components/uncertainty 作为 anchor/context、train/OOF prototypes，以及关闭 gate 时保持 anchor 的病种有界修正；Cine 必须在 ED/reference space 中消费配准后的多帧 anatomy/features/motion/uncertainty，再做 temporal retrieval 和 final-output aggregation。

Round03 的四尺度、十六 expert、two-pass spatial router 是对完整 v3 的合法精确化，而不是图中唯一可能的数字设定。

## 6. Scientific contract assessment

### 6.1 Static scientific review passed

远端静态内容没有把 Route B 降级成 Route A、nnU-Net-only、wrapper-only、postprocess-only、two-scale shortcut 或 validator-only。以下核心要求已经被具体冻结：

- canonical input order `[LGE,T2,C0]`；
- four scales `[32,64,128,256]`；
- 每尺度 16 个 shared/private/pairwise-interaction experts；
- pathology-specific two-pass spatial entmax routing 和 invalid-slot weight/gradient gate；
- 数值化 Pattern-SIP、style cluster、hard-group、loss coefficient 和 schedule；
- four-shard fold-safe OOF-fitted inference-frozen prototypes；
- bootstrap/online EMA formal memory 明确禁止；
- T2-present safe edema negatives 与 no-T2 exact-zero semantics；
- anatomy-guided conservative proposal 加 prototype similarity-difference evidence；
- scar/edema 分开的 proposal、soft ROI、refiner 与 boundary/negative-space objective；
- bounded pathology-specific final correction 和逐节点 final-output intervention；
- B2 real forward/gradient/intervention/save-reload gate 在长正式训练之前；
- staged MyoPS training、fresh selector、same-split help/harm 和 positive-edema coverage；
- official `mathpluscode/CineMA` commit/revision/license/weight SHA、真实 `ConvUNetR` decoder hook、logits/features/entropy；
- matched random source、common downstream initialization、parameter equality receipts；
- seven-step SVF scaling-and-squaring、true Jacobian/inverse-composition 和 real ANTs `SyNOnly`；
- temporal interface 显式消费 registered logits/features/uncertainty、velocity、integrated displacement、Jacobian、motion、quality、temporal position 和 valid mask；
- cumulative resume、atomic checkpoint、zero-credit partial/timeout/preemption；
- semantic known-bad classes、route-local mapper/fingerprint receipts 和 independent reviewer tokens。

这与 Round02 历史分析和 Deep Research 的主张一致：proposal/refiner 不是另一个 dense-head 名称，prototype 不是 bootstrap/EMA helper，CineMA 不是 CARE 小卷积 wrapper，registration 不是 direct-velocity proxy，temporal 不是抽象 `temporal_z`。

### 6.2 Remote partition/race field review largely passed

B2–B10 的静态声明覆盖：

- `htzhulab`、`a100-gpu`、`volta-gpu`；
- 每分区 compatibility、reason、preflight command、preflight receipt；
- V100 不兼容阶段的独立 compatible alternative work；
- 禁止 V100 semantic downscaling；
- identical scientific hashes；
- isolated output/log/checkpoint/cache roots；
- shared atomic winner lock；
- loser zero credit；
- pending-loser cancellation；
- retry lineage；
- all-attempt finalizer coverage 声明。

B0–B10 的 11 个 prompt 路径也均远端存在，executor IDs 与 plan 一致：

| executor | prompt blob |
| --- | --- |
| B0 | `c0e85366584be7a0d1b1e27d22727069466b54d2` |
| B1 | `09cfe10689410716717416b5337a473799ddfa77` |
| B2 | `a4adb0729a78dfe3da497c84a5d21a4562e7504e` |
| B3 | `c040ec2ba8dcaf7d9e7b5b71f7bc21dbedcd58c4` |
| B4 | `81d5e23a060527e0033c2798d8e642f2a8d962a3` |
| B5 | `96e2edecaffcf2a5df74ea59ebf86d6f3a7ec609` |
| B6 | `0f105d4cb53a198e99132750c52df616434b5e21` |
| B7 | `f298243722d1a36ea97677252e457241b2d308cf` |
| B8 | `e0a09f31d215c3b5a8301cee567e8b11d772b19a` |
| B9 | `564f4ca0370c5f291b0af87d4a81c58bde0752cc` |
| B10 | `ad493738e2a664d076ca41d703a0fddf3a8baefb` |

远端人工检查不能替代 handoff 所要求的实际 validator exit code。

## 7. Independent planning blockers

### 7.1 Mandatory executable validation is unavailable

这是直接 hard gate。需要在挂载了 exact `/users/a/e/aereinh/CARE` worktree 的 Critic/coordinator 环境重新运行：

1. `git fetch --all --prune`；
2. executor-plan validator；
3. PyYAML parse 并断言 11 executors；
4. `git diff --check`；
5. executable partition/race checker。

所有命令必须绑定当前 route head 和五个 blobs，且均返回 exit `0`。远端人工检查或 Planner sandbox mirror 不能替代。

### 7.2 Finalizer dependency graph does not guarantee all-attempt coverage

Executor plan 的 B10 只声明：

```text
depends_on: [B9_TEMPORAL_AND_CINE_EVIDENCE]
```

但同一计划又允许：

- B4 OOF/proposal gate failure 时停止在 B5 之前；
- B5 refiner scientific gate failure 时阻断 B6；
- B8 faithful registration adequate-negative 时阻断 temporal B9；
- 其他 implementation/scientific failures 返回更早 phase 或形成 reviewable negative evidence。

这些路径中 B9 不会完成，因此 B10 无法按当前 DAG 正常满足依赖。虽然各 executor 重复声明 `all_attempt_finalizer_coverage_required: true`，声明不能覆盖缺失的控制流。`afterany` 也只能作用于已经提交并捕获的 job IDs，不能自动绕过未满足的 B9 executor dependency。

Required revision：增加独立于科学 success chain 的 controller-level finalizer registration，或为每个 terminal non-ready branch 提供明确转移到 B10/terminal finalizer 的边；B10 必须能在任何已启动 attempt 的成功、失败、timeout、preemption、adequate-negative 或 early scientific gate failure 后运行 terminal accounting、aggregation、mapper/validator 和 packet classification。

### 7.3 B10 references a nonexistent mapper command

B10 的 `mapper-final-command` 是：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python \
  scripts/architecture/care_mapper.py --route route_B --final
```

在精确 reviewed commit 中，`scripts/architecture/care_mapper.py` 不存在。仓库搜索也未找到该文件。B0/B1 的 write scopes 只能创建 `scripts/route_B_round03/**` 等 route-local 文件，shared source edits 明确禁止，因此 Controller 不能合法地在运行时补建这个 shared architecture script。

Required revision：绑定一个当前已存在且可执行的 mapper entrypoint，或将 route-local mapper entrypoint 的创建、路径、命令、schema 和 validator 明确加入 B0/B1 write scope。发现需要新的 shared mapper script 必须重新进行 Planner/Critic scope review。

### 7.4 Planning ancestry metadata is internally inconsistent

绑定 blobs 虽然匹配 handoff，但其内部 provenance 字段不一致：

- `route_B.md`：`remote_route_base_commit=f01427e...`，`planner_main_base_commit=6ed0a3b...`；
- executor plan：`remote_route_base_commit=4c2f2ec...`，`planner_main_base_commit=f15cbcf...`；
- critic request / planner audit：`planner_main_base_commit=f15cbcf...`，audit 的 route base 为 `4c2f2ec...`。

Round03 永久矩阵要求 route contract、executor plan、critic request 和 audit 机器绑定且不能保留 stale ancestry。CURRENT 的最终 blob binding 不能自动解释这些互相冲突的来源字段。

Required revision：将四份规划文件统一到同一个真实 Planner main base 和同一个 pre-planning Route B base，或删除不再作为 machine truth 的 stale ancestry 字段并以 CURRENT-bound final head/blob set 为唯一 provenance；随后重新生成 blobs 和 current critic handoff。

## 8. Required next action

由具有 `/users/a/e/aereinh/CARE` 挂载和可执行权限的 Planner/coordinator：

1. 修正 B10 all-terminal finalizer DAG；
2. 修正 mapper entrypoint；
3. 统一 ancestry metadata；
4. 推送新的 Route B revision；
5. 更新 main `CURRENT.md` 与新的 Route B Critic handoff，重新绑定 head 和 blobs；
6. 在 exact revision 上运行所有 mandatory executable checks 并保留真实 exit codes；
7. 再启动新的 independent Planning Critic。

本轮没有授权 Route B Controller。规划内容静态科学方向可保留，但当前 revision 不能进入执行。

## 9. Authority boundary

本审查只写入当前 Critic 文件。没有修改 Route B contract、executor plan、implementation source、runtime packet、shared prompts、root wiki、Route A/C 或 validation 文件。

`ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION`

该 token 不授权代码实现、训练、Slurm、controller/tmux、validation packaging/upload、route promotion、M11、cross-route merge、hosted metric claim 或 final scientific decision。
