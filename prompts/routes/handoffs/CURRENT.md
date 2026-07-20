# CARE Current Development State

This is the stable source of truth for the current CARE planning/development posture. Read this file first before writing CARE milestones, Codex goals, route judgments, controller prompts, reviewer prompts, or handoffs.

## Active round

```text
round_id: post_round04_main_only
date: 2026-07-20
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
local_executable_validation_owner: Codex coordinator at /users/a/e/aereinh/CARE
controller_authorized_now: 0
route_worktree_development_authorized: false
route_branch_deletion_authorized: false
```

Default future GPT/Codex work is `main`-only. Do not start Route A, Route B, or Route C controllers; do not continue route worktree development; do not open a new portfolio round; and do not use `/users/a/e/aereinh/CARE_worktrees/route_A`, `/users/a/e/aereinh/CARE_worktrees/route_B`, or `/users/a/e/aereinh/CARE_worktrees/route_C` for new implementation unless a later explicit human-approved handoff reactivates a named route.

Remote route branches are retained for provenance. They are not deleted and are not active development targets.

## Exact remote evidence bindings

```text
main_after_route_C_visibility_commit: 26a8d16d8d684551b6e90717ee6715d0d71b6a4d
Route B reviewer commit: 3950fe10ac31ef68da20f3ef7ffb001d6b17e6d9
Route B reviewed controller packet: 2e24f290e83e356fbfba5f73da4fde98b657390b
Route C evidence/review commit: 17062b00edc3443aacefe8583568797a9f2655ba
Route C reviewed controller repair: 1e663cfa64f00413f005bef26310290fd43ec8ab
Route C main visibility commit: 26a8d16d8d684551b6e90717ee6715d0d71b6a4d
```

Route C's reusable conclusion packet is preserved on `main` under `results/route_C/`, including `main_visibility_note.md`, `review.md`, `controller_report.md`, `result.md`, and selected Round03 terminal evidence. This preservation does not mean Route C is active, promoted, upload-authorized, or scientifically resolved.

## Portfolio state

```text
Route A: HISTORICAL_DORMANT_NOT_ACTIVE
Route B: HISTORICAL_EVIDENCE_COMPLETE_NOT_ACTIVE
Route C: HISTORICAL_STOP_AND_HOLD_NOT_ACTIVE
```

No route currently has controller authority. Route A/B/C evidence may be read as historical context, but future implementation and protocol maintenance should target `main` unless a later human-approved planning step explicitly reactivates a route and binds a new critic/controller/reviewer packet.

### Route A

```text
portfolio status: HISTORICAL_DORMANT_NOT_ACTIVE
controller start authorized: false
critic handoff: NO_CURRENT_CRITIC_HANDOFF
reviewer handoff: NO_CURRENT_REVIEWER_HANDOFF
controller handoff: NO_CURRENT_CONTROLLER_HANDOFF
main result packet: NOT_PRESERVED_ON_MAIN
remote branch: origin/route_A
```

Route A remains historical/dormant provenance. Do not delete the remote branch unless the user later approves either preservation of its needed conclusions on `main` or loss of that branch-only evidence.

### Route B

```text
portfolio status: HISTORICAL_EVIDENCE_COMPLETE_NOT_ACTIVE
controller start authorized: false
critic handoff: NO_CURRENT_CRITIC_HANDOFF
review path: results/route_B/review.md
review token: ROUTE_B_ROUND04_REVIEW_EVIDENCE_COMPLETE
reviewer commit: 3950fe10ac31ef68da20f3ef7ffb001d6b17e6d9
reviewed controller repair: 2e24f290e83e356fbfba5f73da4fde98b657390b
validation_upload: false
hosted_metric_claim: false
m11_started: false
```

Route B Round04 controller and independent reviewer are complete for their controller/reviewer scope. This does not authorize route promotion, validation upload, M11, hosted metric claims, cross-route merge, final scientific decision, or new Route B controller work.

### Route C

```text
portfolio status: HISTORICAL_STOP_AND_HOLD_NOT_ACTIVE
controller start authorized: false
critic handoff: NO_CURRENT_CRITIC_HANDOFF
reviewer handoff: NO_CURRENT_REVIEWER_HANDOFF
controller handoff: NO_CURRENT_CONTROLLER_HANDOFF
review path: results/route_C/review.md
review token: ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
reviewer commit: 17062b00edc3443aacefe8583568797a9f2655ba
reviewed controller repair: 1e663cfa64f00413f005bef26310290fd43ec8ab
main visibility note: results/route_C/main_visibility_note.md
validation_upload: false
hosted_metric_claim: false
m11_started: false
```

Route C remains stopped/held as portfolio evidence. `prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md` authorizes no Route C Controller, changes no main authority, and makes no downstream scientific decision.

## Current role entries

```text
Route A critic: NO_CURRENT_CRITIC_HANDOFF
Route B critic: NO_CURRENT_CRITIC_HANDOFF
Route C critic: NO_CURRENT_CRITIC_HANDOFF
Route A reviewer: NO_CURRENT_REVIEWER_HANDOFF
Route B reviewer: NO_CURRENT_REVIEWER_HANDOFF
Route C reviewer: NO_CURRENT_REVIEWER_HANDOFF
Route A controller: NO_CURRENT_CONTROLLER_HANDOFF
Route B controller: NO_CURRENT_CONTROLLER_HANDOFF
Route C controller: NO_CURRENT_CONTROLLER_HANDOFF
```

## Main-only planning policy

Future GPT planning should focus on diagnosing and repairing the current `main` codebase, result interpretation, fair baseline comparison, validation packaging readiness, and small evidence-backed improvements. It must not create Round5, route promotion, validation upload, hosted metric claim, M11, or new route-controller work unless the user explicitly authorizes that scope.

If a future task needs historical route evidence, read the `main` packet first:

```text
results/route_B/
results/route_C/
prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md
```

Read `origin/route_A`, `origin/route_B`, or `origin/route_C` only as read-only provenance unless a later handoff explicitly reactivates that route.

## Authority boundary

```text
controller_authorized_now: 0
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
route_worktree_development_authorized: false
route_branch_deletion_authorized: false
```
