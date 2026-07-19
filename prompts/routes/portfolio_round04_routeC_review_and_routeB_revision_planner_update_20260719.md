---
document_type: portfolio_round04_planner_update
portfolio_round: round04
date: 2026-07-19
planner_branch: main
planner_base_main: 30098813522cecd98e60bcb99e2676b28c1a5461
origin_route_B: b9c7664da7cb1f1892fff37a4497722f31a0a96d
origin_route_C: 17062b00edc3443aacefe8583568797a9f2655ba
route_C_reviewed_controller_commit: 1e663cfa64f00413f005bef26310290fd43ec8ab
route_C_review_token: ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
route_C_portfolio_status: EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION
route_C_reviewer_required_now: false
route_B_revision_source_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
route_B_planning_status: REVISION_PENDING_COORDINATOR_RECEIPT_AND_CRITIC_REREVIEW
route_B_controller_authorized: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
---

# Portfolio Round04 update: Route C review accepted and Route B planning revised

## 1. Exact repository state used

```text
origin/main: 30098813522cecd98e60bcb99e2676b28c1a5461
origin/route_B: b9c7664da7cb1f1892fff37a4497722f31a0a96d
origin/route_C: 17062b00edc3443aacefe8583568797a9f2655ba
```

This update is planning-only and was authored from GitHub repository evidence. It did not access server shell, tmux, Slurm or a local worktree, and it did not perform implementation, training or reviewer work.

## 2. Route C decision

Route C Round03 has reached reviewer-accepted evidence completeness.

The independent review at `17062b00edc3443aacefe8583568797a9f2655ba` is bound to controller repair commit `1e663cfa64f00413f005bef26310290fd43ec8ab` and emits:

```text
ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
```

The review confirms that the old `positive_negative_prototype_swap` fail-open defect was repaired. The repaired validator detects the harmful swap, preserves zero-effect no-op/off-path controls, passes strict R1/R2/final packet validation, and passes the declared known-bad tests.

Current Route C portfolio state:

```text
EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION
```

Route C is not sent to another reviewer now. A new review is required only when a later Route C commit changes the reviewed packet, validator semantics or binding.

Route C remains evidence, not authority. It does not authorize route promotion, validation upload, M11, hosted metrics, cross-route merge or a final scientific decision.

## 3. Route B planning critic result

The Round04 scientific contract was accepted without downgrade, but the independent critic returned:

```text
ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
```

Hard blockers:

```text
CURRENT_NOT_ADVANCED_TO_ROUND04
B10_TERMINAL_FINALIZER_UNREACHABLE_ON_EARLY_TERMINAL_BRANCHES
PER_EXECUTOR_VALIDATOR_COMMANDS_NOT_MACHINE_BOUND
REQUIRED_USERS_EXECUTABLE_CHECKS_NOT_EXIT_ZERO
```

## 4. Route B revision summary

### Current-round handoff

`prompts/routes/handoffs/CURRENT.md` is advanced to Round04. The new Route B critic handoff binds:

- the exact containing planning commit;
- `b9c7664da7cb1f1892fff37a4497722f31a0a96d`;
- the six planning blobs;
- the coordinator receipt path;
- `prompts/routes/route_B_round04_critic_rereview.md`;
- `ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER` and `ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION`;
- the full authority boundary.

### Terminal finalizer

B10 is no longer downstream of successful B6/B9 merge receipts. It is a controller-level terminal finalizer launched from a terminal registry and controller ledger.

It covers:

```text
B0/B1/B2 global blockers
B3/B4/B5 MyoPS implementation terminal classes
B7 official-source or matching blockers
B8 faithful registration blocker without fabricated B9
B6/B9 successful terminal evidence
timeout
preemption
failed startup
cancelled or started race loser
```

All started attempts use `afterany` terminal accounting. No-start paths use deterministic local finalization.

### Exact validators

Every B0-B10 entry now binds exact strict validator and known-bad semantics:

```text
validator script and command
input directory
report file
expected success exit
success token
known-bad matrix path and command
known-bad report
runner success exit
per-fixture validator failure exit
exact failure keys
unexpected-pass failure
```

The controller cannot invent or substitute stage validators.

### Coordinator receipt

The Planner does not claim `/users` execution. A Codex coordinator must run the exact final-commit checks at `/users/a/e/aereinh/CARE` and fill `prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md` with current commit, commands, outputs and exit `0`. The next critic must stop if the receipt is pending, stale or nonzero.

## 5. Scientific contract preserved

The revision retains all Route B Round04 scientific requirements:

- Round03 B3 remains B3-only adequate negative.
- B4/B5/B6 remain mandatory after valid predecessors; B6 is the first MyoPS full-route judgment.
- B7/B8/B9 remain mandatory after B2 and are not removed by B3 or Route C completion.
- Full SRR-v3 four-scale shared/private/interaction retrieval is retained.
- OOF frozen prototypes, safe hard-negative queues, separate proposals/refiners and bounded correction are retained.
- Same-split nnU-Net baseline, case-wise help/harm and all required subgroups are retained.
- Official CineMA pretrained/matched-random, seven-step SVF, real SyN and registered temporal aggregation are retained.
- Fixed effective-training budgets and clean-reload evidence are retained.
- `htzhulab` default, isolated long-wait `htzhulab+a100-gpu` race and V100 unchanged-config memory gate are retained.
- Pending/submitted/running/awaiting-accounting/monitor/undertrained states remain non-completion.
- Controller continuity remains Codex goal/goal resume through terminal accounting, aggregation, packet update and reviewer handoff.

## 6. Next actors

```text
Route C: portfolio reconciliation input; no reviewer now.
Route B: Codex coordinator runs and fills current exit-zero receipt.
Route B after receipt: new independent planning critic rereview.
Route B controller: not authorized.
```

## 7. Authority boundary

Nothing in this update authorizes a controller, validation upload, route promotion, M11, hosted metric claim, cross-route merge or final scientific decision.
