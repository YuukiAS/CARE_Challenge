# CARE Route Portfolio Current Round

This is the stable entrypoint for the active CARE route portfolio round. Read this file first, then read only the handoff named for the current role and route.

## Active Round

```text
round_id: round03
date: 2026-07-18
planner_thread_model: one GPT planner thread owns Route A, Route B, and Route C
critic_thread_model: one separate critic thread for each active route
milestone_model: retired for this route portfolio loop
route_round_model: portfolio planning round with route-specific critic handoffs
remote_evidence_only_for_planner_publication: true
local_worktree_state: NOT_INSPECTED_BY_USER_INSTRUCTION
```

Round03 is not a scientific milestone, route promotion, validation authorization, M11 authorization, cross-route merge, hosted-metric claim, or final scientific decision.

## Planner Entry

The current Planner prompt is:

```text
prompts/routes/handoffs/portfolio_round03_planner_prompt_20260717.md
```

The committed Planner handoff and plan are:

```text
prompts/routes/handoffs/portfolio_round03_planner_handoff_20260718.md
prompts/routes/portfolio_round03_planner_plan_20260718.md
```

Portfolio state:

```text
Route A: DEFERRED_FALLBACK_NOT_ACTIVE
Route B: ACTIVE_FULL_SRR_V3
Route C: ACTIVE_M10_FORENSIC_EVIDENCE_AND_CINE_FIDELITY
current_controller_authorizations: 0
```

## Bound Route Planner Revisions

### Route A

```text
route head: a91ba0eef8dff4600e16331aea99d043e1f4339b
contract blob: 370c25de0e35dbd5c854bbdfb81589ee8c0a4368
executor-plan blob: c681d761cfa145d68ba906f5eb33607843af8b80
critic-request blob: 227c8f69f69e2b07b72f5df5f3323b2f03136bd1
planner-audit blob: 61d8cb48fab3728d1330975fb1bc2178446313f9
```

Route A is a dormant fallback. It has no current Round03 Critic and no Controller/Slurm authority. It may be reactivated only by explicit user authorization or a later Portfolio Planner decision after a documented Route B pre-training implementation blocker.

### Route B

```text
route head: 4c2f2ec146f5cc7a026cf4d5369c79b863f88ad2
contract blob: 2d82b8bb5d05e521adb87281a663fd7fe38582c6
executor-plan blob: e95757507c1025ae9e7538f64c4143ead899d05f
critic-request blob: e9917375f549368a99348a91ca4dd0d1aa9a8932
planner-audit blob: e0f0cca68bd27db0b452a5f35270d57afd8fbf54
```

### Route C

```text
route head: e9966da52b65367a248dbcc746879fcac2422961
contract blob: 0f04a06dce5ebaaaa0e0f84ce317b88123fd1a26
executor-plan blob: 7e3bd792bf15d1778a227df6e5216d4b440c868d
evidence-mapping blob: 2b5a068ee807c5f622dcd5b1732fdc05e144b960
critic-request blob: 314a479e98d2af888cfd945092ab6aef09860a83
planner-audit blob: 623216e8f1b1ecc64f3d6fb8d17b9f1f8711e595
```

A later change to a route head or any bound blob makes that route's Critic handoff stale and requires a new Planner binding.

## Critic Entries

Each Critic thread reads only its route's current prompt.

```text
route_A critic current prompt:
NO_CURRENT_CRITIC_HANDOFF

route_B critic current prompt:
prompts/routes/handoffs/route_B_round03_critic_handoff_20260718.md

route_C critic current prompt:
prompts/routes/handoffs/route_C_round03_critic_handoff_20260718.md
```

Route A Critic must stop and report that no current Critic prompt exists. It must not reuse the Round02 prompt or issue a Round03 ready token.

Route B and Route C Critics must independently re-fetch their exact route heads/blobs, visually read SRR-v2/v2.5/v3 from the Project image channel, read current main governance and route-local evidence, and run the required plan/partition/git-diff checks before any ready token.

Allowed Route B planning tokens:

```text
ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
```

Allowed Route C planning tokens:

```text
ROUTE_C_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_C_ROUND03_PLANNING_NEEDS_REVISION
```

These tokens authorize only the corresponding route Controller to start on the exact reviewed revision. They do not authorize validation packaging/upload, route promotion, M11, cross-route merge, hosted metric claims, or a final scientific decision.

## Planner Validation Boundary

The Round03 Planner publication was produced under an explicit remote-only instruction. No shell/server command was run. The recorded state is:

```text
Route A executor-plan validator: NOT_RUN_USER_PROHIBITED_SHELL
Route B executor-plan validator: NOT_RUN_USER_PROHIBITED_SHELL
Route C executor-plan validator: NOT_RUN_USER_PROHIBITED_SHELL
Route B partition/race validator: NOT_RUN_USER_PROHIBITED_SHELL
Route C partition/race/evidence-mapping validator: NOT_RUN_USER_PROHIBITED_SHELL
git diff --check: NOT_RUN_USER_PROHIBITED_SHELL
remote static schema review: PASS
```

A Route B/C Critic cannot emit a ready token until required executable checks return zero on the exact bound route commit.

## Three-Partition Portfolio Policy

Round03 plans all of:

```text
htzhulab
a100-gpu
volta-gpu
```

The user has approved V100 use, V100 race, and three-way race. Distinct ready work has priority over duplicate routing. A single critical compatible job may race immediately. Exact scientific configuration, isolated attempt roots, atomic winner lock, loser zero credit, pending-loser cancellation, retry lineage, and all-attempt finalizer coverage are mandatory. V100 semantic downscaling is forbidden; incompatible heavy work is reassigned to compatible replay, extraction, evaluation, registration-control, reload, or validator tasks.

## Round03 Decision Checkpoints

```text
2026-07-20:
- Route B implementation/manifest/validator/preflight gate terminal.
- Route C fingerprint/evidence-map and exact recovery decision terminal.

2026-07-21:
- Route B evidence-warmup/proposal gate.
- Route C fresh replay majority, immutable-anchor selector receipts, and real intervention path.

2026-07-22:
- Route B first formal MyoPS evidence and official CineMA/control evidence.
- Route C R1 terminal evidence or exact blocker and R2 real Cine fidelity freeze candidate.

2026-07-23:
- evidence-directed same-scope repair only.

2026-07-24:
- no new scientific design or loss.

2026-07-25:
- route-local packets, independent reviews, Portfolio reconciliation input.

2026-07-26:
- runtime/review/Docker/packaging/paper/submission QA only.

2026-07-27:
- final submission; no new experiment.
```

Route B and Route C do not wait for one another. Their Critic threads may run in parallel; each Controller may start independently only after its own exact ready token.

## Authority Boundary

```text
controller_authorized_now: 0
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
```

Planner publication, commit, or push is not Critic passage. Round03 planning does not execute code, train models, submit or monitor Slurm, write runtime `review.md`, package/upload validation, promote a route, start M11, merge routes, claim hosted metrics, or make a final scientific decision.