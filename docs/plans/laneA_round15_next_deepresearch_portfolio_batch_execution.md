# Lane A Round15 Next DeepResearch Portfolio Batch Execution Plan

Plan metadata:

- Type: next execution controller
- Lane: Lane A / MyoPS scar-edema
- Round scope: Round15
- Status: planned, not executed
- Parent roadmap: `TODO.md`, `README.md`, Lane A Round2-Round14 evidence chain
- Parent plan: `docs/plans/laneA_round14_next_feature_augmented_component_aware_edema_calibrator_execution.md`
- Function: controller document for a future goal-mode run that evaluates DeepResearch-guided high-upside mechanisms through staged, gated, compliance-checked portfolio execution
- Do not: execute experiments during this planning pass, train, submit Slurm, download weights, clone external repos, create validation zip, upload, modify production code, or overwrite existing predictions/results

## 1. Current Evidence Chain And Strategic Decision

Lane A has exhausted the shallow local-tweak routes for `myops_edema`. Round15 is the first controlled portfolio stage: multiple candidates may be prepared and, after gates pass, a batch of independent fold0 very-short jobs may be submitted. This is not a license to run an uncontrolled repo race. Every candidate must be staged, comparable, compliance-checked, cache-isolated, and evaluated against the same nnU-Net501 fold0 reference.

Evidence chain:

- Round2: edema inference postprocess route failed. Small-component and ROI deletion reduced component count but did not cleanly improve GT-positive edema Dice/HD95, so this is not a mainline.
- Round3: loss wiring, gradient smoke, and tiny-overfit could run, but that only proved engineering feasibility.
- Round4: `edema_focal_tversky + no_t2_edema_loss_downweighting` failed in real fold0 short training because remote FP, no-T2 FP, HD95, and scar guardrail were not clean.
- Round5: alignment was `watch`, boundary/distance was `watch`, and anatomy soft prior advanced to bounded diagnostic.
- Round6: anatomy soft attenuation failed. The missing-modality audit showed no-T2 empty-GT cannot be treated as a strong class-4 negative; explicit modality presence and uncertainty-aware supervision remained useful signals.
- Round7: the first-party 6-channel modality-presence pipeline was engineering-feasible, but simple presence channels plus scalar no-T2 weighting failed the tiny gate.
- Round8: T2-present edema expert / separated edema supervision had a tiny-gate signal, but scratch or near-scratch very-short fold0 training collapsed.
- Round9: nnU-Net501 checkpoint migration to a 6-channel model worked and initial logits could match baseline, but whole-network checkpoint fine-tuning had weak edema signal and unclean component/HD95/scar guardrails.
- Round10: add-only edema residual refiner was safer than whole-network tuning, with scar unchanged and no-T2 clean, but gains were tiny and HD95/component were not clean.
- Round11: component-safe bidirectional refiner still failed: scar unchanged and no-T2 clean, but CenterC, remote FP, and component guardrails were not clean.
- Round12: deployable fallback salvage could only be optional calibration, not a mainline.
- Round13: T2/LGE intensity prior and anatomy-lesion consistency had weak signal, but feature-only rules were not enough.
- Round14: feature-calibrator engineering chain ran; component logistic and voxel/patch tiny smoke could learn, but there was no clean CenterC/T2-present improvement beyond `strict_support_filter`. Ordinary CARE-first refiner/calibrator training should not continue as the main route.

Current strategic conclusion:

Lane A should not continue ordinary refiner/calibrator small fixes, add epochs, expand fold1-4, submit validation, or return to Focal Tversky, small-component deletion, hard ROI, anatomy attenuation, or whole-network fine-tuning. The next stage should use DeepResearch as a mechanism source to run a controlled portfolio. The goal is to quickly identify whether any high-upside mechanism has a real CARE signal, and whether Round16 needs a narrower deep-research pass focused on the best mechanism slot.

Resource stance:

User token, Slurm, and GPU resources are sufficient for aggressive goal-mode progress. Round15 may create a candidate registry, run compliance/metadata audits, execute one-case smoke tests, generate multiple fold0 very-short jobs, submit a batch after gates pass, collect results, and submit promoted fold0 short jobs. It must not skip gates. Failure of a candidate stops that candidate. Fold1-4, 5-fold, validation zip, and upload remain forbidden unless fold0 candidates are clean and the user separately authorizes expansion.

## 2. Scope, Output Root, And Non-Negotiable Rules

All Round15 outputs should be isolated under:

```text
results/diagnostics/care_myocardium/laneA_myops/round15_deepresearch_portfolio/
```

Recommended output files:

- `round15_goal_execution_readme.md`
- `round15_candidate_registry.csv`
- `round15_candidate_registry.md`
- `round15_compliance_metadata_matrix.csv`
- `round15_compliance_metadata_matrix.md`
- `round15_batch_job_matrix.csv`
- `round15_batch_job_matrix.md`
- `round15_onecase_smoke_summary.csv`
- `round15_onecase_smoke_summary.md`
- `round15_train_configs/`
- `round15_job_scripts_manifest.csv`
- `round15_submitted_jobs_manifest.csv`
- `round15_fold0_very_short_metrics.csv`
- `round15_fold0_short_metrics.csv`
- `round15_candidate_result_collection.csv`
- `baseline_vs_candidate_by_subset.csv`
- `centerB_centerC_edema_table.csv`
- `no_t2_empty_gt_fp_table.csv`
- `scar_guardrail_table.csv`
- `component_remote_fp_table.csv`
- `case2031_3011_3012_3040_table.csv`
- `case_level_failure_flags.csv`
- `round15_decision_table.md`
- `round15_round16_recommendation.md`
- `round15_deep_research_need_assessment.md`

If overlays or feature visualizations are generated, put them under:

```text
results/diagnostics/care_myocardium/laneA_myops/round15_deepresearch_portfolio/overlays/
```

Non-negotiable rules:

- No external image/label data may be mixed into CARE training. Public pretrained weights are only potentially allowed after license, pretrained-data, and challenge-compliance review.
- No validation pseudo-label supervised training.
- No fold1-4 or 5-fold unless fold0 candidates pass and the user explicitly authorizes expansion.
- No validation zip or upload.
- No foreground mean as a success standard.
- All candidates must compare against the same nnU-Net501 fold0 reference and report `myops_edema` class_4 and `myops_scar` class_5 separately.
- Scar class_5 must be a hard guardrail for any edema-specific route.
- no-T2 empty-GT cases must not be treated as strong dense edema negatives.
- Every candidate needs an isolated experiment name, output directory, config, seed, and job name.

## 3. Portfolio Hypothesis Table

| mechanism slot | priority | hypothesis | expected benefit for CARE | risks | implementation mode | external repo needed | pretrained weights needed | batch job allowed | fail-fast standard |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `I_MMSeg_style_T2_LGE_intensity_prior_route` | highest | Stronger learnable T2/LGE intensity prior can separate true edema support from CenterC weak/remote activation better than Round13/14 fixed features. | Better T2-present and CenterC edema localization without damaging scar/no-T2 stability. | Full I-MMSeg CLIP/GPT pipeline may be too complex or noncompliant; intensity shortcut may overfit center. | Start CARE-first: intensity-prior feature head, support map, or lightweight image-feature module; external I-MMSeg only metadata/one-case first. | no for first-party; yes only for external smoke | no for first-party; unclear for external | yes after feature/shape gate | fail if CenterC/T2-present edema has no clean positive signal or if support features explain only all-case artifact. |
| `Cascaded_FSN_PTNet_anatomy_pathology_consistency_route` | high | Structured anatomy-pathology support can identify plausible edema without hard deletion or simple distance attenuation. | Reduce remote FP/component failures while keeping true T2-positive lesions. | Repeating Round6 hard/attenuation failure; over-pruning true lesions; anatomy GT/probability leakage. | Use baseline myocardium/LV/RV probabilities, distance maps, component support features, lesion-anatomy consistency loss, or two-stage pathology head. | no for first-party; yes only for external smoke | no | yes after one-case/cache gate | fail if it improves components by deleting true GT-positive edema or if CenterC Dice/HD95 worsens. |
| `Boundary_HD_InverseForm_surface_auxiliary_route` | medium | Small-weight boundary/surface/HD objective can reduce HD95/component outliers once support is safe. | Better HD95 and remote-edge control. | Recall-heavy or boundary-only loss can fragment lesions; may repeat Focal Tversky trade-off. | First-party small-weight surface/distance auxiliary; external InverseForm metadata/loss smoke only. | no for simple surface loss; yes for InverseForm smoke | no | yes, but only as auxiliary candidate | fail if Dice improves while HD95/component worsens, or if boundary loss dominates class_4 supervision. |
| `Missing_modality_representation_route` | medium-high | Modality-conditioned representation may solve no-T2 ambiguity and complete-validation mismatch better than scalar weighting. | Cleaner T2-present edema learning while keeping no-T2 empty-GT stable. | Complete-case teacher currently unreliable; distillation may encode center shortcuts; external repo complexity high. | First-party small MoE/modality-conditioned head first; UniME/AdaMM/CoPeDiT/MMPL-Seg metadata and one-case readiness before training. | not for first-party MoE; yes for external readiness | possibly, must audit | yes for first-party small model after gate; external training postponed | fail if no-T2 FP increases, scar guardrail worsens, or teacher reliability is insufficient. |
| `Pretrained_backbone_feature_route` | medium-high | Public pretrained cardiac/medical backbones may improve baseline representation for CenterC/T2 edema. | Better feature quality than scratch or nnU-Net-only adaptation. | External data compliance, license, channel/label mismatch, weight download cost, cache pollution. | Metadata audit, config compatibility, one-case feature extraction; fold0 smoke only after compliance. | maybe | maybe | no training until compliance passes | fail if pretrained data source violates rules, license is incompatible, or one-case shape/label mapping is unclear. |
| `CAA_Seg_SSA_alignment_route` | medium-low | Slice/sequence alignment may matter for CenterC cases if subtle mismatch was missed by coarse Round5 audit. | Could improve T2/LGE support consistency and edema localization. | Round5 did not show strong mismatch; alignment can introduce artifacts. | Metadata/one-case CenterC alignment audit; no full CAA-Seg reproduction initially. | not for CARE-only audit; yes for external smoke | no | metadata/one-case only unless strong evidence | fail if no mismatch evidence or alignment proxy does not correlate with failure cases. |

## 4. Round15 Batch Job Matrix

The future goal-mode run should materialize this matrix as `round15_batch_job_matrix.csv` before any Slurm submission. Names may be adjusted for exact script constraints, but they must remain recognizable and traceable.

| candidate id | mechanism slot | job type | initial implementation | expected output dir | can submit in first batch? | gate before job | pass signal | fail-fast |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `R15_A_intensity_prior_feature_head_fold0_vs` | `I_MMSeg_style_T2_LGE_intensity_prior_route` | fold0 very-short, then fold0 short if promoted | first-party feature head using T2/LGE support maps plus baseline probabilities | `round15_deepresearch_portfolio/R15_A_intensity_prior_feature_head_fold0_vs/` | yes, after one-case smoke | feature cache, import, one-batch forward/backward, scar unchanged, no-T2 policy checked | CenterC or T2-present GT-positive edema improves with HD95/component clean | no CenterC signal, no-T2 FP, scar regression, NaN/Inf |
| `R15_B_anatomy_pathology_cascade_fold0_vs` | `Cascaded_FSN_PTNet_anatomy_pathology_consistency_route` | fold0 very-short, then fold0 short if promoted | first-party anatomy probability/distance support + pathology head/cascade smoke | `round15_deepresearch_portfolio/R15_B_anatomy_pathology_cascade_fold0_vs/` | yes, after one-case smoke | anatomy maps located; label mapping unchanged; no hard deletion | remote FP/component improve without true-lesion loss | over-pruning, CenterC Dice/HD95 regression, scar regression |
| `R15_C_intensity_plus_anatomy_support_head_fold0_vs` | combined intensity + anatomy | fold0 very-short, then fold0 short if promoted | combine A and B support features with bounded edema-only head/calibrator | `round15_deepresearch_portfolio/R15_C_intensity_plus_anatomy_support_head_fold0_vs/` | yes only after A or B one-case is clean | both feature sources cache-isolated and one-batch passes | best chance for clean CenterC/T2-present gain | any support-feature shortcut or no-T2/HD95 regression |
| `R15_D_boundary_surface_auxiliary_fold0_vs` | `Boundary_HD_InverseForm_surface_auxiliary_route` | tiny-overfit or fold0 very-short auxiliary | baseline Dice/CE plus small-weight surface/distance auxiliary | `round15_deepresearch_portfolio/R15_D_boundary_surface_auxiliary_fold0_vs/` | yes after loss gradient smoke | loss finite, gradient bounded, class_5 interference zero or negligible | HD95/component improves without Dice/scar trade-off | Dice/HD95 trade-off, fragmented components, scar regression |
| `R15_E_modality_conditioned_moe_small_fold0_vs` | `Missing_modality_representation_route` | tiny-overfit then fold0 very-short | first-party small modality-conditioned head/MoE with explicit presence and no-T2 uncertainty policy | `round15_deepresearch_portfolio/R15_E_modality_conditioned_moe_small_fold0_vs/` | yes after tiny gate | no-T2 policy documented; one-batch gradient clean; cache isolated | T2-present edema signal with no-T2 stability | no-T2 FP, center shortcut, scar guardrail regression |
| `R15_F_pretrained_or_MedNeXt_readiness_smoke` | `Pretrained_backbone_feature_route` | metadata-only, config/shape smoke; no weight download unless separately approved | MedNeXt/nnU-Net Task114/M&Ms/BiomedParse readiness matrix | `round15_deepresearch_portfolio/R15_F_pretrained_or_MedNeXt_readiness_smoke/` | no training in first batch | license/pretrained-data/source/shape/channel audit | one candidate becomes eligible for future one-case smoke | unclear license, external training data conflict, incompatible I/O |
| `R15_G_external_I_MMSeg_metadata_onecase_smoke` | I-MMSeg external readiness | metadata-only or one-case smoke if source is locally available; no large clone by default | license, dependency, input-output, label mapping, one-case feature feasibility | `round15_deepresearch_portfolio/R15_G_external_I_MMSeg_metadata_onecase_smoke/` | no fold0 training | compliance and tiny compatibility only | identify reusable intensity-prior mechanism | requires external training data, opaque LLM dependency, no usable CARE I/O |
| `R15_H_external_CascadedFSN_or_PTNet_metadata_onecase_smoke` | anatomy external readiness | metadata-only or one-case smoke if feasible | map FSN/PT-Net anatomy prior into CARE soft support | `round15_deepresearch_portfolio/R15_H_external_CascadedFSN_or_PTNet_metadata_onecase_smoke/` | no fold0 training | compliance/shape/label mapping | reusable soft anatomy/pathology module | hard ROI dependence or incompatible labels |
| `R15_I_external_InverseForm_metadata_loss_smoke` | boundary/HD external readiness | metadata-only plus loss one-batch smoke if safe | inspect InverseForm/surface loss as plug-in auxiliary | `round15_deepresearch_portfolio/R15_I_external_InverseForm_metadata_loss_smoke/` | no fold0 training until loss gate | finite loss, finite gradients, class_4-only auxiliary scoped | HD-aware auxiliary is implementable | unstable gradients, broad class interference |
| `R15_J_CAA_Seg_SSA_metadata_centerC_smoke` | alignment watch | metadata/one-case CenterC alignment smoke | CARE-only slice/spacing/intensity alignment proxy; external CAA-Seg only if justified | `round15_deepresearch_portfolio/R15_J_CAA_Seg_SSA_metadata_centerC_smoke/` | no training | identify complete CenterC cases and alignment proxies | alignment mismatch correlates with failures | no mismatch evidence or preprocessing would alter labels/affines silently |

Batch submission policy:

- `metadata-only` and `one-case smoke` candidates must run first.
- Fold0 very-short jobs may be submitted as a batch only for candidates that passed import/shape/label/cache gates.
- Promoted fold0 short jobs may be submitted only after automatic result collection confirms a clean very-short signal.
- Every job needs a unique experiment name, output directory, config YAML, command text, seed, and Slurm job script/log manifest.
- Do not reuse or overwrite nnU-Net501 baseline, Round10/11 refiner, Round13, or Round14 outputs.

## 5. Candidate Compliance And Metadata Requirements

Before any external repo, pretrained asset, or borrowed module enters training, the future goal-mode run must write `round15_compliance_metadata_matrix.csv` with at least these columns:

- `candidate_id`
- `mechanism_slot`
- `candidate_name`
- `source_url_or_local_path`
- `role`
- `license`
- `license_status`
- `pretrained_weights_available`
- `pretrained_data_source`
- `external_data_training_required`
- `challenge_compliance_risk`
- `dependency_risk`
- `input_modalities_expected`
- `output_labels_expected`
- `CARE_label_mapping_plan`
- `channel_count_compatibility`
- `spacing_orientation_assumptions`
- `one_case_smoke_required`
- `eligible_for_fold0_training`
- `reason_if_rejected`

Compliance stance:

- External data training is disallowed.
- Public pretrained weights may be allowed only if the challenge rules and asset license permit them, and the pretrained data source is documented.
- Full I-MMSeg/AdaMM/UniME/CoPeDiT/BiomedParse-style integration is not allowed before metadata, license, I/O, label, one-case, and cache gates pass.
- If compliance is unclear, the candidate is `postpone`, not `go`.

## 6. Implementation Substrate To Reuse

Round15 should reuse first-party code where practical:

- `src/care_myocardium/refiner/` for baseline-preserving class-4-only modification patterns.
- `src/care_myocardium/calibrator/laneA_round14_model.py` for lightweight component/voxel calibrator patterns and scar-unchanged assertions.
- `src/care_myocardium/nnunet/` for Round7-Round9 modality presence and checkpoint-initialized experiments.
- `scripts/diagnostics/laneA_round13_t2_lge_intensity_anatomy_consistency.py` for T2/LGE and anatomy feature sources.
- `scripts/diagnostics/laneA_round14_feature_augmented_calibrator.py` for component/voxel dataset and evaluation scaffolding.
- Existing `jobs/nnUNet/laneA_round*.sh` style for htzhulab Slurm headers and log tee conventions.

Round15 may create new first-party scripts/configs/jobs in the future goal-mode execution, but this plan creation pass must not do so.

## 7. Stage 1: `round15_reproducibility_and_candidate_registry_gate`

Goal: establish a clean Round15 registry and verify all evidence inputs before candidate work.

Allowed:

- Read README/runbook, plans, Round10-Round14 outputs, baseline predictions/probabilities, raw modalities, GT, metadata, and existing scripts.
- Create Round15 output root, registry files, and command templates in the future goal-mode run.
- Identify missing files with `find docs results scripts src jobs -maxdepth 9 -type f | sort`.

Forbidden:

- Training, Slurm submission, external repo clone, weight download, validation zip, upload.
- Editing evaluator, label semantics, or baseline caches.

Required outputs:

- `round15_goal_execution_readme.md`
- `round15_candidate_registry.csv`
- `round15_candidate_registry.md`
- `round15_batch_job_matrix.csv`
- `round15_batch_job_matrix.md`

Pass standard:

- nnU-Net501 fold0 baseline reference, label mapping, fold split, center/modality metadata, Round14 decision, and current output roots are all located.
- Candidate registry has all required mechanism slots and candidate IDs.

Fail standard:

- Baseline reference or label semantics cannot be verified.
- Candidate IDs/output roots collide with previous rounds.
- Registry lacks compliance fields or subset metric requirements.

Next: proceed to Stage 2 only after reproducibility and registry pass.

## 8. Stage 2: `candidate_compliance_and_metadata_audit`

Goal: decide which external/pretrained candidates are allowed to enter compatibility smoke, and which first-party candidates can proceed without external assets.

Allowed:

- Metadata-level web/local-document review only when needed by the future goal-mode run.
- Inspect local docs/PDFs, local repo files, package metadata, and existing environment packages.
- Record source URL if discoverable from existing notes/local docs.

Forbidden:

- Large clone, weight download, external dataset download, training, or Slurm.
- Marking unclear license/pretrained data as acceptable.

Required outputs:

- `round15_compliance_metadata_matrix.csv`
- `round15_compliance_metadata_matrix.md`
- `round15_external_method_readiness_notes.md`

Pass standard:

- First-party A-E candidates are classified as no-external-data.
- External F-J candidates have clear `go/watch/postpone/reject` readiness labels.
- Any candidate requiring external training data is rejected or postponed.

Fail standard:

- License or pretrained data source is unclear but candidate is still marked eligible.
- External repo would require changing CARE label semantics or evaluator.

Next: only `go` or low-risk `watch` candidates proceed to Stage 3.

## 9. Stage 3: `candidate_import_and_onecase_smoke`

Goal: run import, shape, label, and one-case compatibility checks before any training.

Allowed:

- For first-party candidates: py_compile/import tests, one-case feature construction, one-batch forward/backward, finite loss/gradient checks, scar-unchanged assertion, no-T2 policy check.
- For external candidates: metadata-compatible one-case smoke only if code/assets are already available or explicitly permitted later.
- Write small diagnostic outputs.

Forbidden:

- Fold0 training, Slurm batch jobs, full external repo builds, external data, downloaded weights unless separately approved.

Required outputs:

- `round15_onecase_smoke_summary.csv`
- `round15_onecase_smoke_summary.md`
- Candidate-specific smoke outputs under each candidate directory.

Pass standard:

- Input shapes, channel counts, label mapping, spacing/orientation assumptions, loss gradients, and output label semantics are clean.
- Candidate can write predictions/probabilities into an isolated output dir.

Fail standard:

- NaN/Inf, silent label remap, scar class changes when not intended, no-T2 dense hard negative, cache collision, or unbounded class_4 changes.

Next: Stage 4 can batch-submit fold0 very-short jobs only for candidates that pass Stage 3.

## 10. Stage 4: `first_batch_fold0_very_short_jobs`

Goal: submit a controlled batch of independent fold0 very-short jobs for eligible high-priority candidates.

Allowed:

- Generate first-party configs and Slurm scripts for `R15_A`, `R15_B`, `R15_C`, `R15_D`, and `R15_E` if their gates pass.
- Submit multiple fold0 very-short htzhulab jobs if they are independent, cache-isolated, and have passed Stage 3.
- Keep walltime <= 8 hours per job; prefer much shorter very-short budgets.

Forbidden:

- Fold1-4, 5-fold, validation zip, upload, full schedule, overwriting baseline caches.
- Submitting external repo training jobs before metadata/one-case gates and explicit eligibility.

Required outputs:

- `round15_train_configs/`
- `round15_job_scripts_manifest.csv`
- `round15_submitted_jobs_manifest.csv`
- Per-candidate `train_config.yaml`, `train_command.txt`, and logs.

Pass standard:

- Jobs complete or fail cleanly with logs.
- Predictions are non-empty and evaluable.
- No candidate changes scar unexpectedly or introduces no-T2 edema FP beyond strict thresholds.

Fail standard:

- Job writes into baseline or previous-round outputs.
- Label/evaluator/cache changes silently.
- NaN/Inf, empty predictions, failed export, or resource runaway.

Next: completed candidates proceed to Stage 5 result collection.

## 11. Stage 5: `automatic_result_collection_and_gate`

Goal: evaluate all completed very-short candidates in a single comparable table.

Allowed:

- Run unified local evaluation on fold0 validation cases.
- Aggregate by all-case, T2-present, T2-present GT-positive, complete-modality, CenterB, CenterC, no-T2 empty-GT, C0+LGE no-T2, LGE-only, and center groups.
- Generate overlays for failure cases and top improvements.

Forbidden:

- Using foreground mean as success.
- Ignoring scar class_5 guardrail.
- Selecting candidates based only on all-case aggregate or empty-GT artifact.

Required outputs:

- `round15_fold0_very_short_metrics.csv`
- `round15_candidate_result_collection.csv`
- `baseline_vs_candidate_by_subset.csv`
- `centerB_centerC_edema_table.csv`
- `no_t2_empty_gt_fp_table.csv`
- `scar_guardrail_table.csv`
- `component_remote_fp_table.csv`
- `case2031_3011_3012_3040_table.csv`
- `case_level_failure_flags.csv`

Pass standard:

- A candidate shows a clean positive signal in T2-present GT-positive edema or CenterC complete-case edema.
- Dice and HD95 do not trade off severely.
- Component count and remote FP do not worsen.
- scar class_5 Dice/HD95 are unchanged or not meaningfully worse.
- no-T2 empty-GT edema FP is unchanged or within a predeclared negligible limit.

Fail standard:

- HD95/component/remote FP worsens.
- CenterC does not improve or gets worse.
- Scar guardrail is not clean.
- Gains are due to empty-GT cases or all-case artifacts.
- Candidate is not better than strict_support_filter on safety and not better than baseline on the target subset.

Next: only promoted candidates proceed to Stage 6.

## 12. Stage 6: `promoted_fold0_short_jobs`

Goal: run fold0 short jobs only for candidates that passed very-short gates.

Allowed:

- Submit multiple promoted fold0 short htzhulab jobs, each with its own config, output dir, seed, and Slurm script.
- Use the same evaluation protocol and subset tables as Stage 5.
- Continue only candidates with clean evidence.

Forbidden:

- Fold1-4, 5-fold, validation package, hosted upload, full schedules, or new unregistered mechanisms.
- Continuing a failed candidate because resources are available.

Required outputs:

- `round15_fold0_short_metrics.csv`
- Updated `baseline_vs_candidate_by_subset.csv`
- Updated `case_level_failure_flags.csv`
- Candidate-specific summaries.

Pass standard:

- The short run confirms or strengthens the very-short signal in T2-present GT-positive edema or CenterC complete cases.
- HD95/component/remote FP and scar/no-T2 guardrails remain clean.

Fail standard:

- Signal disappears, becomes all-case-only, or guardrails regress.
- Candidate requires case-specific/oracle fallback.

Next: Stage 7 recommendation; no fold expansion without separate user authorization.

## 13. Stage 7: `round16_recommendation_and_deep_research_need_assessment`

Goal: decide whether Round16 should narrow around a successful mechanism, run a targeted deep-research pass, or stop a route.

Allowed:

- Write final decision, mechanism ranking, and next-step prompt.
- Recommend further deep research only if evidence is insufficient or all high-upside candidates fail.

Forbidden:

- Validation zip/upload.
- Fold1-4 or 5-fold without user authorization.
- Broad external repo integration without candidate-specific evidence.

Required outputs:

- `round15_decision_table.md`
- `round15_round16_recommendation.md`
- `round15_deep_research_need_assessment.md`

Decision logic:

- `promote`: candidate improves T2-present GT-positive or CenterC edema with clean HD95/component/remote FP/scar/no-T2 guardrails; eligible for a future user-authorized fold0 longer or fold expansion plan.
- `watch`: candidate has a mechanism signal but not enough local metrics; refine with targeted audit or one more bounded fold0 job.
- `postpone`: compliance, dependency, teacher reliability, or external data uncertainty blocks execution.
- `stop`: candidate repeats known failures or does not beat strict_support_filter/baseline on relevant subsets.

If all high-upside candidates fail:

- Start a narrower Round16 deep-research task focused on CenterC/T2 edema representation, T2 intensity prior reliability, edema label ambiguity, and missing-modality supervision.
- Do not run another generic repo sweep.

## 14. Required Metrics And Gates

Every trainable or prediction-producing candidate must report:

- `myops_edema` class_4 Dice, HD, HD95, component count, remote FP count, small FP count, pred voxels, GT voxels, pred/GT volume ratio.
- `myops_scar` class_5 Dice, HD, HD95, changed scar voxels, and guardrail flags.
- no-T2 edema FP voxel count and case count.
- component-level changed/added/removed voxels when using calibrator/refiner-style outputs.
- case-level failure flags.

Required subsets:

- all-case
- T2-present
- T2-present GT-positive
- complete-modality C0+LGE+T2
- CenterB
- CenterC
- no-T2 empty-GT
- C0+LGE without T2
- LGE-only
- center groups

Promotion requires:

- clean positive signal in T2-present GT-positive edema or CenterC complete-case edema;
- Dice and HD95 not showing a severe one-good-one-bad trade-off;
- component count and remote FP not worse;
- no-T2 empty-GT edema FP unchanged or within a predeclared negligible bound;
- class_5 scar guardrail clean;
- no empty-GT artifact or foreground-mean-only success.

Immediate fail:

- NaN/Inf, label/evaluator/cache silent change, external data training, validation pseudo-label supervised training, scar regression, no-T2 FP increase, CenterC regression, HD95/component/remote FP worsening, or unbounded class_4 edits.

## 15. Candidate-Specific Notes

### 15.1 `I_MMSeg_style_T2_LGE_intensity_prior_route`

First-party start:

- Use CARE raw LGE/T2/C0, modality metadata, baseline probabilities, and Round13/Round14 feature code.
- Build stronger intensity-prior feature maps and a feature head, not the full CLIP/GPT pipeline.
- Compare GT edema, baseline FP/FN/TP, Round11/14 remote activation, and no-T2 empty-GT cases.

External I-MMSeg readiness:

- Metadata and one-case smoke only.
- Reject/postpone if it requires external image-label data, an opaque LLM dependency, incompatible license, or unclear pretrained data.

### 15.2 `Cascaded_FSN_PTNet_anatomy_pathology_consistency_route`

First-party start:

- Use baseline myocardium/LV/RV probabilities, distance maps, component support features, and soft lesion-anatomy consistency.
- Avoid hard deletion and simple distance attenuation.
- Treat anatomy as support/regularizer, not as an oracle mask.

External FSN/PT-Net readiness:

- Metadata and one-case smoke only.
- Confirm labels and input-output shapes match CARE compact/raw mappings.

### 15.3 `Boundary_HD_InverseForm_surface_auxiliary_route`

First-party start:

- Small-weight surface/distance auxiliary only after support features are safe.
- Run loss/gradient smoke before fold0 very-short.
- Scope auxiliary to class_4 edema where possible and monitor class_5 interference.

External InverseForm readiness:

- Metadata/loss smoke only.
- Do not integrate a broad boundary objective if gradients are unstable or class interference appears.

### 15.4 `Missing_modality_representation_route`

First-party start:

- Small modality-conditioned head/MoE, explicit modality presence, no-T2 uncertainty-aware policy.
- no-T2 empty-GT remains weak calibration/stability signal, not dense hard negative.

External AdaMM/UniME/CoPeDiT/MMPL-Seg readiness:

- Metadata, license, pretrained data, teacher reliability, and one-case I/O first.
- Complete-case teacher reliability is a known blocker; do not start full distillation until it is resolved.

### 15.5 `Pretrained_backbone_feature_route`

Candidates:

- MedNeXt or equivalent cardiac backbone.
- nnU-Net Task114/M&Ms weights.
- BiomedParse or other foundation segmentation backbone.

Rules:

- No weight download during planning.
- In goal-mode, only download/use weights if license, pretrained data, challenge compliance, and user authorization are clean.
- First goal-mode step is readiness/shape smoke, not fold0 training.

### 15.6 `CAA_Seg_SSA_alignment_route`

Status:

- Watch, not primary.

Allowed:

- CenterC-focused metadata/one-case alignment proxy if low cost.
- Promote only if slice/sequence mismatch correlates with failure cases.

Forbidden:

- Broad registration/alignment preprocessing that silently changes affines or labels.

## 16. Next Goal Execution Prompt Draft

```text
你现在在 `/overflow/htzhu/CARE` 中工作。请按
`docs/plans/laneA_round15_next_deepresearch_portfolio_batch_execution.md`
执行 Lane A Round15 DeepResearch-guided portfolio batch stage。

资源充足，可以尽可能推进，并且在 gate 通过后可以批量提交多个 fold0 very-short htzhulab jobs；但必须 staged、gated、compliance-checked、cache-isolated、baseline-comparable。不要跳过任何 gate。

本轮目标：
1. 建立 Round15 candidate registry、compliance metadata matrix、batch job matrix。
2. 对 Deep Research 候选机制做 metadata/license/pretrained-data/external-data/input-output/label-mapping audit。
3. 对通过 metadata 的候选做 import/one-case/shape/label/cache/gradient smoke。
4. 对通过 gate 的 first-party 候选生成并可提交一批 fold0 very-short Slurm jobs。
5. 自动收集结果，统一评估 `myops_edema` class_4 和 `myops_scar` class_5，并按 all-case、T2-present GT-positive、complete-modality、CenterB、CenterC、no-T2 empty-GT、modality group 和 center subsets 报告 Dice、HD、HD95、component count、remote FP、small FP、pred/GT volume ratio。
6. 只对通过 very-short gate 的候选继续 fold0 short jobs。
7. 输出 `round15_decision_table.md`、`round15_round16_recommendation.md` 和 `round15_deep_research_need_assessment.md`。

候选至少包括：
- `R15_A_intensity_prior_feature_head_fold0_vs`
- `R15_B_anatomy_pathology_cascade_fold0_vs`
- `R15_C_intensity_plus_anatomy_support_head_fold0_vs`
- `R15_D_boundary_surface_auxiliary_fold0_vs`
- `R15_E_modality_conditioned_moe_small_fold0_vs`
- `R15_F_pretrained_or_MedNeXt_readiness_smoke`
- `R15_G_external_I_MMSeg_metadata_onecase_smoke`
- `R15_H_external_CascadedFSN_or_PTNet_metadata_onecase_smoke`
- `R15_I_external_InverseForm_metadata_loss_smoke`
- `R15_J_CAA_Seg_SSA_metadata_centerC_smoke`

禁止：
- validation zip、upload、fold1-4、5-fold，除非 fold0 candidates clean 且我另行授权。
- external image/label data training。
- validation pseudo-label supervised training。
- 无差别 clone/train 所有外部 repo。
- 下载大权重，除非合规矩阵通过且我另行授权。
- 改 label semantics、改 evaluator、污染 nnU-Net501 baseline cache。
- 用 foreground mean 或 all-case aggregate 掩盖 `myops_edema` / `myops_scar` 单项失败。

如果某候选在任一 gate 失败，请停止该候选并记录原因，不要因为资源充足自动扩大训练。最终给出每个 candidate 的 `promote/watch/postpone/stop` 结论。
```
