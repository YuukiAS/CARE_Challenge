---
route_id: route_B
portfolio_round: round04
date: 2026-07-20
role: planning_critic_request_after_materialization_revision
planner_base_main: 64f5a27298cb2efd1f576a70296e49388ab0b717
revision_source_critic_commit: de5f47b9f4404c85db1bd0f570b576d9d03b0372
concurrent_architecture_context_commit: 64f5a27298cb2efd1f576a70296e49388ab0b717
route_B_evidence_ref: b9c7664da7cb1f1892fff37a4497722f31a0a96d
route_C_evidence_ref: 17062b00edc3443aacefe8583568797a9f2655ba
route_C_hold_decision_token: ROUTE_C_PORTFOLIO_STOP_AND_HOLD
revision_source_critic_blob: 4e5cd46a6494bd6c12f3985b99abd390a00b0786
revision_source_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
status: PENDING_COORDINATOR_RECEIPT_AND_CRITIC_REREVIEW
critic_handoff_path: prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
coordinator_receipt_path: prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
critic_output_path: prompts/routes/route_B_round04_critic_rereview.md
tested_commit_policy: exact_current_main_or_ancestor_with_allowlisted_diff_and_unchanged_six_blobs
six_planning_blob_binding_source: prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
six_planning_blob_binding_required: true
allowed_decision_tokens:
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

# Route B Round04 Independent Planning Critic Rereview Request

This is a separate planning critic task. It is not implementation, Controller runtime, Slurm execution or runtime review.

## Entry and binding

Read CURRENT first and then the current Route B handoff. The handoff must bind one planning commit and six planning blobs. This request binds those hashes through the current handoff rather than duplicating its own Git blob SHA inside itself; literal self-hash embedding would be a recursive Git-object cycle.

The coordinator tested commit is valid when:

```text
tested commit == current origin/main
or
tested commit is an ancestor of current origin/main,
every descendant path is in the explicit allowlist,
and all six planning blob hashes remain byte-identical
```

Reject non-ancestor relations, unreadable diffs, any disallowed descendant path, any changed planning blob, a missing or nonzero coordinator receipt, a dirty coordinator worktree receipt, or a stale Route B evidence ref.

Explicit descendant allowlist:

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

The Route C hold decision is portfolio context. Confirm that it authorizes no Route C controller, changes no Route B authority and does not remove Route B Cine work.

## Materialization review

Parse `controller_planning_materialization` in the controller contract and executor plan. Require all of these:

```text
controller worktree == /users/a/e/aereinh/CARE_worktrees/route_B
read-only source == /users/a/e/aereinh/CARE
fixed snapshot root == results/route_B/round04/planning_snapshot
atomic temporary-to-final rename
six planning files validated against handoff blob hashes
current critic rereview, handoff, coordinator receipt, CURRENT and Route C hold copied
MANIFEST.json, hash_audit.json, descendant_diff_audit.json and materialization_receipt.json required
final snapshot read-only
failure token == ROUTE_B_ROUND04_B0_STALE_PLANNING_BINDING
no code, Slurm, training or runtime review before PASS
```

An equivalent coordinator-provided snapshot is valid only under the identical paths, file set, hashes, receipts, permissions and controller revalidation.

## B0 exact-input review

Require B0 current exact inputs to contain:

```text
prompts/routes/route_B_round04_critic_rereview.md
prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
prompts/routes/handoffs/CURRENT.md
prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md
```

`prompts/routes/route_B_round04_critic_review.md` may appear only in a superseded historical-input field and cannot satisfy a current gate.

## Scientific non-regression

Reject any reduction of:

- four-scale `[32,64,128,256]` SRR-v3;
- `[LGE,T2,C0]` plus explicit availability;
- sixteen shared/private/interaction experts per scale and spatial/pathology-conditioned routing;
- optimized Pattern-SIP;
- four-shard fold-safe OOF-fitted inference-frozen prototype banks;
- training-only safe hard negatives and no-T2 edema exclusion;
- live learned anatomy;
- separate scar/edema proposal, soft ROI and refiner;
- bounded final correction and real final-output intervention;
- same-split nnU-Net baseline and case-wise hard-group evidence;
- official CineMA pretrained/matched-random control;
- seven-step SVF, true Jacobian, inverse consistency, real SyN and case denominators;
- registered temporal aggregation and complete controls;
- fixed budgets and selected-checkpoint clean reload.

Confirm that Round03 B3 is B3-only adequate negative, valid B3 advances B4, valid weak B4 advances B5, faithful weak B5 advances B6, B6 is the first MyoPS full-route judgment, and B7-B9 remain mandatory after B2.

## Terminal finalizer and validators

Require B10 `depends_on: []`, controller ownership, all-started-attempt `afterany`, local deterministic no-job path, atomic launch lock and coverage of global/lane blockers, success, timeout, preemption, failed startup and race losers.

For every B0-B10 executor, inspect the exact validator and known-bad command, report, exit, token and failure-key fields. B0 known-bad must cover source unreadability, snapshot incompleteness, hash mismatch, non-ready rereview, stale receipt and disallowed descendant path.

All formal Python commands use `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`.

## Slurm and continuity

Confirm `htzhulab` default, isolated long-wait `htzhulab+a100-gpu` race, V100 unchanged-config and `<=14.5 GiB` credit gate, zero-credit failed/partial/losing attempts, `afterok` training, `afterany` finalizer and Controller goal/goal-resume responsibility through accounting, aggregation, mapper final, packet commit and reviewer handoff.

Submitted, pending, running, awaiting-accounting, monitor and undertrained states are not completion.

## Allowed decisions

Write `ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER` only after the coordinator receipt and every planning requirement pass for the current binding. Otherwise write `ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION` with exact failed paths and fields.

Neither token authorizes validation upload, route promotion, M11, hosted metrics, cross-route merge or a final scientific decision.
