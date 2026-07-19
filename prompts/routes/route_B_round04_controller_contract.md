---
task_key: route_B_round04_full_srr_v3_leaderboard_implementation
route_id: route_B
portfolio_round: round04
date: 2026-07-19
risk_level: high
task_kind: scientific_route
route_round_not_milestone: true
route_change: true
scientific_decision_scope: mechanism_signal
planning_review_required: true
planning_reviewer: separate_gpt_thread
planning_review_path: prompts/routes/route_B_round04_critic_rereview.md
planning_review_token: ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
planning_commit_binding_mode: exact_planning_commit_and_six_blobs_from_current_handoff
coordinator_receipt_path: prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
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
planner_base_main: 30098813522cecd98e60bcb99e2676b28c1a5461
revision_source_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
route_evidence_ref: b9c7664da7cb1f1892fff37a4497722f31a0a96d
inherited_review_token: ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE
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

## 0. Non-executable status and entry gate

This file is a planning contract. It is not executable until a separate Route B planning critic writes `ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER` in `prompts/routes/route_B_round04_critic_rereview.md` and binds the exact current handoff planning commit and six planning blobs.

Before any implementation or Slurm action, the future controller must verify:

```text
CURRENT.md points to the current Round04 Route B critic handoff
critic token == ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
critic reviewed planning commit == handoff planning commit
six planning blobs == handoff blobs
coordinator receipt status == READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
coordinator tested commit == current origin/main
origin/route_B contains b9c7664da7cb1f1892fff37a4497722f31a0a96d
results/route_B/review.md contains ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE
current branch == route_B
worktree clean
```

Any mismatch returns `ROUTE_B_ROUND04_STALE_PLANNING_BINDING` before code, training or Slurm.

Before executing the scientific task, enforce the hard-gate policy: exact task graph, agent-flow v2 execution contract, strict validator, completion-check-before-final-audit, minimum effective training, current-bad-packet regression, mapper/wiki/fingerprint gates when architecture is affected, and SRR diagram-bootstrap evidence when the task touches SRR/MyoPS/Cine route planning. If any hard gate fails, stop with NEEDS_REVISION or NEEDS_EVIDENCE; do not continue to final audit.

The controller runs only as a Codex goal or goal resume. Runtime roles do not push, do not write `review.md`, and do not authorize any downstream scientific action.

## 1. Frozen evidence interpretation

The inherited Route B Round03 review is an adequate negative for the B3 evidence-warmup gate, not for the full Route B route. Historical facts after B0 fingerprint verification:

```text
optimizer steps: 43003
train-loop seconds: 1800.7964860140346
validation events: 22
sampler: E,E,S,R
sampler counts: E=21502, S=10751, R=10750
passed: finite loss, loss decrease, invalid-slot zero, no-T2 edema zero, exact sampler
failed: anatomy_union_overfit
```

Round03 runtime gives zero Round04 training credit. B4-B6 and B7-B9 were not executed and must not be described as failed.

## 2. Scientific objective and immutable full route

Primary targets:

```text
myops_scar
myops_edema
myocardium_cinemyops
```

MyoPS final path:

```text
observed [LGE,T2,C0] plus availability
-> four-scale modality-specific evidence
-> spatial/pathology-conditioned shared-private-interaction retrieval
-> optimized Pattern-SIP
-> train/OOF frozen prototypes and training-only safe hard negatives
-> learned union/LV/RV support
-> separate scar and edema proposals
-> separate pathology-specific soft ROI refiners
-> bounded final correction
-> official six-label reconstruction
-> same-split case-wise evaluation and real final-output interventions
```

Cine final path:

```text
official CineMA pretrained and architecture-matched random source
-> per-frame multiclass logits/features/probabilities/uncertainty
-> ED/reference and fixed key frames
-> learned seven-step SVF and independently generated real SyN control
-> registered anatomy/features/motion/Jacobian/quality
-> registered temporal aggregation
-> ED-space output, same-case controls and real final-output interventions
```

An nnU-Net-only prediction, postprocessing-only result, single-frame wrapper, internal fake CineMA adapter, direct velocity displacement, proxy Jacobian/SyN, abstract temporal latent, placeholder table or contract-only JSON is forbidden.

## 3. Route-local write boundary

Authorized Round04 implementation paths:

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

Shared model, Cine, anchor, loss, refiner and root wiki/current-state paths are read-only. A required shared-source edit returns `ROUTE_B_ROUND04_NEEDS_PLANNER_SCOPE_REVISION`; the controller cannot enlarge scope.

Required route-local controller/mapper receipts:

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

Root `wiki/current_state.yaml` and current figures do not advance before portfolio reconciliation.

## 4. Data, labels and same-split baseline

B0 freezes and hashes:

```text
configs/route_B_round04/manifests/myops_fold0_primary_44.json
configs/route_B_round04/manifests/myops_t2_edema_positive.json
configs/route_B_round04/manifests/myops_sampler_strata.json
configs/route_B_round04/manifests/myops_anatomy_microset_2.json
configs/route_B_round04/manifests/cine_train12.json
configs/route_B_round04/manifests/nnunet_same_split_anchor.json
results/route_B/round04/manifest_freeze_receipt.json
results/route_B/round04/same_split_baseline_receipt.json
```

The 44-case and 12-case manifests inherit only after exact fingerprint audit. Case-list correction is a planner/critic revision. The sampler is disjoint `E,E,S,R`, Philox seed `26071821`, with replacement.

Anatomy targets are exactly:

```text
Y_union = 1[label in {1,4,5}]
Y_LV    = 1[label == 2]
Y_RV    = 1[label == 3]
```

The nnU-Net anchor receipt binds checkpoint/model/config/split/case/preprocess/label/decode/evaluator/prediction hashes and a command receipt. It remains baseline/context/safety evidence, not the SRR route identity.

## 5. Exact MyoPS model

Inputs are `[B,3,Z,H,W]` in `[LGE,T2,C0]` order with availability `[B,3]`. Missing modalities are masked before and after stems and in every private/interaction path.

Four scales use channels `[32,64,128,256]`. Each scale contains sixteen experts:

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
scar:    shared + LGE-private + LGE-T2 + LGE-C0
edema:   shared + T2-private + LGE-T2 + T2-C0
```

The two-pass spatial router consumes local observed-modality features, availability, anatomy union/distance, anchor entropy/pathology/component/remote-FP evidence and pass-two proposal logits. Entmax-1.5 schedules valid top-all, top-4 and top-2. Invalid logits are `-1e4`; invalid absolute weight is at most `1e-8`.

Pattern-SIP remains a real optimized loss:

```text
family mass target: shared=.50, private=.35, interaction=.15
coverage floors: shared=.60, private=.25, interaction=.20
loss: mass + .50*integrative + .25*load + .10*sparse
coefficient: 0 at steps 0-999; ramp to .02 at 2000; .05 proposal/refiner; .02 joint
```

The anatomy decoder consumes live routed anatomy plus a masked observed-modality lateral feature. Localization support is:

```text
p_support = max(p_learned_union, 0.5 * stop_gradient(p_anchor_union))
```

Both channels remain separately observable. Anchor support cannot receive final-route credit without a nonzero learned-anatomy intervention.

Formal prototypes use four deterministic OOF shards. Per scale/pathology: scar positive `K=8`, scar negative `K=12`, edema positive `K=8`, edema safe-negative `K=12`. Current-case, validation-label and test-label leakage is forbidden. Bootstrap or online EMA bank is forbidden at formal inference. The training-only queue holds 256 component centroids per pathology per scale; no-T2 myocardium never enters edema negatives.

Scar and edema use separate proposal heads, soft ROI geometry and refiners. Scar uses three residual blocks with dilations `[1,2,3]`; edema uses four with `[1,2,4,6]`. Soft ROI never hard-deletes predictions. A weak but valid learned proposal uses the declared conservative anatomy-neighborhood control and must still proceed.

Bounded final composition:

```text
delta_p   = 4.0 * tanh(refiner_logit_p - anchor_logit_p)
z_final_p = z_anchor_p + roi_p * gate_p * delta_p
```

No-T2 edema loss, bank/queue update, proposal, ROI, refiner, gate, delta and Route-B-owned change are exactly zero.

## 6. Exact Cine model

Pinned CineMA source:

```text
repository: mathpluscode/CineMA
code commit: c10daa1d93f0ea28d8b9ad9206b0f673d25805c1
Hugging Face revision: b1251ee50423bceeca84c080782fc3bc7756dea6
weight: finetuned/segmentation/acdc_sax/acdc_sax_0.safetensors
weight SHA256: c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f
model: cinema.segmentation.convunetr.ConvUNetR
license: MIT
```

Pretrained/random matching holds architecture, parameter names/shapes, trainable masks, data, frames, augmentation draws, optimizer, budget, cadence, downstream initialization, selector and decode fixed. Only source initialization differs.

Learned registration emits stationary velocity `v:[B,3,Z,H,W]`. Forward and inverse transforms each use seven scaling-and-squaring steps. Images/probabilities/features use trilinear interpolation, labels use nearest, and padding is border. True Jacobian is computed in voxel coordinates. The loss includes LNCC, soft anatomy Dice, velocity smoothness, negative-Jacobian penalty, inverse composition and feature consistency. Real SyN is independently run and hashed on identical pairs.

Pair gate: folding fraction at most `.005`, positive minimum Jacobian, inverse-composition error at most `1.5` voxels, warped anatomy Dice no worse than unregistered by more than `.01`. Case gate: at least `80%` pair pass and four passed non-reference frames. Aggregate learned gate: at least `90%` of 12 cases. If learned fails and real SyN passes, B9 uses SyN and preserves learned negative evidence. If neither passes, a faithful B8 blocker terminates Cine without fabricating B9.

Temporal inputs are named and mandatory: reference and registered logits/features/uncertainty, velocity, integrated displacement, Jacobian, motion magnitude, texture residual, frame quality, temporal position and valid-frame mask. Every field has consumption and intervention evidence.

## 7. Stage progression and fixed budgets

```text
B0 -> B1 -> B2
B2 -> B3 -> B4 -> B5 -> B6
B2 -> B7 -> B8 -> B9
controller terminal registry -> B10 for every terminal class
```

B3/B7, B4/B8 and B5/B9 may run as isolated two-slot waves. MyoPS and Cine remain sequential within lane.

| Stage | Steps | Minimum seconds | Validation events | Full-case/case floor | Progression |
|---|---:|---:|---:|---|---|
| B1 | 2,000 | 600 | 4 | 2 train-only cases | failure is implementation revision |
| B3 | 6,000 | 1,800 | 3 | 44-case manifest | valid readiness always advances B4 |
| B4 | 8,000 | 2,400 | 4 | 44-case manifest | strong or weak-valid always advances B5 |
| B5 | 10,000 | 3,000 | 5 | 44-case manifest | strong or weak-faithful always advances B6 |
| B6 | 8,000 | 2,400 | 4 | four events, 44 cases | first full MyoPS classification |
| B7 pretrained | 8,000 | 3,600 | 4 | four events, 12 cases | B8 follows faithful matched runtime |
| B7 random | 8,000 | 3,600 | 4 | four events, 12 cases | matched control |
| B8 | 25,000 | 7,200 | 10 | four events, 12 cases, 60 pairs | B9 or faithful blocker |
| B9 | 20,000 cumulative | 7,200 | 10 | four events, 12 cases | Cine terminal evidence |

Selected checkpoints are clean-reloaded. Every stage requires prediction sanity, loss decrease, cache isolation and source/config/split/case/label/preprocess/decode/checkpoint/runtime hashes.

## 8. Same-split evidence, selector and interventions

B6 must produce fresh forced 44-case predictions and case-wise baseline/model values for Dice, HD95, remote-FP, component count, volume ratio, lesion-wise recall, changed logits/voxels/components and help/harm/severe-harm. Required subgroups: scar-positive, T2-present edema-positive, no-T2 safety, CenterB, CenterC, complete tri-modal, remote-FP-positive and high-component-burden.

The MyoPS selector remains:

```text
D_scar   = clip(scar-positive Dice delta,-.25,.25)/.25
D_edema  = clip(T2-positive edema Dice delta,-.25,.25)/.25
H_scar   = clip((anchor HD95 - model HD95)/20,-1,1)
H_edema  = clip((anchor HD95 - model HD95)/20,-1,1)
F_remote = clip((anchor remoteFP - model remoteFP)/max(anchor remoteFP,100),-1,1)
S = .40*D_scar + .25*D_edema + .15*H_scar + .10*H_edema + .10*F_remote
```

Required MyoPS interventions: learned anatomy off, anchor support floor off, prototype similarity off, hard-negative refresh off, interaction experts off, Pattern-SIP off, proposal off, scar refiner off, edema refiner off, both refiners off, bounded correction off and nnU-Net context off.

Required Cine controls: reference-only, unregistered multi-frame, registered temporal full, temporal router off, motion/Jacobian off, anatomy evidence off, uncertainty/quality off, matched random, learned SVF and real SyN.

An ablation/intervention file must contain real same-checkpoint final-output deltas, not a renamed summary.

## 9. Controller-level B10 terminal finalizer

B10 is outside the successful executor merge DAG.

Machine fields in the executor plan:

```text
B10 depends_on: []
controller_terminal_finalizer: true
launch_owner: controller
prepare_wave_helper_exempt: true
depends_on_successful_merge_receipts: false
terminal_registry_path: results/route_B/round04/controller_terminal_registry.json
all_started_attempt_ids_source: results/route_B/round04/controller_ledger.csv
finalizer_dependency_policy: afterany_all_started_attempts
no_started_attempt_backend: local_deterministic
```

The controller records each stage outcome in `controller_terminal_registry.json`.

Launch rules:

1. B0/B1/B2 global terminal blocker or revision launches B10 immediately.
2. After B2, B10 waits until both MyoPS and Cine lanes have terminal classes.
3. B3/B4/B5 implementation revision terminates MyoPS only; Cine continues.
4. B7 blocker or B8 faithful registration blocker terminates Cine only; MyoPS continues.
5. B6 and B9 terminal evidence are normal lane terminal classes.
6. Timeout, preemption, failed startup, started/cancelled race loser and successful attempts all enter the controller ledger.
7. The controller computes an `afterany` dependency over every started attempt. If none started, it runs local deterministic finalization.
8. An atomic launch lock prevents duplicate B10 starts.

B10 performs terminal accounting, post-completion aggregation, retry/race reconciliation, mapper final, all strict validators and known-bad matrices, `git diff --check`, heavy-artifact and authority scans, completion check, review request and one local lightweight packet commit. Pending/running/awaiting-accounting states cannot produce the review-ready token.

## 10. Exact strict validators

`prompts/routes/route_B_round04_executor_plan.yaml` is the machine source. Each B0-B10 entry fixes its strict validator script/command/input/report/exit/success token and known-bad matrix command/report/expected validator exit/failure keys.

| Stage | Strict validator command | Validator report | Known-bad command | Known-bad report |
|---|---|---|---|---|
| B0 | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/validate_B0_binding_manifests.py --strict --input results/route_B/round04/executors/B0 --report results/route_B/round04/executors/B0/validator_report.json --require-token ROUTE_B_ROUND04_B0_READY_FOR_CONTROLLER_MERGE` | `results/route_B/round04/executors/B0/validator_report.json` | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/run_known_bad_matrix.py --stage B0 --matrix tests/route_B_round04/fixtures/B0/known_bad_matrix.yaml --validator scripts/validation/route_B_round04/validate_B0_binding_manifests.py --report results/route_B/round04/executors/B0/known_bad_matrix_report.json` | `results/route_B/round04/executors/B0/known_bad_matrix_report.json` |
| B1 | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/validate_B1_anatomy_repair.py --strict --input results/route_B/round04/executors/B1 --report results/route_B/round04/executors/B1/validator_report.json --require-token ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_IMPLEMENTED` | `results/route_B/round04/executors/B1/validator_report.json` | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/run_known_bad_matrix.py --stage B1 --matrix tests/route_B_round04/fixtures/B1/known_bad_matrix.yaml --validator scripts/validation/route_B_round04/validate_B1_anatomy_repair.py --report results/route_B/round04/executors/B1/known_bad_matrix_report.json` | `results/route_B/round04/executors/B1/known_bad_matrix_report.json` |
| B2 | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/validate_B2_implementation_freeze.py --strict --input results/route_B/round04/executors/B2 --report results/route_B/round04/executors/B2/validator_report.json --require-token ROUTE_B_ROUND04_B2_IMPLEMENTATION_GATE_PASSED` | `results/route_B/round04/executors/B2/validator_report.json` | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/run_known_bad_matrix.py --stage B2 --matrix tests/route_B_round04/fixtures/B2/known_bad_matrix.yaml --validator scripts/validation/route_B_round04/validate_B2_implementation_freeze.py --report results/route_B/round04/executors/B2/known_bad_matrix_report.json` | `results/route_B/round04/executors/B2/known_bad_matrix_report.json` |
| B3 | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/validate_B3_representation.py --strict --input results/route_B/round04/executors/B3 --report results/route_B/round04/executors/B3/validator_report.json --require-token ROUTE_B_ROUND04_B3_REPRESENTATION_READY_FOR_PROPOSAL` | `results/route_B/round04/executors/B3/validator_report.json` | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/run_known_bad_matrix.py --stage B3 --matrix tests/route_B_round04/fixtures/B3/known_bad_matrix.yaml --validator scripts/validation/route_B_round04/validate_B3_representation.py --report results/route_B/round04/executors/B3/known_bad_matrix_report.json` | `results/route_B/round04/executors/B3/known_bad_matrix_report.json` |
| B7 | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/validate_B7_cinema_control.py --strict --input results/route_B/round04/executors/B7 --report results/route_B/round04/executors/B7/validator_report.json --require-token ROUTE_B_ROUND04_B7_CINEMA_MATCHED_CONTROL_COMPLETE` | `results/route_B/round04/executors/B7/validator_report.json` | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/run_known_bad_matrix.py --stage B7 --matrix tests/route_B_round04/fixtures/B7/known_bad_matrix.yaml --validator scripts/validation/route_B_round04/validate_B7_cinema_control.py --report results/route_B/round04/executors/B7/known_bad_matrix_report.json` | `results/route_B/round04/executors/B7/known_bad_matrix_report.json` |
| B4 | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/validate_B4_proposal.py --strict --input results/route_B/round04/executors/B4 --report results/route_B/round04/executors/B4/validator_report.json --require-token ROUTE_B_ROUND04_B4_PROPOSAL_STAGE_COMPLETE` | `results/route_B/round04/executors/B4/validator_report.json` | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/run_known_bad_matrix.py --stage B4 --matrix tests/route_B_round04/fixtures/B4/known_bad_matrix.yaml --validator scripts/validation/route_B_round04/validate_B4_proposal.py --report results/route_B/round04/executors/B4/known_bad_matrix_report.json` | `results/route_B/round04/executors/B4/known_bad_matrix_report.json` |
| B8 | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/validate_B8_registration.py --strict --input results/route_B/round04/executors/B8 --report results/route_B/round04/executors/B8/validator_report.json --require-token ROUTE_B_ROUND04_B8_REGISTRATION_STAGE_COMPLETE` | `results/route_B/round04/executors/B8/validator_report.json` | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/run_known_bad_matrix.py --stage B8 --matrix tests/route_B_round04/fixtures/B8/known_bad_matrix.yaml --validator scripts/validation/route_B_round04/validate_B8_registration.py --report results/route_B/round04/executors/B8/known_bad_matrix_report.json` | `results/route_B/round04/executors/B8/known_bad_matrix_report.json` |
| B5 | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/validate_B5_refiner.py --strict --input results/route_B/round04/executors/B5 --report results/route_B/round04/executors/B5/validator_report.json --require-token ROUTE_B_ROUND04_B5_REFINER_STAGE_COMPLETE` | `results/route_B/round04/executors/B5/validator_report.json` | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/run_known_bad_matrix.py --stage B5 --matrix tests/route_B_round04/fixtures/B5/known_bad_matrix.yaml --validator scripts/validation/route_B_round04/validate_B5_refiner.py --report results/route_B/round04/executors/B5/known_bad_matrix_report.json` | `results/route_B/round04/executors/B5/known_bad_matrix_report.json` |
| B9 | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/validate_B9_temporal.py --strict --input results/route_B/round04/executors/B9 --report results/route_B/round04/executors/B9/validator_report.json --require-token ROUTE_B_ROUND04_B9_TEMPORAL_TERMINAL_EVIDENCE_READY` | `results/route_B/round04/executors/B9/validator_report.json` | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/run_known_bad_matrix.py --stage B9 --matrix tests/route_B_round04/fixtures/B9/known_bad_matrix.yaml --validator scripts/validation/route_B_round04/validate_B9_temporal.py --report results/route_B/round04/executors/B9/known_bad_matrix_report.json` | `results/route_B/round04/executors/B9/known_bad_matrix_report.json` |
| B6 | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/validate_B6_myops_terminal.py --strict --input results/route_B/round04/executors/B6 --report results/route_B/round04/executors/B6/validator_report.json --require-token ROUTE_B_ROUND04_B6_MYOPS_TERMINAL_EVIDENCE_READY` | `results/route_B/round04/executors/B6/validator_report.json` | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/run_known_bad_matrix.py --stage B6 --matrix tests/route_B_round04/fixtures/B6/known_bad_matrix.yaml --validator scripts/validation/route_B_round04/validate_B6_myops_terminal.py --report results/route_B/round04/executors/B6/known_bad_matrix_report.json` | `results/route_B/round04/executors/B6/known_bad_matrix_report.json` |
| B10 | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/validate_B10_terminal_packet.py --strict --input results/route_B/round04/executors/B10 --report results/route_B/round04/executors/B10/validator_report.json --require-token ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW` | `results/route_B/round04/executors/B10/validator_report.json` | `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round04/run_known_bad_matrix.py --stage B10 --matrix tests/route_B_round04/fixtures/B10/known_bad_matrix.yaml --validator scripts/validation/route_B_round04/validate_B10_terminal_packet.py --report results/route_B/round04/executors/B10/known_bad_matrix_report.json` | `results/route_B/round04/executors/B10/known_bad_matrix_report.json` |

The controller cannot select a substitute validator, omit a failure key, accept an unexpected known-bad pass or use a file-existence-only check.

## 11. Slurm and continuity

Formal Python is `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`. Compute-node preflight records Python/torch/CUDA, optimizer construction, semantic config, hashes and writable roots.

`htzhulab` is default. A materially long compatible wait requires an isolated `htzhulab+a100-gpu` race with identical scientific hashes, separate output/log/checkpoint/cache roots, one atomic winner lock, immediate pending-loser cancellation, zero-credit losers and complete accounting. `volta-gpu` is credited only for unchanged scientific configuration and measured peak memory at most `14.5 GiB`; semantic downscaling is forbidden.

Training-to-training dependencies use `afterok`; B10 uses `afterany`. Submitted, pending, running, awaiting-accounting, monitor, timeout, preemption and partial states are not completion. Same-scope operational retry preserves scientific hashes and failed attempts retain zero credit.

## 12. Terminal packet and reviewer boundary

B10 required packet:

```text
results/route_B/round04/executors/B10/routing_ledger.csv
results/route_B/round04/executors/B10/training_adequacy.csv
results/route_B/round04/executors/B10/terminal_branch_coverage.json
results/route_B/round04/executors/B10/validator_packet_report.json
results/route_B/round04/executors/B10/known_bad_report.json
results/route_B/round04/executors/B10/heavy_artifact_scan.json
results/route_B/round04/executors/B10/finalizer_state.json
results/route_B/round04/executors/B10/completion.json
results/route_B/result.md
results/route_B/controller_report.md
results/route_B/completion_check.md
results/route_B/review_request.md
results/route_B/MANIFEST.md
```

Controller report before review fixes:

```text
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
git_push_decision: SKIP_PUSH
```

The independent runtime reviewer may emit only:

```text
ROUTE_B_ROUND04_REVIEW_EVIDENCE_COMPLETE
ROUTE_B_ROUND04_REVIEW_ADEQUATE_NEGATIVE
ROUTE_B_ROUND04_REVIEW_EXTERNAL_RESOURCE_BLOCKER
ROUTE_B_ROUND04_REVIEW_NEEDS_MONITOR
ROUTE_B_ROUND04_REVIEW_NEEDS_EVIDENCE
ROUTE_B_ROUND04_REVIEW_NEEDS_REVISION
```

Reviewer is read-only and runs after the local packet commit. Evidence completeness or adequate negative is not route promotion.

## 13. Authority boundary

This contract authorizes nothing until the new critic-ready token. It never authorizes validation packaging/upload, route promotion, M11, hosted metric claims, cross-route merge or final scientific decision.
