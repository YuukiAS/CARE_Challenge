---
document_type: route_controller_contract
route_id: route_B
portfolio_round: round04
date: 2026-07-19
task_key: route_B_round04_leaderboard_full_implementation
status: DRAFT_FOR_ROUND04_CRITIC_REVIEW
risk_level: high
task_kind: scientific_route
route_change: true
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 2
executor_count: 12
parallel_execution_allowed: true
executor_plan_path: prompts/routes/route_B_round04_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: false
route_local_mapper_receipt_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: independent_thread
reviewer: separate_readonly
planning_review_required: true
planning_reviewer: separate_gpt_thread
planning_review_path: prompts/routes/route_B_round04_critic_review.md
planning_review_token: ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
planning_commit_binding_mode: containing_commit_resolved_and_recorded_by_critic
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# Route B Round04 Controller Contract

## 1. Entry gate

Controller只能作为Codex goal或goal resume运行，并必须同时验证：

```text
origin/route_B contains reviewed packet head 8dfa40f8c4cedb2507f35a482bd46244a7a1c94c
origin/route_B contains review commit b9c7664da7cb1f1892fff37a4497722f31a0a96d
results/route_B/review.md decision == ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE
independent critic token == ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
critic reviewed commit == containing commit of all six Round04 planner files
critic recorded SHA256 for plan, contract, executor plan, critic request and planner audit
working tree clean
current branch == route_B
```

任一条件失败时写`ROUTE_B_ROUND04_CONTROLLER_BINDING_BLOCKED`并停止。Controller不得用Round03 planning ready token、旧route contract、聊天摘要或本地未推送文件代替。

## 2. Branch、worktree与write scope

Controller运行于：

```text
branch: route_B
worktree: /users/a/e/aereinh/CARE_worktrees/route_B
result root: results/route_B/round04
runtime root: results/route_B/runtime/round04
log root: logs/route_B_round04
lock root: results/route_B/runtime/round04/locks
```

正式Round04代码只写：

```text
src/care_myocardium/route_B_round04/**
configs/route_B_round04/**
scripts/route_B_round04/**
scripts/training/route_B_round04/**
scripts/validation/route_B_round04/**
tests/route_B_round04/**
jobs/route_B_round04/**
results/route_B/round04/**
```

Round03 source、shared `src/care_myocardium/models/**`、`cine/**`、`anchors/**`、`losses/**`、`refiner/**`均为read-only evidence。发现共享代码必须改动时返回`ROUTE_B_ROUND04_NEEDS_PLANNER_SCOPE_REVISION`。不得写`/overflow/htzhu/CARE`。

## 3. Ordered lifecycle

```text
bootstrap/binding
-> R4B0 reviewed evidence and fingerprint audit
-> R4B1 route_B_round04 package migration and B3A repair
-> R4B2 real implementation + microfit gate
-> implementation freeze
-> MyoPS R4B3 -> R4B4 -> R4B5 -> R4B6
-> Cine R4B7 -> R4B8 -> R4B9 -> R4B10
-> FINALIZER_A over every started attempt
-> mapper final
-> FINALIZER_B validators, git diff, lightweight local commit
-> controller_report
-> Controller stops
-> separate Reviewer
```

R4B3与R4B7在freeze后可并行；后续同wave MyoPS/Cine runtime executor使用独立worktree、branch、result/runtime/log/lock root。Controller不得超过两个executor slots，不得把MyoPS内部顺序改成并行。

## 4. B3 gate replacement

### 4.1 B3A implementation/label gate

`anatomy_union`必须由compact labels`{1,4,5}`构造；LV=`2`，RV=`3`。microfit cases和eight patches由R4B0确定性生成。R4B2执行512-step无augmentation microfit，必须达到：

```text
loss ratio <= 0.20
union Dice >= 0.55
union Dice gain >= 0.30
LV Dice >= 0.40
RV Dice >= 0.40
valid anatomy family gradient coverage >= 0.90
invalid slot max <= 1e-8
clean reload delta <= 1e-5
```

一次同scope修复后仍失败，返回`ROUTE_B_ROUND04_B3A_IMPLEMENTATION_NEEDS_REVISION`。不得写adequate negative。

### 4.2 B3B evidence readiness

R4B3重新运行至少6000 steps、1800 seconds、3 validation events。Round03 steps为zero Round04 credit。B4 entry只检查finite/loss decrease、all-valid-family gradient、invalid mask、no-T2 zero、exact sampler、positive low-threshold non-collapse和clean reload。旧`anatomy_union_overfit>=0.70`不再是R4B3/B4 entry field；validator发现旧field仍控制flow必须失败。

## 5. MyoPS formal stages

R4B4完成OOF frozen bank、safe hard-negative queue与proposal formal training；R4B5完成pathology-specific refiner；R4B6完成joint fine-tuning、fresh `--force` 44-case same-split evaluation和selector。所有selected checkpoints必须reload后使用。

MyoPS result packet必须提供：

```text
same-split nnU-Net baseline
per-case model and anchor rows
scar-positive matrix
T2-present edema-positive matrix
no-T2 safety matrix
CenterB matrix
CenterC matrix
remote-FP matrix
component-count matrix
HD95 matrix
volume-ratio matrix
help/harm/severe-harm summary
prototype/queue/proposal/ROI/refiner/final-label intervention
```

## 6. Cine formal stages

R4B7/R4B8严格matched；R4B9提供first-party SVF与real SyN；R4B10提供registered temporal七项消融。Cine result packet必须按case而不是pair给出reference-only、unregistered、registered、temporal-off、motion-off、anatomy-off、pretrained/random结果，并绑定frames、source weight、downstream init、registration checkpoint和prediction hashes。

CineMA、registration、temporal均为本轮正式工作，不得标记为后续事项、非阻断附件或仅smoke项目。

## 7. Slurm contract

正式wrapper只调用`/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`。preflight与formal job使用同一Python/env/config/output/log/lock roots。长等待race按planner plan和executor YAML执行；`htzhulab+a100-gpu` mirror必须isolate，winner/loser完整accounting。V100只在exact preflight通过且科学语义不变时执行。

训练链使用`afterok`；finalizer使用`afterany`覆盖all started attempts。monitor、pending、running、awaiting accounting均不能请求normal review。job终态后必须重新aggregation并更新tracked lightweight packet。

## 8. Completion and failure states

Controller可生成的terminal operational token：

```text
ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW
ROUTE_B_ROUND04_NEEDS_MONITOR
ROUTE_B_ROUND04_NEEDS_EVIDENCE
ROUTE_B_ROUND04_NEEDS_REVISION
ROUTE_B_ROUND04_EXTERNAL_RESOURCE_BLOCKED
```

stage-specific sufficient runtime negative必须标注具体stage和后续缺失理由。只有Reviewer可写`EVIDENCE_COMPLETE`或`ADEQUATE_NEGATIVE`。Controller report在review前固定：

```text
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
git_push_decision: SKIP_PUSH
```

## 9. Required controller receipts

```text
results/route_B/round04/controller_context.json
results/route_B/round04/controller_ledger.csv
results/route_B/round04/controller_bootstrap_snapshot.md
results/route_B/round04/implementation_snapshot.md
results/route_B/round04/fingerprint_inheritance_matrix.csv
results/route_B/round04/mapper_report_draft.md
results/route_B/round04/architecture_delta_draft.md
results/route_B/round04/finalizer_state.json
results/route_B/round04/mapper_report_final.md
results/route_B/round04/architecture_delta_final.md
results/route_B/round04/result.md
results/route_B/round04/completion_check.md
results/route_B/round04/review_request.md
results/route_B/round04/MANIFEST.md
results/route_B/round04/controller_report.md
```

Root `wiki/current_state.yaml`和root current figures不得前移；mapper只写route-local candidate snapshot与fingerprint receipt，直到后续portfolio reconciliation。

## 10. FINALIZER_A/B

FINALIZER_A读取all started attempt IDs，执行terminal `sacct`、runtime output existence、aggregation、stage token reconciliation和retry lineage检查。任何missing output、nonterminal accounting或aggregation nonzero返回非ready状态。

FINALIZER_B在mapper final后运行：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/validate_packet.py --strict --require-all-attempt-accounting results/route_B/round04
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/architecture/validate_care_architecture_wiki.py --strict
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/architecture/generate_care_architecture_wiki.py --check
git diff --check
```

known-bad selftests、heavy-artifact scan、bare-interpreter scan、Cine/registration/temporal降级扫描、authority scan全部必须PASS。只允许一个route-local lightweight packet commit；runtime roles不push。

## 11. Reviewer draft

Reviewer固定到Controller local packet commit，保持read-only。必须核对B0/B1/B2 inheritance、B3A/B3B gate semantics、B4–B10 formal runtime、same-split baseline、help/harm、Cine seven-control ablation、all-attempt accounting、strict known-bad、mapper receipts和authority boundary。

Reviewer允许token：

```text
ROUTE_B_ROUND04_REVIEW_EVIDENCE_COMPLETE
ROUTE_B_ROUND04_REVIEW_ADEQUATE_NEGATIVE
ROUTE_B_ROUND04_REVIEW_NEEDS_REVISION
ROUTE_B_ROUND04_REVIEW_NEEDS_EVIDENCE
ROUTE_B_ROUND04_REVIEW_NEEDS_MONITOR
```

无论何种token，都不授权validation upload、promotion、M11、cross-route merge、hosted metric或final scientific decision。
