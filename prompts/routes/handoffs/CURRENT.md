# CARE Route Portfolio Current Round

This is the stable source of truth for the active portfolio round. Read this file first, then read only the handoff named for the current role and route.

## Active round

```text
round_id: round04
date: 2026-07-19
planner_environment: authenticated GitHub repository planning
local_executable_validation_owner: Codex coordinator at /users/a/e/aereinh/CARE
controller_authorized_now: 0
```

Round04 is not a route promotion, validation authorization, M11 authorization, hosted-metric claim, cross-route merge or final scientific decision.

## Exact remote evidence bindings

```text
planner base main: 30098813522cecd98e60bcb99e2676b28c1a5461
Route B evidence: b9c7664da7cb1f1892fff37a4497722f31a0a96d
Route C reviewer commit: 17062b00edc3443aacefe8583568797a9f2655ba
Route C reviewed controller repair: 1e663cfa64f00413f005bef26310290fd43ec8ab
```

## Portfolio state

```text
Route A: DEFERRED_FALLBACK_NOT_ACTIVE
Route B: PLANNING_REVISION_PENDING_COORDINATOR_RECEIPT_AND_CRITIC_REREVIEW
Route C: EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION
```

### Route C

Route C Round03 controller work is complete through reviewer-accepted evidence completeness.

```text
review path: results/route_C/review.md
review commit: 17062b00edc3443aacefe8583568797a9f2655ba
reviewed controller repair: 1e663cfa64f00413f005bef26310290fd43ec8ab
review token: ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
portfolio status: EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION
old blocker repaired: positive_negative_prototype_swap validator fail-open
reviewer required now: false
reviewer required after a binding-changing commit: true
```

Route C is no longer sent to a reviewer unless a new commit makes the reviewer binding stale. It remains portfolio evidence only and authorizes no downstream action.

### Route B Round04 planning binding

```text
planning commit: 755e5919d472e3033c23ff7a848cac618aca1d34
planning parent main: 30098813522cecd98e60bcb99e2676b28c1a5461
Route B evidence commit: b9c7664da7cb1f1892fff37a4497722f31a0a96d
revision source critic token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
critic handoff: prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
coordinator receipt: prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
critic output: prompts/routes/route_B_round04_critic_rereview.md
controller start authorized: false
```

Six planning blobs:

- `prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md`: `e6e31f772e2766ec79c466660fe8f56f14350d6f`
- `prompts/routes/route_B_round04_planner_prompt.md`: `030c4ae0cb97bae1d661b40786bf3d7be78d930d`
- `prompts/routes/route_B_round04_controller_contract.md`: `fdb74c49634ba02a30b96979f185bd71fcf085c4`
- `prompts/routes/route_B_round04_executor_plan.yaml`: `505b3a64d83b3d17cbc28ea7c0837d098665f821`
- `prompts/routes/route_B_round04_critic_request.md`: `9911593bef8d8381e0df620bf22ca8c759e24186`
- `prompts/routes/route_B_round04_planner_audit.md`: `6a9881f3eba630ec51ffed2b9ecb0ca0367262ed`

Any change to one of these six blobs makes the handoff stale.

## Current role entries

```text
Route A critic: NO_CURRENT_CRITIC_HANDOFF
Route B critic: prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
Route C critic: NO_CURRENT_CRITIC_HANDOFF
Route C reviewer: NO_CURRENT_REVIEWER_HANDOFF
```

Allowed Route B Round04 planning decisions:

```text
ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
```

The ready token is invalid unless the coordinator receipt is current, has every required exit `0`, tested current `origin/main`, and the six planning blobs still match.

## Route B scientific invariants

Round03 B3 is an adequate negative for B3 only. A valid B3 continues to B4; a valid weak B4 continues to B5; a faithful weak B5 continues to B6; B6 is the first MyoPS full-route judgment. B7/B8/B9 remain mandatory after B2 and cannot disappear because of B3 or Route C completion.

Full SRR-v3, OOF prototypes, safe hard negatives, separate proposal/refiner, bounded correction, same-split evaluation, official CineMA matched random control, seven-step SVF, real SyN and registered temporal aggregation remain required.

## Authority boundary

```text
controller_authorized_now: 0
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
```
