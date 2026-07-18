---
portfolio_round: round03
date: 2026-07-18
role: planner_handoff
status: PLANNER_YAML_REPAIR_PUBLISHED_CRITIC_VALIDATION_PENDING
not_a_milestone: true
planner_main_base_commit: f15cbcfa7b7f9f699d33abcf4f3ac0c359f06c22
planner_plan_path: prompts/routes/portfolio_round03_planner_plan_20260718.md
planner_plan_blob: 61ae3117137b42b38fbd1a3112ea77a019cd87f5
active_routes: [route_B, route_C]
deferred_routes: [route_A]
route_A_status: DEFERRED_FALLBACK_NOT_ACTIVE
route_A_current_critic_handoff: NO_CURRENT_CRITIC_HANDOFF
current_controller_authorizations: 0
validator_not_run_by_planner: true
slurm_partitions: [htzhulab, a100-gpu, volta-gpu]
v100_user_approved: true
three_way_race_user_approved: true
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# CARE Route Portfolio Round03 Planner handoff — YAML repair revision

## Portfolio state

```text
Route A: DEFERRED_FALLBACK_NOT_ACTIVE
Route B: ACTIVE_FULL_SRR_V3
Route C: ACTIVE_M10_FORENSIC_EVIDENCE_AND_CINE_FIDELITY
current_controller_authorizations: 0
```

This handoff supersedes the earlier Round03 binding only to repair machine-readable YAML and refresh commits/blobs. Scientific route decisions and hard requirements are unchanged. Route A remains dormant with `NO_CURRENT_CRITIC_HANDOFF`; no Route A Controller, Critic, training or Slurm work is authorized.

## Exact route bindings

### Route A

```text
head: a91ba0eef8dff4600e16331aea99d043e1f4339b
contract blob: 370c25de0e35dbd5c854bbdfb81589ee8c0a4368
executor-plan blob: c681d761cfa145d68ba906f5eb33607843af8b80
critic-request blob: 227c8f69f69e2b07b72f5df5f3323b2f03136bd1
planner-audit blob: 61d8cb48fab3728d1330975fb1bc2178446313f9
current Critic prompt: NO_CURRENT_CRITIC_HANDOFF
```

### Route B

```text
head: 0d7e0d295ca94f23c39767506bd711890ae6022e
contract blob: 2d82b8bb5d05e521adb87281a663fd7fe38582c6
executor-plan blob: 83494fbf40df7b79c26c3be3c00d51e23830208c
critic-request blob: 50fba61a5512e4ba7b124fd2355ca84c2a688ed8
planner-audit blob: 3a0d422ed81695f77750f59ebfdca38700c69516
Critic prompt: prompts/routes/handoffs/route_B_round03_critic_handoff_20260718.md
Critic-handoff blob: 20b63e09aba621a05d9a3d175071bca4c41ddde4
Critic output: prompts/routes/route_B_round03_critic_review.md
```

### Route C

```text
head: 8c2f4fef4f25805e8eac1a44628045bbb2875a5a
contract blob: 0f04a06dce5ebaaaa0e0f84ce317b88123fd1a26
executor-plan blob: 9b5d0bd369dd95d926337ef2d8c315e7fdbfb982
evidence-mapping blob: 2b5a068ee807c5f622dcd5b1732fdc05e144b960
evidence-mapping required row count: 37
critic-request blob: 0beb1ef72cc8fb1e712be76a57c11b0fdc04043e
planner-audit blob: f703decf4b8480da467f7f3387a273fe3b66d3eb
Critic prompt: prompts/routes/handoffs/route_C_round03_critic_handoff_20260718.md
Critic-handoff blob: 32c67840e9c8f73c6af280534b126e8012de5a0d
Critic output: prompts/routes/route_C_round03_critic_review.md
```

Any later route head or bound blob change makes the corresponding Critic handoff stale.

## Machine-readable repair

Route B/C unsafe YAML flow mappings were replaced by block mappings. Commands/templates containing `${SLURM_JOB_PARTITION}`, `{phase}`, `{checkpoint_sha}`, `{partition}`, `{attempt}`, nested quotes or `&&` are explicit strings. All B0–B10 and C0/C0B/R1/R2/R3 prompt paths were re-fetched and exist. Route C's evidence mapping remains unchanged and spans `C_MAP_001` through `C_MAP_037`.

The Planner had no `/users` shell. It does not claim repository validator or `git diff --check` exits. Local ChatGPT-sandbox parsing found Route B `executors=11`, Route C `executors=5`, and zero findings under a mirror of current executor-plan validation rules. This is not sufficient for a ready token.

## Required next actors

Route B and Route C may be handed to their independent Planning Critics only after a Codex coordinator runs the exact commands listed in each Critic handoff. At minimum, the exact route commit must produce exit `0` for its executor-plan validator, PyYAML parse, route-specific partition/race checks, Route C 37-row mapping parse where applicable, and `git diff --check`.

Allowed Route B tokens:

```text
ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
```

Allowed Route C tokens:

```text
ROUTE_C_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_C_ROUND03_PLANNING_NEEDS_REVISION
```

A nonzero or unavailable required check requires the revision token; it cannot be delegated to a Controller. A ready token authorizes only the corresponding exact-route Controller as a Codex goal or goal resume.

## Hardening retained

`htzhulab` remains default, `a100-gpu` fallback/race partner, and `volta-gpu` is used for exact-compatible work or independent compatible replay/extraction/evaluation/registration-control/reload/validator work. V100 scientific downscaling is forbidden. Distinct ready work precedes duplication. Race attempts retain identical scientific hashes, isolated roots, atomic winner lock, pending-loser cancellation, loser zero credit, retry lineage and all-attempt finalizer coverage. Formal wrappers use `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`.

Route B remains complete SRR-v3 and keeps its implementation gate before formal training. Route C remains historical M10 forensic/fidelity, keeps the zero-effect `anchor_residual_control_off_path`, exact fingerprint recovery, fresh forced replay, 37-row evidence mapping and R1/R2/R3 freeze boundaries.

## Authority boundary

```text
controller_authorized_now: 0
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
```

Planner publication, commit or push is not Critic passage. This revision performs no implementation, training, Slurm submission/monitoring, runtime `review.md`, validation upload, route promotion, M11, cross-route merge, hosted metric claim or final scientific decision.
