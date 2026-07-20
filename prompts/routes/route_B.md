---
route_id: route_B
portfolio_round: round03
date: 2026-07-18
task_key: route_B_round03_full_srr_v3
route_name: "Route B — active full SRR-v3 construction and evidence"
branch: route_B
round03_current_binding_source: prompts/routes/handoffs/CURRENT.md
status: DRAFT_FOR_ROUND03_CRITIC_REVIEW
portfolio_status: ACTIVE_FULL_SRR_V3
not_a_milestone: true
current_round_critic_required: true
controller_start_authorized: false
required_planning_ready_token: ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
critic_request_path: prompts/routes/route_B_critic_request.md
planner_audit_path: prompts/routes/route_B_planner_audit.md
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_PROJECT_BACKGROUND_CURRENT_CONVERSATION
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# Route B Round03 full SRR-v3 controller contract

## 1. Scope and prior-evidence judgment

Route B is the only Round03 route allowed to construct a new full model. It answers:

> Can a faithful, final-path SRR-v3 produce a new CARE candidate after implementation gating, staged MyoPS training, official CineMA/registration/temporal training, and fresh lesion-centric evaluation?

The previous Route B packet is operational background, not Round03 scientific credit. Its race/accounting completed and its bounded run reached 25,000 optimizer steps, but evaluation covered only ten MyoPS cases, all with zero edema ground truth, and five Cine cases through a local proxy. Its implementation was two-scale, used the legacy order `[LGE,C0,T2]`, used a small internal Cine adapter, approximate registration, and weak semantic validators. Round03 changes the architecture, data sampling, positive-case coverage, official Cine source, registration, temporal interface, selector, and validators; blind reuse of that packet is forbidden.

## 2. Visual route and source-probe result

The Project-background diagrams were read independently.

- v2 defines availability-aware modality-specific evidence, selective shared/private retrieval, anatomy-guided scar/edema proposal, pathology-specific refinement, and reference-space Cine temporal evidence.
- v2.5 makes scar and edema proposal/refinement geometries separate.
- v3 adds nnU-Net logits/probabilities/hard components/uncertainty as anchor and context, train/OOF prototypes, and bounded final correction.

Evidence-selection modules are stems, routers, expert banks, and prototypes. Lesion-formation modules are the anatomy-guided proposals, soft ROIs, scar/edema refiners, and bounded final composition. M9 proved that a dictionary can be nonidentity yet harmful: selecting different evidence does not by itself control lesion recall, remote false positives, component burden, or HD95.

The targeted code probe freezes these facts:

1. Main first-party canonical modality and availability order is `[LGE,T2,C0]` in `src/care_myocardium/anchors/myops_decode.py`.
2. The old Route B implementation used `[LGE,C0,T2]`; it is incompatible and cannot be a formal Round03 wrapper.
3. `srr_propref.py` still permits deterministic bootstrap prototypes, `srr_dictionary_memory.py` contains EMA/helper memory, `cinema_adapter.py` is a small convolutional control, `registration_model.py` directly warps with `0.25*tanh(v)`, and `temporal_model.py` accepts an abstract `temporal_z`. Each is a named Round03 known-bad path.
4. Pinned CineMA source defines `cinema.segmentation.convunetr.ConvUNetR`, `decoder_dict["sax"]`, and `pred_head_dict["sax"]`. The ACDC configuration uses spacing `[1.0,1.0,10.0]`, patch size `[192,192,16]`, output classes `0=background, 1=RV, 2=MYO, 3=LV`, and a 32-channel final decoder tensor before the prediction head.

All new implementation is route-local under `src/care_myocardium/route_B_round03/**`. Shared first-party source edits are prohibited. Discovery of a necessary shared edit returns `ROUTE_B_ROUND03_NEEDS_PLANNER_SCOPE_REVISION`; the Controller cannot enlarge scope.

## 3. Data, order, manifests, and sampling

### 3.1 Canonical order and migration

All tensors, configs, manifests, logs, and checkpoints use `[LGE,T2,C0]`. Input shape is `[B,3,Z,H,W]`; availability is `[B,3]` in the same order. A missing modality is multiplied out before and after its stem and has zero private/interaction routing weight.

The old Route B checkpoint is classified `NONLOADABLE_ARCHITECTURE_AND_MODALITY_ORDER_MISMATCH`; the new four-scale model does not load it. The nnU-Net anchor remains read-only. A wrong-order known-bad fixture permutes T2/C0 and must fail the input fingerprint and semantic test.

### 3.2 Deterministic manifests

B0 creates and freezes these exact tracked manifests and SHA256 receipts before B1:

```text
configs/route_B_round03/manifests/myops_fold0_primary_44.json
configs/route_B_round03/manifests/myops_t2_edema_positive.json
configs/route_B_round03/manifests/myops_sampler_strata.json
configs/route_B_round03/manifests/cine_train12.json
results/route_B/round03/manifest_freeze_receipt.json
```

The generation command is fixed in the B0 executor prompt. `myops_fold0_primary_44.json` is the exact prior 44-case fold-0 list. The edema-positive manifest contains every primary case with T2 present and positive edema ground truth, sorted by case ID; fewer than eight makes formal MyoPS training ineligible. The primary evaluation must include scar-positive, T2-positive edema-positive, no-T2, CenterB, and CenterC rows.

The twelve-case Cine manifest contains six sorted case IDs from each of the two available training centers, real 4D image paths, reference-label paths, frame count, affine/header hash, and center. Fewer than twelve cases or fewer than four non-reference frames on a credited case blocks formal Cine work.

Hash values are deterministic B0 outputs, not Planner guesses. Until the freeze receipt contains all four SHA256 values, B1 and every formal job are blocked.

### 3.3 Disjoint pathology-balanced sampler

Strata are disjoint by precedence:

1. `E`: T2-present edema-positive cases;
2. `S`: scar-positive cases not already in `E`;
3. `R`: all remaining train cases.

Every four optimizer steps draw `E,E,S,R`. Sampling is with replacement inside each stratum using a sorted case list and Philox seed `26071821`; epoch boundaries do not change the 2:1:1 ratio. Empty `E`, fewer than eight evaluation-positive edema cases, missing CenterB/CenterC coverage, or a runtime count receipt inconsistent with the ratio blocks stage entry.

## 4. Four-scale SRR-v3 architecture

### 4.1 Stems, scales, and experts

Channels are exactly `[32,64,128,256]`. Each modality has an independent stem and encoder path. At every scale there are sixteen experts:

```text
4 shared
2 LGE-private
2 T2-private
2 C0-private
2 LGE-T2 interaction
2 LGE-C0 interaction
2 T2-C0 interaction
```

Each expert is:

```text
Conv3d(C,C,3,padding=1,bias=false)
GroupNorm(min(8,C/4),C)
SiLU
Conv3d(C,C,3,padding=1,bias=false)
GroupNorm(min(8,C/4),C)
residual add
SiLU
```

Private inputs are modality features. Pairwise inputs concatenate the two present modality features, project with `Conv3d(2C,C,1,bias=false)`, and then enter the same residual expert. Unavailable private or interaction slots are invalid and cannot receive gradients or weight.

### 4.2 Pathology-specific two-pass routing

Default semantic slot masks are fixed:

- anatomy: shared + C0-private + LGE-C0 + T2-C0;
- scar: shared + LGE-private + LGE-T2 + LGE-C0;
- edema: shared + T2-private + LGE-T2 + T2-C0.

At each scale and voxel, the router query concatenates: local fused features; a 16-channel availability embedding; anatomy union probability and signed distance; anchor entropy; anchor pathology probability; anchor component and remote-FP flags; and, in pass two, scar and edema proposal logits. The network is `Conv3d(Q,C/2,1) -> GroupNorm -> SiLU -> Conv3d(C/2,16,1)`. Routing uses entmax-1.5.

Schedule by total MyoPS progress:

```text
0%–20%: all valid entmax weights
20%–50%: valid top-4 followed by renormalization
50%–100%: valid top-2 followed by renormalization
```

Invalid logits are `-1e4`; maximum invalid absolute weight is `1e-8`. Receipts record per-task/per-scale slot mass, invalid weight, gradient norm, and response to availability/image/proposal perturbations.

### 4.3 Pattern-SIP

For spatially averaged router weight `u[b,t,l,k]`, define family mass `M[b,t,l,c]` for shared/private/interaction families. The target is `(0.50,0.35,0.15)`.

Availability groups are the observed canonical patterns. Style clusters are deterministic train-only k-means with `K=4`, seed `26071822`, over per-case modality-wise median/IQR/p05/p95 plus stage-1 pooled stem features. Centroids are fitted after stage-1 step 2000, frozen, serialized, and never use validation/test cases. Hard groups are scar-positive, T2-positive edema-positive, CenterB, CenterC, and anchor-remote-FP-positive multi-hot indicators.

For group mean expert use `ubar[g,k]`, soft activity is `q[g,k]=min(1,ubar[g,k]/0.05)`. Coverage `gamma[k]` is the weighted mean of `q` over nonempty availability×style×hard groups. The exact loss is:

```text
L_mass = mean(sum_c (M_c-target_c)^2)
L_integrative = mean_shared relu(0.60-gamma)^2
              + mean_private relu(0.25-gamma)^2
              + mean_interaction relu(0.20-gamma)^2
L_load = mean_group_family KL(normalized expert use || uniform within family)
L_sparse = mean(normalized entropy of valid router weights)
L_pattern_sip = L_mass + 0.50*L_integrative + 0.25*L_load + 0.10*L_sparse
```

Its full-loss coefficient is `0` for steps 0–999, linearly ramps to `0.02` at step 2000, is `0.05` through proposal/refiner stages, and is `0.02` in joint fine-tuning. It has an independent tensor, alias, finite-gradient, and no-gradient known-bad test.

## 5. OOF prototype bank and hard negatives

Formal prototypes are offline-fitted, fold-safe, inference-frozen, and serialized with checkpoints. Four shards are assigned by `int(sha256(case_id)[:8],16) % 4`. For each scale and pathology, positive and negative features are fitted separately with spherical k-means: scar positive 8, scar negative 12, edema positive 8, edema safe-negative 12. Candidate component centroids are sorted by case/component hash, capped at 4096 per category, initialized by deterministic farthest-point selection, and updated for 20 cosine Lloyd iterations. Empty clusters take the current farthest candidate.

For OOF shard `q`, fitting uses only the other three train shards. Validation/test labels and the current case never contribute. Banks are fitted after each selected stage checkpoint and frozen during the next stage; the final selected joint checkpoint receives a final clean-reloaded bank fit before evaluation. Receipts bind source manifest, fit commit, model checkpoint SHA, split hash, class counts, fallback count, and bank tensor SHA.

Online EMA and deterministic bootstrap are forbidden as formal memory. A no-prototype conservative-proposal control may pass the implementation gate, but missing or invalid OOF banks block formal Route B training readiness.

The training-only hard-negative queue has 256 component centroids per pathology per scale. Rank 0 gathers candidates, sorts by descending false-positive confidence then stable case/component hash, inserts at most 16 per batch, evicts oldest entries FIFO, broadcasts every 50 steps, and serializes queue state in training checkpoints. It is never loaded for validation/test inference. No-T2 myocardium can never enter the edema queue.

## 6. Proposal, ROI, refinement, and final composition

### 6.1 Proposal tensors

Each pathology upsamples its four routed features to the finest scale, projects each to 32 channels, and sums them. Scar proposal input has 43 channels: routed 32; anatomy union; anchor pathology logit and probability; anchor entropy; anchor component map; remote-FP map; positive similarity; negative similarity; similarity difference; signed anatomy distance; and anatomy-neighborhood probability. Edema adds one T2-availability channel for 44 channels.

Anchor/context maps are stop-gradient. Prototype tensors are frozen; similarity gradients reach routed features. Proposal layers are:

```text
Conv3d(in,64,3,padding=1) -> GroupNorm(8) -> SiLU
Conv3d(64,32,3,dilation=d,padding=d) -> GroupNorm(8) -> SiLU
Conv3d(32,1,1)
```

`d=2` for scar and `d=3` for edema. Scar target is a one-voxel dilation of scar GT; edema target is a three-voxel dilation and exists only on T2-present labeled cases.

### 6.2 Soft ROI

For pathology `p`:

```text
roi_p = sigmoid((proposal_prob_p-theta_p)/temperature_p)
        * (0.7+0.3*anatomy_union)
        * exp(-relu(distance_p-d0_p)/distance_temperature_p)
```

Scar uses `theta=.55`, `temperature=.10`, dilation 2, `d0=3`, distance temperature 2, minimum crop `[8,64,64]`, and margin `[1,4,4]`. Edema uses `theta=.35`, `temperature=.12`, dilation 5, `d0=6`, distance temperature 4, minimum crop `[12,96,96]`, and margin `[2,8,8]`. The crop includes `roi>0.1` plus anatomy support; it never hard-deletes outside predictions. Anatomy-only fallback may occur on at most 5% of formal cases and cannot earn candidate credit.

### 6.3 Refiners and bounded final logits

Scar refiner uses three 64-channel residual blocks with dilations `[1,2,3]`. Edema uses four 64-channel blocks with dilations `[1,2,4,6]`. Each consumes the cropped routed feature, pathology image evidence, proposal probability, ROI, endo/epi/union distance maps, anchor logit/probability, positive/negative similarity, uncertainty, and anatomy probabilities. Each returns one pathology logit and is pasted back with trilinear probability blending and the soft ROI.

Gate architecture is `Conv3d(12,16,1) -> GroupNorm(4) -> SiLU -> Conv3d(16,1,1) -> sigmoid`. Gate target is the anchor-error opportunity mask inside the ROI: pathology false negatives plus pathology false positives. Gate loss is focal BCE with `alpha=.75`, `gamma=2`.

Final logits preserve classes 0–3 and apply bounded pathology corrections:

```text
delta_p = 4.0*tanh(refiner_logit_p-anchor_logit_p)
z_final_p = z_anchor_p + roi_p*gate_p*delta_p
```

No-T2 edema loss, bank update, queue update, proposal, ROI, refiner, gate, delta, and Route-B-owned edema change are exactly zero. Official six-label reconstruction uses argmax after this composition; no post-hoc label invention is allowed.

Every selected checkpoint exposes the causal chain:

```text
retrieval -> prototype similarity -> proposal -> ROI -> refiner -> bounded delta -> final logits -> final labels
```

On/off interventions report changed logits, voxels, components, Dice, HD95, remote-FP, component count, and volume ratio for each node.

## 7. Full loss and four-stage MyoPS training

Loss terms are Dice-CE unless specified. Scar boundary uses a distance-transform boundary loss; edema boundary is uncertainty-weighted. Prototype positive/negative terms use margin `0.20`. Negative-space loss uses only safe negatives. ROI loss is BCE against the dilated target. Bounded-delta regularization is mean squared delta outside anchor-error opportunities.

| term | evidence warmup | proposal | refiner | joint |
|---|---:|---:|---:|---:|
| anatomy | 1.00 | 0.50 | 0.20 | 0.10 |
| scar evidence | 0.75 | 0.25 | 0.10 | 0.10 |
| edema evidence, T2 only | 0.75 | 0.25 | 0.10 | 0.10 |
| scar proposal | 0 | 1.00 | 0.25 | 0.20 |
| edema proposal, T2 only | 0 | 1.00 | 0.25 | 0.20 |
| prototype margin | 0 | 0.25 | 0.10 | 0.10 |
| negative space | 0 | 0.20 | 0.25 | 0.10 |
| scar refiner | 0 | 0 | 1.00 | 0.50 |
| edema refiner, T2 only | 0 | 0 | 1.00 | 0.50 |
| scar boundary | 0 | 0.10 | 0.20 | 0.10 |
| edema boundary, T2 only | 0 | 0.05 | 0.10 | 0.05 |
| ROI | 0 | 0.20 | 0.20 | 0.10 |
| anatomy prior | 0.10 | 0.10 | 0.10 | 0.10 |
| gate | 0 | 0 | 0 | 0.20 |
| final output | 0 | 0 | 0.50 | 1.00 |
| Pattern-SIP | scheduled | 0.05 | 0.05 | 0.02 |
| bounded-delta regularizer | 0 | 0 | 0 | 0.01 |

All stages use batch size 1, gradient accumulation 2, AMP, gradient clip 5, and the frozen sampler. Exact stages:

1. Evidence warmup: 6,000 steps, at least 1,800 train-loop seconds, 3 validation events, AdamW `2e-4`, weight decay `1e-4`, 500-step warmup then cosine. Train stems/encoders/experts/routers/anatomy/evidence heads; freeze proposal/refiner/gate. Checkpoints 2000/4000/6000. Exit requires finite losses, one-batch overfit, anatomy-union Dice at least .70 on the overfit batch, live gradients for every valid family, and valid style-cluster freeze.
2. Proposal: 8,000 steps, at least 2,400 seconds, 4 validation events, AdamW `1e-4`, cosine. Train routers/upper experts/anatomy/proposals; freeze refiners/gates. Checkpoints 2000/4000/6000/8000. Exit requires scar proposal recall at least .85, T2-positive edema proposal recall at least .90, nonzero similarity contribution, and no forbidden negatives.
3. Refiner: 10,000 steps, at least 3,000 seconds, 5 validation events, AdamW `1e-4`, cosine. Freeze stems/lower encoders/prototype banks; train refiners and upper routed features. Checkpoints 2000/4000/6000/8000/10000. Exit requires positive proposal-to-final retention, nonzero changed components, scar remote-FP non-increase on the gate set, and no-T2 exact zero.
4. Joint fine-tuning: 8,000 steps, at least 2,400 seconds, 4 validation events, AdamW `2e-5`, cosine without restart. Unfreeze all Route B modules except frozen OOF banks. Checkpoints 2000/4000/6000/8000. Exit requires 32,000 cumulative steps, 9,600 cumulative train seconds, 16 validation events, fresh 44-case evaluation, at least eight T2-positive edema-positive cases, clean reload, and all validators.

A stage cannot advance when its gate fails. Operational failures receive at most two same-scope retries with identical code/config/split/scientific hashes. Scientific gate failure does not permit redesign during execution; it yields a non-ready or adequate-negative packet for review.

## 8. Official CineMA and matched random control

Pinned source:

```text
repository: mathpluscode/CineMA
code commit: c10daa1d93f0ea28d8b9ad9206b0f673d25805c1
Hugging Face revision: b1251ee50423bceeca84c080782fc3bc7756dea6
weight: finetuned/segmentation/acdc_sax/acdc_sax_0.safetensors
SHA256: c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f
model: cinema.segmentation.convunetr.ConvUNetR
license: MIT
```

The adapter imports the pinned official preprocessing symbol `cinema.data.sitk.clip_and_normalise_intensity_4d`, reorients to RAS, resamples images with linear interpolation and labels with nearest interpolation to `[1.0,1.0,10.0]` mm, and applies one physical-center crop/pad `[192,192,16]` to all frames. Tensor order is SimpleITK `(x,y,z,t)` to PyTorch `[B,T,1,192,192,16]`. No GT label is used to center a CARE inference crop.

A forward hook captures the 32-channel `decoder_dict["sax"]` output immediately before `pred_head_dict["sax"]`; a route-local frozen `1x1x1` projection produces 16 channels. Outputs are logits `[B,4,192,192,16]`, probabilities, features `[B,16,192,192,16]`, and normalized entropy `[B,1,192,192,16]`. Official class mapping is `0 background, 1 RV, 2 MYO, 3 LV`; CARE mapping is recorded explicitly. Affine, direction, origin, spacing, crop, interpolation, and inverse-resampling provenance are hashed.

The official source and the matched random `ConvUNetR` are both frozen. Their only difference is source initialization. One common downstream initialization artifact contains the feature projection, registration, temporal router, and temporal head state. It is created once with seed `26071831`, stored untracked, and bound by `results/route_B/round03/downstream_initialization_receipt.json`. Before any run, parameter names/shapes/frozen/trainable masks, downstream values, optimizer, cases, frames, augmentation draws, cadence, and selector hashes must match exactly; only source-weight hashes differ.

Each source adapter/control uses 8,000 optimizer steps, at least 3,600 train seconds, 4 validation events, 12 cases, AdamW `2e-4`, weight decay `1e-4`, batch size one case, gradient clip 5, and checkpoints 2000/4000/6000/8000. Augmentation draws are serialized and shared: rotation `[-10,10]` degrees, gamma `[0.9,1.1]`, Gaussian sigma `[0,.03]`; temporal order is never shuffled.

## 9. Faithful registration and SyN control

The first-party registration U-Net has channels `[16,32,64,128]` and outputs stationary velocity `v:[B,3,Z,H,W]` in normalized-grid units. With `align_corners=true`, convert normalized displacement to voxel units only for receipts and Jacobian computation.

```text
d0 = v / 2^7
d_{i+1} = d_i + warp(d_i,d_i), i=0..6
phi = identity + d7
phi_inverse = exp(-v) by the same seven steps
```

Images/features/probabilities use trilinear warp; labels use nearest; padding is border. Direct velocity-as-displacement is forbidden. Jacobian determinant uses central finite differences in voxel coordinates. Receipts include minimum/mean Jacobian, folding rate, forward/inverse output hashes, and inverse-composition error.

Registration loss weights are LNCC image 1.0, soft anatomy Dice 1.0, velocity smoothness .10, negative Jacobian .05, inverse composition .50, and CineMA feature consistency .25. Training is 25,000 steps, at least 7,200 seconds, 10 validation events, four full-case events, 12 cases, at least 60 pairs, AdamW `1e-4`, weight decay `1e-5`, gradient clip 5, seed `26071832`, checkpoints 5000/10000/15000/20000/25000.

A pair passes when folding fraction is at most `.005`, minimum Jacobian is positive, mean inverse-composition error is at most `1.5` voxels, and warped anatomy Dice is no worse than unregistered by more than `.01`. A case passes with at least 80% pair pass and four passed non-reference frames. The aggregate gate requires at least 90% of 12 cases.

Real control uses `ants.registration(type_of_transform="SyNOnly", reg_iterations=(40,20,0), syn_metric="CC", syn_sampling=2, flow_sigma=3, total_sigma=0, grad_step=.2)` on identical pairs; `ants.apply_transforms` uses linear interpolation for images/probabilities/features and nearest-neighbor for labels. Learned and SyN outputs are independently hashed and never copied.

## 10. Registered temporal aggregation

The temporal interface is a named structure, never an abstract `temporal_z`. It contains ED logits/features/uncertainty; registered non-reference logits/features/uncertainty; velocity; integrated displacement; Jacobian; motion magnitude; texture residual; frame quality; two-channel sinusoidal temporal position; and valid-frame mask.

Each frame is projected to 32 channels. An eight-slot masked router implements: ED anatomy anchor, early/late systolic contraction, early/late diastolic relaxation, motion magnitude, registered texture residual, and registration-uncertainty safety. Two 32-channel residual convolution blocks and a four-class head produce ED-space logits.

Controls are reference-only, unregistered multi-frame, registered temporal, temporal-off, motion-off, anatomy-off, and pretrained-vs-random. Temporal starts only after selected registration clean reload passes. It trains cumulatively to 20,000 credited steps in targets 4000/8000/12000/16000/20000, at least 7,200 seconds, 10 validation events, four full-case events, 12 cases, AdamW `2e-4`, weight decay `1e-4`, gradient clip 5, seed `26071833`. Chunks are capped at 6.5 estimated hours; checkpoints are atomic at most every 500 steps and on `SIGUSR1/TERM`. Gap, overlap, reset, duplicate, missing parent hash, timeout, preemption, or partial attempts receive zero credit.

Temporal on/off must alter real final logits, labels, voxels, and components on at least eight cases.

## 11. Checkpoint eligibility and selector

Eligibility precedes scoring: fresh `--force`; manifest/checkpoint/state-dict/prediction/evaluator hashes; complete denominators; proposal recall floors; changed voxels and components greater than zero; no-T2 edema delta exactly zero; nonempty prediction on at least 80% of positive cases; median pathology volume ratio in `[.25,4]`; finite values; clean reload within `1e-5`; and all implementation/packet validators passing.

For GT-positive cases, empty prediction gives Dice 0 and HD95 100 mm. Both-empty rows are excluded and cannot count as improvement. Missing required subgroup rows make a checkpoint ineligible.

Normalize terms:

```text
D_scar = clip(scar_positive_Dice_delta,-.25,.25)/.25
D_edema = clip(T2_positive_edema_Dice_delta,-.25,.25)/.25
H_scar = clip((anchor_HD95-model_HD95)/20,-1,1)
H_edema = clip((anchor_HD95-model_HD95)/20,-1,1)
F_remote = clip((anchor_remoteFP-model_remoteFP)/max(anchor_remoteFP,100),-1,1)
S = .40*D_scar + .25*D_edema + .15*H_scar + .10*H_edema + .10*F_remote
```

Tie-breakers are higher `S`, lower severe-harm fraction, lower component-count delta, lower absolute volume-ratio deviation, then earlier cumulative optimizer step.

Cine selects each source by highest mean myocardium Dice, then lower HD95 within `.001`, then earlier step. `PRETRAINED_BENEFIT` requires Dice advantage at least `.01` and HD95 disadvantage at most 1 mm. `RANDOM_NONINFERIOR` requires absolute Dice difference at most `.005` and random HD95 no worse. Otherwise state is `CINEMA_CONTROL_UNRESOLVED`. Downstream always uses the clean-reloaded pretrained source.

## 12. Metric and evidence classification

Positive gates:

- scar: Dice delta at least `.01` or HD95 improvement at least 1 mm, with remote-FP nonincrease and severe-harm fraction at most `.20`;
- edema: T2-positive Dice delta at least `.02` or HD95 improvement at least 1 mm, with exact no-T2 zero;
- Cine: temporal Dice delta versus reference-only at least `.01`, HD95 disadvantage at most 1 mm, and changed labels on at least eight cases.

Candidate-ready review requires all implementation/safety/mechanism gates, nonzero MyoPS changed voxels/components/cases, at least two positive target gates, and a non-worse third target. A faithful adequate run that misses this is an adequate negative, not a route stop.

## 13. Executor, Slurm, and deadline contract

The exact B0–B10 graph, commands, outputs, completion tokens, retry states, partition matrices, and race ledgers are in `route_B_executor_plan.yaml` and its prompt files. Multiple independent ready jobs are assigned to different partitions before duplication. Full MyoPS formal stages default to `htzhulab` and `a100-gpu`; they are V100-incompatible unless exact unchanged-config preflight proves peak memory at most 14.5 GiB. `volta-gpu` is assigned official CineMA extraction/control, replay/evaluation, registration evaluation, and lightweight GPU gates. A single compatible critical job may race immediately; no two-hour delay is required. Race attempts have identical scientific hashes, isolated output/log/checkpoint/cache roots, one atomic winner lock, pending-loser cancellation, loser zero credit, and complete accounting.

Decision checkpoints:

```text
2026-07-20: B0–B2 source/manifest/validator/implementation gate terminal; no long training before pass.
2026-07-21: evidence-warmup and proposal stages terminal with intermediate gates.
2026-07-22: refiner/joint first formal MyoPS evidence and official CineMA/control preflight or terminal evidence.
2026-07-23: only evidence-directed same-scope repair.
2026-07-24: model/loss freeze.
2026-07-25: route-local packet and independent review input.
2026-07-26: runtime/review/Docker/packaging/paper QA only.
2026-07-27: no new experiment.
```

## 14. Strict validators, known-bad, and reviewer state machine

Strict validators must parse values and exit nonzero on every error. Executable fixtures cover wrong modality order; nnU-Net-only bypass; disconnected retrieval/proposal/refiner/gate; bootstrap/EMA formal memory; OOF leakage; no-T2 edema negatives; fewer than eight positive edema cases; zero positive edema GT; Pattern-SIP alias/no gradient; fake CineMA or wrong weight SHA; unmatched random control; direct velocity displacement; missing seven-step integration; proxy Jacobian; pair-as-case aggregation; unconsumed temporal inputs; `temporal_z`-only or frame0 fallback; zero MyoPS effect plus Cine gain; stale metrics/missing `--force`; local proxy as official metric; selected checkpoint not reloaded; pending/monitor/undertrained/stale receipts; runtime push/review; forbidden authority; inconsistent race hashes; shared race output; missing atomic lock; loser credit; pending loser not cancelled; V100 semantic downscaling; and V100 compatibility without exact-config preflight.

Final Controller packet token is `ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW` only after terminal accounting, aggregation, mapper final, strict validator pass, known-bad pass, heavy-artifact scan, and a lightweight local commit. Monitor, awaiting-accounting, undertrained-in-progress, stale, or validator-failed states cannot use it.

B10 is a terminal accounting/finalizer DAG, not a B9-success continuation. The Controller must schedule or run B10 for every terminal class after any attempt has started, including success, failure, timeout, preemption, adequate-negative evidence, early implementation/data/validator gate failure, cancelled pending race loser, and bounded retry replacement. B10 uses `afterany` over all started Slurm attempt IDs from the controller ledger; if no Slurm attempt was started because an early local gate failed, it runs the local deterministic finalizer path. A packet cannot request normal review until every started attempt has terminal accounting, aggregation, mapper/architecture validation, strict validator, known-bad, git-diff and lightweight packet receipts.

The independent reviewer may emit only:

```text
ROUTE_B_ROUND03_REVIEW_CANDIDATE_READY
ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE
ROUTE_B_ROUND03_REVIEW_EXTERNAL_RESOURCE_BLOCKER
ROUTE_B_ROUND03_REVIEW_UNDERTRAINED
ROUTE_B_ROUND03_REVIEW_NEEDS_MONITOR
ROUTE_B_ROUND03_REVIEW_NEEDS_EVIDENCE
ROUTE_B_ROUND03_REVIEW_NEEDS_REVISION
```

Each token must bind required files, validator state, adequacy, race/finalizer accounting, rejection reasons, and next actor as specified in B10. Reviewer acceptance permits only later Portfolio reconciliation.

## 15. Authority boundary

Planner publication is not Critic approval. Only a Round03 Critic ready token bound to the exact route commit and blobs can authorize the Route B Controller. Nothing in this contract authorizes validation packaging/upload, route promotion, M11, cross-route merge, hosted metric claims, or a final scientific decision.
