---
route_id: route_B
portfolio_round: round04
date: 2026-07-19
role: planning_critic_handoff
planning_commit: 755e5919d472e3033c23ff7a848cac618aca1d34
planning_parent_main: 30098813522cecd98e60bcb99e2676b28c1a5461
route_B_evidence_commit: b9c7664da7cb1f1892fff37a4497722f31a0a96d
route_C_review_commit_context: 17062b00edc3443aacefe8583568797a9f2655ba
revision_source_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
planner_plan_blob: e6e31f772e2766ec79c466660fe8f56f14350d6f
planner_prompt_blob: 030c4ae0cb97bae1d661b40786bf3d7be78d930d
controller_contract_blob: fdb74c49634ba02a30b96979f185bd71fcf085c4
executor_plan_blob: 505b3a64d83b3d17cbc28ea7c0837d098665f821
critic_request_blob: 9911593bef8d8381e0df620bf22ca8c759e24186
planner_audit_blob: 6a9881f3eba630ec51ffed2b9ecb0ca0367262ed
coordinator_receipt_path: prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
coordinator_receipt_required_status: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
critic_request_path: prompts/routes/route_B_round04_critic_request.md
critic_output_path: prompts/routes/route_B_round04_critic_rereview.md
allowed_tokens:
  - ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
  - ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
controller_start_authorized: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
---

# Route B Round04 planning critic handoff

## Exact binding

Review the Route B Round04 planning revision at exact planning commit `755e5919d472e3033c23ff7a848cac618aca1d34`, based on main `30098813522cecd98e60bcb99e2676b28c1a5461`, with Route B evidence `b9c7664da7cb1f1892fff37a4497722f31a0a96d`.

Six bound files:

- `prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md`: `e6e31f772e2766ec79c466660fe8f56f14350d6f`
- `prompts/routes/route_B_round04_planner_prompt.md`: `030c4ae0cb97bae1d661b40786bf3d7be78d930d`
- `prompts/routes/route_B_round04_controller_contract.md`: `fdb74c49634ba02a30b96979f185bd71fcf085c4`
- `prompts/routes/route_B_round04_executor_plan.yaml`: `505b3a64d83b3d17cbc28ea7c0837d098665f821`
- `prompts/routes/route_B_round04_critic_request.md`: `9911593bef8d8381e0df620bf22ca8c759e24186`
- `prompts/routes/route_B_round04_planner_audit.md`: `6a9881f3eba630ec51ffed2b9ecb0ca0367262ed`

A change to any bound blob requires a new Planner handoff.

Current `origin/main` may be a descendant of the planning commit through non-planning administrative, documentation and observability commits when the six planning blobs above remain byte-identical. Allowed descendant changes include these paths/classes:

```text
prompts/routes/handoffs/CURRENT.md
prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
docs/figures/round03_route_architecture/*
controller_notifications/*
scripts/ops/build_route_watchboard.py
tests/ops/test_build_route_watchboard.py
tests/ops/test_controller_notifications.py
```

The known descendant `aea169e65e19c674b8c6cdba74fc1cab7a07713f` (`Fix round04 watchboard status parsing`) is allowed only as an ops/observability update. Watchboard/notifier state is not scientific evidence, not Route B runtime evidence, and does not modify the Route B planning contract, controller contract, executor plan, reviewer pass/fail standard, or authority boundary.

A coordinator receipt update is allowed only when the six planning blobs remain byte-identical. Because the receipt is committed after the executable checks, its `tested_origin_main` may be an ancestor of current `origin/main` when the descendant diff is limited to `CURRENT.md`, this handoff, and the coordinator receipt itself. A change to any one of the six planning blobs remains a hard stale handoff condition, regardless of whether `origin/main` descends from `755e5919d472e3033c23ff7a848cac618aca1d34`.

## Entry gate

Read `prompts/routes/handoffs/CURRENT.md`, the six bound planning files, the old critic review, the exact Route B Round03 reviewed evidence and the coordinator receipt.

Stop with `ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION` when:

- current main is not descended from `755e5919d472e3033c23ff7a848cac618aca1d34` through only declared non-planning binding/receipt/docs/ops/observability paths;
- one bound blob differs;
- `origin/route_B` differs from `b9c7664da7cb1f1892fff37a4497722f31a0a96d`;
- the coordinator receipt is pending, stale or contains any nonzero required exit;
- the receipt `tested_origin_main` is neither current `origin/main` nor an ancestor whose descendant diff is limited to the declared non-planning receipt/handoff update paths;
- the working tree receipt is not clean;
- the critic cannot visually read SRR-v2/v2.5/v3 from Project/current-conversation materials.

## Required review focus

1. Confirm no scientific downgrade: four-scale SRR-v3, OOF bank, hard negatives, proposal/refiner, bounded correction, same-split evaluation, official CineMA matched control, seven-step SVF, real SyN and registered temporal remain mandatory.
2. Confirm B3 is B3-only adequate negative, valid B4/B5 continue, B6 is first MyoPS full-route judgment, and B7/B8/B9 remain independent after B2.
3. Parse the B10 controller-terminal-finalizer contract. B10 must not depend on successful B6/B9 merge receipts and must cover B1/B2/B7/B8 blockers, timeout, preemption, cancelled race loser and successful B6/B9.
4. Parse every B0-B10 exact strict validator and known-bad contract, including expected validator exit `1` and exact failure keys.
5. Independently inspect all coordinator command outputs and exits.
6. Confirm Slurm hardening and all authority boundaries.

## Allowed decisions

```text
ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
```

A ready token authorizes only the exact future Route B controller as a Codex goal/goal resume. It does not authorize validation upload, route promotion, M11, hosted metrics, cross-route merge or final scientific decision.
