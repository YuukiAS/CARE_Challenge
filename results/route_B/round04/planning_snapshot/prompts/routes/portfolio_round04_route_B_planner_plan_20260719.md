---
route_id: route_B
portfolio_round: round04
date: 2026-07-20
role: portfolio_planner_revision_after_critic_rereview
planner_branch: main
planner_base_main: 64f5a27298cb2efd1f576a70296e49388ab0b717
revision_source_critic_commit: de5f47b9f4404c85db1bd0f570b576d9d03b0372
concurrent_architecture_context_commit: 64f5a27298cb2efd1f576a70296e49388ab0b717
revision_source_critic_path: prompts/routes/route_B_round04_critic_rereview.md
revision_source_critic_blob: 4e5cd46a6494bd6c12f3985b99abd390a00b0786
revision_source_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
route_B_evidence_ref: b9c7664da7cb1f1892fff37a4497722f31a0a96d
route_C_review_commit: 17062b00edc3443aacefe8583568797a9f2655ba
route_C_reviewed_controller_commit: 1e663cfa64f00413f005bef26310290fd43ec8ab
route_C_review_token: ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
route_C_followup_decision_path: prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md
route_C_followup_decision_blob: 6564e1d6423b43b44a0c96b510a172fb92785873
route_C_followup_decision_token: ROUTE_C_PORTFOLIO_STOP_AND_HOLD
status: PLANNING_REVISION_PENDING_COORDINATOR_RECEIPT_AND_CRITIC_REREVIEW
controller_start_authorized: false
required_coordinator_receipt: prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
required_critic_output: prompts/routes/route_B_round04_critic_rereview.md
required_critic_token: ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_CURRENT_CONVERSATION_PROJECT_MATERIALS
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
---

# CARE Route B Round04 planner revision after critic rereview

## 1. Decision and scope

The revision source critic is bound to `de5f47b9f4404c85db1bd0f570b576d9d03b0372`. Before publication, `origin/main` advanced to `64f5a27298cb2efd1f576a70296e49388ab0b717` through the allowlisted `docs/figures/round03_route_architecture/**` architecture audit only. The updated report was read; it confirms the same B3-only evidence boundary and full Round04 target, so the new planning parent is the later commit.

This pass repairs only the four controller-forward binding blockers in the independent planning critic rereview at `de5f47b9f4404c85db1bd0f570b576d9d03b0372`. It does not change the accepted scientific contract, execute implementation, train, submit Slurm, start a controller, start a runtime reviewer, package validation, upload validation, promote a route, start M11, merge routes, claim hosted metrics, or make a final scientific decision.

The current state remains:

```text
Route B planning: revision pending coordinator receipt and independent critic rereview
Route C: ROUTE_C_PORTFOLIO_STOP_AND_HOLD
controller_authorized_now: 0
```

Route C hold is now explicit portfolio context. It records that Route C is evidence-complete and held, does not authorize a Route C controller, does not alter Route B scientific scope, and does not remove the mandatory Route B Cine lane.

## 2. Route objective recovered from SRR-v2, SRR-v2.5 and SRR-v3

MyoPS remains:

```text
observed [LGE,T2,C0] plus explicit availability
-> four-scale modality-specific encoding [32,64,128,256]
-> sixteen shared/private/interaction experts at every scale
-> spatial/pathology-conditioned two-pass retrieval and optimized Pattern-SIP
-> learned union/LV/RV anatomy support
-> four-shard fold-safe OOF-fitted inference-frozen prototypes
-> training-only safe hard-negative queues
-> separate scar and edema proposal heads
-> separate pathology-specific soft ROIs and refiners
-> bounded correction over nnU-Net anchor/context/safety evidence
-> official six-label reconstruction
-> fresh same-split case-wise evaluation and real final-output interventions
```

Cine remains:

```text
official CineMA pretrained source and architecture-matched random control
-> per-frame multiclass logits/features/probabilities/uncertainty
-> ED/reference and fixed key-frame provenance
-> learned stationary velocity with seven-step scaling-and-squaring
-> true Jacobian, inverse consistency and independently generated real SyN
-> registered anatomy/features/motion/Jacobian/quality evidence
-> registered temporal aggregation
-> same-case controls and ED-space final output
```

Route B is not Route A, nnU-Net-only, postprocess-only, wrapper-only, validator-only, proxy-only, single-frame-only or declaration-only.

## 3. Critic rereview blockers and exact repairs

### 3.1 Concurrent main movement

`prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md` is added to the explicit Round04 descendant allowlist. Its meaning is fixed:

```text
decision: ROUTE_C_PORTFOLIO_STOP_AND_HOLD
Route C controller authorized: false
Route B controller authority changed: false
Route B scientific contract changed: false
```

The unified tested-commit rule is:

```text
accept when tested commit == current origin/main
or
accept when tested commit is an ancestor of current origin/main,
the descendant diff contains only explicit allowlist paths,
and every one of the six Route B planning blob hashes remains unchanged
```

Any other descendant path, any six-blob change, a non-ancestor tested commit or an unreadable diff is stale.

Explicit allowlist:

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

### 3.2 Immutable planning materialization

The future controller runs only in:

```text
/users/a/e/aereinh/CARE_worktrees/route_B
```

The read-only planning source is:

```text
/users/a/e/aereinh/CARE
```

The controller may consume an equivalent immutable snapshot produced by the coordinator, but the resulting snapshot paths, manifest fields, hashes and failure behavior are identical.

Before B0 writes code, starts a worker, submits Slurm, trains, or requests runtime review, the controller executes the exact `controller_planning_materialization` contract in the controller contract and executor plan. It copies the current gate files and the six planning files into:

```text
results/route_B/round04/planning_snapshot/
```

Required snapshot outputs:

```text
results/route_B/round04/planning_snapshot/MANIFEST.json
results/route_B/round04/planning_snapshot/hash_audit.json
results/route_B/round04/planning_snapshot/descendant_diff_audit.json
results/route_B/round04/planning_snapshot/materialization_receipt.json
```

The six planning files are validated against the current handoff hashes. The critic rereview, current handoff, coordinator receipt, CURRENT and Route C hold decision are validated from the accepted current-main gate state. Snapshot files become read-only after the atomic rename.

Source unreadability, incomplete snapshot, hash mismatch, disallowed descendant path, missing current rereview, non-ready critic token or stale receipt returns:

```text
ROUTE_B_ROUND04_B0_STALE_PLANNING_BINDING
```

No later stage starts.

### 3.3 B0 current gate inputs

B0 current exact inputs now include:

```text
prompts/routes/route_B_round04_critic_rereview.md
prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
prompts/routes/handoffs/CURRENT.md
prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md
```

`prompts/routes/route_B_round04_critic_review.md` is retained only as superseded historical context and cannot satisfy the current controller gate.

### 3.4 Unified receipt and controller entry policy

CURRENT, handoff, coordinator receipt, critic request, controller contract and executor plan use the same exact-or-ancestor-with-allowlist rule. No file requires strict current-main equality while another accepts a declared ancestor. The six planning blobs remain immutable under both branches of the rule.

## 4. Frozen Round03 interpretation

Round03 B3 reached `43003` optimizer steps, `1800.7964860140346` train-loop seconds and `22` validation events. It passed finite loss, loss decrease, exact `E,E,S,R` sampling, invalid-slot zero and no-T2 edema zero, but failed `anatomy_union_overfit`.

This is adequate negative evidence for the old B3 gate only. B4-B9 did not execute. Therefore:

- B1 retains the repaired anatomy micro-overfit implementation gate.
- B3 is representation readiness and cannot terminate the full route.
- A valid B3 continues to B4.
- A valid weak B4 continues to B5 through the conservative soft-ROI control.
- A faithful weak B5 continues to B6.
- B6 is the first MyoPS full-route scientific classification.
- B7-B9 remain mandatory after B2 and run independently of B3 and Route C hold.

## 5. Frozen scientific contract

### 5.1 MyoPS

Canonical modality order is `[LGE,T2,C0]`; availability is explicit. Missing inputs are masked before and after modality stems and in every private/interaction route.

Each scale has sixteen experts:

```text
4 shared
2 LGE-private
2 T2-private
2 C0-private
2 LGE-T2 interaction
2 LGE-C0 interaction
2 T2-C0 interaction
```

Pattern-SIP family targets remain `.50/.35/.15`, coverage floors remain `.60/.25/.20`, and the optimized coefficient schedule remains frozen.

Anatomy targets remain:

```text
Y_union = 1[label in {1,4,5}]
Y_LV    = 1[label == 2]
Y_RV    = 1[label == 3]
```

Prototypes remain four-shard, fold-safe, OOF-fitted, inference-frozen and serialized with source/checkpoint/split/tensor hashes. Current-case, validation-label and test-label leakage is forbidden. Formal inference cannot use bootstrap or online EMA prototypes.

The training-only hard-negative queue retains 256 component centroids per pathology per scale. No-T2 myocardium and unknown edema-status tissue cannot enter edema negatives.

Scar and edema use separate proposal heads, separate soft ROI geometry and separate refiners. No-T2 edema loss, bank update, queue update, proposal, ROI, refiner, gate, delta and Route-B-owned final change are exactly zero.

Final correction remains:

```text
delta_p   = 4.0 * tanh(refiner_logit_p - anchor_logit_p)
z_final_p = z_anchor_p + roi_p * gate_p * delta_p
```

### 5.2 Cine

Pinned source remains:

```text
repository: mathpluscode/CineMA
code commit: c10daa1d93f0ea28d8b9ad9206b0f673d25805c1
Hugging Face revision: b1251ee50423bceeca84c080782fc3bc7756dea6
weight: finetuned/segmentation/acdc_sax/acdc_sax_0.safetensors
weight SHA256: c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f
model: cinema.segmentation.convunetr.ConvUNetR
license: MIT
```

Pretrained and random lanes retain identical architecture, parameter names/shapes, trainable masks, cases, frames, augmentation draws, optimizer, schedule, downstream initialization, cadence, selector and decode. Only source initialization differs.

Registration retains symmetric stationary velocity, exactly seven scaling-and-squaring steps, true voxel-coordinate Jacobian, folding rate, inverse composition, full loss, independent real SyN, pair receipts, case aggregation, full denominators and clean selected-checkpoint reload.

Temporal retains explicit consumption of registered logits/features/uncertainty, velocity, integrated displacement, Jacobian, motion magnitude, texture residual, frame quality, temporal position and valid-frame mask. Every field requires a consumption hook and final-output intervention.

## 6. Fixed budgets and progression

| Stage | Optimizer steps | Minimum train-loop seconds | Validation events | Evaluation floor |
|---|---:|---:|---:|---|
| B1 | 2,000 | 600 | 4 | two train-only anatomy cases |
| B3 | 6,000 | 1,800 | 3 | 44-case manifest |
| B4 | 8,000 | 2,400 | 4 | 44-case manifest |
| B5 | 10,000 | 3,000 | 5 | 44-case manifest |
| B6 | 8,000 | 2,400 | 4 | four full-case events, 44 cases |
| B7 pretrained | 8,000 | 3,600 | 4 | four events, 12 cases |
| B7 random | 8,000 | 3,600 | 4 | four events, 12 cases |
| B8 | 25,000 | 7,200 | 10 | four events, 12 cases, at least 60 pairs |
| B9 | 20,000 cumulative | 7,200 | 10 | four events, 12 cases |

Every selected checkpoint is clean-reloaded. Failed startup, timeout, preemption, incomplete chunk, race loss and partial checkpoint receive zero scientific credit.

## 7. Same-split and challenge-facing evidence

B6 reports per-case anchor/model Dice, HD95, remote FP, component count, volume ratio, lesion-wise recall, changed logits/voxels/components and help/harm/severe-harm. Required groups are scar-positive, T2-present edema-positive, no-T2 safety, CenterB, CenterC, complete tri-modal, remote-FP-positive and high-component-burden.

B9 compares reference-only, unregistered multi-frame, registered temporal, router-off, motion/Jacobian-off, anatomy-off, uncertainty/quality-off, matched-random, learned-SVF and real-SyN on identical cases, frames, downstream checkpoint and decode.

Local results are not hosted metrics.

## 8. Slurm and continuity

- Formal command interpreter is `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`.
- `htzhulab` is the default partition.
- A materially long compatible wait triggers an isolated `htzhulab+a100-gpu` race.
- Race attempts retain identical scientific hashes and separate output/log/checkpoint/cache roots.
- One atomic winner lock assigns credit; pending losers are cancelled; all losers receive zero credit and remain in accounting.
- V100 credit requires an unchanged scientific configuration and measured peak memory at most `14.5 GiB`.
- Training dependencies use `afterok`; terminal accounting uses `afterany`.
- Submitted, pending, running, awaiting-accounting, monitor and undertrained states are not completion.
- The controller runs as a Codex goal or goal resume through terminal accounting, post-completion aggregation, mapper final, packet validation, local lightweight commit and reviewer handoff.
- Runtime roles do not push and do not write `review.md`.

## 9. B10 and independent review

B10 remains a controller-level terminal finalizer with `depends_on: []`. It consumes the controller terminal registry and all started attempt IDs, covers global and lane-local blockers, success, timeout, preemption, failed startup and race losers, and uses `afterany` for all started attempts. When no Slurm attempt started, it uses the deterministic local finalizer path.

The next independent planning critic remains mandatory. Planner publication and coordinator validation do not authorize the controller.

## 10. Authority boundary

```text
controller_authorized_now: 0
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
```
