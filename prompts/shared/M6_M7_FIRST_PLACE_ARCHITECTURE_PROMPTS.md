# M6/M7 First-Place Architecture Prompts

This file is a high-standard replacement / supplement for the current M6 and M7 milestone prompts. It is written for a mature medical-imaging / statistics / computer-science review standard. It is intentionally more prescriptive than the existing milestone prompts because the project has repeatedly failed when Codex was allowed to infer architecture details during execution.

Use this file when revising or launching the next M6 / M7 work. Do not treat it as a loose idea list. The executor must implement the explicitly required design choices, ablations, reports, and hard gates, or stop with `NEEDS_REVISION`, `NEEDS_EVIDENCE`, or `RESOURCE_BLOCKED`.

## Diagram-source and recovered objective

The route diagrams have been visually read from the ChatGPT Project background materials, corresponding to canonical repository filenames:

```yaml
diagram_source: "ChatGPT Project background materials"
diagram_versions_read:
  - "SRR-v2"
  - "SRR-v2.5"
  - "SRR-v3"
canonical_repo_paths:
  - "images/SRR-v2.png"
  - "images/SRR-v2.5.png"
  - "images/SRR-v3.png"
visual_read_status: "READ_FROM_PROJECT_BACKGROUND"
```

Recovered route objective:

SRR-MyoPS is not a plain multi-channel segmentation model, not a post-processing wrapper around nnU-Net, and not a generic nnU-Net fallback. It is a baseline-preserving, availability-aware, pathology-specific representation retrieval system. It must retrieve reliable modality-specific evidence from shared/private/interaction dictionaries, use anatomy-guided lesion proposal, use scar/edema-specific soft-ROI refinement, preserve strong nnU-Net evidence only as anchor/context/safety, and include explicit losses for proposal, refinement, negative space, dictionary regularization, residual/gate consistency, no-T2 edema safety, and registration/alignment where relevant.

The three diagrams all keep a registration/alignment idea in the route. For MyoPS this appears as `feature-level LGE-reference alignment expert` on complete tri-modal subsets. For Cine this appears as `registration-aware temporal retrieval`, with reference-frame registration / warping before temporal representation dictionary and aggregation. Therefore, future milestones must not silently downgrade the route to registration-free retrieval.

## Current evidence that motivates this stricter design

M3/M4 established that the current SRR-v3 implementation can train and can export evidence, but it is not yet competitive with nnU-Net. The failure is not merely a missing longer training run. The observed mechanism reading is:

1. The SRR branch can change predictions, but the current trained path hurts same-split metrics relative to nnU-Net.
2. Closed-gate identity is neutral, so baseline-preserving fallback itself is not the source of harm.
3. Removing the nnU-Net anchor is strongly harmful, so nnU-Net must remain a protected anchor/context source.
4. Proposal/refinement/decode behavior remains weak or miscalibrated; this is the route’s main bottleneck.
5. Cine M5 established that registration evidence is incomplete, but it also produced enough router/proxy evidence to stop pure audit and force runtime experiments. However, M7 must not convert `registration evidence incomplete` into `registration-free method`.

The design below is what SRR must become if the goal is a leaderboard-winning method, not merely a diagram-faithful diagnostic packet.

---

# Part I. M6-Plus: First-place MyoPS architecture

## Scientific target

M6-Plus targets `myops_scar` and `myops_edema` while protecting the current nnU-Net baseline. The method should be called:

```text
SRR-ProposeAlignRefine: Baseline-preserving selective retrieval with LGE-reference alignment, anatomy-guided pathology proposal, and bounded scar/edema refinement
```

The first-place-level hypothesis is:

A strong nnU-Net anchor already provides stable general anatomy and scar structure, but fails on edema localization, CenterC/T2-present cases, component burden, remote false positives, and small pathology boundary/topology. SRR should not replace nnU-Net globally. It should learn where the anchor is uncertain or wrong, retrieve modality-specific scar/edema evidence, generate anatomically plausible lesion proposals, and apply bounded local corrections. On complete tri-modal cases, C0 and T2 must be aligned to LGE/reference evidence at least at feature level or through a classical registration pilot; otherwise retrieval is mixing spatially inconsistent evidence.

## Non-negotiable design principles

1. nnU-Net is an anchor and evidence provider, not the method’s final answer. It supplies logits/probabilities, hard predictions, components, uncertainty, anatomy context, and safety fallback.
2. SRR is the correction mechanism. It must produce real retrieval/proposal/refinement evidence and bounded residual maps.
3. Alignment is required as a runtime pilot. It may be classical or feature-level, but it cannot be only future work.
4. Scar and edema must be treated as different tasks. Scar is LGE-driven, small, high-precision, HD-sensitive. Edema is T2-conditioned, broader, recall-sensitive, and no-T2 unsafe for negative supervision.
5. No-T2 myocardium must never be used as an edema-negative label.
6. All improvements must be evaluated by same-split help/harm, not just all-case Dice. Required dimensions include Dice, HD95, component count, remote FP, GT-positive Dice, T2-present edema, no-T2 safety, CenterC, and scar guardrails.

## M6-Plus architecture overview

The final system should contain eight explicit modules:

```text
Input/availability
  -> LGE-reference alignment / registration evidence layer
  -> modality-specific stems + strong encoder
  -> nnU-Net anchor/context interface
  -> semantic representation retrieval bank
  -> anatomy decoder + anatomy prior/distance/uncertainty maps
  -> scar/edema proposal dictionaries and proposal decoders
  -> pathology-specific soft-ROI refiners
  -> baseline-preserving residual arbitration and final decode
```

### Module 1. Input, availability, and preprocessing

Inputs:

```text
LGE: required when available; primary scar signal
C0 / bSSFP: anatomy / boundary support
T2: primary edema signal
m = (m_LGE, m_C0, m_T2): availability mask
spacing / orientation / case metadata: provenance only, not a center shortcut
```

Required preprocessing rules:

1. No zero-filling semantics. If a modality is absent, the model sees an explicit missing mask and no fake image evidence for that modality.
2. All available modalities must be resampled onto a common computational grid. The default grid is LGE-reference for MyoPS.
3. Intensity normalization must be per-modality and robust: foreground percentile clipping, z-score or median/IQR normalization, and provenance rows for normalization parameters.
4. Save an `input_availability_audit.csv` containing case id, modality availability, shape, spacing, grid target, normalization stats, and label availability.

### Module 2. Required LGE-reference alignment / registration evidence layer

The current M6 prompt makes alignment optional. That is not sufficient. M6-Plus must implement a bounded alignment pilot for complete tri-modal cases.

Required alignment candidates:

```text
A. Classical high-quality reference path:
   - ANTs SyN or SimpleITK SyN-like / Demons where available.
   - Register C0 -> LGE and T2 -> LGE on complete cases.
   - Use masks/anatomy/foreground weighting where possible.

B. Fast fallback path:
   - SimpleITK Demons or dense optical-flow-style registration.
   - Must run on a larger subset than SyN if SyN is too slow.

C. Baseline-inspired TPS path:
   - U-MyoPS-style LGE-reference TPS or feature-warp adapter.
   - A full U-MyoPS Stage1->Stage2 bridge is not required, but a small TPS/STN adapter is required as a candidate if feasible.

D. No-warp control:
   - The current resampled but unregistered input.
```

Required alignment scope:

```text
minimum_cases: 12 complete tri-modal cases, unless resource-blocked
preferred_cases: all fold0 complete tri-modal eval cases plus CenterC hard cases
moving_to_fixed: C0->LGE and T2->LGE
```

Required alignment evidence file:

```text
registration_alignment_runtime_sanity.csv
```

Required columns:

```text
case_id
moving_modality
fixed_modality
method
status
moving_shape
fixed_shape
warped_shape
ncc_before
ncc_after
mi_before
mi_after
foreground_overlap_proxy_before
foreground_overlap_proxy_after
jacobian_min
jacobian_p01
jacobian_p99
foldover_voxel_count
runtime_seconds
artifact_path_ignored
used_in_model_or_eval
failure_reason
```

Required downstream impact file:

```text
alignment_help_harm.csv
```

Required rows compare at least:

```text
no_warp_control
syn_or_demons_warped_input
feature_warp_or_tps_candidate
```

Required metrics:

```text
scar_proposal_recall_delta
scar_remote_fp_delta
scar_hd95_delta
edema_proposal_recall_delta
edema_remote_fp_delta
edema_hd95_delta
centerC_edema_delta
no_t2_safety_delta
```

Hard gate:

If `registration_alignment_runtime_sanity.csv` is missing, empty, only natural-language, or contains only one-case smoke without a blocked state, M6-Plus must not be `READY_FOR_REVIEW`. If alignment is genuinely too slow, M6-Plus must write `M6_RESOURCE_BLOCKED_ALIGNMENT` with exact attempted commands, case count, runtime, and fallback decision. Do not mark alignment as optional future work.

### Module 3. Strong encoder and modality-specific stems

A first-place SRR should not use a toy encoder. Use a memory-safe but real 3D encoder.

Minimum architecture:

```text
Input patch: same as current MyoPS training ROI / nnU-Net-compatible crop
Stems: one per modality, each with 2 residual conv blocks
Stem channels: 32
Encoder levels: 4
Level channels: 32, 64, 128, 256
Each level: 2 residual blocks, InstanceNorm3d, LeakyReLU, dropout only if already stable
Downsample: strided conv or nnU-Net-style pooling
Deep supervision: optional for anatomy/proposal, not for final arbitrary full-volume residual
```

For each modality `m`, produce features:

```text
F_m^1, F_m^2, F_m^3, F_m^4
```

Fusion must be availability-aware:

```text
F_fused^l = masked_fusion(F_LGE^l, F_C0^l, F_T2^l, m, alignment_quality)
```

Alignment quality must enter the router. A low-quality T2 warp should reduce T2 contribution, not silently poison edema evidence.

### Module 4. nnU-Net anchor/context interface

The nnU-Net position in SRR-v3 is correct only if it is protected and auditable. It is wrong if it becomes the final answer by hidden shortcut, and it is wrong if SRR ignores it.

Required nnU-Net inputs:

```text
anchor_logits: [B, C, H, W, D]
anchor_probabilities
anchor_hard_prediction
class-specific components for scar and edema
component size / centroid / distance-to-myo statistics
anchor_uncertainty: entropy, margin, or fold ensemble variance
anatomy context: myocardium/LV/RV/union probabilities or hard masks
```

Required anchor provenance:

```text
nnunet_anchor_context_index.csv
```

Required fields:

```text
case_id
anchor_dataset
folds_used
checkpoint
prediction_path
probability_path
logit_path_if_available
component_count_scar
component_count_edema
uncertainty_mean_scar_region
uncertainty_mean_edema_region
```

Final output form:

```text
z_final_scar  = z_anchor_scar  + g_scar  * bounded_delta_scar
z_final_edema = z_anchor_edema + g_edema * bounded_delta_edema
```

where:

```text
g_scar, g_edema in [0, 1] spatial gates
bounded_delta = delta_max * tanh(raw_delta / delta_scale)
```

Exact identity rule:

If fallback is chosen, gate is closed, or arbitration selects pure anchor, final labels must be exactly equal to anchor labels for the affected class/case/region. Hidden decode deltas are a hard failure.

### Module 5. Semantic representation retrieval bank

The current dictionary idea is under-specified for a winning method. It must become a semantic, multi-slot, prototype-grounded, negative-aware memory system.

At each encoder scale `l`, define:

```text
D_sh^l: shared dictionary, K_sh = 8 expert slots
D_LGE^l: LGE-private dictionary, K_LGE = 4
D_C0^l: C0-private dictionary, K_C0 = 4
D_T2^l: T2-private dictionary, K_T2 = 4
D_mix^l: interaction dictionary, K_mix = 4, enabled only for complete or reliable multi-modal cases
```

Each dictionary slot is a lightweight residual expert block, not just a scalar prototype:

```text
ExpertBlock_l,k:
  1x1x1 conv reduce -> 3x3x3 depthwise/separable or residual conv -> 1x1x1 conv restore
  channels = level channels
  norm = InstanceNorm or GroupNorm
```

Routing query per scale:

```text
q_l = concat(
  pooled fused feature,
  availability embedding e(m),
  anchor uncertainty summary,
  alignment quality summary,
  anatomy prior summary
)
```

Each head has separate sparse gates:

```text
alpha_ana^l  = SparseGate(router_ana^l(q_l))
alpha_scar^l = SparseGate(router_scar^l(q_l))
alpha_ede^l  = SparseGate(router_ede^l(q_l))
```

Use soft top-k / entmax during training and top-2 or top-3 during inference. Do not hard-top-k too early.

Prototype bank must be real and same-split safe:

```text
scar_positive prototypes
scar_safe_negative prototypes
edema_positive prototypes (T2-present only)
edema_safe_negative prototypes (T2-present far-from-GT + anatomy-safe background)
normal_myo prototypes
blood_pool prototypes
remote_artifact prototypes
```

Prototype source rules:

1. Prototypes must come from train or OOF source only. No validation GT leakage.
2. Store case ids and source split in `prototype_bank_index.json`.
3. Edema prototypes must report T2-present positive and safe-negative counts.
4. No-T2 myocardium is not edema-safe-negative.
5. Prototype updates during training should use EMA or epoch-refresh, not uncontrolled batch noise.

Required dictionary losses:

```text
L_dict = L_sparsity + L_coverage + L_load_balance + L_diversity + L_prototype_margin
```

Minimum definitions:

```text
L_sparsity: encourage sparse gates but do not collapse
L_coverage: every clinically meaningful dictionary group used by at least N cases
L_load_balance: avoid all samples using one shared slot
L_diversity: cosine separation among prototype slots within a class
L_prototype_margin: positive region closer to positive prototype than safe-negative prototype
```

Prototype-margin formula for class `k`:

```text
s_pos(p,k) = max_{c in D_k^+} cos(f_p, c)
s_neg(p,k) = max_{c in D_k^-} cos(f_p, c)
L_pos(k) = sum_{p in positive_k} max(0, margin_pos - s_pos(p,k) + s_neg(p,k))
L_neg(k) = sum_{q in safe_negative_k} max(0, margin_neg + s_pos(q,k) - s_neg(q,k))
```

### Module 6. Anatomy-guided lesion proposal

A first-place method requires lesion proposal. Dense SRR without proposal is not enough.

Anatomy decoder output:

```text
P_union: myocardium union / pathology-support prior
P_LV
P_RV
P_epi_or_wall_distance optional
```

Use union rather than pure myocardium as the primary support because CARE labels can replace myocardium with pathology. Hard clipping is forbidden except as a conservative post-hoc safety control in ablation.

Scar proposal decoder:

```text
Inputs:
  routed scar features
  LGE-private features
  anchor scar probability/component/uncertainty
  anatomy prior/distance maps
  scar prototype similarity maps
  alignment quality
Output:
  P_scar_prop coarse proposal
```

Edema proposal decoder:

```text
Inputs:
  routed edema features
  T2-private features only if m_T2=1 and alignment quality is acceptable
  anchor edema probability/component/uncertainty
  anatomy prior/distance maps
  edema prototype similarity maps
Output:
  P_ede_prop coarse proposal
```

Proposal logit should be evidence-difference based, not a plain conv head only:

```text
logit_prop_k = a_k * E_k + b_k * P_union - c_k * distance_to_union
             + d_k * s_pos(k) - e_k * s_neg(k)
             + f_k * anchor_uncertainty_or_error_signal
             + h_k * alignment_quality
```

Required proposal metrics:

```text
proposal_recall_at_thresholds
proposal_precision_at_thresholds
lesion_wise_recall
remote_fp_count
component_count
bbox_distance_to_union
volume_ratio
```

### Module 7. Pathology-specific soft-ROI refinement

Refinement must be local, bounded, and pathology-specific. Full-volume residual refinement is a hard failure.

Soft-ROI generator:

```text
ROI_k = f(P_prop_k, P_union, distance_to_union, anchor_uncertainty, alignment_quality, component_stats)
```

The ROI is not a hard deletion mask. It produces crops / soft weights.

Scar refiner:

```text
Purpose: small-ROI high-resolution high-precision correction
Input channels:
  original LGE crop
  aligned C0 crop if available
  aligned T2 crop as weak context if reliable
  anchor scar probability crop
  anchor scar component map crop
  P_scar_prop crop
  P_union / distance maps
  scar prototype similarity maps
  uncertainty crop
Architecture:
  3D mini U-Net, channels 16/32/64 or 24/48/96
  3 levels, residual blocks, skip connections
  output bounded_delta_scar and gate_scar
```

Edema refiner:

```text
Purpose: larger-ROI context-preserving T2-conditioned correction
Input channels:
  original/aligned T2 crop when m_T2=1
  LGE crop as scar/context evidence
  C0 crop as anatomy context
  anchor edema probability crop
  anchor edema component map crop
  P_ede_prop crop
  P_union / distance maps
  edema prototype similarity maps
  uncertainty crop
Architecture:
  3D mini U-Net, channels 16/32/64 or 24/48/96
  larger crop or larger dilation than scar
  output bounded_delta_edema and gate_edema
```

Required crop evidence:

```text
refiner_roi_component_sanity.csv
```

Required fields:

```text
case_id
class
roi_voxel_count
crop_volume_ratio
is_full_volume_crop
proposal_recall_proxy
proposal_precision_proxy
residual_abs_mean
residual_abs_p95
gate_mean
gate_open_rate
remote_fp_delta
component_delta
hd95_delta
```

### Module 8. Branch arbitration and final decode

Arbitration is mandatory. It must choose among anchor, SRR proposal/refiner, and fallback by evidence quality.

Required arbitration outputs:

```text
segmentation_weight
srr_retrieval_weight
proposal_weight
refiner_weight
registration_weight_or_alignment_quality
chosen_source
fallback_reason
```

Arbitration features:

```text
anchor confidence
anchor component plausibility
SRR proposal confidence
prototype margin
anatomy support
alignment quality
T2 availability and quality
remote-FP risk
no-T2 edema flag
```

Hard safety rules:

1. No-T2 edema final decode must not add edema unless explicitly authorized by a separate no-T2 inference experiment. Current default: no new edema in no-T2 cases.
2. Scar correction must be bounded and must not create distant remote islands unless proposal/anatomy/prototype evidence supports it.
3. If alignment quality is poor, do not use aligned moving modality evidence for correction; downweight it.
4. If refiner ROI is empty or low confidence, fallback to anchor for that class/case.

## M6-Plus losses

Total loss:

```text
L_total = L_anchor_preserve
        + L_ana
        + L_scar_prop + m_T2 * L_ede_prop
        + L_scar_ref  + m_T2 * L_ede_ref
        + L_boundary_hd
        + L_neg
        + L_dict
        + L_prior + L_roi
        + L_gate_decode
        + L_align
```

Definitions:

```text
L_anchor_preserve:
  penalizes harmful changes in high-confidence anchor-correct regions.
  uses anchor confidence and available GT on train folds.

L_ana:
  DiceCE for P_union, P_LV, P_RV.

L_scar_prop:
  scar proposal Dice/Focal/Tversky + weak boundary/HD surrogate.

L_ede_prop:
  T2-present only edema proposal loss. No-T2 cases do not contribute edema negatives.

L_scar_ref:
  local crop scar refinement DiceCE/Focal-Tversky + boundary/HD/instance loss.

L_ede_ref:
  T2-present only local crop edema refinement DiceCE/Focal-Tversky + surface/distance loss.

L_boundary_hd:
  use MONAI HausdorffDTLoss, boundary loss, or regional HD surrogate; start with scar and remote-FP-sensitive regions.

L_neg:
  hard-negative / safe-negative prototype margin.

L_dict:
  sparsity, coverage, load-balance, prototype diversity, prototype margin.

L_prior / L_roi:
  soft anatomy containment and ROI regularization, not hard clipping.

L_gate_decode:
  if gate closed / fallback chosen, final output equals anchor; all label deltas trace to explicit masks.

L_align:
  image/anatomy/feature consistency for C0/T2 -> LGE on complete cases; smoothness/Jacobian penalty for learned/feature warp.
```

## M6-Plus training schedule

Do not train all losses from scratch at once.

```text
Stage 0: Precompute and audit
  - nnU-Net anchor probabilities/logits/components/uncertainty
  - complete-case registration/alignment artifacts
  - train/OOF prototype bank
  - availability and normalization audit

Stage 1: One-batch and tiny-overfit sanity
  - verify all modules run
  - verify non-empty loss components
  - verify no-T2 edema safety
  - verify closed-gate identity

Stage 2: Proposal warmup
  - train anatomy decoder, retrieval bank, scar/edema proposal heads
  - freeze or strongly regularize final residual decode
  - target: proposal recall and safe-negative discrimination

Stage 3: Refiner training
  - train scar and edema soft-ROI refiners on proposal-generated crops
  - include boundary/HD and hard-negative losses
  - target: component burden, remote FP, HD95

Stage 4: Arbitration / residual calibration
  - calibrate gates and bounded residual maps
  - protect anchor-correct regions
  - same-split help/harm selection

Stage 5: Expansion gate
  - only after fold0 hard-gate pass: expand to more folds or validation package
```

Minimum effective pilot for any claim beyond smoke:

```text
min_optimizer_steps: 6000 for a training-based route claim
min_train_loop_seconds: 1800
min_eval_cases: 12
require_same_split_baseline: true
require_prediction_sanity: true
require_loss_decrease: true
require_one_batch_overfit: true
require_cache_isolation: true
```

## M6-Plus required files

Use or extend the current M6 result directory:

```text
results/20260705_srr_v3_m6_myops_diagram_faithful_repair/
```

Required files:

```text
result.md
srr_v3_fidelity_contract.md
architecture_component_trace.csv
m4_failure_mapping.csv
input_availability_audit.csv
registration_alignment_runtime_sanity.csv
alignment_help_harm.csv
nnunet_anchor_context_index.csv
prototype_bank_index.json
segmentation_context_interface_sanity.csv
retrieval_bank_runtime_sanity.csv
anatomy_proposal_sanity.csv
proposal_metrics_by_class.csv
branch_arbitration_sanity.csv
decode_gate_consistency_sanity.csv
loss_refiner_component_sanity.csv
refiner_roi_component_sanity.csv
hard_negative_memory_sanity.csv
no_t2_safety_sanity.csv
same_split_help_harm.csv
hard_subgroup_metrics.csv
strict_validator_report.md
unit_test_report.md
completion_check.md
review_request.md
MANIFEST.md
```

## M6-Plus hard gates

`completion_check.md` may say `M6_READY_FOR_REVIEW` only if all of the following are true:

1. Diagram fidelity contract maps every v2/v2.5/v3 module to code or blocked evidence.
2. Runtime evidence proves retrieval, proposal, refiner, anchor interface, and losses are non-empty.
3. nnU-Net anchor is used as evidence/context and protected fallback, not hidden final answer.
4. Closed-gate / fallback identity is exact.
5. Scar and edema proposal/refiner are separate.
6. Refiner is soft-ROI and not full-volume residual.
7. No-T2 edema safety is preserved end-to-end.
8. Registration/alignment pilot exists on complete tri-modal cases, or a strict resource-blocked state exists.
9. Same-split help/harm reports Dice, HD95, component, remote FP, T2-present edema, CenterC, and no-T2 safety.
10. Strict validator fails closed on claim-only, hidden-decode-delta, SRR-zero-contribution, no-registration-evidence, no-T2 unsafe, full-volume-refiner, and missing-prototype-source packets.

---

# Part II. M7-Plus: First-place Cine architecture

## Scientific target

M7-Plus targets `myocardium_cinemyops` first. It may report class-3/scar sanity, but the primary objective is hosted Cine myocardium segmentation and temporal consistency.

The method should be called:

```text
Cine-RegisterRetrieveAggregate: registration-aware anatomy-first temporal retrieval for CineMyoPS
```

The first-place-level hypothesis is:

The current Cine path is weak because single-frame or frame0-only wrappers discard cardiac motion. A leaderboard-winning Cine method must use ED/reference anatomy, register or warp informative frames into reference space, aggregate anatomy/motion/texture evidence, and explicitly control registration risk. Descriptor-only temporal retrieval is a control, not the main method.

## M7-Plus non-negotiable design principles

1. Cine is a 4D problem. At least three frames per case are required for runtime evidence; preferred is 4-6 frames per case.
2. ED/reference-frame warping is required for the main path. Registration-free descriptor dictionary is only a control.
3. Registration quality must be measured and used in aggregation weights.
4. Frame0/ED control, descriptor-no-warp control, and warp-assisted temporal aggregation must all be compared on the same cases.
5. Untrained VoxelMorph cannot be counted as a successful registration method.
6. One-case SyN smoke cannot be counted as method evidence.
7. The method must report local `class_1` myocardium proxy and any available class-3 sanity separately.

## M7-Plus algorithm candidates

M7-Plus should implement the fastest robust option first, but the design must list and evaluate candidates.

### Candidate A. Fast classical warp-assisted temporal aggregation

This is the default required path.

```text
Reference: ED/frame0 or detected ED-like frame
Moving frames: high-motion frame, ES/late frame, low-quality control frame, optional extra frames
Registration: SimpleITK Demons or optical-flow/DVF proxy to reference
Features: image, anatomy probability, motion magnitude, Jacobian, registration confidence
Aggregation: quality-weighted feature/probability aggregation in reference space
```

Advantages: feasible in hours, no large training, directly addresses motion.

Required status: must run unless resource blocked.

### Candidate B. SyN high-quality subset reference

```text
Registration: ANTs SyN or SyN-like classical registration
Scope: smaller subset if slow, but more than one case if possible
Purpose: quality upper bound / sanity reference
```

Advantages: high-quality classical reference.

Hard rule: one-case SyN is only smoke, not M7 success.

### Candidate C. Learned registration / VoxelMorph-style pilot

```text
Architecture: small 2D/3D U-Net registration network or VoxelMorph adapter
Training: self-supervised NCC/MSE + smoothness + anatomy consistency if labels/teacher anatomy available
Scope: optional if time permits; at least a meaningful trained pilot, not untrained near-identity
```

Advantages: closer to CineMyoPS motion-estimation story.

Hard rule: untrained VoxelMorph is a negative control, not evidence.

### Candidate D. Anatomy-teacher temporal student

```text
Teacher: existing nnU-Net/CineMA/CorSeg anatomy prior if compliant and available
Student: small temporal model that consumes reference + warped key-frame features
Loss: anatomy DiceCE + temporal consistency + topology/largest-component loss
```

Advantages: likely strongest for `myocardium_cinemyops` if external/pretrained use is allowed and already integrated.

### Candidate E. Full CineMyoPS-like multitask model

```text
Motion estimation module
Anatomy segmentation module
MyoPS/pathology module
Temporal aggregation over 4/6 cardiac cycle
```

This is the conceptual upper bound but probably too heavy for immediate execution unless the code path already exists. It should inform design, not block M7-Plus.

## M7-Plus reference-frame and frame-selection design

Required frame selection:

```text
reference_frame: ED/frame0 or best available reference
high_motion_frame: frame with high motion saliency / large difference from reference
late_or_ES_like_frame: late systolic / ES-like or deterministic late-frame control
low_quality_control_frame: optional, to test router rejection
```

Preferred 4-6 frame selection:

```text
ED/reference
25% cycle
50% cycle / ES-like
75% cycle
highest motion saliency
highest anatomy confidence non-reference frame
```

Frame router input features:

```text
frame_index_normalized
image_quality_score
anatomy_confidence
motion_magnitude_to_reference
registration_quality
NCC/MI after warp
Jacobian/foldover quality
temporal position embedding
```

Frame router output:

```text
frame_weight
selected_or_rejected
selection_reason
registration_risk_level
```

## M7-Plus registration / warping module

Required ED-reference warping outputs:

```text
warp_field(frame_i -> reference)
warped_image_i
warped_anatomy_probability_i
motion_magnitude_i
jacobian_map_i
registration_quality_i
```

Registration methods and risk labels:

```text
frame0_control: no registration needed
classical_syn: high-quality classical, slow, subset allowed
classical_demons: fast classical, main required path if SyN too slow
optical_flow_proxy: proxy, useful but not validated registration
trained_voxelmorph: valid only if trained and QA-passed
untrained_voxelmorph: negative control only
registration_free_descriptor: control only, not first-place main path
```

Required file:

```text
reference_frame_registration_sanity.csv
```

Required fields:

```text
case_id
frame_id
reference_frame_id
method
risk_label
status
ncc_before
ncc_after
mi_before
mi_after
anatomy_overlap_proxy_before
anatomy_overlap_proxy_after
jacobian_min
jacobian_p01
jacobian_p99
foldover_voxel_count
motion_magnitude_mean
motion_magnitude_p95
runtime_seconds
used_in_temporal_aggregation
failure_reason
```

Hard gate:

If no non-reference frame is warped into reference space and used in temporal aggregation, M7-Plus cannot be `READY_FOR_REVIEW`. It must be `M7_NEEDS_REVISION` or `M7_RESOURCE_BLOCKED`.

## M7-Plus temporal representation dictionary

The temporal dictionary should not be a list of frame descriptors only. It must contain reference-space evidence.

Dictionary slots:

```text
D_ref: reference anatomy/texture slots
D_motion: motion magnitude / strain-like slots
D_warped_texture: warped non-reference image feature slots
D_warped_anatomy: warped anatomy probability slots
D_quality: frame quality / registration confidence slots
D_phase: temporal phase slots
```

Minimum architecture:

```text
Per-frame encoder: 2D/2.5D or 3D encoder, channels 32/64/128
Feature warp: warp frame features or probabilities into reference space
Temporal aggregator: gated attention / ConvGRU / quality-weighted temporal fusion
Output decoder: myocardium/LV/RV or task-specific compact labels
```

Fast implementation option:

```text
Use existing per-frame anatomy predictions/probabilities.
Warp probabilities and image-derived features into reference space.
Aggregate with quality weights.
Train or calibrate a small 2D/3D decoder/refiner on aggregated channels.
```

Stronger implementation option:

```text
Encode selected frames separately.
Warp encoder features to reference space.
Use cross-frame attention with registration-quality gating.
Decode reference-space myocardium.
```

## M7-Plus temporal aggregation candidates

Run at least these same-case comparisons:

```text
A0: frame0_control
A1: descriptor_no_warp_temporal_control
A2: demons_or_optical_flow_warp_assisted_aggregation
A3: registration_quality_gated_temporal_dictionary
A4: syn_subset_quality_reference, if available
A5: learned_registration_candidate, if trained and QA-passed
```

`A2` is the minimum main path. `A1` cannot be the main route. `A4`/`A5` are optional but highly desirable.

Required metrics file:

```text
temporal_aggregation_metrics.csv
```

Required fields:

```text
case_id
candidate_id
num_frames_used
registration_method
aggregation_method
class_1_dice
class_1_hd95
class_1_component_count
class_1_lcc_fraction
class_3_dice_if_available
class_3_hd95_if_available
frame0_delta_dice
frame0_delta_hd95
registration_quality_mean
registration_quality_min
failure_reason
```

Required help/harm file:

```text
frame0_vs_temporal_help_harm.csv
```

Required summary:

```text
help_cases
harm_cases
neutral_cases
mean_delta_dice
median_delta_hd95
worst_harm_case
failure_mode
```

## M7-Plus losses

If M7 includes training or fine-tuning, use:

```text
L_total_cine = L_ana_ref
             + L_temporal_consistency
             + L_motion_smooth
             + L_registration_quality_weighted_seg
             + L_topology_lcc
             + L_boundary_hd
             + L_quality_router
```

Definitions:

```text
L_ana_ref:
  DiceCE for reference-frame myocardium/LV/RV labels.

L_temporal_consistency:
  prediction from non-reference frame, warped to reference, should agree with reference anatomy.

L_motion_smooth:
  smoothness/Jacobian regularization for learned registration.

L_registration_quality_weighted_seg:
  downweight warped frames with poor registration quality.

L_topology_lcc:
  encourage one coherent myocardium component / large LCC fraction.

L_boundary_hd:
  boundary/HD loss for myocardium contours.

L_quality_router:
  selected high-quality frames should improve or at least not harm frame0 control.
```

## M7-Plus required files

Use or extend:

```text
results/20260705_srr_v3_m7_cine_temporal_retrieval_runtime/
```

Required files:

```text
result.md
cine_temporal_runtime_contract.md
code_diff_summary.md
reference_frame_registration_sanity.csv
temporal_dictionary_index.json
temporal_dictionary_case_summary.csv
frame_router_weights.csv
temporal_aggregation_candidates.csv
temporal_aggregation_metrics.csv
frame0_vs_temporal_help_harm.csv
registration_risk_matrix.csv
cine_prediction_sanity.csv
source_evidence_index.csv
unit_test_report.md
strict_validator_report.md
completion_check.md
review_request.md
MANIFEST.md
```

## M7-Plus hard gates

`completion_check.md` may say `M7_READY_FOR_REVIEW` only if all are true:

1. At least 24 cases have runtime dictionary/eval evidence, unless resource-blocked.
2. Each valid case uses at least 3 frames, unless case-specific reason exists.
3. At least one non-reference frame is warped to reference space and used in temporal aggregation.
4. Frame0 control, descriptor-no-warp control, and warp-assisted temporal aggregation are compared on the same cases.
5. Registration risk labels are present for every non-reference feature source.
6. Temporal aggregation metrics include local class-1 myocardium proxy; class-3 sanity is reported if available.
7. The method does not claim full registration or hosted improvement unless evidence supports it.
8. Strict validator fails closed on claim-only, one-case-smoke, no-runtime-dictionary, no-warped-frame-used, no-frame0-comparison, untrained-VoxelMorph-as-success, missing-registration-risk, and committed-heavy-artifact packets.

---

# Part III. Reviewer standard for both M6-Plus and M7-Plus

A reviewer must judge not only file existence but scientific sufficiency.

## Reject as `NEEDS_REVISION` if any of the following occurs

1. The executor converts registration into optional prose without runtime artifacts.
2. SRR retrieval/proposal/refiner are present only as natural-language claims.
3. nnU-Net is either ignored or used as hidden final answer.
4. A one-case smoke is used to claim method readiness.
5. A descriptor-only temporal dictionary is presented as a registration-aware Cine method.
6. No-T2 myocardium is used as edema negative.
7. Full-volume residual refinement is used instead of soft-ROI bounded correction.
8. Metrics omit HD95/component/remote-FP and report only Dice.
9. The packet lacks same-case controls: anchor vs SRR for M6; frame0 vs descriptor vs warp-assisted temporal for M7.
10. The validator fails to fail known-bad packets.

## Accept only as diagnostic if

1. Runtime modules exist, but training scope is smoke-scale.
2. Registration artifacts exist but do not yet improve metrics.
3. Temporal warping runs but aggregation is neutral or harmful.
4. Proposal/refiner evidence is complete but same-split metrics remain below anchor.

Use `AUDITED_DIAGNOSTIC_GO` only when the packet is scientifically useful and complete as a diagnostic, not when it is route-promoted.

## Accept as `AUDITED_GO` only if

For M6-Plus:

```text
- architecture fidelity complete
- runtime registration/alignment evidence present
- retrieval/proposal/refiner losses and outputs non-empty
- exact anchor identity fallback works
- same-split hard metrics show no unacceptable harm
- route-promotion claims are not made unless the promotion gate is met
```

For M7-Plus:

```text
- runtime temporal dictionary exists
- non-reference warped frames are used in aggregation
- frame0/control vs temporal comparisons exist
- registration risk is explicit
- temporal aggregation is not just descriptor-only
- class-1 myocardium proxy is reported with HD/component sanity
```

---

# Part IV. Minimal executor prompt to paste into Codex

```text
You are executing the revised high-standard M6/M7 architecture task. Read `prompts/shared/M6_M7_FIRST_PLACE_ARCHITECTURE_PROMPTS.md` first and treat it as binding. Do not invent a simpler architecture during execution. Do not replace required registration/alignment artifacts with prose. Do not replace SRR proposal/refiner with a generic dense head. Do not let nnU-Net become the hidden final answer. Do not claim readiness without the required CSV/JSON/MD evidence and strict validator.

For M6-Plus, implement and audit SRR-ProposeAlignRefine: nnU-Net anchor/context, LGE-reference alignment pilot, semantic dictionary, anatomy-guided scar/edema proposal, pathology-specific soft-ROI refiners, hard-negative/prototype memory, bounded residual arbitration, no-T2 edema safety, and same-split help/harm.

For M7-Plus, implement and audit Cine-RegisterRetrieveAggregate: ED/reference selection, non-reference frame registration/warping, registration-risk matrix, temporal dictionary, frame router, warp-assisted temporal aggregation, frame0/descriptor/warp-assisted same-case comparison, class-1 myocardium metrics, and strict validator.

If any required part cannot be completed, stop with the correct blocked state and exact evidence. Do not mark ready and do not start the next milestone.
```
