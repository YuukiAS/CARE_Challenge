---
route_id: route_B
portfolio_round: round04
date: 2026-07-19
role: route_B_planner_revision_prompt
planner_base_main: 30098813522cecd98e60bcb99e2676b28c1a5461
route_B_evidence_ref: b9c7664da7cb1f1892fff37a4497722f31a0a96d
route_C_review_commit: 17062b00edc3443aacefe8583568797a9f2655ba
revision_source_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
status: REVISION_PENDING_COORDINATOR_RECEIPT_AND_CRITIC_REREVIEW
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

You are the CARE Route Portfolio GPT Planner. Work only from the exact GitHub repository refs and repository files. Do not require this planning thread to access server shell, tmux, Slurm or a local `/users` worktree. Do not write `the prohibited overflow CARE workspace`.

## Exact remote bindings

```text
origin/main: 30098813522cecd98e60bcb99e2676b28c1a5461
origin/route_B: b9c7664da7cb1f1892fff37a4497722f31a0a96d
origin/route_C: 17062b00edc3443aacefe8583568797a9f2655ba
Route C reviewer token: ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
Route B planning critic token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
```

Visually read SRR-v2, SRR-v2.5 and SRR-v3 from current Project/current-conversation materials. Preserve the full route objective: availability-aware four-scale retrieval, shared/private/interaction experts, train/OOF frozen prototypes, safe hard negatives, anatomy-guided scar/edema proposals, separate soft-ROI refiners, bounded final correction, official CineMA matched random control, seven-step SVF, real SyN and registered temporal aggregation.

## Portfolio state to preserve

Route C Round03 is `EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION`. The `positive_negative_prototype_swap` fail-open has been repaired and independently re-reviewed. Route C does not need another reviewer unless a new Route C commit makes the review binding stale. Route C completion does not authorize promotion/upload/M11/hosted metrics/cross-route merge/final decision and does not remove Route B Cine work.

Route B Round03 B3 is an adequate negative for B3 only. B4/B5/B6 must run after valid predecessor implementation/readiness; B6 is the first MyoPS full-route judgment. B7/B8/B9 are mandatory after B2 and remain independent of B3 and Route C.

## Required planning repairs

1. Advance `prompts/routes/handoffs/CURRENT.md` to Round04 and bind the exact planning commit, Route B evidence ref, six planning blobs, current critic handoff, critic output path, allowed Round04 tokens and authority boundary.
2. Make B10 a controller-level terminal finalizer with no successful B6/B9 merge dependency. It must cover global B0/B1/B2 blockers, lane-local B3/B4/B5/B7/B8 blockers, timeout, preemption, failed startup, cancelled/started race losers and successful B6/B9.
3. Bind B0-B10 exact strict validator script/command/input/report/success token and exact known-bad matrix command/report/expected validator exit/failure keys.
4. Require a Codex coordinator to run the final-commit checks at `/users/a/e/aereinh/CARE` and fill `prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md` with exit-zero evidence before critic rereview.
5. Keep `controller_start_authorized: false` until `ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER` is written by a new independent critic against the current binding.

## Output files

```text
prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md
prompts/routes/route_B_round04_planner_prompt.md
prompts/routes/route_B_round04_controller_contract.md
prompts/routes/route_B_round04_executor_plan.yaml
prompts/routes/route_B_round04_critic_request.md
prompts/routes/route_B_round04_planner_audit.md
prompts/routes/portfolio_round04_routeC_review_and_routeB_revision_planner_update_20260719.md
prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
prompts/routes/handoffs/CURRENT.md
```

A planning-file edit after binding makes the critic handoff stale. A receipt-only commit may follow only when all six planning blobs remain byte-identical.

No controller, implementation, training, Slurm, validation upload, route promotion, M11, hosted metric claim, cross-route merge or final scientific decision is authorized.
