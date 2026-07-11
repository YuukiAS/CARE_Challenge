---
task_key: 20260711_srr_v3_m10_complete_mechanism_repair
task_kind: scientific_milestone
task_type: controller
controller_mode: true
milestone_number: 10
milestone_id: M10
status: READY_FOR_CODEX_MERGE
risk_level: high
route_change: true
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 3
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: independent_thread
reviewer: separate_readonly
review_required: true
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: independent M10 runtime reviewer and later GPT planner only; M10 cannot promote itself
experiment_adequacy_gate: all ten formal runs must meet per-run and aggregate steps, train-loop seconds, validation, full-case, stability, provenance, and cache-isolation minima
route_negative_gate: no scientific stop from undertrained, failed-registration, stale, smoke, proxy, or monitor evidence
scientific_completion_gate: D0-D3, hard-negative refresh, no-context control, alignment control, mature registration, learned Cine, component attribution, strict validation, mapper final, and committed controller packet
diagnostic_publication_gate: reviewed lightweight md/csv/json packet only
diagnostic_publication_scope: ["md", "csv", "json"]
blocked_after_diagnostic_publication: ["validation_packaging", "upload", "hosted_claim", "fold_expansion", "route_promotion", "scientific_stop", "M11"]
planning_review_required: true
planning_reviewer: separate_gpt_thread
planning_review_path: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_planning_review.md
planning_review_token: "PLANNING_CRITIC_READY_FOR_CODEX_MERGE"
planning_reviewed_commit: ""
---

# M10 — SRR-v3 complete mechanism repair, design attribution, and registration-gated Cine

This is the reconciled planner/critic staging contract. Its planner baseline is
`828735482396d6d727d2294e88c89868e3118ad3` on `agent/m10-planner-draft`.
The previous critic review against `e26895b99dc142ff64ea6e6f291600c6b67af98c` is superseded.
This file authorizes planning integration only after a matching critic review; it does not execute M10.

## Execution Contract

```yaml
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 3
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: independent_thread
reviewer: separate_readonly
```

The three executors are serial waves, not parallel workers. Wave 1 owns shared architecture and fidelity;
wave 2 owns formal MyoPS jobs/evidence after wave 1 is merged and frozen; wave 3 owns CineMA adaptation,
learned registration, and learned temporal aggregation after MyoPS terminal aggregation. The controller owns
continuity and all merges. This resolves the prior one-versus-three executor conflict in favor of three isolated,
sequential responsibilities while retaining `max_parallel: 1`.

## Grounding, lineage, and prerequisites

Required reviewed predecessor:

```text
wiki/current_state.yaml
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md:
M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY
results/20260711_agent_flow_generic_protocol_repair/review.md:
AGENT_FLOW_GENERIC_PROTOCOL_REPAIR_AUDITED_GO
```

Required planning lineage:

```text
planner_branch: agent/m10-planner-draft
planner_draft_commit: 828735482396d6d727d2294e88c89868e3118ad3
critic_branch: agent/m10-planning-critic-repair
common_default_baseline: 925a00169649a523947e475204e68228cb8816f6
```

Controller bootstrap must verify that the planner draft commit is an ancestor of current HEAD and that the
planning-review hash/token matches this staging contract. Any mismatch yields `M10_BLOCKED_PREREQUISITE`.

The planner, critic, controller, mapper, finalizer, validator, and reviewer must read the active protocols and schemas,
root `wiki/README.md`, `wiki/MODEL.md`, `wiki/COMPONENTS.csv`, `wiki/architecture.yaml`,
`wiki/current_state.yaml`, `wiki/history/README.md`, `wiki/history/COMPARISON.md`, and every predecessor
component file matching `wiki/history/M09/components/*.md`. M08/M09 history remains immutable.

Diagram bootstrap is fixed:

```yaml
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_CHATGPT_PROJECT_MATERIALS_AND_CURRENT_CONVERSATION
recovered_route_objective: availability-aware selective spatial retrieval, semantic shared/private/interaction dictionary, anatomy-guided pathology proposal, pathology-specific soft-ROI refinement, safe negative-space learning, and a registration-gated learned Cine temporal path
```

`nnU-Net` may be a same-split baseline, detached context/teacher, uncertainty source, or explicit safety comparator.
It is never the formal final-logit base and cannot silently replace SRR output.

## Fixed MyoPS tensor and architecture contract

Canonical modality order is `[LGE, T2, C0]`.

```text
x_m: B×1×H×W×D
a: B×3 binary availability
encoder channels: [32,64,128,256]
F_m^l: B×C_l×H_l×W_l×D_l
```

Missing modalities do not enter a stem as semantic zero images. Storage placeholders are permitted only when every
biased/normalized block is followed by the deterministic availability mask. Formal candidates use four scales;
`tiny_3scale` is smoke-only. D0-D3 parameter counts must be within ±5%, and FLOPs/patch, peak memory, and
trainable counts must be published.

### Exact 16-slot dictionary per scale

Each scale contains exactly:

```text
4 shared slots
2 LGE-private slots
2 T2-private slots
2 C0-private slots
2 LGE×T2 interaction slots
2 LGE×C0 interaction slots
2 T2×C0 interaction slots
```

Available features are projected to common channels. Shared input is projected from masked mean and variance;
private input is its modality feature; interaction input is
`Conv1x1([F_a,F_b,|F_a-F_b|,F_a⊙F_b])`. Every expert is an independent residual block:

```text
GN → SiLU → depthwise 3×3×3 Conv → pointwise 1×1×1 Conv
→ GN → SiLU → depthwise 3×3×3 Conv → pointwise 1×1×1 Conv + residual
```

Validity is deterministic:

```text
v_shared = 1[sum(a)>0]
v_private(m)=a_m
v_interaction(m,n)=a_m a_n
```

Invalid forward value, gate weight, gradient, and memory update must be zero. The strict threshold is
`max_invalid_weight <= 1e-8`; the evidence table also reports mean and per-case maxima.

### Four matched formal designs

All designs share encoder, anatomy, proposal/refiner capacity, split, augmentation, seed schedule, decode, and full-case
evaluation. They are true retrains, not inference toggles.

```text
D0_STATIC_MATCHED_PROPREF
  Sixteen parameter-matched residual experts with validity-masked fixed pathology mixtures.
  No content router, Pattern-SIP, prototype memory, or similarity term. Proposal/refiner remain.

D1_SPATIAL_BR2_PROPREF
  One-pass spatial content router over the 16-slot bank. No Pattern-SIP or prototype memory.

D2_HIERARCHICAL_BR2_PSIP_PROPREF
  Two-pass coarse-to-fine spatial router, proposal feedback, and real Pattern-SIP. No prototype memory.

D3_HIERARCHICAL_BR2_MEMORY_PROPREF
  D2 plus cross-fitted EMA+learnable-residual memory, safe hard negatives, pathology-specific proposal/refiner,
  and pair-valid feature-alignment hooks. This is the full candidate.
```

D0 is the parameter-matched no-retrieval control retained from the prior critic; D1-D3 preserve the latest Planner's
scientific design ladder.

### Two-pass lesion-conditioned spatial retrieval

Let `B_l` be the availability-masked base fusion and `E_lk` the 16 expert outputs. Anatomy retrieval uses feature and
availability evidence only and emits `Q_struct`, `P_union`, `P_LV`, and `P_RV`. Initial pathology evidence and
prototype maps are computed from `B_0`, avoiding circular dependence.

For pathology `t∈{scar,edema}`:

```text
q_tl^(0)(x) = phi_tl^(0)([B_l,e(a),P_union,P_LV,P_RV,d_remote,E_t^(0),S_t^+,S_t^-,U_t])
alpha_tl^(0) = entmax_1.5((A_tl^(0)+log(v_l+1e-12))/tau_l, dim=slot)
R_tl^(0) = sum_k alpha_tlk^(0) E_lk
p_t^(0) = sigmoid(H_t^(0)(R_t^(0)))

q_tl^(1)(x) = phi_tl^(1)([B_l,R_tl^(0),e(a),p_t^(0),P_union,P_LV,P_RV,d_remote,S_t^+,S_t^-,U_t])
alpha_tl^(1) = entmax_1.5((A_tl^(1)+log(v_l+1e-12))/tau_l, dim=slot)
R_tl = sum_k alpha_tlk^(1) E_lk
```

`e(a)` is 16-dimensional. Center ID is forbidden as a router input; center and train-only style clusters are audit groups.
Temperature is `1.5→0.7` by step 30000. The first 20% uses masked soft routing, 20%-70% uses top-4 straight-through,
and the final 30% uses top-2 straight-through. Inference uses valid top-2 and renormalization. No stop-gradient is allowed
from retrieved representation to final pathology output.

### Pattern-SIP and load control

For availability-pattern × train-style × hard-subgroup group `g` and ROI weight `r_i(x)`:

```text
u_tlkg = sum_{i in g,x} r_i(x) alpha_tlk(i,x) / (sum_{i in g,x} r_i(x)+eps)
gamma_tlk = (sum_{g in G_k} u_tlkg)^2 / (sum_{g in G_k} u_tlkg^2+eps)
L_PSIP = mean_shared relu(gamma_min-gamma)^2
         + mean_{t,l,g} KL(u_bar_tlg || pi_tlg)
         + 0.01 mean_x H(alpha_tl(x))
         + L_collapse
```

`G_k` contains only groups where slot `k` is legal. `pi` allocates 0.50 mass to shared slots, 0.35 to the pathology-key
private family (LGE for scar, T2 for edema), and 0.15 to valid interactions/auxiliary private slots. Pattern-SIP has an
independent implementation, log key, weight, computation graph, and gradient test; aliasing `dict_loss` is a blocker.

### Cross-fitted prototype memory and negative space

Each pathology has exactly 8 positive and 12 negative slots. Positive slots are split evenly between lesion core and boundary.
Negative slots are category-stratified across normal myocardium, blood/outside anatomy, acquisition/texture artifact, and
current-model hard false positives. Edema categories use only T2-present, edema-labeled cases.

Training cases are assigned to four deterministic memory shards by case hash. A case's proposal may use only prototypes
fitted from the other three shards. For each slot:

```text
mu <- L2Norm(0.99 mu + 0.01 mean(stopgrad(f)))
p = L2Norm(mu + 0.1 tanh(delta))
S_t^+(x)=0.07 logsumexp_j(cos(f_t(x),p_tj^+)/0.07)
S_t^-(x)=0.07 logsumexp_j(cos(f_t(x),p_tj^-)/0.07)
```

The FIFO capacity is 65536 embeddings per pathology. Ledgers contain source case, shard, count, age, assignment, category,
checkpoint, and safety reason. No-T2 myocardium is neither edema positive nor edema negative and has accepted count,
gradient, and update exactly zero.

Hard-negative replay uses current D3 out-of-fold full-case predictions, caps replay at 25% of sampled voxels and four components
per case, and records component provenance. It is followed by a bounded formal refresh and before/after evaluation.

Margin objectives are fixed:

```text
L_pos(t)=mean_{positive} relu(0.20-S_t^+ + S_t^-)
L_neg(t)=mean_{safe_negative} relu(0.20+S_t^+ - S_t^-)
```

### Anatomy, proposal, uncertainty, soft ROI, and final output

The anatomy head predicts `[background,myocardium,LV,RV]` plus `P_union`; scar and edema labels fold into myocardium for
anatomy supervision. The soft anatomy support is:

```text
G_ana = clamp(P_union + 0.25 MaxPool3D(P_union,k=9),0,1) (1-Q_LV)(1-Q_RV)
d_remote = clamp(EDT(1[stopgrad(G_ana)>0.30])/20mm,0,1)
```

Initial learned evidence `E_t` and prototype disagreement define:

```text
P_evidence,t=sigmoid(E_t)
P_proto,t=sigmoid(S_t^+-S_t^-)
U_t=0.5 H_binary(P_evidence,t)/log(2)+0.5|P_evidence,t-P_proto,t|
```

Final proposal logits are fixed; detached teacher/context cannot be tuned above the stated coefficients:

```text
z_prop,t = E_t + S_t^+ - lambda_neg,t S_t^-
           + lambda_ana,t logit(clamp(G_ana,1e-4,1-1e-4))
           - lambda_remote,t d_remote - lambda_unc,t U_t
           + lambda_teacher,t C_t_detached
```

| pathology | lambda_neg | lambda_ana | lambda_remote | lambda_unc | lambda_teacher |
|---|---:|---:|---:|---:|---:|
| scar | 1.25 | 0.75 | 0.60 | 0.35 | 0.10 |
| edema | 1.00 | 0.60 | 0.40 | 0.25 | 0.05 |

Soft ROI and refinement are:

```text
G_prop,t=sigmoid(z_prop,t)
rho_t=clamp(G_ana(0.20+0.80 G_prop,t)(1-U_t)+0.05 MaxPool3D(G_prop,t,k=9),0,1)
Delta z_t = delta_t tanh(H_t([R_t^0,E_t,S_t^+,S_t^-,G_ana,d_remote,U_t,G_prop,t]))
z_final,t = z_prop,t + rho_t Delta z_t
```

Scar refiner has three residual blocks, dilation `[1,1,2]`, 64 channels, `delta_scar=2.0`. Edema refiner has four residual
blocks, dilation `[1,2,3,1]`, 64 channels, `delta_edema=1.5`. Crop boxes are compute boundaries only; the gate is soft.
An empty proposal may use anatomy-union ROI and must record `ANATOMY_FALLBACK`; image-center seed is forbidden.

The formal six-class probability relation is:

```text
P_scar=sigmoid(z_final,scar)
P_edema=a_T2 q_edema (1-P_scar) sigmoid(z_final,edema)
r=1-P_scar-P_edema
[P_bg,P_myo,P_LV,P_RV]=r Q_struct
P_final=[P_bg,P_myo,P_LV,P_RV,P_edema,P_scar]
yhat=argmax(P_final)
```

`q_edema=1[T2 present and edema label semantics available]`. No-T2 export has `P_edema=0` exactly. The formal output
records `final_output_base: SRR_PROPOSAL_REFINEMENT`; no anchor identity, silent fallback, or label replacement is allowed.

### Pair-valid MyoPS feature alignment

D3 implements LGE-reference feature alignment for LGE-T2 and LGE-C0 at the two coarsest decoder scales. It predicts a
stationary velocity, uses five scaling-and-squaring steps, and optimizes local NCC/feature similarity, anatomy consistency,
smoothness, and Jacobian folding penalty. It only runs when both modalities exist and feeds interaction experts. Formal evidence
includes aligned and unaligned controls, pair masks, overlap, Jacobian/folding, displacement, and final-output effect. It is a
required trained control but may remain disabled in the selected checkpoint when it fails the predeclared help/harm gate.

## Loss and optimization contract

```text
L_total = w_ana L_anatomy + w_full L_final6
        + w_prop,s L_prop,scar + q_edema w_prop,e L_prop,edema
        + w_ref,s L_ref,scar + q_edema w_ref,e L_ref,edema
        + w_pos L_pos + w_neg L_neg + w_mem L_memory
        + w_PSIP L_PSIP + w_invalid L_invalid
        + w_roi L_ROI + w_boundary L_boundary + w_HD L_HD
        + w_align L_align + w_teacher L_detached_teacher + w_relation L_scar_to_edema
```

Anatomy uses DiceCE. Final and proposal terms use DiceCE; scar adds precision-aware Focal-Tversky and boundary/HD terms;
edema adds recall-aware Focal-Tversky and every edema term is `q_edema` masked. The soft scar-to-edema relation is enabled
only for T2-present, low-uncertainty edema and never imposes hard containment.

Every component is classified as `real_optimized_loss`, `diagnostic_metric_only`, or `disabled_with_reason`. Alias and
placeholder-zero losses are forbidden. Changing any active weight from 0 to 10 must change total loss and intended parameter
gradient. Each event records raw/weighted value, configured/actual weight, EMA, gradient norm, parameter group, masked
denominator, and dominance fraction.

Fixed optimizer:

```text
AdamW; betas=(0.9,0.999); weight_decay=1e-4
MyoPS base lr=3e-4; refresh/alignment lr=1e-4
Cine adapter/temporal lr=2e-4; registration lr=1e-4
5% linear warmup; cosine floor=1e-2 of peak; AMP; grad clip=5.0
patch batch=2; gradient accumulation=2
```

Four MyoPS phases are A anatomy/evidence warmup, B dictionary/proposal/PSIP/memory, C refiner/full-output/boundary-HD,
and D current-model hard-negative refresh plus low-LR calibration. Modality dropout applies only to originally complete cases:
C0 0.20, T2 0.20, never LGE; T2 dropout sets `q_edema=0` rather than creating a negative.

## Minimum effective training and checkpoint selection

```yaml
minimum_effective_training:
  min_optimizer_steps: 220000
  min_train_loop_seconds: 72000
  min_eval_cases: 44
  min_validation_events: 120
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  require_loss_stability: true
  require_same_split_baseline: true
  require_cache_isolation: true
  require_challenge_metric_checkpoint_selection: true
  require_hard_subgroup_metrics: true
  require_terminal_slurm_accounting: true
  require_post_job_aggregation: true
```

| formal run | min steps | min train-loop seconds | validation events | full-case events | eval cases |
|---|---:|---:|---:|---:|---:|
| D0 static matched | 20000 | 7200 | 12 | 4 | 44 |
| D1 spatial BR2 | 25000 | 9000 | 15 | 5 | 44 |
| D2 hierarchical BR2+PSIP | 25000 | 9000 | 15 | 5 | 44 |
| D3 full memory PropRef | 45000 | 14400 | 22 | 8 | 44 |
| D3 hard-negative refresh | 20000 | 5400 | 10 | 4 | 44 |
| D3 no-nnU-Net-context retrain | 20000 | 5400 | 10 | 4 | 44 |
| MyoPS alignment train/control | 10000 | 3600 | 8 | 3 | 44 |
| CineMA CARE adapter | 10000 | 3600 | 8 | 3 | at least 12 |
| learned Cine registration | 25000 | 7200 | 10 | 4 | at least 12 |
| learned Cine temporal dictionary | 20000 | 7200 | 10 | 4 | at least 12 |

The sum is 220000 steps and 72000 effective train-loop seconds. Every row is blocking. Queue time, sleep, cache generation,
repeated smoke, failed startup, and reset-counter restart do not count. Each job walltime request is <=8 hours. Early stopping is
forbidden before that row's complete steps, seconds, and event minima; any earlier termination is `SCIENTIFIC_UNDERTRAINED`.
Preemption/OOM resumes only from a scheduled checkpoint with matching code/config/split/cache hashes and cumulative counters.

One-batch overfit must reduce loss >=90%, produce nonempty target prediction, and show positive gradient for encoder, router,
experts, memory residual, proposal, and refiner. Formal stability requires first-to-last 10-event median loss decrease >=20%,
last-five-event coefficient of variation <=0.15 or a documented stable plateau, no prediction-volume explosion, and no active
component dominating >70% or falling below 0.5% for three windows without a valid mask reason.

Save every 2500 steps. Every scheduled checkpoint runs 44-case full-case evaluation, including at least 16 T2-present
edema-positive cases, 7 CenterB cases, and 9 CenterC cases. Patch loss never selects the checkpoint. Eligibility requires finite
metrics, valid labels, no-T2 edema max <=1e-6, positive-case nonempty prediction on >=80%, volume ratio `[0.05,20]` on >=95%,
and exact split/cache/decode hashes.

For pathology `t`:

```text
g_t = Dice_t-Dice_anchor,t
      -0.01 clip((HD95_t-HD95_anchor,t)/10mm,-5,5)
      -0.02 clip((remoteFP_t-remoteFP_anchor,t)/(remoteFP_anchor,t+1),-2,2)
S_checkpoint=min(g_scar,g_edema)+0.25(g_scar+g_edema)
```

Select maximum eligible score, tie-breaking by lower worst-case HD95 then earlier step. Publish every scheduled checkpoint.
Threshold and component calibration use train/inner-validation only and are frozen before the 44-case evaluation.

Hard subgroups include scar-positive, T2-present edema-positive, modality patterns, every center, small/large lesion quartiles,
worst-anchor-HD95 quintile, anchor remote-FP cases, and empty-GT cases reported separately. Scar and edema gates remain
pathology-specific; foreground mean cannot hide harm.

## Controls and causal classification

Same-split nnU-Net predictions require matching case IDs, split, preprocessing, label map, decode, and metric hashes. D0-D3,
no-context retrain, pre/post refresh, and alignment train/control are the only matched L4 comparisons. The selected D3 checkpoint
also runs same-case interventions:

```text
static_mixture
dictionary_uniform_valid
top_pathology_slots_zeroed
spatial_router_to_global
PSIP_stateless
prototype_memory_off
anatomy_prior_flat
proposal_only
scar_refiner_off
edema_refiner_off
both_refiners_off
uncertainty_flat
nnunet_context_off
alignment_off
swapped_positive_negative_known_bad
```

For each component/pathology publish call count, gradient norm, activation variance, proposal/refiner/final-logit delta, changed
voxels/components, Dice, HD95, and remote-FP delta. Classification is exactly one of:

```text
NOT_CALLED
CALLED_NO_GRADIENT
GRADIENT_NO_OUTPUT_EFFECT
OUTPUT_EFFECT_NO_BENEFIT
OUTPUT_EFFECT_WITH_BENEFIT
UNDERTRAINED
PIPELINE_BUG
MECHANISM_NO_SIGNAL_AFTER_ADEQUATE_MATCHED_TEST
```

The last state requires adequate formal training, a matched retrain, true output intervention, and a clean pipeline.

## Registration-gated Cine lane

Cine is a blocking secondary lane and cannot rescue or reinterpret MyoPS. Wave 3 first verifies the license, model identifier,
commit, SHA256, preprocessing, label map, orientation, spacing, and time axis of the approved CineMA asset. CineMA supplies
per-frame anatomy features/logits and uncertainty; the CARE adapter trains on CARE data, adapts the final two blocks or an
explicit LoRA/adapter, and is compared with a random-initialization capacity-matched adapter.

### Learned diffeomorphic registration

Input is `I: B×T×1×H×W×D`; ED is reference, ES is minimum predicted LV volume. Select
`max(8,ceil(4T/6))` frames, including ED, ES, uniformly spaced and motion-salient frames. A 3D U-Net with channels
`[16,32,64,128]` predicts symmetric stationary velocities. Seven scaling-and-squaring steps produce physical-space warps.

```text
L_reg = 1.0[1-LNCC_9^3(I0,W(It,phi_0<-t))]
      + 1.0 DiceLoss(Q0,W(Qt,phi_0<-t))
      + 0.05 ||grad v_t||^2
      + 0.10 mean(relu(-det J(phi))^2)
      + 0.10 ||phi_0<-t o phi_t<-0 - Id||_1
```

ANTs SyN is the paired classical control. Demons, optical flow, untrained checkpoints, frame0 copying, and descriptor-only
correspondence are forbidden formal substitutes. Formal held-out QC covers >=12 cases and >=60 non-reference pairs and requires:

```text
median warped-anatomy Dice gain >=0.03
>=90% cases non-worse in mean anatomy Dice
LNCC improves on >=75% pairs
negative-Jacobian fraction <=0.5% every case and <=0.1% median
99th-percentile displacement <=35mm and inside FOV
median inverse-consistency error <=2 voxels
learned registration non-inferior to SyN within 0.01 Dice, with no folding violation,
and either >=25% lower runtime or fewer failures
```

Every case/frame remains in the denominator with overlap, HD95, LNCC, displacement, folding, cycle error, and failure reason.
Persistent gate failure blocks learned temporal training; frame0 fallback cannot satisfy M10.

### Learned temporal dictionary

After registration passes, warp CineMA feature, anatomy, texture, velocity, Jacobian, and residual into ED space. Exactly eight
temporal slots represent ED anatomy anchor, early/late systolic contraction, early/late diastolic relaxation, motion magnitude,
registered texture residual, and registration-uncertainty safety. For frame `t`:

```text
Z_t=[W(F_t,phi),||v_t||,detJ(phi),|I0-W(It,phi)|,W(Q_t,phi),time_embed(t/T)]
beta_tk=entmax_1.5((Router_temp(Z_t)-M_qc)/0.7,dim=(t,k))
T_ED=sum_tk beta_tk E_k(Z_t)
Q_cine=softmax(H_cine([F0,T_ED,Q0]))
```

`M_qc=inf` for an invalid frame. Fewer than four valid non-reference frames is a registration failure, not frame0 completion.

```text
L_cine=DiceCE(Q_cine,Y_ED)
      +0.50 mean_t DiceLoss(Q_cine,W(Q_t,phi))
      +0.20 mean_t ||Q_cine-W(Q_t,phi)||_1 (1-U_reg,t)
      +0.05 L_temporal_load
```

Same-subset controls are frame0 matched backbone, unregistered mean, registered mean, deterministic union, M9 proxy, and
no-temporal-dictionary. Report myocardium Dice/HD95, temporal jitter, topology failure, final-label changed voxels, and per-case
help/harm. No hosted readiness claim is permitted.

## Exact task graph and evidence

All are blocking and exact paths are required:

```text
results/20260711_srr_v3_m10_architecture_fidelity/
results/20260711_srr_v3_m10_mechanism_smoke/
results/20260711_srr_v3_m10_myops_d0_control/
results/20260711_srr_v3_m10_myops_d1_spatial_br2/
results/20260711_srr_v3_m10_myops_d2_hierarchical_psip/
results/20260711_srr_v3_m10_myops_d3_full_propref/
results/20260711_srr_v3_m10_hard_negative_refresh/
results/20260711_srr_v3_m10_no_nnunet_context_control/
results/20260711_srr_v3_m10_alignment_control/
results/20260711_srr_v3_m10_component_causal_audit/
results/20260711_srr_v3_m10_cinema_adapter/
results/20260711_srr_v3_m10_cine_registration/
results/20260711_srr_v3_m10_cine_learned_temporal/
results/20260711_srr_v3_m10_completion_check/
results/20260711_srr_v3_m10_complete_mechanism_repair/
```

Every formal training directory contains `result.md`, `training_budget_ledger.csv`, `loss_stability.csv`,
`validation_events.csv`, `checkpoint_selection.csv`, `case_metrics.csv`, `hard_subgroup_metrics.csv`,
`prediction_sanity.md`, `runtime_manifest.json`, `commands_run.md`, and `MANIFEST.md`, plus mechanism-specific
router/memory/proposal/refiner/registration/Cine evidence. The controller packet contains every file required by
`prompts/schemas/controller_packet.schema.yaml`, all three executor completion receipts, mapper draft/final,
architecture deltas, finalizer state, validator report, completion check, review request, and reviewer prompt.

The strict validator scans Markdown/CSV/JSON and must reject missing frontmatter, stale planning hash, invalid plan lane,
undertraining, patch-loss selection, cache collision, nonzero invalid slots, zero router/expert gradients, SIP alias,
deterministic/no-OOF prototypes, unsafe edema negatives, no final-output effect, hidden anchor identity, fake causal tables,
monitor completion, missing aggregation, folding-heavy/single-case/untrained registration, frame0/union-only Cine, excluded
failure cases, and stale wiki/figures. Known-bad includes swapped prototypes, unsafe no-T2 negative, invalid private slot,
hidden anchor identity, folding-heavy registration, and frame0-only Cine.

## Slurm continuity and finalizers

`htzhulab` is default; fallbacks/routing races follow the repository Slurm skill with isolated roots, logs, and locks. Each wave
submits an `afterany` wave finalizer over all of its job IDs and cannot return a completion token until terminal accounting and
post-job aggregation succeed. The controller retains every job ID across waves and submits the global durable finalizer over all
recorded jobs. `PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, and `AWAITING_SACCT` map to
`NEEDS_MONITOR`; scheduler saturation requires 12 checks at two-hour intervals over 24 hours.

`FINALIZER_A` records terminal state, exit code, elapsed, partition, log, runtime root, checkpoint provenance, output checks,
and aggregation command; it writes `finalizer_state.json` as `READY_FOR_MAPPER_FINAL` or a fail-closed state. After mapper
final, `FINALIZER_B` runs packet, handoff, wiki/history, generated-figure, known-bad, and `git diff --check` validation, then
creates exactly one local lightweight packet commit. No checkpoint, prediction, NIfTI, zip, raw data, large log, or secret is
committed. Controller pre-review fields remain `NOT_REVIEWED`/`AWAITING_REVIEW`, and push is skipped.

## Wiki and history

Mapper draft runs after wave 1 merge. Mapper final runs only after all formal runtime aggregation. It updates root wiki,
`COMPONENTS.csv`, `architecture.yaml`, model-current/model-gap/execution-flow figures, and appends an M09→M10 candidate
comparison. It creates `wiki/history/M10/` with all component files, architecture and figures marked
`candidate_unreviewed`, `review_token: NOT_REVIEWED`. It never rewrites M08/M09. `wiki/current_state.yaml` remains on
M09 until the independent runtime review is committed and a later reconciliation task advances it.

## Controller Prompt

Before executing the scientific task, enforce the hard-gate policy: exact task graph, agent-flow v2 execution contract, strict
validator, completion-check-before-final-audit, minimum effective training, current-bad-packet regression, mapper/wiki/fingerprint
gates, and SRR diagram-bootstrap evidence. If any gate fails, stop with NEEDS_REVISION or NEEDS_EVIDENCE.

Launch exactly the three serial executor waves in the validated plan. Merge only after each completion receipt. Freeze shared
architecture during wave 2; any wiring defect returns to wave 1 rather than being hot-patched. Submit Cine temporal only after
the registration gate passes. Maintain durable continuity and stop after the local final packet and review request. Do not write
`review.md`, push, package/upload validation, claim hosted metrics, promote, stop the route, or start M11.

This is an executor/controller session for one milestone only. Stop after writing completion_check.md and review_request.md,
force-add/commit the lightweight required result files, then stop. Do not push automatically. Do not write review.md and do not
start the next milestone.

## Executor Worker Contract

Wave 1 implements the fixed shared architecture, losses, tests, fidelity and smoke only. Wave 2 uses merged frozen architecture
to run D0→D1→D2→D3→refresh→no-context→alignment formal work and evidence. Wave 3 verifies CineMA provenance,
implements/trains the CARE adapter, learned diffeomorphic registration, registration gate, learned temporal dictionary, and
same-subset controls. Executors remain inside plan write scopes, use isolated worktrees/branches/results/runtime/logs/locks,
write completion receipts, and never merge themselves, self-review, push, or redesign formulas/budgets.

## Mapper Contract

The mapper uses `.agents/skills/care-mapper/SKILL.md`, reads first-party source/config/entrypoints and lightweight evidence,
and does not inspect raw data, checkpoints, NIfTI, large logs, secrets, or upload packages. It does not modify model code or write
`review.md`. Any source/evidence/wiki fingerprint mismatch is stale and blocks `FINALIZER_B`.

## Reviewer Prompt

This is a separate read-only reviewer session. Do not fix code, generate missing artifacts, train, resume jobs, package/upload,
push, or start M11. Inspect the planning hash/lineage, exact task graph, three wave receipts, terminal accounting, all ten formal
budgets, loss/prediction stability, split/cache provenance, D0-D3 matched retrains, dictionary/router/memory gradients and
final-output effects, proposal/refiner metrics, no-T2 safety, pathology subgroups, registration QC, learned Cine, known-bad,
and wiki/history/diagram consistency.

Allowed decisions are:

```text
M10_AUDITED_GO_MECHANISM_SIGNAL
M10_AUDITED_COMPLETE_NO_PROMOTION_SCIENTIFIC_UNRESOLVED
M10_AUDITED_SCIENTIFIC_UNDERTRAINED
M10_AUDITED_NEEDS_EVIDENCE
M10_AUDITED_NEEDS_REVISION
M10_AUDITED_NEEDS_MONITOR
```

`M10_AUDITED_GO_MECHANISM_SIGNAL` permits only later GPT planning. It does not authorize validation packaging/upload,
hosted claims, fold expansion, route promotion, scientific stop, or M11. Adequate negative results use the no-promotion,
scientifically-unresolved decision; registration failure, Cine skip, undertraining, proxy-only components, anchor identity,
monitor state, or stale wiki cannot receive audited completion.

## Codex prompt-merge instruction

After candidate validation, Codex maintenance merges Execution Contract, Controller Prompt, Executor Worker Contract, and
Mapper Contract into `prompts/shared/EXECUTOR_PROMPTS.md`; only Reviewer Prompt enters
`prompts/shared/REVIEWER_PROMPTS.md`. Keep the executor plan, delete this standalone staging only after verified integration,
and stop before M10 execution.
