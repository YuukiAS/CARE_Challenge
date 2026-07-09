# M9 SRR Dictionary Fidelity Repair + Training Evidence Staging Prompt

This is a GPT-authored staging file for the post-M8 / post-M8-follow-up repair milestone. It must be split by a later Codex maintenance step into `prompts/shared/EXECUTOR_PROMPTS.md` and `prompts/shared/REVIEWER_PROMPTS.md`, then deleted after the split/merge is verified.

This file is intentionally a milestone prompt, not a result packet and not a route-promotion claim. It does not authorize validation packaging, validation upload, hosted metric claims, leaderboard claims, fold expansion, scientific stop, or M10.

## Route Bootstrap Evidence

```yaml
diagram_source: "current conversation uploaded visual materials / ChatGPT visual channel"
diagram_versions_read: ["SRR-v2", "SRR-v2.5", "SRR-v3"]
canonical_repo_paths: ["images/SRR-v2.png", "images/SRR-v2.5.png", "images/SRR-v3.png"]
visual_read_status: "READ_FROM_CURRENT_CONVERSATION_UPLOADS"
previous_m8_review_path: "results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/review.md"
previous_m8_review_token: "M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED"
previous_followup_review_path: "results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/review.md"
previous_followup_review_token: "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED"
source_todo: "TODO.md"
source_dictionary_todo: "TODO-dictionary.md"
source_paper_local: "Representation Retrieval Learning for Heterogeneous Data Integration.pdf"
staging_file: "prompts/shared/M9_srr_dictionary_fidelity_repair_training.md"
```

Recovered route objective: SRR-MyoPS is a primary availability-aware selective representation retrieval system for medical imaging, not an nnU-Net postprocess. The key research claim is that a Blockwise Representation Retrieval-style dictionary can be adapted from heterogeneous tabular/multi-source learning into multi-modal CMR segmentation by using real modality-specific image encoders, source/availability-aware representer retrieval, pathology-specific lesion proposal dictionaries, pattern-SIP regularization, anatomy-guided soft ROI refinement, safe negative-space learning, and final output evidence where SRR is the primary lesion-evidence generator. nnU-Net may be used only as context, teacher, uncertainty feature, safety source, and same-split control. It must not be the normal final-logit anchor for candidate models.

Diagram-specific refiner objective re-read: SRR-v2.5 / SRR-v3 explicitly distinguish scar and edema. Scar is LGE-dominant, usually smaller, precision-sensitive, and remote-FP / HD95 sensitive; it needs a small-ROI, high-resolution, high-precision refiner. Edema is T2-conditioned, often broader / more diffuse, context-preserving, and recall-sensitive under T2-present supervision; it needs a large-ROI, context-preserving refiner with no-T2 blocking. M9 must not implement scar and edema as a shared generic pathology refiner with only class-name changes. The candidate must expose separate scar and edema proposal/refiner modules, separate ROI generation rules, separate crop/field-of-view policy, separate loss terms, separate thresholds, and separate hard-subgroup success gates.

Diagram-specific Cine objective re-read: SRR-v2.5 / SRR-v3 show Cine as a registration-aware anatomy-first temporal retrieval branch, not an optional note. It must progress toward a final-output model: cine sequence -> ED/reference and key-frame selection -> registration/warping -> temporal representation dictionary -> frame-wise anatomy prior + temporal aggregation -> `myocardium_cinemyops` output. Downloading CineMA weights, running frame0-only predictions, producing descriptor-only temporal tables, or running a single SyN/Demons smoke test is not implementation completion.

The R2 / BR2 paper basis to preserve in this milestone:

1. R2 learns a shared representer dictionary `Theta = {theta_1, ..., theta_D}` and source/task-specific sparse retrieval coefficients `beta^(s)` so each source retrieves a relevant subset of representers.
2. Integrativeness is the number of sources that retrieve a representer, `gamma_d = sum_s I(beta_d^(s) != 0)`.
3. SIP encourages integrative representers instead of forcing either full sharing or isolated per-source experts.
4. BR2 handles blockwise missingness by using modality-specific dictionaries `Theta_m`, observed-modality indicators `I_m^(s)`, and no imputation. Missing modalities must contribute zero by construction, not by fake zero-filled images.
5. For medical imaging, the natural extension is pattern-conditioned dictionary retrieval across availability groups, centers/styles, hard subgroups, and lesion contexts; dictionary usefulness must be proven by final-logit/final-label causal effect, not by slot names or diagnostic CSVs alone.

M8 / M8 follow-up scientific state: current M8 candidate family is `NO_PROMOTION`; M8 follow-up found `NO_DEPLOYABLE_REPAIR_CONTRACT_FOUND`; neither packet scientifically disproves SRR. They show that the current implementation is too anchor-centered, loss-weight wiring is suspect, checkpoint selection is not metric-aligned, prototype memory is not strong enough, and Cine evidence is proxy-only. M9 is therefore a fidelity-repair-plus-training milestone, not a route abandonment milestone.

## Executor Prompt

You are the Codex executor/controller for exactly one milestone: M9 SRR dictionary fidelity repair + training evidence. This is a high-risk CARE model implementation milestone. It is not fold expansion, not validation packaging, not validation upload, not route promotion, and not M10.

Required protocol sentence: This is an executor/controller session for one milestone only. Stop after writing completion_check.md and review_request.md, force-add/commit the lightweight required result files, then stop. Do not push automatically. Do not write review.md and do not start the next milestone. The milestone must be reviewed by a separate read-only Codex session before continuation.

Before executing the scientific task, enforce the hard-gate policy: exact task graph, strict validator, completion-check-before-final-audit, minimum effective training, current-bad-packet regression, and SRR diagram-bootstrap evidence when the task touches SRR/MyoPS/Cine route planning. If any hard gate fails, stop with NEEDS_REVISION or NEEDS_EVIDENCE; do not continue to final audit.

### 1. Required reading before execution

Read these files before editing code or running training:

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
README.md
prompts/CHATGPT_RULES.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
prompts/shared/M9_srr_dictionary_fidelity_repair_training.md
TODO.md
TODO-dictionary.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/review.md
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/review.md
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/m8_repair_contract.md
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/m8_next_required_action.md
src/care_myocardium/models/srr_blocks.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/proposal_prototypes.py
src/care_myocardium/losses/srr_losses.py
scripts/training/run_srr_propref_myops_fold0.py
scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py
```

If any required M8 or M8 follow-up review file is missing, write a blocked packet with status `M9_NEEDS_EVIDENCE_MISSING_PREREQUISITE_REVIEW` and stop. Do not infer from chat summaries.

If this milestone will submit any Slurm job, also read and apply:

```text
.agents/skills/slurm-routing-partition/SKILL.md
```

### 2. Task identity and result directory

Use this result directory:

```text
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/
```

Allowed first-party code paths:

```text
src/care_myocardium/models/srr_blocks.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/proposal_prototypes.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/models/cine_temporal_srr.py
src/care_myocardium/losses/srr_losses.py
scripts/training/run_srr_propref_myops_fold0.py
scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py
scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py
scripts/evaluation/run_srr_v3_m9_cine_temporal_output_probe.py
jobs/src/run_srr_v3_m9_dictionary_fidelity_training_htzhulab.sh
jobs/src/run_srr_v3_m9_dictionary_fidelity_training.sh
```

You may add small unit tests under an appropriate first-party test path if the repo already has a test convention. If no test convention exists, place validator self-tests inside the M9 validator and report them in result files.

### 3. Scientific goal

M9 must answer this question:

After repairing implementation fidelity, does a true BR2-inspired SRR dictionary system produce stable lesion-evidence improvement over current M8-style anchor-residual behavior, especially for T2-present edema-positive CenterB/CenterC cases, while preserving scar and no-T2 safety?

Do not answer this by claiming a leaderboard result. Answer it by code fidelity checks, causal ablations, M8-equivalent training evidence, same-split metrics, hard-subgroup metrics, and independent review.

### 4. Non-negotiable design constraints

nnU-Net must not be the main model in M9 candidate outputs. It is allowed only as:

```text
same_split_control
context_feature
teacher_feature
uncertainty_feature
safety_fallback_for_explicit_failure_cases
anatomy/context source when explicitly tagged
```

Forbidden for M9 candidate outputs:

```text
final_logits = nnunet_anchor_logits + bounded_srr_delta
normal output path uses anchor logits as the base logits
candidate selected because it preserves anchor identity
route promotion based on anchor-only or foreground_mean
silent fallback to nnU-Net
hidden nnU-Net identity under SRR naming
```

A separate `anchor_only_control` and an `m8_anchor_residual_control` are required as controls. They may not be selected as SRR route candidates.

### 5. Required repairs

#### 5.1 Loss-weight wiring repair

Fix the M8/M9 loss contract bug: variant-specific JSON or CLI loss weights must actually enter `srr_m6_expanded_total_loss(...)` or its M9 replacement. The repair must support explicit weights for at least:

```text
loss_anatomy_union_lv_rv
loss_scar_proposal
loss_edema_proposal_t2_present_only
loss_scar_refiner_roi
loss_edema_refiner_t2_present_roi
loss_anchor_preservation_outside_roi
loss_correction_opportunity
loss_branch_arbitration_consistency
loss_bounded_correction
loss_component_remote_fp
loss_no_t2_edema_safety
loss_dictionary_entropy_coverage_load_balance
loss_pattern_sip_integrativeness
loss_prototype_diversity_margin
loss_memory_bank_update_or_alignment
loss_refiner_final_label_effect
```

Required proof: a unit/validator test must set a component weight to `0` and a large value such as `10`, then prove that total loss and at least one relevant gradient norm change. If this test is missing, M9 must be `NEEDS_REVISION`.

#### 5.2 Metric-aligned checkpoint selection repair

Stop selecting best checkpoint by patch loss alone. Patch loss may remain a sanity metric. For formal M9 candidates, scheduled checkpoints must be evaluated on a bounded same-split validation subset and best selection must use metric-facing fields:

```text
scar Dice
scar HD95
scar remote-FP count
scar component count
edema Dice on T2-present edema-positive cases
edema HD95 on T2-present edema-positive cases
edema remote-FP count
edema component count
CenterB / CenterC subgroup help-harm
no-T2 edema safety
```

The selected checkpoint must be recorded in `m9_metric_aligned_checkpoint_selection.csv`. If GPU budget prevents full-volume evaluation at every checkpoint, evaluate at a fixed schedule and document the exact cases and cost. Do not select by `val_patch_loss` alone.

#### 5.3 SRR-main final-output repair

Add a formal M9 candidate mode where SRR, proposal, and refiner logits are the primary final evidence. In this mode nnU-Net may enter as context/teacher/safety features but not as final-logit base. The model must expose:

```text
m9_final_output_mode: SRR_MAIN_NOT_ANCHOR_RESIDUAL
nnunet_role: CONTEXT_TEACHER_SAFETY_CONTROL_ONLY
srr_main_logits
proposal_logits
refiner_logits
anatomy_context_logits
final_logits
final_label_delta_vs_srr_without_dictionary
final_label_delta_vs_anchor_control
```

You may preserve an explicit safety fallback branch only for diagnostic rows. If a candidate mostly collapses to fallback, it must be labeled `FALLBACK_DOMINATED_NOT_SRR_MAIN`.

#### 5.4 True-BR2 modality dictionary repair

Implement a true BR2 medical-imaging dictionary path. It must prohibit `[fused, fused, fused]` pseudo-modality input for formal M9 candidates. Each scale dictionary must consume real per-modality features:

```text
LGE_scale_l
T2_scale_l when T2 is available
C0_scale_l when C0 is available
```

Required dictionary families:

```text
shared dictionary D_l^shared
LGE private dictionary D_l^LGE
T2 private dictionary D_l^T2
C0 private dictionary D_l^C0
LGE-T2 interaction dictionary D_l^{LGE,T2}
LGE-C0 interaction dictionary D_l^{LGE,C0}
optional T2-C0 interaction dictionary D_l^{T2,C0} only when justified
```

Invalid missing-modality slots must be masked before routing. Interaction slots must be unavailable unless all modalities in the pair are present.

#### 5.5 Pattern-SIP / integrativeness repair

Implement a differentiable medical-imaging adaptation of SIP. It should not merely force uniform gate coverage. It must estimate soft integrativeness by task, slot, and pattern group:

```text
u_{task, slot, group} = mean gate usage for task/slot over group
```

Pattern groups must include, when available:

```text
availability pattern: LGE-only, C0+LGE, C0+LGE+T2
center/style group: CenterA/CenterB/CenterC or documented available centers
pathology group: scar-positive, edema-positive, empty-GT
hard subgroup: remote-FP, component-burden, T2-present edema-positive
```

The M9 pattern-SIP objective should encourage true shared slots to have stable usage across multiple compatible groups, encourage LGE-private slots for scar evidence, T2-private / LGE-T2 interaction slots for edema evidence when T2 is present, and avoid invalid slot usage. It must report:

```text
m9_pattern_sip_usage_by_group.csv
m9_integrativeness_gamma_soft.csv
m9_dictionary_slot_group_stability.csv
m9_dictionary_invalid_slot_mask_report.csv
```

#### 5.6 Prototype / memory repair

Replace or augment fixed-buffer prototypes with a stronger auditable prototype memory. Acceptable implementations:

```text
learnable prototype parameters initialized from same-split train/OOF features
or EMA prototype buffers updated from train features with explicit update ledger
or a hybrid: fitted prototypes plus learnable projection and EMA category means
```

The memory must separately track scar-positive, scar-safe-negative, edema-positive, and edema-safe-negative categories. Edema negatives must be T2-present only. no-T2 myocardium must never enter edema negative memory.

Required evidence:

```text
m9_prototype_memory_summary.json
m9_prototype_update_ledger.csv
m9_hard_negative_replay_ledger.csv
m9_no_t2_edema_negative_violation_report.csv
```

If any formal candidate still uses deterministic axis prototypes as the only prototype source, mark it `DETERMINISTIC_BOOTSTRAP_NOT_FORMAL` and do not use it for route decisions.

#### 5.7 Lesion proposal dictionary and T2-present edema recall repair

M9 must prioritize lesion formation, not just evidence selection. For scar and edema proposal dictionaries, report proposal recall/precision and lesion-wise recall before final mask evaluation.

Required for edema:

```text
T2-present edema-positive proposal recall
CenterB edema proposal recall
CenterC edema proposal recall
edema HD95 and component count on T2-present edema-positive subset
no-T2 edema blocked logits and export safety
```

Training must stratify or oversample T2-present edema-positive cases, especially CenterB/CenterC, without turning no-T2 cases into edema negatives.

#### 5.8 Pathology-specific scar/edema refiner repair

SRR-v2.5 / SRR-v3 require scar and edema to have different proposal/refinement behavior. M9 must make this explicit in code and evidence.

Scar refiner requirements:

```text
small-ROI / high-resolution crop policy
LGE-dominant evidence path
high precision and remote-FP suppression
HD95 / component guard
scar-specific proposal threshold sweep
scar-specific refiner loss and causal-effect rows
```

Edema refiner requirements:

```text
large-ROI / context-preserving crop policy
T2-conditioned evidence path
T2-present edema proposal recall floor
CenterB / CenterC T2-present edema hard-subgroup reporting
no-T2 edema logits blocked before proposal, refiner, decode, and export
edema-specific refiner loss and causal-effect rows
```

Forbidden shortcut: a single shared generic pathology refiner with only class-name changes, identical ROI/crop policy, identical thresholds, and no scar-vs-edema causal-effect evidence. Existing code already has separate `scar_refine` and `edema_refine`; M9 must preserve and strengthen that separation rather than flatten it.

Required outputs:

```text
m9_pathology_specific_refiner_contract.md
m9_refiner_roi_policy_by_pathology.csv
m9_scar_refiner_causal_effect.csv
m9_edema_refiner_causal_effect.csv
m9_refiner_ablation_by_pathology.csv
```

#### 5.9 Refiner causal-effect repair

The refiner must prove it changes final logits/final labels in a useful way, not only produce residual tensors. Required ablations:

```text
SRR-main without refiner
SRR-main with proposal only
SRR-main with scar refiner only
SRR-main with edema refiner only
SRR-main with scar + edema refiners
SRR-main with dictionary disabled
SRR-main with pattern-SIP disabled
M8 anchor-residual control
anchor-only control
```

For each ablation, report final-label delta, Dice/HD95/component/remote-FP, and hard-subgroup help/harm separately for scar and edema. The refiner is not considered implemented for scientific purposes unless scar and edema each have their own reported causal pathway. Scar may pass with high-precision local improvement; edema must be judged on T2-present edema-positive recall/HD95/component/remote-FP plus no-T2 safety. A scar-only signal cannot be used to claim edema refiner success.

#### 5.10 Cine final-output architecture and no false completion

M9 remains primarily a MyoPS dictionary fidelity repair milestone, but Cine is not optional. M9 must add a fully specified Cine final-output architecture contract and at least a first-party implementation scaffold that can produce final-output tensors/masks from a cine sequence interface. It may be undertrained or untrained in M9, but it must not remain a download/proxy/smoke placeholder.

Required Cine architecture:

```text
input: cine sequence with frame index metadata
ED/reference and key-frame selector
frame-quality / motion-saliency router
registration candidate interface: identity, SimpleITK/ANTs, future VoxelMorph slot
reference-frame warping / probability or segmentation warping
temporal representation dictionary with valid-frame masks
frame-wise anatomy prior
temporal aggregation head
output: myocardium_cinemyops logits or mask in official label space / documented proxy label conversion
```

Required first-party code / evidence:

```text
src/care_myocardium/models/cine_temporal_srr.py
scripts/evaluation/run_srr_v3_m9_cine_temporal_output_probe.py
m9_cine_temporal_output_architecture_contract.md
m9_cine_final_output_model_scaffold_report.md
m9_cine_shape_forward_probe.csv
m9_cine_registration_plan.csv
m9_cine_no_false_completion_report.md
```

Completion blockers for Cine:

```text
downloaded CineMA weights only
frame0-only output
descriptor-only temporal retrieval
single-case or near-single-case SyN/Demons smoke
untrained or unvalidated VoxelMorph claimed ready
registration evidence with no final-output tensor/mask path
temporal dictionary that does not feed temporal aggregation
local proxy evidence used as hosted Cine readiness
```

M9 does not need to prove hosted Cine improvement, but it must leave a complete, non-lazy Cine implementation contract for a future Cine milestone. If local assets allow, run a bounded shape/forward probe on a small safe subset. If assets are unavailable, write an honest blocker in the Cine report. Do not use CineMA/registration proxy evidence to rescue MyoPS claims.

### 6. Required M9 variants and controls

Formal M9 must include at least these candidate/control families:

```text
anchor_only_control
m8_anchor_residual_control
m9_srr_main_true_br2_pattern_sip
m9_srr_main_lesion_proposal_memory
m9_srr_main_t2_edema_recall_focus
```

Minimum causal ablations may be done by toggles or separate runs, but the result packet must include their metric rows:

```text
no_dictionary
no_pattern_sip
no_prototype_memory
no_refiner
proposal_only
refiner_enabled
```

The controls are mandatory for interpretation but cannot be promoted.

### 7. Minimum training budget and runtime rules

M9 must include M8-like training evidence, not just smoke. Minimum formal budget:

```text
aggregate_train_loop_seconds >= 28800 OR at least three formal SRR-main candidates with >= 7200 train_loop_seconds each plus one control eval
min_optimizer_steps_per_formal_candidate >= 6000 unless train_loop_seconds >= 7200 and loss plateau is documented
validation_event_count_per_formal_candidate >= 20
one_batch_overfit required
loss decrease required
prediction sanity required
same-split anchor/control metrics required
hard subgroup metrics required
```

If scheduler or runtime blocks training, write `M9_NEEDS_MONITOR` or `M9_RESOURCE_BLOCKED` as appropriate. A monitor packet is not completion.

Training must produce stable loss and metrics. If loss is NaN/Inf, detached, non-decreasing without explanation, or if required loss components have zero gradient without a valid mask reason, M9 must be `NEEDS_REVISION` or `SCIENTIFIC_UNDERTRAINED`, not ready.

### 8. Required outputs

The result directory must contain at least:

```text
result.md
completion_check.md
review_request.md
MANIFEST.md
commands_run.md
m9_route_objective.md
m9_rrl_brr2_adaptation_contract.md
m9_dictionary_fidelity_matrix.csv
m9_code_patch_summary.md
m9_loss_weight_wiring_test_report.md
m9_metric_aligned_checkpoint_selection.csv
m9_nnunet_role_audit.md
m9_pattern_sip_usage_by_group.csv
m9_integrativeness_gamma_soft.csv
m9_dictionary_slot_group_stability.csv
m9_dictionary_invalid_slot_mask_report.csv
m9_prototype_memory_summary.json
m9_prototype_update_ledger.csv
m9_hard_negative_replay_ledger.csv
m9_no_t2_edema_negative_violation_report.csv
m9_training_budget_ledger.csv
m9_training_curves.csv
m9_validation_events.csv
m9_loss_component_gradient_sanity.csv
m9_candidate_assembly_matrix.csv
m9_same_split_help_harm.csv
m9_hard_subgroup_metrics.csv
m9_component_remote_fp_hd95_report.csv
m9_proposal_refiner_recall_precision.csv
m9_refiner_causal_effect.csv
m9_pathology_specific_refiner_contract.md
m9_refiner_roi_policy_by_pathology.csv
m9_scar_refiner_causal_effect.csv
m9_edema_refiner_causal_effect.csv
m9_refiner_ablation_by_pathology.csv
m9_ablation_matrix.csv
m9_cine_temporal_output_architecture_contract.md
m9_cine_final_output_model_scaffold_report.md
m9_cine_shape_forward_probe.csv
m9_cine_registration_plan.csv
m9_cine_no_false_completion_report.md
m9_route_promotion_decision.md
m9_next_required_action.md
m9_strict_validator_report.csv
m9_strict_validator_report.md
m9_validator_selftest_report.csv
m9_validator_selftest_report.md
```

`m9_route_promotion_decision.md` may state only one of:

```text
M9_NO_PROMOTION_DIAGNOSTIC_ONLY
M9_REPAIR_CONTRACT_READY_FOR_REVIEW
M9_NEEDS_EVIDENCE
M9_NEEDS_REVISION
M9_SCIENTIFIC_UNDERTRAINED
M9_NEEDS_MONITOR
```

`M9_REPAIR_CONTRACT_READY_FOR_REVIEW` means only that an independent reviewer may consider whether GPT can plan M10. It does not authorize validation packaging/upload, hosted metric claims, leaderboard claims, fold expansion, or scientific stop.

`m9_next_required_action.md` must choose exactly one:

```text
GPT_PLAN_M10_DICTIONARY_ITERATION
GPT_PLAN_M10_CINE_TEMPORAL_ROUTE
GPT_REPLAN_AFTER_M9_NO_PROMOTION
NEEDS_EVIDENCE_BEFORE_NEXT_TASK
NEEDS_REVISION_BEFORE_REVIEW
NEEDS_MONITOR
```

### 9. Strict validator and known-bad self-tests

Implement `scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py`. It must fail closed on at least these mutations:

1. missing M8 follow-up review token;
2. missing diagram bootstrap fields;
3. missing required output file;
4. loss-weight wiring test absent or does not prove total loss/gradient changes;
5. checkpoint selected by patch loss only;
6. formal candidate uses `final_logits = nnunet_anchor_logits + bounded_delta` as normal output;
7. anchor-only or M8 anchor-residual control marked as candidate promotion;
8. pseudo-modality `[fused,fused,fused]` used in a formal BR2 candidate;
9. invalid modality interaction slot active when a modality is missing;
10. pattern-SIP report missing or uniform coverage substituted for integrativeness;
11. deterministic axis prototypes are the only formal prototype source;
12. no-T2 myocardium used as edema negative;
13. no-T2 formal candidate emits edema voxels;
14. refiner has no final-label effect but is claimed implemented;
15. scar and edema use identical generic refiner/ROI/crop policy without pathology-specific evidence;
16. scar-only refiner signal is used to claim edema refiner success;
17. hard subgroup metrics missing CenterB/CenterC/T2-present/edema-positive/no-T2 safety rows when present in evidence;
18. Cine branch is marked complete because weights were downloaded;
19. Cine branch is marked complete from frame0-only, descriptor-only temporal table, or single SyN/Demons smoke;
20. Cine temporal dictionary does not feed a final-output tensor/mask path;
21. Cine final-output model class or forward probe is missing without an honest asset blocker;
22. monitor/pending Slurm packet marked ready;
23. smoke-only or synthetic-only evidence marked formal training;
24. validation package/upload/hosted metric claim present;
25. M10 or fold expansion started automatically;
26. reviewer output written by executor.

Self-test must include one good fixture and all known-bad mutations. If any known-bad mutation passes, completion must be `M9_NEEDS_REVISION_VALIDATOR_NOT_FAIL_CLOSED`.

### 10. Allowed executor completion states

```text
M9_READY_FOR_REVIEW
M9_NEEDS_EVIDENCE
M9_NEEDS_REVISION
M9_SCIENTIFIC_UNDERTRAINED
M9_NEEDS_MONITOR
M9_RESOURCE_BLOCKED
M9_BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE
```

`M9_READY_FOR_REVIEW` requires all required outputs, completed post-job aggregation, validator pass with `error_count=0`, known-bad self-tests fail closed, M8-like training evidence, and no forbidden claims. It is not an audited decision.

### 11. Git and artifact policy

Commit only first-party code/helpers/tests and lightweight Markdown/CSV/JSON result files. Do not commit checkpoints, predictions, NIfTI files, upload zips, raw data, large logs, secrets, or full runtime trees.

Recommended local commit command after successful completion:

```bash
git add -f \
  src/care_myocardium/models/srr_blocks.py \
  src/care_myocardium/models/srr_propref.py \
  src/care_myocardium/models/proposal_prototypes.py \
  src/care_myocardium/models/srr_dictionary_memory.py \
  src/care_myocardium/models/cine_temporal_srr.py \
  src/care_myocardium/losses/srr_losses.py \
  scripts/training/run_srr_propref_myops_fold0.py \
  scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py \
  scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py \
  scripts/evaluation/run_srr_v3_m9_cine_temporal_output_probe.py \
  jobs/src/run_srr_v3_m9_dictionary_fidelity_training_htzhulab.sh \
  jobs/src/run_srr_v3_m9_dictionary_fidelity_training.sh \
  results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/*.md \
  results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/*.csv \
  results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/*.json
git commit -m "Add M9 SRR dictionary fidelity repair training packet"
```

Do not push automatically unless the user explicitly instructs it in the Codex session.

## Reviewer Prompt

You are the separate read-only reviewer/auditor for M9 SRR dictionary fidelity repair + training evidence.

Required protocol sentence: This is a separate read-only reviewer/auditor session. Do not fix code, do not generate missing artifacts, do not train, and do not start the next milestone. Review only the completed result directory, write review.md with the controlled milestone decision, then force-add/commit review.md. Do not push automatically.

### 1. Review scope

Review only:

```text
prompts/shared/M9_srr_dictionary_fidelity_repair_training.md
src/care_myocardium/models/srr_blocks.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/proposal_prototypes.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/models/cine_temporal_srr.py
src/care_myocardium/losses/srr_losses.py
scripts/training/run_srr_propref_myops_fold0.py
scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py
scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py
scripts/evaluation/run_srr_v3_m9_cine_temporal_output_probe.py
jobs/src/run_srr_v3_m9_dictionary_fidelity_training_htzhulab.sh
jobs/src/run_srr_v3_m9_dictionary_fidelity_training.sh
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/review.md
TODO.md
TODO-dictionary.md
```

You may read protocol files as needed:

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
README.md
prompts/CHATGPT_RULES.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
```

### 2. Required review checks

Check M9 did not claim validation packaging, validation upload, hosted metrics, leaderboard readiness, fold expansion, scientific stop, or M10.

Check loss-weight wiring. The review must inspect both code and `m9_loss_weight_wiring_test_report.md`. If component weights do not reach the actual M9 total loss, return `M9_AUDITED_NEEDS_REVISION`.

Check checkpoint selection. If best checkpoint is selected only by patch loss, return `M9_AUDITED_NEEDS_REVISION`.

Check nnU-Net role. If formal M9 candidate outputs normally use `nnunet_anchor_logits + bounded_delta` as final logits, or if anchor-only / M8 anchor-residual controls are treated as SRR candidate wins, return `M9_AUDITED_PROTOCOL_BLOCKED` or `M9_AUDITED_NEEDS_REVISION`.

Check True-BR2 dictionary fidelity. Formal M9 candidates must use real per-modality features and invalid-slot masks. `[fused,fused,fused]` pseudo-modality paths may appear only in legacy controls, never formal M9 candidates.

Check Pattern-SIP. The packet must report pattern-conditioned soft integrativeness across availability/style/hard-subgroup groups. Uniform entropy/coverage alone is insufficient.

Check prototype memory. Deterministic axis prototypes alone cannot support formal evidence. Edema negatives must be T2-present safe negatives only, and no-T2 myocardium must not enter edema negative memory.

Check pathology-specific refiner fidelity. Scar and edema must have separate refiner policies aligned with the diagrams: scar small-ROI / LGE-dominant / precision-HD95; edema large-ROI / T2-conditioned / recall-context / no-T2-safe. A single generic refiner cannot pass.

Check refiner causal effect. The refiner must be evaluated by final-label/logit effect and ablations separately for scar and edema. A residual tensor without final-label impact is not enough.

Check training adequacy. M9 must meet its training budget or use a controlled undertrained/monitor/resource-blocked state. Monitor packets, pending Slurm jobs, smoke-only evidence, or synthetic evidence cannot be audited-go.

Check metrics. Same-split comparison must report scar and edema separately, hard subgroups, no-T2 safety, remote FP, component count, HD95, proposal recall/precision, and refiner causal effect. Do not accept foreground mean as evidence.

Check Cine boundary and progress. M9 must not use CineMA/registration proxy evidence to claim MyoPS route success or hosted Cine readiness, but it must also not skip Cine. The packet must include a complete Cine final-output architecture contract and first-party scaffold/probe evidence or an honest asset blocker. Downloaded weights, frame0-only predictions, descriptor-only tables, or single SyN/Demons smoke cannot satisfy Cine progress.

Check validator. The strict validator must pass the real packet with zero errors and fail all known-bad self-tests. If known-bad passes, return `M9_AUDITED_NEEDS_REVISION`.

### 3. Review decisions

Write `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md` with exactly one of:

```text
M9_AUDITED_REPAIR_CONTRACT_READY
M9_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED
M9_AUDITED_SCIENTIFIC_UNDERTRAINED
M9_AUDITED_NEEDS_EVIDENCE
M9_AUDITED_NEEDS_REVISION
M9_AUDITED_NEEDS_MONITOR
M9_AUDITED_PROTOCOL_BLOCKED
```

`M9_AUDITED_REPAIR_CONTRACT_READY` means only this: GPT may plan a future M10 dictionary iteration or training expansion based on reviewed M9 evidence. It does not authorize validation packaging/upload, hosted claims, leaderboard claims, fold expansion, scientific stop, or automatic M10 execution.

Use `M9_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED` if M9 validly repairs fidelity and trains adequately but still does not show enough SRR-main/dictionary signal for the next implementation step.

Use `M9_AUDITED_SCIENTIFIC_UNDERTRAINED` if implementation fidelity is improved but training did not meet adequacy or loss/metrics are too immature for scientific judgment.

Use `M9_AUDITED_NEEDS_EVIDENCE` if required output files, runtime evidence, same-split controls, or hard subgroup metrics are missing.

Use `M9_AUDITED_NEEDS_REVISION` if code, loss wiring, checkpoint selection, dictionary fidelity, prototype memory, pathology-specific refiner design, refiner causal effect, Cine final-output architecture scaffold, no-T2 safety, or validator behavior is broken.

Use `M9_AUDITED_NEEDS_MONITOR` if any required Slurm-derived evidence is still pending/running/awaiting aggregation.

Use `M9_AUDITED_PROTOCOL_BLOCKED` if the executor wrote review.md, started M10, packaged validation, uploaded, claimed hosted metrics, or made nnU-Net the formal candidate protagonist.

### 4. Commit policy

Commit only the review file:

```bash
git add -f results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md
git commit -m "Add M9 SRR dictionary fidelity repair review"
```

Do not push automatically.
