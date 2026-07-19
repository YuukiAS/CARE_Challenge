---
route_id: route_B
portfolio_round: round04
date: 2026-07-20
role: route_B_planner_revision_prompt
planner_base_main: 64f5a27298cb2efd1f576a70296e49388ab0b717
revision_source_critic_commit: de5f47b9f4404c85db1bd0f570b576d9d03b0372
concurrent_architecture_context_commit: 64f5a27298cb2efd1f576a70296e49388ab0b717
route_B_evidence_ref: b9c7664da7cb1f1892fff37a4497722f31a0a96d
route_C_review_commit: 17062b00edc3443aacefe8583568797a9f2655ba
route_C_followup_decision_token: ROUTE_C_PORTFOLIO_STOP_AND_HOLD
revision_source_critic_path: prompts/routes/route_B_round04_critic_rereview.md
revision_source_critic_blob: 4e5cd46a6494bd6c12f3985b99abd390a00b0786
revision_source_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
status: PLANNING_REVISION_PENDING_COORDINATOR_RECEIPT_AND_CRITIC_REREVIEW
controller_start_authorized: false
required_coordinator_receipt: prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
required_critic_output: prompts/routes/route_B_round04_critic_rereview.md
required_critic_token: ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
---

# Route B Round04 Planner Revision Prompt

You are the CARE Round04 Route B Planner revision thread. Work only on planning files. Do not implement code, train, submit Slurm, start a controller or runtime reviewer, package or upload validation, promote a route, start M11, merge routes, claim hosted metrics, or make a final scientific decision.

## Exact revision baseline

```text
origin/main: 64f5a27298cb2efd1f576a70296e49388ab0b717
origin/route_B: b9c7664da7cb1f1892fff37a4497722f31a0a96d
origin/route_C: 17062b00edc3443aacefe8583568797a9f2655ba
revision source: prompts/routes/route_B_round04_critic_rereview.md
revision source token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
Route C decision: ROUTE_C_PORTFOLIO_STOP_AND_HOLD
```

Visually read SRR-v2, SRR-v2.5 and SRR-v3 from Project/current-conversation materials. Preserve full Route B: four-scale availability-aware shared/private/interaction retrieval, optimized Pattern-SIP, OOF frozen prototypes, safe hard negatives, learned anatomy, separate scar/edema proposal and soft-ROI refiners, bounded correction, same-split evidence, official CineMA matched random control, seven-step SVF, true Jacobian, inverse consistency, real SyN and registered temporal aggregation.

## Required repairs

1. Add the Route C hold decision path to the explicit Round04 descendant allowlist. State that it is portfolio context only, changes no Route B authority and authorizes no Route C controller.
2. Add one machine-readable `controller_planning_materialization` policy to the controller contract and executor plan. The controller runs in `/users/a/e/aereinh/CARE_worktrees/route_B`, reads `/users/a/e/aereinh/CARE` only as a read-only planning source, atomically creates `results/route_B/round04/planning_snapshot/`, writes manifest/hash/diff/materialization receipts, and fails closed before any code or Slurm action on source, completeness or hash failure.
3. Change B0 current exact inputs to the current critic rereview, current handoff, current coordinator receipt, CURRENT and Route C hold decision. Keep `route_B_round04_critic_review.md` only under superseded historical context.
4. Use one tested-commit rule everywhere: exact current `origin/main`, or an ancestor whose descendant diff is restricted to the explicit allowlist while all six planning blobs remain unchanged.
5. Regenerate the six planning blob mapping in CURRENT, handoff and coordinator receipt; make critic request and planner audit bind that exact mapping through the current handoff to avoid recursive self-hash embedding.
6. Keep `controller_authorized_now: 0`. A future controller requires a fresh coordinator receipt and a new independent critic token for the exact binding.

## Explicit descendant allowlist

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

A six-planning-blob change is never covered by the allowlist.

## Required outputs

```text
prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md
prompts/routes/route_B_round04_planner_prompt.md
prompts/routes/route_B_round04_controller_contract.md
prompts/routes/route_B_round04_executor_plan.yaml
prompts/routes/route_B_round04_critic_request.md
prompts/routes/route_B_round04_planner_audit.md
prompts/routes/handoffs/CURRENT.md
prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
```

No output from this planning thread authorizes runtime action.
