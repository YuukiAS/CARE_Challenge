# CARE Current Development State

This is the stable source of truth for the current CARE planning/development posture. Read this file first before writing CARE plans, Codex goals, route judgments, controller prompts, reviewer prompts, or handoffs.

## Active state

```text
state_id: srr_mainline_production_sprint_20260720
round_id: post_round04_main_only
date: 2026-07-20
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED_BY_USER_FOR_FIVE_DAY_SPRINT
single_active_scientific_line: SRR_MyoPS_Cine_from_historical_Route_B
controller_authorized_now: 0
route_worktree_development_authorized: false
route_branch_deletion_authorized: false
formal_training_authorized_today: false
slurm_authorized_today: false
```

Default future GPT/Codex work is `main`-only. Do not start Route A, Route B, or Route C controllers; do not continue route worktree development; do not open a new portfolio round; and do not use `/users/a/e/aereinh/CARE_worktrees/route_A`, `/users/a/e/aereinh/CARE_worktrees/route_B`, or `/users/a/e/aereinh/CARE_worktrees/route_C` for new implementation unless a later explicit human-approved handoff reactivates a named route.

Remote route branches are retained for provenance. They are not deleted and are not active development targets.

## User-authorized mainline sprint

The user explicitly decided on 2026-07-20 that only the scientific line inherited from Route B remains active. Route A is retired from active work, Route C remains historical evidence/hold, and all new SRR/MyoPS/Cine implementation is developed directly on `main`.

The following old cycle is suspended for this five-day deadline sprint:

```text
portfolio planner -> route critic -> route controller -> staged Slurm -> reviewer -> next round
```

The current development model is:

```text
one main integrator writes main
+ multiple exact-SHA read-only GPT/Codex audits
+ small sequential code-completion commits
+ append-only human-readable change ledger
+ code freeze before any real training
```

Today, 2026-07-20, formal training and Slurm are forbidden. Allowed work is production code completion, real-data loading/inference smoke, one-step forward/backward, checkpoint save/reload, nnU-Net metric reproduction, fair evaluator work, static/known-bad tests, documentation, commit and push.

## Active plan, TODO and change ledger

```text
active production plan:
docs/plans/laneB_round04_active_srr_mainline_production_execution.md
commit: 8b801e80472dba54c1bcee008f5c2525e9636723

active code-completion TODO:
docs/plans/laneB_round04_active_srr_code_completion_todo.md
commit: bde402a85fd11beca3f908e3e41c93d369f529d7

append-only change review ledger:
docs/plans/laneB_round04_active_srr_change_review_ledger.md
bootstrap commit: 1db3c46a3e51915eb51402bc894c2529f1cfa498
```

The `laneB_round04` filename prefix is retained only for compatibility with the existing plan registry and historical provenance. These documents do not open Round05 and do not reactivate a Route B controller.

Every implementation commit must append a ledger entry explaining exact changed files, behavior before/after, real dataflow, removed bypasses, commands/exits, hashes/shapes, unresolved items and the next allowed scope. A bare `PASS`, token, test count or packet completion statement is not an acceptable change report.

## Exact remote evidence bindings

```text
main_after_route_C_visibility_commit: 26a8d16d8d684551b6e90717ee6715d0d71b6a4d
main_only_protocol_commit: 74dadb1fe69f7d1c4a76aac5e32ea788212f8be1
main_default_test_fix_commit: af630ef017b87fe86b01d5fd8aaa44203c1aa6d4
Route B reviewer commit: 3950fe10ac31ef68da20f3ef7ffb001d6b17e6d9
Route B reviewed controller packet: 2e24f290e83e356fbfba5f73da4fde98b657390b
Route C evidence/review commit: 17062b00edc3443aacefe8583568797a9f2655ba
Route C reviewed controller repair: 1e663cfa64f00413f005bef26310290fd43ec8ab
Route C main visibility commit: 26a8d16d8d684551b6e90717ee6715d0d71b6a4d
```

Route B Round04 reviewer acceptance was operational only: job accounting, packet reviewability and current validators. It did not establish real CARE training, valid local Dice/HD/HD95, scientific superiority, hosted readiness or first-place capability. Old B3-B6/B8 scripts and proxy results must be treated as legacy/known-bad until the new production code explicitly reuses or replaces them.

Route C's reusable conclusion packet is preserved on `main` under `results/route_C/`, including `main_visibility_note.md`, `review.md`, `controller_report.md`, `result.md`, and selected Round03 terminal evidence. This preservation does not mean Route C is active, promoted, upload-authorized, or scientifically resolved.

## Portfolio state

```text
Route A: HISTORICAL_DORMANT_NOT_ACTIVE
Route B: HISTORICAL_EVIDENCE_MERGED_TO_MAIN_NOT_ACTIVE_AS_ROUTE
Route C: HISTORICAL_STOP_AND_HOLD_NOT_ACTIVE
SRR mainline: ACTIVE_CODE_COMPLETION_NO_TRAINING_TODAY
```

No route currently has controller authority. Route A/B/C evidence may be read as historical context, but future implementation and protocol maintenance target `main`.

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
portfolio status: HISTORICAL_EVIDENCE_MERGED_TO_MAIN_NOT_ACTIVE_AS_ROUTE
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

Route B Round04 is historical input to the new mainline production repair. Do not resume its old B0-B10 controller task graph.

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

Route C remains stopped/held as historical evidence. `prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md` authorizes no Route C Controller and makes no downstream scientific decision.

## Current execution order

```text
C0/C1: formal entrypoint + legacy/synthetic audit
-> C2/C3: real data + real nnU-Net anchor
-> C4/C5: one complete SRR production model
-> C6/C7/C8: real prototypes + losses + checkpoint continuity
-> C9/C10: real inference + fair evaluator
-> C11/C12: real Cine path
-> C13/C14: red-team + human-readable change ledger
-> only then discuss real training
```

The detailed acceptance requirements are in the active TODO. These are code/data facts, not route tokens.

## Multiple GPT/Codex participation

```text
Integrator: only writer to main
Model audit GPT: read-only, exact main SHA
Data/evaluation audit GPT: read-only, exact main SHA
Cine audit GPT: read-only, exact main SHA
Red-team GPT: read-only, exact main SHA
```

Audits must cite exact files, functions, observed behavior and reproduction commands. The integrator fixes findings in the next sequential commit and records the result in the change ledger. Do not create new critic/controller/reviewer handoffs for these audits.

## Scientific invariants

The active SRR mainline must preserve:

```text
[LGE,T2,C0] + explicit availability
modality-specific stems
four-scale shared/private/interaction retrieval
spatial/pathology-conditioned routing
real train/OOF prototypes and safe negatives
anatomy union/LV/RV
separate scar/edema proposals
separate soft-ROI refiners
no-T2 edema exact safety
bounded nnU-Net-anchored correction
real NIfTI inference
fair Dice/HD/HD95/component/remote-FP evaluation
real multi-frame Cine + registration + temporal aggregation
```

nnU-Net may be anchor/context/safety/baseline, but SRR must own real raw-modality retrieval, proposal, refiner and bounded final correction. SRR-off must reproduce nnU-Net exactly. SRR-on must be judged using the same split, label mapping, empty-GT rule, resampling, postprocessing and prediction-based evaluator.

## Current role entries

```text
portfolio planner handoff: NONE
Route A critic/controller/reviewer: NONE
Route B critic/controller/reviewer: NONE_FOR_NEW_EXECUTION
Route C critic/controller/reviewer: NONE
active mainline plan: docs/plans/laneB_round04_active_srr_mainline_production_execution.md
active code TODO: docs/plans/laneB_round04_active_srr_code_completion_todo.md
active change ledger: docs/plans/laneB_round04_active_srr_change_review_ledger.md
```

Old `prompts/routes/handoffs/route_B_round04_*` files are historical material and cannot start a new controller.

## Authority boundary

```text
controller_authorized_now: 0
formal_training_authorized_today: false
slurm_authorized_today: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
route_worktree_development_authorized: false
route_branch_deletion_authorized: false
```
