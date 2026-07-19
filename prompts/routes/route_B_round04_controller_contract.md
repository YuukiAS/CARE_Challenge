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
planning_review_path: prompts/routes/route_B_round04_critic_review.md
planning_review_token: ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
planning_commit_binding_mode: containing_commit_resolved_and_recorded_by_critic
execution_mode: controller_supervised
requires_execution_controller: true
executor_plan_path: prompts/routes/route_B_round04_executor_plan.yaml
executor_count: 11
executor_slots: 2
parallel_execution_allowed: true
merge_owner: controller
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
planner_base_main: 7042135a4cc5be44b090fee93d4d1ee25b72fc0e
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

## 0. Authority and entry gate

This contract becomes executable only after a separate critic writes:

```text
prompts/routes/route_B_round04_critic_review.md
ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
planning_reviewed_commit: <exact main planning commit>
```

The controller must verify that the reviewed commit contains byte-identical versions of this contract, the executor plan, the planner plan, the critic request, and the planner audit. A mismatch returns `ROUTE_B_ROUND04_STALE_PLANNING_BINDING` and stops before implementation or Slurm.

This contract does not authorize validation upload, route promotion, M11, hosted metric claims, cross-route merge, or a final scientific decision. Runtime roles do not push and do not write `review.md`.

## 1. Frozen Round03 evidence interpretation

The controller must not rerun Round03 B3 merely to reproduce the reviewed negative. The following evidence is inherited as historical background after B0 fingerprint verification:

```text
review token: ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE
optimizer steps: 43003
train-loop seconds: 1800.7964860140346
validation events: 22
sampler cycle: E,E,S,R
sampler counts: E=21502, S=10751, R=10750
passed: finite loss, loss decrease, invalid-slot zero, no-T2 edema zero, sampler count/sequence
failed: anatomy_union_overfit
```

Historical runtime receives no Round04 training credit. B0 must classify every inherited artifact through code/config/split/case/label/preprocess/decode/checkpoint/runtime fingerprints. Any mismatch is recorded rather than silently inherited.

## 2. Scientific objective

The controller must implement and execute the complete SRR-v3 chain for the three leaderboard-facing targets:

```text
myops_scar
myops_edema
myocardium_cinemyops
```

The full chain is:

```text
observed modalities
-> modality-specific four-scale features
-> availability/spatial/pathology-conditioned shared-private-interaction retrieval
-> train/OOF frozen prototype similarity and training-only safe hard negatives
-> union/LV/RV anatomy support
-> scar and edema proposals
-> pathology-specific soft ROIs
-> scar and edema refiners
-> bounded final correction
-> official label reconstruction
-> case-wise same-split evaluation and interventions
```

The Cine chain is:

```text
official CineMA pretrained or matched-random source
-> per-frame multiclass logits/features/uncertainty
-> ED/reference and fixed key frames
-> learned seven-step SVF and real SyN control
-> registered anatomy/features/motion/Jacobian/quality
-> temporal retrieval and aggregation
-> ED-space myocardium output
-> same-case controls and interventions
```

No stage may replace these chains with an nnU-Net-only prediction, a morphology-only result, a single-frame wrapper, a placeholder table, a mock tensor, or contract JSON without runtime effects.

## 3. Route-local source and write boundary

Round04 implementation lives under:

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

Shared source under these paths is read-only during Route B execution:

```text
src/care_myocardium/models/
src/care_myocardium/cine/
src/care_myocardium/anchors/
src/care_myocardium/losses/
src/care_myocardium/refiner/
wiki/current_state.yaml
wiki/README.md
wiki/MODEL.md
wiki/COMPONENTS.csv
wiki/architecture.yaml
```

A required shared-source edit returns `ROUTE_B_ROUND04_NEEDS_PLANNER_SCOPE_REVISION`. The controller cannot widen scope.

Route-local mapper outputs are required:

```text
results/route_B/round04/controller_context.json
results/route_B/round04/controller_ledger.csv
results/route_B/round04/controller_bootstrap_snapshot.md
results/route_B/round04/implementation_snapshot.md
results/route_B/round04/mapper_report_draft.md
results/route_B/round04/architecture_delta_draft.md
results/route_B/round04/mapper_report_final.md
results/route_B/round04/architecture_delta_final.md
results/route_B/round04/finalizer_state.json
```

The mapper records a route-local architecture delta and code fingerprint. Root wiki/current-state publication waits for later portfolio reconciliation.

## 4. Frozen data and baseline contracts

B0 must create and hash:

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

The 44-case and 12-case lists must match the verified Round03 manifests byte-for-byte unless B0 proves a manifest defect. A manifest correction requires planner/critic revision; execution cannot change cases.

The MyoPS sampler remains disjoint `E,E,S,R` with Philox seed `26071821`, sampling with replacement. The microset is the lexicographically first qualifying complete tri-modal anatomy-positive CenterB case and the lexicographically first qualifying complete tri-modal anatomy-positive CenterC case in the frozen 44-case list. Missing either class blocks B1.

The nnU-Net receipt contains checkpoint path and SHA, model/config SHA, split SHA, case-list SHA, preprocess SHA, label-map SHA, decode SHA, evaluator SHA, prediction SHA per case, and command receipt. The anchor is read-only baseline/context/safety evidence.

## 5. Exact MyoPS model contract

### 5.1 Inputs and stems

```text
modality order: [LGE,T2,C0]
input: [B,3,Z,H,W]
availability: [B,3]
channels: [32,64,128,256]
```

Unavailable modalities are masked before the stem, after the stem, and in every private/interaction route. Their private or interaction weight and gradient are zero. Zero-filled tensors never imply availability.

### 5.2 Expert bank

Every scale has sixteen experts:

```text
4 shared
2 LGE-private
2 T2-private
2 C0-private
2 LGE-T2 interaction
2 LGE-C0 interaction
2 T2-C0 interaction
```

Each expert uses two `3x3x3` convolutions, GroupNorm, SiLU, and a residual connection. Pairwise features concatenate the two present modalities and use a `1x1x1` projection before the residual expert.

Task family masks are fixed:

```text
anatomy: shared + C0-private + LGE-C0 + T2-C0
scar: shared + LGE-private + LGE-T2 + LGE-C0
edema: shared + T2-private + LGE-T2 + T2-C0
```

The two-pass spatial router consumes local observed-modality features, availability embedding, anatomy union/distance, anchor entropy/pathology/component/remote-FP evidence, and pass-two proposal logits. Entmax-1.5 is used with valid top-all, top-4, then top-2 scheduling. Invalid logits are `-1e4`; maximum invalid absolute weight is `1e-8`.

### 5.3 Pattern-SIP

Pattern-SIP is a real forward loss over availability groups, four train-only style clusters, and hard subgroup indicators. It retains the Round03 numeric target and schedule:

```text
family target mass: shared=.50, private=.35, interaction=.15
shared coverage floor=.60
private coverage floor=.25
interaction coverage floor=.20
loss = mass + .50*integrative + .25*load + .10*sparse
coefficient: 0 steps 0-999; ramp to .02 at step 2000; .05 proposal/refiner; .02 joint
```

The validator rejects an alias to generic dictionary loss, a detached report-only value, a constant tensor, or missing final-output intervention.

### 5.4 Anatomy target and decoder repair

Targets are:

```text
Y_union = 1[compact label in {1,4,5}]
Y_LV = 1[compact label == 2]
Y_RV = 1[compact label == 3]
```

The anatomy decoder input at scale `l` is:

```text
a_l = Conv1x1(concat(routed_anatomy_l, masked_mean(valid_modality_features_l)))
```

The localization support passed to proposal/ROI is:

```text
p_support = max(p_learned_union, 0.5 * stop_gradient(p_anchor_union))
```

Both learned and anchor support channels remain separately observable. The final output cannot be credited without a nonzero learned-anatomy intervention.

### 5.5 OOF prototypes and hard negatives

Four shards are assigned by `int(sha256(case_id)[:8],16) % 4`. Every scale and pathology uses:

```text
scar positive K=8
scar negative K=12
edema positive K=8
edema safe-negative K=12
```

Each OOF bank is fitted from the other three train shards, frozen for validation/test, serialized with checkpoint and source receipts, and clean-reloaded. Current-case, validation-label, and test-label contributions are forbidden. Bootstrap vectors and online EMA banks cannot enter formal inference.

The training-only hard-negative queue holds 256 component centroids per pathology per scale. Rank 0 inserts at most 16 stable-sorted candidates per batch and broadcasts every 50 steps. No-T2 myocardium and unknown edema-status tissue cannot enter the edema queue.

### 5.6 Proposals, soft ROI, and refiners

Scar and edema use separate heads and targets. Scar is LGE-dominant with smaller dilation and higher precision. Edema is T2-conditioned with larger context and no loss/update/output on no-T2 cases.

Soft ROI never hard-deletes predictions. The full path uses learned proposal plus `p_support`, anatomy distance, uncertainty, anchor component, positive similarity, and negative similarity. A fixed anatomy-neighborhood floor preserves lesion coverage when B4 classifies the learned proposal as weak.

Scar refiner uses three residual blocks with dilations `[1,2,3]`. Edema refiner uses four residual blocks with dilations `[1,2,4,6]`. Both return pathology logits and are blended back through the soft ROI.

### 5.7 Bounded final composition

```text
delta_p = 4.0 * tanh(refiner_logit_p - anchor_logit_p)
z_final_p = z_anchor_p + roi_p * gate_p * delta_p
```

Classes 0-3 remain unchanged by the pathology correction. No-T2 edema loss, bank update, queue update, proposal, ROI, refiner, gate, delta, and Route-B-owned edema change are exactly zero. Final labels are the official six-label argmax reconstruction; no post-hoc label invention is permitted.

## 6. Exact Cine model contract

### 6.1 CineMA source

```text
repository: mathpluscode/CineMA
code commit: c10daa1d93f0ea28d8b9ad9206b0f673d25805c1
Hugging Face revision: b1251ee50423bceeca84c080782fc3bc7756dea6
weight: finetuned/segmentation/acdc_sax/acdc_sax_0.safetensors
weight SHA256: c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f
model: cinema.segmentation.convunetr.ConvUNetR
license: MIT
```

The source exposes official four-class logits, probabilities, pre-head decoder features, projected features, and normalized entropy for every selected frame. Orientation, spacing, crop/pad, affine, interpolation, and inverse-resampling provenance are hashed.

### 6.2 Matched random control

Pretrained and random lanes use the same ConvUNetR architecture, config, cases, frames, augmentation draws, trainable/frozen masks, downstream initialization artifact, optimizer, budget, cadence, selector, and decode. Only source initialization differs. A parameter-name/shape/value audit runs before training.

### 6.3 Registration

The learned registration network outputs stationary velocity `v:[B,3,Z,H,W]`. Forward and inverse transforms use seven scaling-and-squaring steps:

```text
d0 = v / 2^7
d_{i+1} = d_i + warp(d_i,d_i), i=0..6
phi = identity + d7
phi_inverse = exp(-v) by the same seven steps
```

Images, probabilities, and features use trilinear interpolation; labels use nearest; padding is border. Jacobian determinant uses central finite differences in voxel coordinates. The full loss contains LNCC, soft-anatomy Dice, velocity smoothness, negative-Jacobian penalty, inverse-composition loss, and CineMA feature consistency.

Real SyN uses the frozen `SyNOnly` parameter contract on identical pairs. Learned and SyN transforms and outputs are independently produced and hashed.

A pair passes when folding fraction is at most `.005`, minimum Jacobian is positive, inverse-composition error is at most `1.5` voxels, and warped anatomy Dice is no worse than unregistered by more than `.01`. A case passes with at least `80%` pair pass and four passed non-reference frames. Aggregate learned registration passes with at least `90%` of 12 cases.

### 6.4 Registered temporal model

The temporal interface contains:

```text
reference logits/features/uncertainty
registered non-reference logits/features/uncertainty
velocity and integrated displacement
Jacobian and motion magnitude
registered texture residual
frame quality
temporal position
valid-frame mask
```

The eight-slot router models ED anchor, early/late systole, early/late diastole, motion, texture residual, and registration-uncertainty safety. Two residual blocks and a four-class ED-space head produce final logits. Every required input has a consumption hook, gradient/intervention receipt, and shape/hash provenance.

## 7. Training and evaluation budgets

### B1 anatomy repair

```text
steps: 2000
minimum train-loop seconds: 600
validation events: 4
cases: frozen train-only microset of 2
optimizer: AdamW, lr=2e-4, weight_decay=1e-4
batch size: 1
gradient accumulation: 2
AMP: enabled
gradient clip: 5
```

Pass gates: union Dice `>=.90` each case; mean LV/RV Dice `>=.85` each case; loss decrease `>=70%`; finite live routed/lateral gradients; reload delta `<=1e-5`.

### B3 representation warmup

```text
steps: 6000
minimum train-loop seconds: 1800
validation events: 3
optimizer: AdamW, lr=2e-4, weight_decay=1e-4
warmup: 500 steps
scheduler: cosine
```

Pass gates: all adequacy checks; B1 microset union Dice retained `>=.85`; invalid weight `<=1e-8`; exact no-T2 zero; live gradients for every valid family; style cluster freeze; finite nonconstant learned anatomy; one of the two localization classes defined in the planner plan.

### B4 proposal

```text
steps: 8000
minimum train-loop seconds: 2400
validation events: 4
optimizer: AdamW, lr=1e-4, weight_decay=1e-4
```

B4 always emits a proposal-strength classification after valid OOF/provenance/gradient/safety gates. `PROPOSAL_STRONG` and `PROPOSAL_WEAK_WITH_CONSERVATIVE_ROI` both advance to B5. Invalid OOF, leakage, unsafe edema negatives, disconnected similarity, or nonfinite training block progression.

### B5 refiner

```text
steps: 10000
minimum train-loop seconds: 3000
validation events: 5
optimizer: AdamW, lr=1e-4, weight_decay=1e-4
```

Pass gates: proposal-to-final retention positive; changed logits/voxels/components nonzero; scar remote-FP does not increase on the gate set; exact no-T2 zero; full and conservative-ROI controls evaluated when B4 is weak.

### B6 joint and MyoPS terminal evidence

```text
steps: 8000
minimum train-loop seconds: 2400
validation events: 4
optimizer: AdamW, lr=2e-5, weight_decay=1e-4
```

B6 performs fresh full 44-case predictions, clean reload, selector, case-wise baseline comparison, full interventions, and ablations. B6 is the first stage that may provide complete MyoPS candidate or adequate-negative evidence to the independent reviewer.

### B7 CineMA control

Each lane uses:

```text
steps: 8000
minimum train-loop seconds: 3600
validation events: 4
full-case events: 4
cases: 12
optimizer: AdamW, lr=2e-4, weight_decay=1e-4
```

### B8 registration

```text
steps: 25000
minimum train-loop seconds: 7200
validation events: 10
full-case events: 4
cases: 12
pairs: at least 60
optimizer: AdamW, lr=1e-4, weight_decay=1e-5
```

B9 uses learned SVF when learned aggregation passes. B9 uses real SyN when learned aggregation misses and SyN passes. Neither passing yields a faithful registration blocker.

### B9 temporal

```text
credited cumulative steps: 20000
minimum train-loop seconds: 7200
validation events: 10
full-case events: 4
cases: 12
optimizer: AdamW, lr=2e-4, weight_decay=1e-4
```

Chunks target 4000/8000/12000/16000/20000 credited steps. Atomic checkpoints occur at most every 500 steps and on `SIGUSR1`/`TERM`. Reset, gap, overlap, duplicate, missing parent, timeout, preemption, and partial attempts receive zero credit.

## 8. Checkpoint eligibility and selector

Eligibility precedes scoring. Required gates:

- fresh forced evaluation;
- complete source/config/split/case/label/preprocess/decode/evaluator/checkpoint/prediction hashes;
- complete denominators;
- proposal/ROI coverage floors;
- changed voxels and components greater than zero;
- no-T2 Route-B-owned edema change exactly zero;
- positive-case nonempty rate at least `0.80`;
- median pathology volume ratio in `[0.25,4.0]`;
- finite metrics;
- selected checkpoint clean reload within `1e-5`;
- all strict validators and known-bad tests pass.

For GT-positive cases, empty prediction has Dice `0` and HD95 `100 mm`. Both-empty rows are excluded and cannot count as improvement.

The MyoPS score is:

```text
D_scar = clip(scar-positive Dice delta,-.25,.25)/.25
D_edema = clip(T2-positive edema Dice delta,-.25,.25)/.25
H_scar = clip((anchor HD95 - model HD95)/20,-1,1)
H_edema = clip((anchor HD95 - model HD95)/20,-1,1)
F_remote = clip((anchor remoteFP - model remoteFP)/max(anchor remoteFP,100),-1,1)
S = .40*D_scar + .25*D_edema + .15*H_scar + .10*H_edema + .10*F_remote
```

Tie-break order: higher `S`, lower severe-harm fraction, lower component-count delta, lower absolute volume-ratio deviation, then earlier cumulative optimizer step.

Cine source selection uses higher mean myocardium Dice, then lower HD95 within `.001`, then earlier step. `PRETRAINED_BENEFIT` requires Dice advantage at least `.01` and HD95 disadvantage at most `1 mm`. `RANDOM_NONINFERIOR` requires absolute Dice difference at most `.005` and random HD95 no worse. Other results are `CINEMA_CONTROL_UNRESOLVED`. The downstream full lane still uses the clean-reloaded pretrained source; the control classification limits scientific claims.

## 9. Required case-wise and subgroup evidence

MyoPS case rows contain:

```text
case_id
center
availability pattern
scar-positive flag
T2-present flag
edema-positive flag
complete-trimodal flag
remote-FP-positive baseline flag
baseline and model Dice by pathology
baseline and model HD95 by pathology
baseline and model remote-FP volume
baseline and model component count
baseline and model volume ratio
lesion-wise recall
changed logits/voxels/components
help/harm/severe-harm classification
```

Summaries are mandatory for scar-positive, T2-present edema-positive, no-T2 safety, CenterB, CenterC, complete tri-modal, remote-FP-positive, and high-component-burden groups.

Cine rows contain case/center/frame counts, registration source, passed-pair denominator, reference-only and temporal Dice/HD95, changed logits/labels/components, and ablation deltas.

## 10. Real intervention and ablation contract

A real intervention uses the same selected/reloaded checkpoint, same cases, same inputs, same decode rule, and one named node disabled or replaced. Required MyoPS interventions:

```text
learned_anatomy_off
anchor_support_floor_off
prototype_similarity_off
hard_negative_refresh_off
interaction_experts_off
pattern_sip_off
proposal_off
scar_refiner_off
edema_refiner_off
both_refiners_off
bounded_correction_off
nnunet_context_off
```

Required Cine interventions:

```text
reference_only
unregistered_multiframe
registered_temporal_full
temporal_router_off
motion_jacobian_off
anatomy_evidence_off
uncertainty_quality_off
matched_random_source
learned_svf_source
real_syn_source
```

Each intervention records final logit L1/Linf delta, changed voxels, changed components, Dice, HD95, remote-FP, component count, and volume ratio. A summary derived from unrelated rows cannot use an intervention or ablation filename.

## 11. Slurm routing and environment

Every formal job starts with compute-node preflight using:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python
```

The preflight prints and stores Python executable/version, torch/CUDA versions, CUDA visibility, optimizer construction, semantic config, code/config/split hashes, and writability of output/log/checkpoint/cache/lock roots.

Long compatible waits use an isolated routing race across `htzhulab` and `a100-gpu`. Rules:

```text
same logical_run_id
same code/config/split/checkpoint/scientific hashes
isolated attempt output/log/checkpoint/cache roots
one atomic winner lock
first started lock holder receives credit
started losers write RACE_LOST and exit zero-credit
pending losers are cancelled immediately
all attempts remain in routing and finalizer ledgers
```

`volta-gpu` has user authorization for unchanged-semantics work. A stage can submit a V100 attempt only when its exact scientific configuration passes peak memory `<=14.5 GiB`. Failed V100 compatibility gives zero credit and cannot trigger batch, crop, model, loss, label, split, or budget changes.

Training-to-training dependencies use `afterok`. B10 accounting/finalizer dependencies use `afterany`. Operational retries preserve all scientific fingerprints and use at most two startup retries, two preemption retries, and zero unknown-state retries. A semantic change returns to planning/critic.

## 12. Executor contracts and completion tokens

### B0 — evidence, fingerprint, manifest, baseline rebind

Inputs: current planning commit, Round03 reviewed packet, current main governance, current route_B source/evidence.
Outputs:

```text
results/route_B/round04/executors/B0/source_fingerprint_audit.json
results/route_B/round04/executors/B0/round03_inheritance_matrix.csv
results/route_B/round04/executors/B0/label_target_audit.json
results/route_B/round04/executors/B0/manifest_freeze_receipt.json
results/route_B/round04/executors/B0/same_split_baseline_receipt.json
results/route_B/round04/executors/B0/validator_fixture_index.json
results/route_B/round04/executors/B0/completion.json
```

Success token: `ROUTE_B_ROUND04_B0_READY_FOR_CONTROLLER_MERGE`.
Failure tokens: `ROUTE_B_ROUND04_B0_STALE_BINDING`, `ROUTE_B_ROUND04_B0_FINGERPRINT_BLOCKER`, `ROUTE_B_ROUND04_B0_MANIFEST_OR_LABEL_BLOCKER`.

### B1 — anatomy target and optimization repair

Inputs: B0 receipts and inherited route-local Round03 scaffold.
Outputs:

```text
results/route_B/round04/executors/B1/anatomy_target_roundtrip.json
results/route_B/round04/executors/B1/anatomy_microset_metrics.csv
results/route_B/round04/executors/B1/anatomy_gradient_receipt.csv
results/route_B/round04/executors/B1/anatomy_intervention_receipt.csv
results/route_B/round04/executors/B1/save_reload_report.json
results/route_B/round04/executors/B1/completion.json
```

Success token: `ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_IMPLEMENTED`.
Failure token: `ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_NEEDS_REVISION`.

### B2 — implementation and regression freeze

Inputs: merged B1 code/config and all B0 manifests.
Outputs:

```text
results/route_B/round04/executors/B2/implementation_gate.json
results/route_B/round04/executors/B2/myops_gradient_interventions.csv
results/route_B/round04/executors/B2/cinema_source_smoke.json
results/route_B/round04/executors/B2/registration_temporal_smoke.json
results/route_B/round04/executors/B2/export_roundtrip.json
results/route_B/round04/executors/B2/known_bad_selftest_report.json
results/route_B/round04/executors/B2/freeze_receipt.json
results/route_B/round04/executors/B2/completion.json
```

Success token: `ROUTE_B_ROUND04_B2_IMPLEMENTATION_GATE_PASSED`.
Failure tokens: `ROUTE_B_ROUND04_B2_IMPLEMENTATION_NEEDS_REVISION`, `ROUTE_B_ROUND04_B2_EXTERNAL_RESOURCE_BLOCKER`.

### B3 — MyoPS representation warmup

Outputs include training summary, checkpoints, validation rows, sampler traces, router/Pattern-SIP gradients, style clusters, anatomy classification, stage gate, and completion.
Success token: `ROUTE_B_ROUND04_B3_REPRESENTATION_READY_FOR_PROPOSAL`.
Failure tokens: monitor/accounting operational states or `ROUTE_B_ROUND04_B3_NEEDS_REVISION`. No full-route negative token is valid at B3.

### B4 — OOF bank and proposal

Outputs include bank provenance/tensors, queue ledger, proposal metrics, similarity interventions, conservative-ROI comparison, stage classification, and completion.
Success token: `ROUTE_B_ROUND04_B4_PROPOSAL_STAGE_COMPLETE`.
The completion records `PROPOSAL_STRONG` or `PROPOSAL_WEAK_WITH_CONSERVATIVE_ROI`. Invalid OOF/safety/connectivity returns `ROUTE_B_ROUND04_B4_NEEDS_REVISION`.

### B5 — refiner

Outputs include refiner training, ROI retention, changed-component rows, remote-FP comparison, full versus conservative control when present, and completion.
Success token: `ROUTE_B_ROUND04_B5_REFINER_STAGE_COMPLETE`.
Failure token: `ROUTE_B_ROUND04_B5_NEEDS_REVISION`.

### B6 — joint selector and MyoPS terminal evidence

Outputs include fresh 44-case predictions, selector, case-wise metrics, help/harm, subgroups, real ablations, final interventions, clean reload, export QA, and completion.
Success token: `ROUTE_B_ROUND04_B6_MYOPS_TERMINAL_EVIDENCE_READY`.
B6 completion class is `MYOPS_CANDIDATE_SIGNAL`, `MYOPS_ADEQUATE_NEGATIVE`, or `MYOPS_NEEDS_EVIDENCE`. Only the independent reviewer interprets the route.

### B7 — official CineMA matched control

Outputs include source provenance, matched-parameter audit, shared downstream initialization receipt, both runtime ledgers, selected checkpoints, case-wise control metrics, reload checks, and completion.
Success token: `ROUTE_B_ROUND04_B7_CINEMA_MATCHED_CONTROL_COMPLETE`.
Failure tokens: `ROUTE_B_ROUND04_B7_EXTERNAL_RESOURCE_BLOCKER`, `ROUTE_B_ROUND04_B7_MATCHING_NEEDS_REVISION`, and operational monitor/accounting states.

### B8 — faithful registration

Outputs include learned and SyN pair receipts, true Jacobian, inverse-composition, full loss, case aggregation, full denominators, selected/reloaded registration, source classification, and completion.
Success token: `ROUTE_B_ROUND04_B8_REGISTRATION_STAGE_COMPLETE`.
Completion class: `LEARNED_SVF_PRIMARY`, `SYN_PRIMARY_LEARNED_NEGATIVE`, or `CINE_REGISTRATION_BLOCKER`.

### B9 — registered temporal terminal evidence

Outputs include cumulative ledger, parent hashes, registered input manifest, temporal training, case-wise metrics, help/harm, full ablation, final interventions, clean reload, export QA, and completion.
Success token: `ROUTE_B_ROUND04_B9_TEMPORAL_TERMINAL_EVIDENCE_READY`.
A `CINE_REGISTRATION_BLOCKER` from B8 produces an evidence-complete blocker packet rather than a fabricated B9 result.

### B10 — durable finalizer and reviewer handoff

B10 runs through local deterministic finalization or Slurm `afterany` over every started attempt. It records terminal `sacct`, exit code, elapsed, node, log, runtime output, retry lineage, race cancellation, aggregation commands/exits, validator commands/exits, tracked lightweight files, ignored heavy files, and superseded receipts.

Required outputs:

```text
results/route_B/round04/executors/B10/routing_ledger.csv
results/route_B/round04/executors/B10/training_adequacy.csv
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

Final controller token: `ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW` only after terminal accounting, aggregation, mapper final, strict validator pass, known-bad pass, `git diff --check`, heavy-artifact scan, and local lightweight packet commit.

## 13. Required semantic validators and known-bad fixtures

The strict validator must fail closed on:

1. stale planning commit or evidence ref;
2. wrong modality order or zero-fill availability shortcut;
3. legacy Round03 formal wrapper invocation;
4. pure-myocardium anatomy union target;
5. anatomy micro-overfit failure labeled as scientific negative;
6. Round03 B3 failure used to skip B4-B9;
7. missing lateral or routed anatomy gradient;
8. invalid private/interaction slot weight above `1e-8`;
9. Pattern-SIP alias, detached tensor, constant tensor, or missing gradient;
10. bootstrap/EMA formal prototype path;
11. current-case, validation, or test leakage into an OOF bank;
12. no-T2 myocardium entering edema negatives;
13. disconnected proposal similarity or constant proposal;
14. hard ROI deletion;
15. shared undifferentiated scar/edema refiner;
16. zero or unbounded final correction;
17. missing same-split nnU-Net baseline;
18. missing scar-positive, T2-present edema-positive, no-T2, CenterB, or CenterC rows;
19. empty-GT rows counted as improvements;
20. summary rows named as interventions;
21. selected checkpoint not clean-reloaded;
22. fake CineMA source, wrong SHA, or internal small wrapper used as official source;
23. pretrained/random mismatch beyond source initialization;
24. direct velocity-as-displacement;
25. fewer than seven scaling-and-squaring steps;
26. proxy Jacobian, copied SyN output, or pair-level rows presented as case-level gate;
27. temporal path missing any required registered input;
28. frame0 fallback, unregistered primary output, reset/gap/overlap/duplicate cumulative ledger;
29. formal Slurm wrapper resolving to a system or unapproved interpreter;
30. smoke/one-batch/local run credited as formal training;
31. submitted/pending/running/monitor/awaiting-accounting packet presented as completion;
32. race attempts sharing output roots, mismatched scientific hashes, loser credit, or uncancelled pending loser;
33. V100 semantic downscaling;
34. validator checking only file presence;
35. controller push, controller-authored review, or forbidden authority claim;
36. inconsistent final receipts that leave superseded failure text as current truth.

## 14. Independent reviewer prompt draft

The independent reviewer must check the exact committed terminal packet and may emit only:

```text
ROUTE_B_ROUND04_REVIEW_EVIDENCE_COMPLETE
ROUTE_B_ROUND04_REVIEW_ADEQUATE_NEGATIVE
ROUTE_B_ROUND04_REVIEW_EXTERNAL_RESOURCE_BLOCKER
ROUTE_B_ROUND04_REVIEW_NEEDS_MONITOR
ROUTE_B_ROUND04_REVIEW_NEEDS_EVIDENCE
ROUTE_B_ROUND04_REVIEW_NEEDS_REVISION
```

Reviewer decision rules:

- `EVIDENCE_COMPLETE`: all B0-B10 integrity gates pass; B6 and B9 are terminal; two target gates are positive; the third is non-worse; final-output effects are real; no-T2 safety and subgroup evidence pass. This is evidence completeness, not route promotion.
- `ADEQUATE_NEGATIVE`: implementation and fidelity are faithful; minimum effective training and terminal accounting pass; the full MyoPS and available registered Cine chains were exercised; candidate thresholds are missed. A faithful B8 blocker with real learned/SyN evidence can support this classification only when the missing B9 result is causally forced by the registration gate and all blocker evidence is complete.
- `EXTERNAL_RESOURCE_BLOCKER`: official external asset access prevents the exact Cine source and the packet proves the blocker without substitutes.
- `NEEDS_MONITOR`: at least one required attempt lacks terminal accounting.
- `NEEDS_EVIDENCE`: runtime is terminal but required aggregation, denominators, hashes, intervention rows, or receipts are missing/inconsistent.
- `NEEDS_REVISION`: implementation, label semantics, data leakage, matcher fidelity, registration mathematics, temporal consumption, validator semantics, or authority boundary is defective.

The reviewer is read-only, runs after the terminal packet commit, and does not authorize validation upload, route promotion, M11, hosted metrics, cross-route merge, or final scientific decision.

## 15. Controller completion checklist

Before requesting review, the controller verifies:

- exact critic-ready planning binding;
- B0-B2 implementation/fingerprint gates;
- B3-B6 MyoPS lane terminal state;
- B7-B9 Cine lane terminal state or faithful B8 blocker state;
- every started Slurm attempt terminal and aggregated;
- every failed/losing attempt zero-credit and retained in ledger;
- same-split baseline and all hard subgroup rows;
- real final-output interventions and full ablations;
- selected checkpoints clean-reloaded;
- route-local mapper final and architecture delta final;
- strict validator and known-bad suite pass;
- no heavy artifact tracked;
- old receipts explicitly superseded;
- lightweight local commit created;
- git push skipped by controller;
- runtime `review.md` absent.

Only then may B10 write `ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW`.
