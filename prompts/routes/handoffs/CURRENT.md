# CARE Route Portfolio Current Round

This is the stable source of truth for the active portfolio round. Read this file first, then read only the handoff named for the current role and route.

## Active round

```text
round_id: round04
date: 2026-07-20
planner_environment: authenticated GitHub repository planning
local_executable_validation_owner: Codex coordinator at /users/a/e/aereinh/CARE
controller_authorized_now: 0
```

Round04 is not route promotion, validation authorization, M11 authorization, hosted-metric authorization, cross-route merge or a final scientific decision.

## Exact remote and planning bindings

```text
planning parent main: 64f5a27298cb2efd1f576a70296e49388ab0b717
planning commit: 38551ed98a42b005a1a3f0b793efdef700037ee8
Route B evidence: b9c7664da7cb1f1892fff37a4497722f31a0a96d
Route B reviewed controller packet: 2e24f290e83e356fbfba5f73da4fde98b657390b
Route B reviewer commit: 3950fe10ac31ef68da20f3ef7ffb001d6b17e6d9
Route C evidence/review commit: 17062b00edc3443aacefe8583568797a9f2655ba
Route C reviewed controller repair: 1e663cfa64f00413f005bef26310290fd43ec8ab
revision source critic commit: de5f47b9f4404c85db1bd0f570b576d9d03b0372
revision source critic blob: 4e5cd46a6494bd6c12f3985b99abd390a00b0786
revision source token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
```

## Portfolio state

```text
Route A: DEFERRED_FALLBACK_NOT_ACTIVE
Route B: EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION
Route C: ROUTE_C_PORTFOLIO_STOP_AND_HOLD
```

Route C hold is portfolio context only. `prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md` authorizes no Route C Controller, changes no Route B authority, removes no Route B Cine stage and makes no downstream scientific decision.

### Route B

```text
route head: 3950fe10ac31ef68da20f3ef7ffb001d6b17e6d9
review commit: 3950fe10ac31ef68da20f3ef7ffb001d6b17e6d9
reviewed controller repair: 2e24f290e83e356fbfba5f73da4fde98b657390b
review path: results/route_B/review.md
review token: ROUTE_B_ROUND04_REVIEW_EVIDENCE_COMPLETE
completion check: results/route_B/completion_check.md
review request: results/route_B/review_request.md
portfolio status: EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION
controller start authorized: false
critic handoff: NO_CURRENT_CRITIC_HANDOFF
coordinator receipt: prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
critic output: prompts/routes/route_B_round04_critic_rereview.md
controller planning materialization root: results/route_B/round04/planning_snapshot
materialization failure token: ROUTE_B_ROUND04_B0_STALE_PLANNING_BINDING
```

Route B Round04 controller and independent reviewer are complete. The reviewer reported no blocking findings and confirmed the terminal packet is reviewable and operational execution is complete for the controller scope. This does not authorize route promotion, validation upload, M11, hosted metric claims, cross-route merge, or a final scientific decision.

## Controller Terminal Packet / Reviewer Targets

```text
route_B reviewer_target_head: 3950fe10ac31ef68da20f3ef7ffb001d6b17e6d9
route_B terminal_token: ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW
route_B reviewer_output_path: results/route_B/review.md
route_B route_promotion_decision: NOT_REVIEWED
route_B route_negative_decision: NOT_REVIEWED
route_B scientific_resolution_status: AWAITING_REVIEW
route_B validation_upload: false
route_B hosted_metric_claim: false
route_B m11_started: false
```

Six planning blobs:

- `prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md`: `a537e0e86e3059efa27d128ac3a018a22a6a40aa`
- `prompts/routes/route_B_round04_planner_prompt.md`: `1ea2277d20f9e4eab1711c767274204342c372e2`
- `prompts/routes/route_B_round04_controller_contract.md`: `3087283d65dbb6eeca697a393fc545528fe7fada`
- `prompts/routes/route_B_round04_executor_plan.yaml`: `c5e437a0cd847ade5244727a43c239da9825c737`
- `prompts/routes/route_B_round04_critic_request.md`: `fcac92428b38d4b10e21e3ff594b83cac7eeba60`
- `prompts/routes/route_B_round04_planner_audit.md`: `7a7964867557fb8f43a236d4aefecfd6174a7b4c`

A change to any of the six planning blobs makes the handoff stale.

## Tested-commit policy

The coordinator tested commit is valid only when it equals current `origin/main`, or is its ancestor and every descendant path is in this explicit allowlist while all six planning blobs remain byte-identical:

```text
prompts/routes/handoffs/CURRENT.md
prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
prompts/routes/route_B_round04_critic_rereview.md
prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md
docs/figures/round03_route_architecture/**
controller_notifications/**
scripts/ops/build_route_watchboard.py
tests/ops/test_build_route_watchboard.py
tests/ops/test_controller_notifications.py
```

A non-ancestor relation, unreadable diff, disallowed path or changed planning blob is stale.

## Current role entries

```text
Route A critic: NO_CURRENT_CRITIC_HANDOFF
Route B critic: NO_CURRENT_CRITIC_HANDOFF
Route C critic: NO_CURRENT_CRITIC_HANDOFF
Route C reviewer: NO_CURRENT_REVIEWER_HANDOFF
Route C controller: NO_CURRENT_CONTROLLER_HANDOFF
```

Allowed Route B planning decisions:

```text
ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
```

The ready token is invalid until a fresh coordinator receipt records all required exits `0` and a new independent critic binds `38551ed98a42b005a1a3f0b793efdef700037ee8` plus all six blobs.

## Scientific invariants

Route B remains full four-scale SRR-v3: `[LGE,T2,C0]` with explicit availability, sixteen shared/private/interaction experts per scale, spatial two-pass routing, optimized Pattern-SIP, learned anatomy, four-shard OOF-fitted frozen prototypes, safe hard negatives, separate scar/edema proposal and refiners, bounded correction, same-split final-output evidence, official CineMA matched random control, seven-step SVF, true Jacobian/inverse consistency, real SyN and registered temporal aggregation.

Round03 B3 is B3-only adequate negative. B4-B6 and B7-B9 remain required after valid predecessors; B6 is the first MyoPS full-route judgment.

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
