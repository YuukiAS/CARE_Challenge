---
route_id: route_B
portfolio_round: round04
date: '2026-07-20'
role: planning_critic_handoff
planning_commit: 38551ed98a42b005a1a3f0b793efdef700037ee8
planning_parent_main: 64f5a27298cb2efd1f576a70296e49388ab0b717
route_B_evidence_commit: b9c7664da7cb1f1892fff37a4497722f31a0a96d
route_C_evidence_commit: 17062b00edc3443aacefe8583568797a9f2655ba
route_C_hold_decision_path: prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md
route_C_hold_decision_blob: 6564e1d6423b43b44a0c96b510a172fb92785873
route_C_hold_decision_token: ROUTE_C_PORTFOLIO_STOP_AND_HOLD
revision_source_critic_commit: de5f47b9f4404c85db1bd0f570b576d9d03b0372
revision_source_critic_blob: 4e5cd46a6494bd6c12f3985b99abd390a00b0786
revision_source_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
six_planning_blobs:
  prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md: a537e0e86e3059efa27d128ac3a018a22a6a40aa
  prompts/routes/route_B_round04_planner_prompt.md: 1ea2277d20f9e4eab1711c767274204342c372e2
  prompts/routes/route_B_round04_controller_contract.md: 3087283d65dbb6eeca697a393fc545528fe7fada
  prompts/routes/route_B_round04_executor_plan.yaml: c5e437a0cd847ade5244727a43c239da9825c737
  prompts/routes/route_B_round04_critic_request.md: fcac92428b38d4b10e21e3ff594b83cac7eeba60
  prompts/routes/route_B_round04_planner_audit.md: 7a7964867557fb8f43a236d4aefecfd6174a7b4c
coordinator_receipt_path: prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
coordinator_receipt_required_status: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
critic_request_path: prompts/routes/route_B_round04_critic_request.md
critic_output_path: prompts/routes/route_B_round04_critic_rereview.md
tested_commit_policy: exact_current_main_or_ancestor_with_allowlisted_diff_and_unchanged_six_blobs
allowed_descendant_paths:
- prompts/routes/handoffs/CURRENT.md
- prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
- prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
- prompts/routes/route_B_round04_critic_rereview.md
- prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md
- docs/figures/round03_route_architecture/**
- controller_notifications/**
- scripts/ops/build_route_watchboard.py
- tests/ops/test_build_route_watchboard.py
- tests/ops/test_controller_notifications.py
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

# Route B Round04 planning critic handoff after rereview blockers

## Binding

Review planning commit `38551ed98a42b005a1a3f0b793efdef700037ee8`, parent `64f5a27298cb2efd1f576a70296e49388ab0b717`, Route B evidence `b9c7664da7cb1f1892fff37a4497722f31a0a96d`, and all six exact Git blobs:

- `prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md`: `a537e0e86e3059efa27d128ac3a018a22a6a40aa`
- `prompts/routes/route_B_round04_planner_prompt.md`: `1ea2277d20f9e4eab1711c767274204342c372e2`
- `prompts/routes/route_B_round04_controller_contract.md`: `3087283d65dbb6eeca697a393fc545528fe7fada`
- `prompts/routes/route_B_round04_executor_plan.yaml`: `c5e437a0cd847ade5244727a43c239da9825c737`
- `prompts/routes/route_B_round04_critic_request.md`: `fcac92428b38d4b10e21e3ff594b83cac7eeba60`
- `prompts/routes/route_B_round04_planner_audit.md`: `7a7964867557fb8f43a236d4aefecfd6174a7b4c`

The prior `prompts/routes/route_B_round04_critic_review.md` is superseded historical context. The current gate input and output path is `prompts/routes/route_B_round04_critic_rereview.md`.

## Concurrent-main policy

Accept a coordinator tested commit only when it equals current `origin/main`, or when it is an ancestor and every descendant path is allowlisted while all six planning blobs remain unchanged.

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

`prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md` is allowlisted only as Route C hold/portfolio context. It authorizes no Route C Controller and changes no Route B authority or scientific requirement.

## Controller materialization review

The critic must inspect `controller_planning_materialization` in the controller contract and executor plan. Before B0 code or Slurm, the future Controller must use the fixed route_B worktree, read-only main source, immutable `results/route_B/round04/planning_snapshot/`, exact six hashes, current rereview/handoff/receipt/CURRENT/Route C decision, four PASS receipts, atomic publication and read-only revalidation. Any defect must map to `ROUTE_B_ROUND04_B0_STALE_PLANNING_BINDING`.

## Entry gate

The critic must reject when the coordinator receipt is pending/stale/nonzero, any planning blob differs, route refs differ, tested-main relation violates the unified policy, B0 binds the old critic as current input, the materialization contract is incomplete, or SRR-v2/v2.5/v3 cannot be visually read.

The critic must preserve full SRR-v3, B3-only interpretation, mandatory B4-B9, B10 all-terminal accounting, B0-B10 exact validators/known-bad, Slurm hardening and all authority boundaries.

## Allowed decisions

```text
ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
```

A ready token authorizes only the exact future Route B Controller as a Codex goal/goal resume. It does not authorize validation upload, route promotion, M11, hosted metrics, cross-route merge or a final scientific decision.
