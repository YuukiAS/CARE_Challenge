---
task_key: route_B_round04_full_srr_v3_leaderboard_implementation
route_id: route_B
portfolio_round: round04
date: 2026-07-20
risk_level: high
task_kind: scientific_route
route_round_not_milestone: true
route_change: true
scientific_decision_scope: mechanism_signal
planning_review_required: true
planning_reviewer: separate_gpt_thread
planning_review_path: prompts/routes/route_B_round04_critic_rereview.md
planning_review_token: ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
planning_commit_binding_mode: handoff_planning_commit_plus_six_blobs
coordinator_receipt_path: prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
tested_commit_policy: exact_current_main_or_ancestor_with_allowlisted_diff_and_unchanged_six_blobs
execution_mode: controller_supervised
requires_execution_controller: true
executor_plan_path: prompts/routes/route_B_round04_executor_plan.yaml
executor_count: 11
executor_slots: 2
parallel_execution_allowed: true
merge_owner: controller
mapper_slots: 1
mapper_required: true
route_local_mapper_receipt_required: true
architecture_impact: system
wiki_update_required: false
diagram_update_required: true
wiki_deferral_reason: route-local candidate remains unreviewed until portfolio reconciliation
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
reviewer: separate_readonly
review_mode: independent_thread
planner_base_main: 64f5a27298cb2efd1f576a70296e49388ab0b717
revision_source_critic_commit: de5f47b9f4404c85db1bd0f570b576d9d03b0372
concurrent_architecture_context_commit: 64f5a27298cb2efd1f576a70296e49388ab0b717
revision_source_critic_blob: 4e5cd46a6494bd6c12f3985b99abd390a00b0786
revision_source_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
route_evidence_ref: b9c7664da7cb1f1892fff37a4497722f31a0a96d
inherited_review_token: ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE
route_C_hold_decision_token: ROUTE_C_PORTFOLIO_STOP_AND_HOLD
controller_start_authorized: false
required_final_controller_token: ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# Route B Round04 Controller Contract

## 0. Non-executable status

This is a planning contract. A future controller may start only after all of these conditions hold:

```text
CURRENT points to the current Route B Round04 critic handoff
the current critic rereview contains ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
the critic binds the handoff planning commit and all six planning blobs
the coordinator receipt contains READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
every coordinator required exit is 0
origin/route_B == b9c7664da7cb1f1892fff37a4497722f31a0a96d
current branch == route_B
controller worktree == /users/a/e/aereinh/CARE_worktrees/route_B
route_B worktree is clean before materialization
```

The tested coordinator commit is accepted when it equals current `origin/main`, or when it is an ancestor and the complete descendant diff is limited to the explicit allowlist while all six planning blobs remain unchanged. No other relation is accepted.

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

`prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md` is Route C hold context only. It authorizes no Route C controller, changes no Route B authority and removes no Route B stage.

Any entry mismatch returns `ROUTE_B_ROUND04_STALE_PLANNING_BINDING`. Snapshot-specific failure returns `ROUTE_B_ROUND04_B0_STALE_PLANNING_BINDING`.

Before executing the scientific task, enforce the hard-gate policy: exact task graph, agent-flow v2 execution contract, strict validator, completion-check-before-final-audit, minimum effective training, current-bad-packet regression, mapper/wiki/fingerprint gates when architecture is affected, and SRR diagram-bootstrap evidence when the task touches SRR/MyoPS/Cine route planning. A failed hard gate stops with NEEDS_REVISION or NEEDS_EVIDENCE and does not continue to final audit.

The controller runs only as a Codex goal or goal resume. Runtime roles do not push, do not write `review.md`, and do not authorize downstream scientific action.

## 1. Controller planning materialization

Machine source is `controller_planning_materialization` in `prompts/routes/route_B_round04_executor_plan.yaml`.

Fixed locations:

```text
controller worktree: /users/a/e/aereinh/CARE_worktrees/route_B
read-only planning source: /users/a/e/aereinh/CARE
snapshot root: /users/a/e/aereinh/CARE_worktrees/route_B/results/route_B/round04/planning_snapshot
temporary root: /users/a/e/aereinh/CARE_worktrees/route_B/results/route_B/round04/planning_snapshot.tmp
manifest: results/route_B/round04/planning_snapshot/MANIFEST.json
hash audit: results/route_B/round04/planning_snapshot/hash_audit.json
descendant audit: results/route_B/round04/planning_snapshot/descendant_diff_audit.json
receipt: results/route_B/round04/planning_snapshot/materialization_receipt.json
failure token: ROUTE_B_ROUND04_B0_STALE_PLANNING_BINDING
```

The controller performs this phase before preparing any executor wave, editing code, submitting Slurm, training, aggregating runtime evidence or requesting review.

Exact ordered actions:

1. `git -C /users/a/e/aereinh/CARE fetch --all --prune`.
2. Resolve current `origin/main`, handoff planning commit, six bound blob hashes, coordinator tested commit and current critic token.
3. Apply the exact-or-ancestor-with-allowlist policy. Record every descendant path and its allowlist match.
4. Verify read access to every required source file.
5. Copy all snapshot files into the temporary root while preserving repository-relative paths.
6. Hash every copied file with Git blob SHA and SHA256.
7. Verify the six planning Git blob SHAs against the handoff.
8. Verify the current critic rereview contains the ready token and binds the same planning commit and six blobs.
9. Verify the current handoff and coordinator receipt agree on tested-commit policy, evidence refs, six blobs and authority boundary.
10. Write all four receipts, recursively remove write permissions from snapshot contents, and atomically rename the temporary root to the fixed snapshot root.
11. Re-read the snapshot receipts from the route_B worktree and require status `PASS`.

Snapshot file set:

```text
prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md
prompts/routes/route_B_round04_planner_prompt.md
prompts/routes/route_B_round04_controller_contract.md
prompts/routes/route_B_round04_executor_plan.yaml
prompts/routes/route_B_round04_critic_request.md
prompts/routes/route_B_round04_planner_audit.md
prompts/routes/route_B_round04_critic_rereview.md
prompts/routes/handoffs/CURRENT.md
prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md
```

`prompts/routes/route_B_round04_critic_review.md` is not a current gate input. It may be copied only under `planning_snapshot/superseded_history/` and must be marked `superseded: true`.

Any unreadable source, non-ancestor relation, disallowed descendant path, missing file, incomplete copy, six-blob mismatch, non-ready critic token, stale receipt, manifest mismatch or writable final snapshot returns `ROUTE_B_ROUND04_B0_STALE_PLANNING_BINDING`. No executor launches.

An equivalent immutable snapshot created by the coordinator is accepted only when it has the identical fixed snapshot root, file set, four receipt paths, hash semantics, read-only permissions and PASS status. The controller still revalidates it before B0.

## 2. Frozen evidence interpretation

Round03 B3 is adequate negative evidence for the old B3 gate only:

```text
optimizer steps: 43003
train-loop seconds: 1800.7964860140346
validation events: 22
sampler: E,E,S,R
passed: finite loss, loss decrease, exact sampler, invalid-slot zero, no-T2 edema zero
failed: anatomy_union_overfit
```

Round03 runtime gives zero Round04 training credit. B4-B9 were not executed and cannot be described as failed.

## 3. Scientific objective

Primary targets are `myops_scar`, `myops_edema` and `myocardium_cinemyops`.

MyoPS path:

```text
[LGE,T2,C0] plus availability
-> four-scale modality-specific stems
-> sixteen shared/private/interaction experts per scale
-> spatial/pathology-conditioned two-pass entmax routing
-> optimized Pattern-SIP
-> live learned union/LV/RV anatomy
-> four-shard OOF frozen prototypes and safe hard negatives
-> separate scar and edema proposals
-> separate pathology-specific soft ROIs and refiners
-> bounded correction over nnU-Net anchor/context/safety evidence
-> official six-label reconstruction
-> same-split case-wise evaluation and final-output interventions
```

Cine path:

```text
official CineMA pretrained and architecture-matched random control
-> multiclass logits/features/probabilities/uncertainty
-> ED/reference and fixed key frames
-> learned seven-step SVF and independently generated real SyN
-> registered anatomy/features/motion/Jacobian/quality
-> registered temporal aggregation
-> ED-space output and same-case controls
```

Forbidden substitutes include nnU-Net-only output, postprocessing-only output, internal fake CineMA, direct velocity as displacement, proxy Jacobian, proxy SyN, frame0-only primary output, abstract latent without named temporal fields, placeholder tables and contract-only JSON.

## 4. Route-local write boundary

Authorized paths:

```text
src/care_myocardium/route_B_round04/
configs/route_B_round04/
scripts/route_B_round04/
scripts/training/route_B_round04/
scripts/evaluation/route_B_round04/
scripts/validation/route_B_round04/
tests/route_B_round04/
jobs/route_B_round04/
results/route_B/round04/
```

The immutable planning snapshot is controller-owned and read-only after materialization. Executors cannot edit it. Shared model/Cine/anchor/loss/refiner paths and root wiki/current-state are read-only. A required shared-source edit returns `ROUTE_B_ROUND04_NEEDS_PLANNER_SCOPE_REVISION`.

Required controller and mapper receipts:

```text
results/route_B/round04/controller_context.json
results/route_B/round04/controller_ledger.csv
results/route_B/round04/controller_terminal_registry.json
results/route_B/round04/controller_bootstrap_snapshot.md
results/route_B/round04/implementation_snapshot.md
results/route_B/round04/mapper_report_draft.md
results/route_B/round04/architecture_delta_draft.md
results/route_B/round04/mapper_report_final.md
results/route_B/round04/architecture_delta_final.md
results/route_B/round04/finalizer_state.json
```

Root current-state files do not advance before portfolio reconciliation.

## 5. Exact MyoPS model

Input is `[B,3,Z,H,W]` in `[LGE,T2,C0]` order with explicit `[B,3]` availability. Missing modalities are masked before and after stems and in every private/interaction path.

Scale channels are `[32,64,128,256]`. Each scale has:

```text
4 shared
2 LGE-private
2 T2-private
2 C0-private
2 LGE-T2 interaction
2 LGE-C0 interaction
2 T2-C0 interaction
```

Task family masks:

```text
anatomy: shared + C0-private + LGE-C0 + T2-C0
scar: shared + LGE-private + LGE-T2 + LGE-C0
edema: shared + T2-private + LGE-T2 + T2-C0
```

The two-pass router consumes local observed-modality features, availability, anatomy union/distance, anchor entropy/pathology/component/remote-FP evidence and second-pass proposal logits. Entmax-1.5 schedules valid top-all, top-4 and top-2. Invalid logits are `-1e4`; maximum invalid absolute weight is `1e-8`.

Pattern-SIP:

```text
family target mass: shared=.50, private=.35, interaction=.15
coverage floors: shared=.60, private=.25, interaction=.20
loss: mass + .50*integrative + .25*load + .10*sparse
coefficient: 0 at steps 0-999; ramp to .02 at 2000; .05 proposal/refiner; .02 joint
```

Anatomy targets:

```text
Y_union = 1[label in {1,4,5}]
Y_LV    = 1[label == 2]
Y_RV    = 1[label == 3]
```

The anatomy decoder consumes routed anatomy plus a masked valid-modality lateral feature. Localization support is `max(p_learned_union, 0.5 * stop_gradient(p_anchor_union))`; both branches remain separately observable and learned anatomy requires nonzero final-path intervention.

Formal prototype banks use four deterministic OOF shards. Per scale/pathology: scar positive 8, scar negative 12, edema positive 8, edema safe-negative 12. Current-case, validation-label and test-label leakage is forbidden. Bootstrap and online EMA banks cannot enter formal inference. The training-only queue holds 256 component centroids per pathology per scale, and no-T2 myocardium cannot enter edema negatives.

Scar and edema retain separate proposal heads, soft ROI geometry and refiners. Scar uses three residual blocks with dilations `[1,2,3]`; edema uses four with `[1,2,4,6]`. Soft ROI cannot hard-delete predictions. A weak but valid proposal advances through the fixed conservative anatomy-neighborhood control.

Bounded final composition:

```text
delta_p   = 4.0 * tanh(refiner_logit_p - anchor_logit_p)
z_final_p = z_anchor_p + roi_p * gate_p * delta_p
```

No-T2 edema loss, bank/queue update, proposal, ROI, refiner, gate, delta and Route-B-owned change are exactly zero.

## 6. Exact Cine model

Pinned source:

```text
repository: mathpluscode/CineMA
code commit: c10daa1d93f0ea28d8b9ad9206b0f673d25805c1
Hugging Face revision: b1251ee50423bceeca84c080782fc3bc7756dea6
weight: finetuned/segmentation/acdc_sax/acdc_sax_0.safetensors
weight SHA256: c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f
model: cinema.segmentation.convunetr.ConvUNetR
license: MIT
```

Pretrained/random matching holds architecture, parameter names/shapes, trainable masks, cases, frames, augmentation draws, optimizer, budget, cadence, downstream initialization, selector and decode fixed. Only source initialization differs.

Learned registration emits stationary velocity. Forward and inverse transforms each use exactly seven scaling-and-squaring steps. Images/probabilities/features use trilinear interpolation, labels use nearest interpolation, padding is border. True Jacobian is computed in voxel coordinates. Full loss contains LNCC, soft anatomy Dice, velocity smoothness, negative-Jacobian penalty, inverse composition and feature consistency. Real SyN is independently generated and hashed on identical pairs.

Pair gate: folding fraction at most `.005`, positive minimum Jacobian, inverse-composition error at most `1.5` voxels, warped anatomy Dice no worse than unregistered by more than `.01`. Case gate: at least `80%` pair pass and four passed non-reference frames. Aggregate learned gate: at least `90%` of 12 cases. Learned failure with real-SyN pass routes B9 through SyN and preserves learned negative evidence. Failure of both methods creates the faithful B8 blocker and does not fabricate B9.

Temporal inputs are explicit and mandatory: reference and registered logits/features/uncertainty, velocity, integrated displacement, Jacobian, motion magnitude, texture residual, frame quality, temporal position and valid-frame mask. Every field has consumption and final-output intervention evidence.

## 7. Stage graph and budgets

```text
B0 -> B1 -> B2
B2 -> B3 -> B4 -> B5 -> B6
B2 -> B7 -> B8 -> B9
controller terminal registry -> B10 for every terminal class
```

B3/B7, B4/B8 and B5/B9 use isolated two-slot waves. MyoPS and Cine remain sequential inside each lane.

| Stage | Steps | Minimum seconds | Validation events | Evaluation floor |
|---|---:|---:|---:|---|
| B1 | 2,000 | 600 | 4 | two train-only cases |
| B3 | 6,000 | 1,800 | 3 | 44 cases |
| B4 | 8,000 | 2,400 | 4 | 44 cases |
| B5 | 10,000 | 3,000 | 5 | 44 cases |
| B6 | 8,000 | 2,400 | 4 | four events, 44 cases |
| B7 pretrained | 8,000 | 3,600 | 4 | four events, 12 cases |
| B7 random | 8,000 | 3,600 | 4 | four events, 12 cases |
| B8 | 25,000 | 7,200 | 10 | four events, 12 cases, 60 pairs |
| B9 | 20,000 cumulative | 7,200 | 10 | four events, 12 cases |

Every selected checkpoint is clean-reloaded. Failed startup, timeout, preemption, incomplete chunk, race loss and partial checkpoint receive zero credit.

## 8. Same-split evidence and interventions

B6 produces fresh forced 44-case predictions and case-wise baseline/model Dice, HD95, remote FP, component count, volume ratio, lesion-wise recall, changed logits/voxels/components and help/harm/severe-harm. Groups: scar-positive, T2-present edema-positive, no-T2 safety, CenterB, CenterC, complete tri-modal, remote-FP-positive and high-component-burden.

MyoPS interventions: learned anatomy off, anchor support floor off, prototype similarity off, hard-negative refresh off, interaction experts off, Pattern-SIP off, proposal off, scar refiner off, edema refiner off, both refiners off, bounded correction off and nnU-Net context off.

Cine controls: reference-only, unregistered multi-frame, registered temporal full, temporal router off, motion/Jacobian off, anatomy evidence off, uncertainty/quality off, matched random, learned SVF and real SyN.

Every intervention uses the same selected/reloaded checkpoint, cases, frames and decode, and records final-label effects rather than renamed summaries.

## 9. Slurm and continuity

Formal Python is `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`. Compute-node preflight records Python, torch, CUDA, optimizer construction, semantic config, scientific hashes and writable roots.

`htzhulab` is default. A materially long compatible wait requires an isolated `htzhulab+a100-gpu` race with identical scientific hashes, separate output/log/checkpoint/cache roots, one atomic winner lock, immediate pending-loser cancellation, zero-credit losers and full accounting. V100 credit requires an unchanged scientific configuration and measured peak memory at most `14.5 GiB`.

Training dependencies use `afterok`; B10 uses `afterany`. Submitted, pending, running, awaiting-accounting, monitor, timeout, preemption and partial states are not completion. Same-scope operational retry preserves scientific hashes and records all attempts.

## 10. B10 terminal finalizer

B10 is outside the successful merge DAG and has `depends_on: []`. The controller records every outcome in `results/route_B/round04/controller_terminal_registry.json` and every attempt in `results/route_B/round04/controller_ledger.csv`.

B0/B1/B2 global blockers launch B10 immediately. After B2, B10 waits for one terminal class from each lane. B3/B4/B5 revision terminates MyoPS only; B7 external/matching blocker or faithful B8 registration blocker terminates Cine only. B6 and B9 are normal terminal classes.

B10 uses `afterany` over all started attempts; with no started attempt it uses local deterministic finalization. An atomic launch lock prevents duplicate finalization. It performs terminal accounting, post-completion aggregation, retry/race reconciliation, mapper final, strict validators and known-bad matrices, diff/heavy-artifact/authority scans, completion check, review request and one local lightweight packet commit.

## 11. Validator contract

The executor plan is the machine source. Every B0-B10 entry binds:

```text
validator script
exact command
input directory
report path
expected exit 0
success token
known-bad matrix
exact matrix command
matrix report
runner exit 0
per-fixture validator exit 1
exact failure keys
all keys required
unexpected fixture pass is failure
```

B0 additionally requires failure keys for unreadable source, incomplete snapshot, hash mismatch, non-ready critic, stale receipt and disallowed descendant path.

## 12. Reviewer and authority boundary

B10 controller report before review uses:

```text
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
git_push_decision: SKIP_PUSH
```

The independent runtime reviewer starts after the local packet commit. Evidence completeness or an adequate negative does not promote the route.

This contract does not authorize validation packaging/upload, route promotion, M11, hosted metric claims, cross-route merge or final scientific decision.
