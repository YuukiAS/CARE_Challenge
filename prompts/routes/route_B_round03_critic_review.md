---
route_id: route_B
portfolio_round: round03
date: 2026-07-18
role: independent_planning_critic
status: PLANNING_READY_FOR_CONTROLLER
reviewed_branch: route_B
reviewed_commit: 11d5c3d90028fa19ccd1c709d9ce5d4e90f5b96f
route_head_at_binding_check: 11d5c3d90028fa19ccd1c709d9ce5d4e90f5b96f
route_head_match: true
handoff_path: prompts/routes/handoffs/route_B_round03_critic_handoff_20260718.md
handoff_blob_sha: e444320bdb6bb04007a937d5728892f7b5ce9d08
contract_path: prompts/routes/route_B.md
expected_contract_blob_sha: 1d58d7a37eacaee8cc15c159758e5074e794de8b
observed_contract_blob_sha: 1d58d7a37eacaee8cc15c159758e5074e794de8b
contract_blob_match: true
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
expected_executor_plan_blob_sha: 082e2641d8fdf693e929d1aa460ae689b80ce0d2
observed_executor_plan_blob_sha: 082e2641d8fdf693e929d1aa460ae689b80ce0d2
executor_plan_blob_match: true
critic_request_path: prompts/routes/route_B_critic_request.md
expected_critic_request_blob_sha: a1b03b7366df14bf9ca9628b309ced55dbf6db47
observed_critic_request_blob_sha: a1b03b7366df14bf9ca9628b309ced55dbf6db47
critic_request_blob_match: true
planner_audit_path: prompts/routes/route_B_planner_audit.md
expected_planner_audit_blob_sha: 5f8764c08908e725830817d42ed3dc606971cda9
observed_planner_audit_blob_sha: 5f8764c08908e725830817d42ed3dc606971cda9
planner_audit_blob_match: true
b10_prompt_path: prompts/routes/executors/route_B_round03/B10_finalize_validate_review_request.md
expected_b10_prompt_blob_sha: ad48d04aeac2a69fb99d41ec4fa73d159138d269
observed_b10_prompt_blob_sha: ad48d04aeac2a69fb99d41ec4fa73d159138d269
b10_prompt_blob_match: true
deep_research_commit: 28c8aac80b7f18f3441c495dc9f2625fc10c460f
deep_research_blob_sha: 05f35a6843a0f14247cd40e5cfdd3a837c03c8d3
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_PROJECT_BACKGROUND_CURRENT_CONVERSATION
critic_local_users_worktree_available: false
critic_local_git_fetch_exit_code: 128
coordinator_executable_receipts_verified: true
coordinator_executor_plan_validator: PASS_EXIT_0
coordinator_pyyaml_parse: PASS_EXECUTORS_11
coordinator_git_diff_check: PASS_EXIT_0
coordinator_path_mapper_check: PASS_EXIT_0
coordinator_partition_race_static_check: PASS_EXIT_0
remote_prompt_path_count: 11
remote_prompt_paths_all_exist: true
scientific_contract_review: PASS
fast_repair_review: PASS
finalizer_terminal_coverage_review: PASS
mapper_entrypoint_review: PASS
ancestry_binding_review: PASS
decision_token: ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
controller_start_authorized: true
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

本轮只进行 Route B Round03 规划审查。没有实现代码、训练模型、提交或监控 Slurm、写 runtime `review.md`、启动 Controller、启动 tmux、准备 validation、路线晋级、启动 M11、跨路线合并、主张 hosted metric 或作出最终科学判断。

最终决定：

`ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER`

该 token 只授权在精确 reviewed revision 上，以 Codex goal 或 goal resume 启动 Route B Controller。它不授权任何其他动作。

## 2. Exact binding

写入本审查文件前，远端 `route_B` 与绑定 commit 完全一致，ahead `0`、behind `0`。所有要求的 Git blob 均重新读取并匹配：

| binding | expected | observed | result |
| --- | --- | --- | --- |
| route head | `11d5c3d90028fa19ccd1c709d9ce5d4e90f5b96f` | `11d5c3d90028fa19ccd1c709d9ce5d4e90f5b96f` | MATCH |
| `route_B.md` | `1d58d7a37eacaee8cc15c159758e5074e794de8b` | `1d58d7a37eacaee8cc15c159758e5074e794de8b` | MATCH |
| executor plan | `082e2641d8fdf693e929d1aa460ae689b80ce0d2` | `082e2641d8fdf693e929d1aa460ae689b80ce0d2` | MATCH |
| critic request | `a1b03b7366df14bf9ca9628b309ced55dbf6db47` | `a1b03b7366df14bf9ca9628b309ced55dbf6db47` | MATCH |
| planner audit | `5f8764c08908e725830817d42ed3dc606971cda9` | `5f8764c08908e725830817d42ed3dc606971cda9` | MATCH |
| B10 prompt | `ad48d04aeac2a69fb99d41ec4fa73d159138d269` | `ad48d04aeac2a69fb99d41ec4fa73d159138d269` | MATCH |

本轮 handoff 不是 stale。

## 3. Executable validation receipts

本 ChatGPT runtime 没有挂载 `/users/a/e/aereinh/CARE`。我实际尝试执行：

```text
git -C /users/a/e/aereinh/CARE fetch --all --prune
exit: 128
reason: /users/a/e/aereinh/CARE is not mounted in this runtime
```

这不是对 executor plan 的失败判定。当前 main handoff 明确记录：协调器已经在绑定 Route B worktree 和当前绑定 revision 上完成所需本地检查，Critic 可以重新运行或核对这些收据，不能仅因为原 Planner/当前 ChatGPT runtime 没有 `/users` 挂载而拒绝 handoff。

已核对的协调器收据为：

```text
executor-plan validator: PASS_EXIT_0
PyYAML parse: PASS_EXECUTORS_11
git diff --check: PASS_EXIT_0
B0-B10 path and mapper check: PASS_EXIT_0
architecture validator/generator --help: PASS_EXIT_0
partition/race/finalizer static check: PASS_EXIT_0
```

partition/race 收据为：

```text
PASS route_B critic_equivalent_partition_race_static_check
slurm_executors=9
prompt_paths=11
```

这些收据只满足规划期 executable gate，不构成 Controller、训练或科学结论。

## 4. Required sources and independent visual review

已读取当前 main 治理、Agent-Flow、handoff、anti-laziness、permanent hard requirements、Slurm、mapper、wiki、Round02 历史分析、Deep Research commit `28c8aac80b7f18f3441c495dc9f2625fc10c460f`、Round02 Critic review、上一版 Round03 Critic review、当前 Route B contract/plan/request/audit、全部 B0-B10 prompts，以及当前 handoff。

SRR-v2、v2.5、v3 均从当前 Project/current-conversation visual channel 独立视觉读取：

- SRR-v2 要求 availability-aware modality evidence、shared/private/interaction retrieval、解剖引导 proposal、pathology-specific soft-ROI refinement 和 registration-aware Cine temporal path。
- SRR-v2.5 明确分离 scar 与 edema 的 proposal、ROI 几何和 refiner。
- SRR-v3 加入 nnU-Net anchor/context、components/uncertainty、train/OOF prototypes，以及 gate 关闭时保持 anchor 的 bounded pathology correction；Cine 必须消费 reference-space registered multiframe evidence。

当前计划仍是完整 SRR-v3 new-model route，不是 Route A 压缩版。

## 5. Fast repair findings

### 5.1 B10 all-terminal finalizer DAG: PASS

上一版 B10 只依赖 B9，无法覆盖 B4/B5/B8 等中途科学失败。当前计划已修为：

```text
depends_on: []
independent_of_upstream_success: true
```

B10 由 Controller 针对任何已启动 attempt 或 early terminal gate 注册，并通过 `afterany` 覆盖：

- success；
- implementation/data/validator failure；
- startup failure；
- timeout；
- preemption；
- faithful adequate-negative；
- early scientific gate failure；
- cancelled pending race loser；
- bounded retry replacement。

Controller ledger 是所有 started attempt 的 source of truth。若没有 Slurm attempt，计划要求走 local deterministic finalizer。任何 attempt 缺 terminal accounting、aggregation、mapper、validator 或 ledger coverage 时均禁止 review-ready。

因此上一轮的 success-only finalizer blocker 已关闭。

### 5.2 Mapper and architecture entrypoints: PASS

不存在的：

```text
scripts/architecture/care_mapper.py
```

已从绑定 plan 和 B10 prompt 移除。当前 B10 使用现有 first-party entrypoints：

```text
scripts/architecture/validate_care_architecture_wiki.py --strict
scripts/architecture/generate_care_architecture_wiki.py --check-all
```

两个文件均在精确 commit 中存在；协调器还记录了两者 `--help` exit `0`。B10 仍要求 `mapper_report_final.md`、`route_local_architecture_fingerprint.json` 和 architecture validation，未取消 mapper/fingerprint gate。

因此上一轮的 nonexistent mapper command blocker 已关闭。

### 5.3 Ancestry and binding metadata: PASS

`route_B.md`、executor plan、critic request 和 planner audit 不再各自保存互相冲突的 `remote_route_base_commit` / `planner_main_base_commit` 机器真值，而统一使用：

```text
round03_current_binding_source: prompts/routes/handoffs/CURRENT.md
```

最终 head、五个 planning blobs 和 B10 blob 均由 CURRENT/current critic handoff 精确绑定。route-local coordinator receipt 中提到 `e893624...` 只描述 repair worktree 的历史 rebase provenance，不覆盖当前 CURRENT-bound final head/blob set。

因此上一轮的 stale ancestry blocker 已关闭。

## 6. Inherited scientific hardening remains intact

本轮窄修订没有削弱 Route B 科学合同。以下要求仍被机器绑定：

- canonical modality order `[LGE,T2,C0]`；
- four scales `[32,64,128,256]`；
- 每尺度 sixteen shared/private/pairwise-interaction experts；
- pathology-specific two-pass spatial entmax router；
- invalid-slot weight 与 gradient exact gates；
- 数值化 Pattern-SIP、style clusters、hard groups、full-loss weights 和 schedules；
- four-shard fold-safe OOF-fitted inference-frozen prototype banks；
- bootstrap/online EMA formal memory 禁止；
- training-only safe hard-negative queues；
- no-T2 edema loss、bank、queue、proposal、ROI、refiner、gate、delta 和 final Route-B change exact zero；
- anatomy-guided conservative proposal 加 positive/negative prototype similarity-difference evidence；
- scar/edema 分开的 proposal、soft ROI、refiners、boundary 与 negative-space objectives；
- bounded final correction 和 retrieval-to-final-label interventions；
- B2 real forward/loss/gradient/intervention/save-reload gate 在任何长训之前；
- staged MyoPS training、positive-edema evaluation、fresh selector、clean reload 和 same-split help/harm；
- official `mathpluscode/CineMA` commit/revision/license/weight SHA；
- real `ConvUNetR` decoder hook、multiclass logits、features 和 normalized entropy；
- matched random source、common downstream initialization 和 parameter equality；
- seven-step SVF scaling-and-squaring、true Jacobian、inverse composition 和 real ANTs `SyNOnly`；
- temporal path 显式消费 registered logits/features/uncertainty、velocity、integrated displacement、Jacobian、motion magnitude、quality、temporal position 和 valid mask；
- cumulative temporal resume、atomic checkpoint 和 zero-credit partial/timeout/preemption；
- semantic known-bad fixtures、durable finalizer、route-local mapper/fingerprint receipts 和 independent reviewer tokens。

Proposal/refiner 不是 dense-head 名词，formal prototype 不是 bootstrap/EMA helper，CineMA 不是 CARE 小卷积 wrapper，registration 不是 direct-velocity proxy，temporal 不是抽象 `temporal_z` 或 frame0 fallback。

## 7. Partition, race, V100 and continuity review

B2-B10 覆盖 `htzhulab`、`a100-gpu`、`volta-gpu`，并为每个 Slurm executor 声明 compatibility、reason、per-partition preflight command 和 receipt。

- `htzhulab` 为默认主路径；
- `a100-gpu` 为 fallback/race partner；
- `volta-gpu` 只运行 exact-compatible 或独立 compatible work；
- full MyoPS/full temporal 在 V100 exact compatibility 未证明时明确 incompatible，并给独立 evaluation/replay/validator alternatives；
- 禁止为 V100 改 batch semantics、model、loss、split、label 或科学预算。

所有 race 声明保留：

- identical scientific hashes；
- isolated output/log/checkpoint/cache roots；
- shared atomic winner lock；
- loser zero credit；
- pending-loser cancellation；
- retry lineage；
- all-attempt finalizer accounting。

Controller 只能作为 Codex goal 或 goal resume 启动。submitted、pending、running、awaiting-accounting、undertrained-in-progress 和 monitor packet 都不是 completion，不能导致 Controller 提交 job 后早退或随意宣称 blocked。

## 8. B0-B10 prompt path review

全部 11 个 prompt 在精确 Route B revision 中存在，executor ID 与 plan 一致：

```text
B0_BIND_PROBE_MANIFEST_VALIDATOR
B1_IMPLEMENT_FULL_SRR_V3
B2_IMPLEMENTATION_GATE
B3_MYOPS_EVIDENCE_WARMUP
B4_MYOPS_PROPOSAL
B5_MYOPS_REFINER
B6_MYOPS_JOINT_AND_SELECTOR
B7_CINEMA_MATCHED_CONTROL
B8_REGISTRATION_AND_SYN
B9_TEMPORAL_AND_CINE_EVIDENCE
B10_FINALIZE_VALIDATE_REVIEW_REQUEST
```

B10 prompt blob 也与 handoff 精确匹配，并明确它不是 B9-success-only path。

## 9. Decision and authority boundary

规划的科学结构、机器合同、三分区策略、终态 finalizer、mapper/fingerprint、known-bad 和 reviewer 边界均达到 Controller-forward 条件。

`ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER`

该 token 只授权 exact Route B Controller 在 reviewed commit `11d5c3d90028fa19ccd1c709d9ce5d4e90f5b96f` 上，以 Codex goal 或 goal resume 启动。它不授权：

- validation packaging 或 upload；
- route promotion；
- M11；
- cross-route merge；
- hosted metric claim；
- final scientific decision。

Critic 未启动 Controller、tmux、训练或 Slurm，也未写 runtime `review.md`。