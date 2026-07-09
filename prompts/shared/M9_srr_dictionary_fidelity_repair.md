# M9 SRR Dictionary Fidelity Repair Staging Prompt

This is a GPT-authored staging file for the first formal milestone after the M8 no-promotion follow-up. It must be split by a later Codex maintenance step into `prompts/shared/EXECUTOR_PROMPTS.md` and `prompts/shared/REVIEWER_PROMPTS.md`, then deleted after the split/merge is verified.

This staging file does not authorize route promotion, fold expansion, validation packaging, validation upload, hosted-metric claims, leaderboard claims, scientific stop, or automatic M10.

## Route Bootstrap Evidence

```yaml
diagram_source: "current conversation uploaded visual materials / ChatGPT visual channel"
diagram_versions_read: ["SRR-v2", "SRR-v2.5", "SRR-v3"]
canonical_repo_paths: ["images/SRR-v2.png", "images/SRR-v2.5.png", "images/SRR-v3.png"]
visual_read_status: "READ_FROM_CURRENT_CONVERSATION_UPLOADS"
source_paper: "Representation Retrieval Learning for Heterogeneous Data Integration"
source_repo_notes: ["TODO.md", "TODO-dictionary.md", "docs/notes/20260620_r2_deep_research_assessment.md"]
previous_m8_review_path: "results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/review.md"
previous_m8_review_token: "M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED"
previous_followup_review_path: "results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/review.md"
previous_followup_review_token: "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED"
staging_file: "prompts/shared/M9_srr_dictionary_fidelity_repair.md"
```

Recovered SRR-v3 route objective: SRR-MyoPS is not an nnU-Net postprocess and not a generic residual patch around nnU-Net. It is a medical-imaging adaptation of representation retrieval learning: availability-aware selective retrieval over modality-specific and interaction representer dictionaries, pathology-specific lesion proposal, anatomy-guided soft ROI refinement, explicit safe negative / hard-negative objectives, and final-label evidence that proves the retrieved representations affect scar and edema outputs. nnU-Net may appear only as context, teacher, anchor-control, uncertainty/safety source, or ablation comparator. It must not be the primary final-logit generator for the M9 candidate.

## Why this is M9

This is M9 because M8 and M8 follow-up are completed and independently reviewed. M8 produced a completed executor evidence packet but did not promote any candidate. M8 follow-up found no deployable non-GT repair contract from existing M8 evidence. M9 therefore starts a new repair milestone rather than extending M8 automatically.

M9 is not route promotion. M9 is a fidelity-repair and retraining milestone. Its job is to determine whether the core SRR dictionary idea has been implemented faithfully enough to test, then to run a bounded but real training/evaluation packet comparable to M8.

## R2 / BR2 idea to preserve

The paper `Representation Retrieval Learning for Heterogeneous Data Integration` motivates the main scientific story. In the paper, a representer dictionary is written as:

```text
Theta = {theta_1, ..., theta_D}
```

Each source/task retrieves a sparse subset of representers through task/source-specific coefficients. The integrativeness of representer `d` is:

```text
gamma_d = sum_s I(beta_{s,d} != 0)
```

The Selective Integration Penalty, SIP, encourages useful representers to be shared by multiple sources while preserving partial sharing instead of forcing either one universal representation or one fully isolated model per source.

For CARE dense segmentation, direct copying is wrong. The medical-imaging version must reinterpret these terms:

- source/task patterns: availability pattern, center/style group for training diagnostics, T2-present edema-positive subgroup, scar-positive subgroup, remote-FP/component-burden subgroup;
- representers: multi-scale modality-private, shared, and interaction feature blocks, plus pathology proposal prototypes and lesion-level refinement features;
- retrieval coefficients: task-specific and lesion-aware gate weights, not only global pooled sample weights;
- integrativeness: stable reuse of a representer across valid availability/style/hard-subgroup patterns, with invalid missing-modality slots masked out;
- SIP: pattern-conditioned soft integrativeness regularization, not uniform entropy or slot coverage alone.

M9 must explicitly bridge this paper idea to code and runtime evidence. A model that only renames a mixture-of-experts block as `dictionary`, or only logs CSV slot usage without final-logit effect, fails this milestone.

## Executor Prompt

You are the Codex executor/controller for exactly one milestone: M9 SRR dictionary fidelity repair. This task includes code repair, strict tests, bounded Slurm training, post-job aggregation, same-split metrics, causal ablations, and review packet generation.

Required protocol sentence: This is an executor/controller session for one milestone only. Stop after writing `completion_check.md` and `review_request.md`, force-add/commit the lightweight required result files, then stop. Do not push automatically. Do not write `review.md` and do not start the next milestone. The milestone must be reviewed by a separate read-only Codex session before continuation.

Before executing the scientific task, enforce the hard-gate policy: exact task graph, strict validator, completion-check-before-final-audit, minimum effective training, current-bad-packet regression, and SRR diagram-bootstrap evidence when the task touches SRR/MyoPS/Cine route planning. If any hard gate fails, stop with `NEEDS_REVISION` or `NEEDS_EVIDENCE`; do not continue to final audit.

### 1. Required reading before execution

Read these files before any code or training work:

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
README.md
prompts/CHATGPT_RULES.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
.agents/skills/slurm-routing-partition/SKILL.md
prompts/shared/M9_srr_dictionary_fidelity_repair.md
TODO.md
TODO-dictionary.md
docs/notes/20260620_r2_deep_research_assessment.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/review.md
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/review.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_variant_config_contract.json
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_training_budget_ledger.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_best_variant_decision_table.csv
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/m8_candidate_failure_matrix.csv
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/m8_proxy_arbitration_help_harm.csv
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/m8_hard_subgroup_help_harm.csv
src/care_myocardium/models/srr_blocks.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/proposal_prototypes.py
src/care_myocardium/losses/srr_losses.py
scripts/training/run_srr_propref_myops_fold0.py
scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py
```

If the prerequisite review token `M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED` is missing, write a minimal blocked packet with `M9_BLOCKED_MISSING_M8_FOLLOWUP_REVIEW` and stop.

### 2. Task identity and output location

Use this result directory:

```text
results/20260708_srr_v3_m9_dictionary_fidelity_repair/
```

Allowed code paths:

```text
src/care_myocardium/models/srr_blocks.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/proposal_prototypes.py
src/care_myocardium/losses/srr_losses.py
scripts/training/run_srr_propref_myops_fold0.py
scripts/evaluation/export_srr_v3_m9_dictionary_fidelity_eval.py
scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py
scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py
jobs/src/run_srr_v3_m9_dictionary_fidelity_htzhulab.sh
jobs/src/run_srr_v3_m9_dictionary_fidelity.sh
```

Allowed tests:

```text
tests/test_srr_m9_loss_weight_wiring.py
tests/test_srr_m9_dictionary_fidelity.py
tests/test_srr_m9_validator_fail_closed.py
```

Do not modify validation upload code except to explicitly assert that validation packaging/upload is not authorized.

### 3. Scientific goal

M9 must repair the implementation fidelity problems identified after M8, then perform real bounded training and same-split evaluation. The question is:

Can a faithful SRR-main, dictionary-centered, R2/BR2-inspired medical imaging implementation produce stable training and measurable same-split scar/edema help/harm evidence, without making nnU-Net the primary final-logit generator?

A negative result is acceptable only if the repaired implementation actually meets the fidelity contract and the training/evaluation evidence is complete. If fidelity is not repaired, the result is `NEEDS_REVISION`, not route-negative evidence.

### 4. Mandatory repairs

#### 4.1 Loss-weight wiring repair

Fix the M8/M9 loss-weight bug. `m8_variant_config_contract.json`-style component weights must actually reach `srr_m6_expanded_total_loss(...)` or the new M9 equivalent. Do not only record the weights in JSON.

Implement a clear mapping from config keys to expanded loss component keys, for example:

```text
scar -> loss_scar_refiner_roi
edema -> loss_edema_refiner_t2_present_roi
proposal -> loss_scar_proposal and loss_edema_proposal_t2_present_only
prototype_margin -> loss_prototype_diversity_margin
component_proposal -> loss_component_remote_fp or explicit component proposal terms
semantic_retrieval -> loss_dictionary_entropy_coverage_load_balance / pattern_sip
baseline_preservation -> teacher/context preservation outside selected SRR regions only
roi -> ROI coverage/objective terms
roi_remote -> remote-FP / outside-support ROI terms
```

Add tests proving that changing at least three weights changes total loss and gradients:

```text
loss_scar_refiner_roi
loss_edema_refiner_t2_present_roi
loss_dictionary_entropy_coverage_load_balance or pattern_sip
```

Known-bad fixture: a config with `edema=0.0` and `edema=10.0` producing identical total loss or identical edema gradient must fail.

#### 4.2 SRR-main final-output repair

M9 candidate outputs must not use the M8 default formula:

```text
final_logits = nnunet_anchor_logits + bounded_delta
```

as the primary final-logit path.

Implement an SRR-main final path where:

```text
final_logits = srr_main_logits
```

or an equivalent SRR-owned final head, with nnU-Net used only as:

```text
context_features
teacher_regularization
uncertainty / safety feature
anchor-only control
explicit safety fallback ablation
```

A safety fallback may exist, but it must be an explicit ablation/control mode such as `anchor_safety_fallback_control`, not the default candidate output. The packet must include `m9_final_output_ownership.csv` proving, for every trained/evaluated candidate, whether final logits are SRR-owned or anchor-owned. Any candidate marked `anchor_owned_default` cannot be used for M9 repaired-candidate conclusions.

#### 4.3 True-BR2 modality dictionary repair

For formal M9 candidates, prohibit `[fused, fused, fused]` pseudo-modality dictionary inputs. All shared/private/interaction experts must consume real per-scale modality features:

```text
[LGE_scale, T2_scale, C0_scale]
```

and invalid missing-modality slots must be masked through availability. This applies to every scale used by the formal candidate.

Add tests that fail if:

```text
SRRRetrievalBlock.forward() or any formal M9 path duplicates one fused tensor as all modalities;
private LGE/T2/C0 experts receive identical tensors in a formal path;
interaction slots stay valid when one paired modality is unavailable;
T2-private or LGE-T2 interaction slots contribute on no-T2 cases.
```

Lite dictionary may remain in repo only as a legacy sanity control. It must not be part of the repaired M9 formal candidate.

#### 4.4 Lesion-aware router and Pattern-SIP

Implement a pattern-conditioned SIP-style objective, not just uniform entropy or coverage.

For each task `t`, slot/expert `k`, and group `g`, compute soft usage:

```text
u[t,k,g] = mean gate weight for task t, slot k, group g over valid samples/regions
```

Groups must include at least:

```text
availability pattern: LGE-only, C0+LGE, C0+LGE+T2
T2_present vs no_T2
scar_positive vs scar_empty
edema_positive_T2_present vs edema_empty_or_no_T2
CenterB and CenterC as diagnostic-only training/reporting groups, not inference-only routing rules
remote_FP/component_burden groups if available
```

Approximate integrativeness as:

```text
gamma_hat[t,k] = sum_g valid[t,k,g] * sigmoid((u[t,k,g] - epsilon) / tau)
```

Then implement pattern-SIP with slot-type-specific expectations:

```text
shared slots: encourage gamma_hat across multiple valid groups;
LGE-private slots: encourage reuse across LGE-observed groups and scar-positive groups;
T2-private slots: encourage reuse across T2-present edema-positive groups, not no-T2 groups;
interaction slots: encourage reuse only when all paired modalities are present;
invalid slots: must have near-zero usage.
```

Export `m9_pattern_sip_usage.csv` and `m9_pattern_sip_loss_terms.csv` with fields:

```text
variant, step, task, scale, slot_index, slot_group, slot_kind, group_name,
valid_for_group, usage_mean, gamma_hat, sip_target, sip_penalty,
invalid_usage_penalty, entropy, collapse_warning
```

Known-bad fixtures must fail if pattern-SIP is replaced by uniform coverage alone, if invalid missing-modality slots receive nontrivial usage, or if all slots collapse to a single expert without a fail-closed warning.

#### 4.5 Prototype / memory repair

Do not rely on deterministic axis prototypes for any formal candidate. Formal M9 candidates must use one of:

```text
train/OOF fitted fixed prototype bank with explicit source/counts;
learnable prototype parameters initialized from train/OOF features;
EMA prototype memory updated from train batches with leakage-safe labels;
```

A formal candidate using deterministic fallback prototypes must fail readiness.

For scar, negative categories must include, when evidence exists:

```text
normal_myocardium
blood_pool
outside_myocardium
LGE_bright_artifact_or_anchor_hard_fp
remote_FP_island
```

For edema, negatives must be restricted to T2-present safe negatives:

```text
T2_present_normal_myocardium_far_from_edema
T2_present_blood_pool
T2_present_outside_myocardium
T2_present_hard_fp
T2_present_artifact
```

No no-T2 myocardium may enter edema negative prototypes. Export:

```text
m9_prototype_memory_summary.json
m9_prototype_update_sanity.csv
m9_hard_negative_replay_summary.csv
```

If iterative hard-negative mining is feasible inside the budget, run one bounded loop:

```text
initial repaired model checkpoint -> mine high-confidence false-positive / remote components on same-split train or OOF outputs -> safe filter -> replay in continued training
```

If not feasible, write `NOT_RUN_BUDGETED_DEFERRED` and do not claim iterative hard-negative mining was implemented.

#### 4.6 Lesion proposal and refiner causal effect repair

The refiner must be evaluated as a lesion formation module, not just a crop residual hidden behind anchor arbitration. Export causal effect metrics:

```text
m9_proposal_recall_precision.csv
m9_soft_roi_coverage.csv
m9_refiner_causal_effect.csv
m9_final_label_effect_by_case.csv
```

Required fields include:

```text
variant, case_id, metric_name, center, modality_group, t2_present,
proposal_threshold, proposal_recall, proposal_precision, lesion_wise_recall,
proposal_component_count, proposal_remote_fp_count,
soft_roi_gt_coverage, outside_myocardium_roi_ratio,
refiner_enabled, refiner_disabled_counterfactual,
final_label_voxels_changed_by_refiner, final_dice_delta_refiner_on,
final_hd95_delta_refiner_on, final_remote_fp_delta_refiner_on
```

A refiner that only changes diagnostic tensors but not final logits/final labels cannot support a repaired candidate.

#### 4.7 Metric-based checkpoint selection repair

Do not select best checkpoint using patch loss alone. Patch loss may be logged as training sanity only.

Implement checkpoint selection based on full-case or broad same-split evaluation. At minimum, at scheduled checkpoints run full-volume or reviewer-approved bounded full-case eval on a hard subset that includes:

```text
CenterB T2-present edema-positive
CenterC T2-present edema-positive
LGE-only scar-positive / no-T2 safety
remote-FP cases
component-burden cases
```

Selection must consider scar and edema separately:

```text
scar Dice, scar HD95, scar remote FP, scar component count;
edema Dice, edema HD95, edema remote FP, edema component count;
no-T2 edema voxels;
T2-present edema-positive metrics;
CenterB/CenterC metrics.
```

Export:

```text
m9_checkpoint_selection_trace.csv
m9_same_split_help_harm.csv
m9_hard_subgroup_metrics.csv
m9_best_candidate_decision_table.csv
```

`m9_best_candidate_decision_table.csv` must explicitly compare against:

```text
anchor_only_control
M8 best candidate or current anchor-residual control, if reproducible
M9 repaired candidates
```

#### 4.8 Causal ablations

M9 must include causal ablations. At minimum:

```text
anchor_only_control                           # evaluation-only control, not model owner
m8_anchor_residual_control                    # current M8-style anchor-owned residual, if reproducible
m9_srr_main_true_br2_pattern_sip              # SRR-owned final logits + true BR2 + pattern-SIP
m9_srr_main_no_pattern_sip                    # same SRR-main without pattern-SIP or with SIP weight zero
m9_srr_main_no_prototype_memory               # same SRR-main with prototype proposal disabled / replaced, clearly marked
m9_srr_main_no_refiner                        # same SRR-main with refiner disabled
m9_srr_main_prototype_memory_refiner          # full repaired candidate
m9_srr_main_t2_edema_recall                   # T2-present edema-focused candidate if budget allows
```

If resource limits prevent training all variants, train at least:

```text
anchor_only_control evaluation
m8_anchor_residual_control evaluation or reproduced metrics
m9_srr_main_true_br2_pattern_sip formal training
m9_srr_main_prototype_memory_refiner formal training
m9_srr_main_no_refiner ablation evaluation from compatible checkpoint
```

Ablations must be honest: if an ablation is not trained/evaluated, mark `NOT_RUN_RESOURCE_LIMIT` and do not infer from it.

#### 4.9 Cine boundary

M9 is primarily MyoPS SRR dictionary fidelity repair. Cine must not be used to rescue MyoPS. However, M9 must prevent false Cine claims.

Write `m9_cine_fidelity_status.md` with:

```text
CineMA_status: frame-wise anatomy proxy / prior pilot, not complete Cine route unless separately proven
registration_status: diagnostic Demons/SyNOnly proxy unless trained/validated temporal model exists
VoxelMorph_status: not ready unless trained/validated and before/after metrics exist
final_output_effect: whether temporal aggregation changes final CineMyoPS labels
```

Do not claim Cine readiness from frame0-only, descriptor-only temporal retrieval, single-case registration smoke, untrained VoxelMorph, or local proxy evidence without final-output effect.

### 5. Training requirements

M9 must include real training comparable to M8 unless blocked by failed fidelity gates.

Minimum training evidence for formal M9 candidate(s):

```yaml
minimum_effective_training:
  aggregate_min_train_loop_seconds: 28800
  min_formal_trained_variants: 2
  min_single_variant_train_loop_seconds: 7200
  min_optimizer_steps_per_formal_variant: 6000
  min_validation_events_per_formal_variant: 20
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  require_same_split_baseline: true
  require_hard_subgroup_eval: true
  require_metric_based_checkpoint_selection: true
  require_cache_isolation: true
```

Use Slurm according to `.agents/skills/slurm-routing-partition/SKILL.md`. Default to `htzhulab`; use `a100-gpu` fallback only with queue evidence and lock-safe routing. Each job must be eight hours or less unless explicitly justified. Pending/running/submitted-only states are `NEEDS_MONITOR`, not completion.

If all fidelity unit tests fail before training, do not launch long training. Write `M9_NEEDS_REVISION_FIDELITY_REPAIR_FAILED`.

If training jobs are submitted but not completed/aggregated, write `M9_NEEDS_MONITOR` and stop. Do not request normal review until post-job aggregation is complete.

### 6. Required output files

The result directory must contain:

```text
result.md
completion_check.md
review_request.md
MANIFEST.md
commands_run.md
m9_route_objective.md
m9_prerequisite_review_check.md
m9_r2_br2_to_srr_mapping.md
m9_architecture_fidelity_matrix.csv
m9_code_change_summary.md
m9_loss_weight_wiring_report.csv
m9_loss_weight_wiring_test_report.md
m9_final_output_ownership.csv
m9_true_br2_dictionary_report.csv
m9_pattern_sip_usage.csv
m9_pattern_sip_loss_terms.csv
m9_prototype_memory_summary.json
m9_prototype_update_sanity.csv
m9_hard_negative_replay_summary.csv
m9_training_budget_ledger.csv
m9_training_curves.csv
m9_validation_events.csv
m9_checkpoint_selection_trace.csv
m9_same_split_help_harm.csv
m9_hard_subgroup_metrics.csv
m9_best_candidate_decision_table.csv
m9_proposal_recall_precision.csv
m9_soft_roi_coverage.csv
m9_refiner_causal_effect.csv
m9_final_label_effect_by_case.csv
m9_no_t2_safety_report.csv
m9_cine_fidelity_status.md
m9_route_promotion_decision.md
m9_next_required_action.md
m9_strict_validator_report.csv
m9_strict_validator_report.md
m9_validator_selftest_report.csv
m9_validator_selftest_report.md
```

`m9_route_promotion_decision.md` must default to:

```text
route_promotion_decision: NOT_AUTHORIZED_BY_EXECUTOR
validation_packaging: NOT_AUTHORIZED_NOT_CREATED
validation_upload: NOT_AUTHORIZED_NOT_RUN
hosted_metric_claim: NOT_AUTHORIZED_NOT_CLAIMED
```

Even if M9 metrics improve, executor may only write `M9_REPAIRED_CANDIDATE_READY_FOR_REVIEW`. The reviewer and GPT decide any future M10.

### 7. Strict validator and known-bad cases

Implement strict validator:

```text
scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py
```

The validator must fail closed on at least these known-bad mutations:

1. missing M8 follow-up review token;
2. missing R2/BR2-to-SRR mapping;
3. loss config weights recorded but not used in loss/gradient;
4. formal candidate uses anchor-owned final logits by default;
5. `[fused, fused, fused]` pseudo-modality dictionary appears in formal candidate path;
6. invalid missing-modality private/interaction slot has nonzero usage;
7. pattern-SIP is replaced by uniform entropy/coverage only;
8. deterministic prototype fallback used for a formal candidate;
9. no-T2 myocardium enters edema negative prototypes or hard-negative replay;
10. checkpoint best is selected only by patch loss;
11. same-split nnU-Net anchor comparison missing;
12. hard subgroup metrics missing CenterB/CenterC/T2-present/edema-positive/no-T2 safety where present;
13. refiner has no final-logit/final-label effect but is claimed implemented;
14. monitor/pending Slurm job is marked ready;
15. validation packaging/upload/hosted claim is created or claimed;
16. Cine frame0-only/descriptor-only/untrained VoxelMorph is marked ready;
17. required output missing;
18. validator self-test known-bad mutation passes.

The self-test report must include at least one good fixture and all known-bad mutations. If any known-bad mutation passes, completion is `M9_NEEDS_REVISION_VALIDATOR_NOT_FAIL_CLOSED`.

### 8. Allowed executor completion states

```text
M9_REPAIRED_CANDIDATE_READY_FOR_REVIEW
M9_NO_REPAIRED_CANDIDATE_READY_FOR_REVIEW
M9_NEEDS_REVISION_FIDELITY_REPAIR_FAILED
M9_NEEDS_EVIDENCE_MISSING_INPUTS
M9_NEEDS_MONITOR
M9_RESOURCE_BLOCKED
M9_BLOCKED_MISSING_M8_FOLLOWUP_REVIEW
M9_BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE
```

`M9_REPAIRED_CANDIDATE_READY_FOR_REVIEW` requires all fidelity repairs, tests, training, aggregation, metrics, validator, and self-tests to pass. It does not authorize route promotion.

`M9_NO_REPAIRED_CANDIDATE_READY_FOR_REVIEW` is allowed only if fidelity repairs pass and real training/evaluation completes, but metrics do not support a candidate. It is not scientific stop.

### 9. Git and artifact policy

Commit only lightweight Markdown/CSV/JSON result files, tests, first-party source, evaluation helpers, and Slurm entrypoints. Do not commit checkpoints, predictions, NIfTI files, upload zips, raw data, large logs, secrets, or full runtime trees.

Recommended local commit command:

```bash
git add -f \
  src/care_myocardium/models/srr_blocks.py \
  src/care_myocardium/models/srr_propref.py \
  src/care_myocardium/models/proposal_prototypes.py \
  src/care_myocardium/losses/srr_losses.py \
  scripts/training/run_srr_propref_myops_fold0.py \
  scripts/evaluation/export_srr_v3_m9_dictionary_fidelity_eval.py \
  scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py \
  scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py \
  jobs/src/run_srr_v3_m9_dictionary_fidelity_htzhulab.sh \
  jobs/src/run_srr_v3_m9_dictionary_fidelity.sh \
  tests/test_srr_m9_loss_weight_wiring.py \
  tests/test_srr_m9_dictionary_fidelity.py \
  tests/test_srr_m9_validator_fail_closed.py \
  results/20260708_srr_v3_m9_dictionary_fidelity_repair/*.md \
  results/20260708_srr_v3_m9_dictionary_fidelity_repair/*.csv \
  results/20260708_srr_v3_m9_dictionary_fidelity_repair/*.json
git commit -m "Add M9 SRR dictionary fidelity repair packet"
```

Do not push automatically.

## Reviewer Prompt

You are the separate read-only reviewer/auditor for M9 SRR dictionary fidelity repair.

Required protocol sentence: This is a separate read-only reviewer/auditor session. Do not fix code, do not generate missing artifacts, do not train, and do not start the next milestone. Review only the completed result directory, write `review.md` with the controlled milestone decision, then force-add/commit `review.md`. Do not push automatically.

### 1. Review scope

Review only:

```text
prompts/shared/M9_srr_dictionary_fidelity_repair.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair/
src/care_myocardium/models/srr_blocks.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/proposal_prototypes.py
src/care_myocardium/losses/srr_losses.py
scripts/training/run_srr_propref_myops_fold0.py
scripts/evaluation/export_srr_v3_m9_dictionary_fidelity_eval.py
scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py
scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py
jobs/src/run_srr_v3_m9_dictionary_fidelity_htzhulab.sh
jobs/src/run_srr_v3_m9_dictionary_fidelity.sh
tests/test_srr_m9_loss_weight_wiring.py
tests/test_srr_m9_dictionary_fidelity.py
tests/test_srr_m9_validator_fail_closed.py
```

You may read required protocol and prior evidence files:

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
README.md
prompts/CHATGPT_RULES.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
TODO.md
TODO-dictionary.md
docs/notes/20260620_r2_deep_research_assessment.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/review.md
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/review.md
```

### 2. Required checks

Check that the packet preserves the R2/BR2 idea: representer dictionary, modality-specific / interaction dictionaries, sparse or soft retrieval, integrativeness / SIP-style reuse, and blockwise missingness without imputation or zero-fill semantics.

Check that nnU-Net is not the primary final-logit generator for any M9 repaired candidate. If `final_logits = anchor_logits + delta` remains the default formal candidate, return `M9_AUDITED_NEEDS_REVISION`.

Check loss wiring. The reviewer must confirm that config loss weights change total loss and gradients through tests, not just logs. If M9 still records loss weights without passing them into expanded loss, return `M9_AUDITED_NEEDS_REVISION`.

Check dictionary fidelity. Formal candidates must not use `[fused, fused, fused]` pseudo-modality dictionary input. Private/interaction slots must consume real per-modality features and respect availability masks.

Check pattern-SIP. It must be pattern-conditioned and slot-type-aware. Uniform entropy/coverage alone is insufficient.

Check prototype memory. Formal candidates must not use deterministic axis prototypes. Prototype/memory summary must report source, case count, positive/negative counts, T2-present edema counts, hard-negative counts, no-T2 edema-negative exclusion, and whether prototypes are fixed, learnable, or EMA.

Check refiner causal effect. The packet must show whether proposal/refiner changes final logits/final labels and whether those changes help or harm scar/edema and hard subgroups.

Check checkpoint selection. Best checkpoint must not be chosen by patch loss only. It must use same-split metric/hard-subgroup evidence.

Check training adequacy. If the packet claims repaired candidate readiness, it must include real training comparable to M8: aggregate at least 28800 train-loop seconds, at least two formal trained variants, at least 20 validation events per formal variant, post-job aggregation, and same-split metrics. Pending jobs or monitor packets are not completion.

Check no-T2 safety. No-T2 myocardium may not be used as edema negative prototype/replay, and selected candidates must report zero no-T2 edema voxels unless explicitly diagnostic-only and not selected.

Check Cine boundary. CineMA/registration may be reported as diagnostic/anatomy proxy only unless there is multi-case temporal evidence and final Cine output effect. Do not accept frame0-only, descriptor-only, single-case SyN smoke, or untrained VoxelMorph as ready.

Check artifact policy. No checkpoints, predictions, NIfTI files, upload packages, raw data, large logs, secrets, or full runtime trees should be committed.

### 3. Review decisions

Write:

```text
results/20260708_srr_v3_m9_dictionary_fidelity_repair/review.md
```

with exactly one controlled decision:

```text
M9_AUDITED_REPAIRED_CANDIDATE_READY_FOR_GPT_M10_PLANNING
M9_AUDITED_NO_REPAIRED_CANDIDATE_SCIENTIFIC_UNRESOLVED
M9_AUDITED_NEEDS_EVIDENCE
M9_AUDITED_NEEDS_REVISION
M9_AUDITED_NEEDS_MONITOR
M9_AUDITED_PROTOCOL_BLOCKED
```

`M9_AUDITED_REPAIRED_CANDIDATE_READY_FOR_GPT_M10_PLANNING` means only that GPT may plan M10 from the reviewed candidate. It does not authorize route promotion, fold expansion, validation packaging, upload, hosted metric claims, leaderboard claims, scientific stop, or automatic M10 execution.

Use `M9_AUDITED_NO_REPAIRED_CANDIDATE_SCIENTIFIC_UNRESOLVED` only if fidelity repairs, tests, training, aggregation, and metrics are complete but no candidate improves enough to justify a next implementation. This is not scientific stop.

Use `M9_AUDITED_NEEDS_EVIDENCE` if required output files, runtime aggregation, metric tables, or provenance are missing.

Use `M9_AUDITED_NEEDS_REVISION` if loss wiring, dictionary fidelity, SRR-main final output, prototype/memory, pattern-SIP, checkpoint selection, no-T2 safety, refiner causality, validator, or tests are broken.

Use `M9_AUDITED_NEEDS_MONITOR` if Slurm jobs are submitted/pending/running/awaiting accounting or runtime output has not been aggregated.

Use `M9_AUDITED_PROTOCOL_BLOCKED` if the executor writes its own review, starts M10, packages validation, uploads, claims hosted metrics, or claims route promotion.

### 4. Commit policy

Commit only the review file:

```bash
git add -f results/20260708_srr_v3_m9_dictionary_fidelity_repair/review.md
git commit -m "Add M9 SRR dictionary fidelity repair review"
```

Do not push automatically.
