# Lane A Round16 Next External Mechanism Integration Large-Smoke Execution Plan

Plan metadata:
- Type: `next/planned round execution`
- Lane: `Lane A`
- Round scope: `Round16`
- Status: `next`
- Parent roadmap: `TODO.md`
- Parent plan: `docs/plans/laneA_round15_next_deepresearch_portfolio_batch_execution.md`
- Function: control DeepResearch-guided external mechanism integration and large fold0-bounded smoke execution for Lane A MyoPS edema.
- Do not: run experiments, train, submit Slurm, download weights, clone external repositories, create validation zips, upload, modify production code, or expand to fold1-4/5-fold during this planning pass.
- Topic: `external_mechanism_integration_large_smoke`
- Registry: `docs/plans/care_myocardium_plan_registry_rules.md`
- Primary results root: `results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/`
- Path policy: use the current cleaned diagnostics root under `results/diagnostics/care_myocardium/`; do not recreate legacy phase-style diagnostics paths.

Execution authorization update:
- 2026-05-23: user explicitly authorized continuing Round16 execution and submitting bounded Slurm jobs after the plan-only pass.
- Authorized Slurm scope: only the four first-party candidates that passed metadata/unit/tiny gates (`R16_A`, `R16_C`, `R16_E`, `R16_F`) may be submitted as fold0 very-short jobs through `jobs/nnUNet/laneA_round16_external_mechanism_fold0_very_short.sh`.
- Still forbidden without separate user authorization: validation zip creation, upload/submission, fold1-4, 5-fold, full training, large-weight download, broad external repo training, or promoting failed candidates past gates.

## Strategic Decision

Lane A should now move from CARE-first local refiner/calibrator tweaks into a DeepResearch-guided external mechanism integration stage, but only through staged, compliance-checked, fold0-bounded large smoke experiments.

Round15 showed that ordinary CARE-first feature calibrators and local refiner variants are not producing a clean CenterC / T2-present edema improvement. The next useful step is not another small threshold, epoch, or scalar-weight tweak. The next useful step is a controlled portfolio that tests higher-upside mechanisms while preserving the hard lessons from Rounds 2-15:

- nnU-Net501 remains the conservative MyoPS baseline and fallback.
- `myops_edema` class 4 is the target bottleneck.
- `myops_scar` class 5 remains a hard guardrail.
- no-T2 empty-GT cases cannot be treated as reliable dense class_4 negative labels.
- CenterC complete-modality edema remains the most important failure zone.
- HD/HD95, component count, remote FP, and case-level failure flags must be reported with Dice.
- No validation submission is allowed until a candidate beats the fold0 reference cleanly on the required subsets.

## Evidence Chain Through Round15

| Round | Conclusion | Status for Round16 |
|---|---|---|
| Round2 | Edema inference postprocess route failed. Small component / ROI deletion reduced components but did not cleanly improve GT-positive Dice/HD95. | Stop as mainline. |
| Round3 | Loss wiring, gradient smoke, and tiny-overfit wiring can run. | Engineering evidence only, not performance evidence. |
| Round4 | `edema_focal_tversky + no_t2_edema_loss_downweighting` failed in real fold0 short train: remote FP, no-T2 FP, HD95 and scar guardrail were not clean. | Stop recall-heavy Focal Tversky / simple no-T2 downweighting. |
| Round5 | Alignment was watch, boundary/distance was watch, anatomy soft prior merited bounded diagnostic. | Keep as mechanism slots, not standalone fixes. |
| Round6 | Anatomy soft attenuation failed, including oracle-style distance support. Missing-modality audit showed no-T2 empty-GT cannot be strong negative; modality presence and uncertainty-aware supervision remain relevant. | Stop simple anatomy attenuation and hard ROI deletion. |
| Round7 | First-party 6-channel modality-presence pipeline worked, but simple presence channels plus scalar no-T2 weighting failed tiny gate. | Reuse channel engineering only if needed. |
| Round8 | T2-present separated edema supervision had tiny signal, but scratch / near-scratch fold0 very-short training collapsed against baseline. | Do not train structural changes from scratch as the main route. |
| Round9 | nnU-Net501 checkpoint migration to 6-channel model worked with baseline-identical initial logits, but whole-network fine-tune had weak edema signal and unclean component/HD95/scar guardrails. | Stop whole-network fine-tune. |
| Round10 | Add-only edema residual refiner was safer than whole-network tuning: scar unchanged and no-T2 clean, but only tiny Dice gain and unclean HD95/component behavior. | Refiner safety useful, effectiveness weak. |
| Round11 | Component-safe bidirectional refiner still failed; scar unchanged and no-T2 clean, but CenterC / remote FP / component guardrails were not clean. | Stop bidirectional refiner as mainline. |
| Round12 | Deployable fallback salvage could only be optional calibration, not a mainline solution. | Refiner becomes auxiliary substrate. |
| Round13 | T2/LGE intensity prior and anatomy-lesion consistency had weak signal; feature-only rules were insufficient. | Mechanism evidence exists but needs stronger representation. |
| Round14 | Feature-calibrator engineering ran, component logistic and voxel/patch tiny smoke learned, but no clean CenterC/T2-present improvement beyond strict safety filter. | Ordinary CARE-first calibrator is not enough. |
| Round15 | DeepResearch portfolio first batch did not promote a candidate. A had tiny edema signal but CenterC component safety failed; B/C effectively fell back to baseline. | Enter stronger external mechanism integration with compliance and fold0 gates. |

Round15 failure should be interpreted narrowly: the first-party A/B/C candidates reached fold0 very-short evaluation and produced 44/44 validation predictions; the stop decision was not caused by NaN/Inf, missing predictions, scar regression, no-T2 FP explosion, label/evaluator/cache corruption, or Slurm failure. It was caused by insufficient lesion-level / representation-level edema support: `R15_A` had a weak intensity-prior signal but CenterC component safety failed, while `R15_B` and `R15_C` behaved like baseline fallback without clean T2-present or CenterC gain.

## Current Stop List

Do not continue these routes as Lane A mainline:

- Small component deletion / ROI threshold postprocess.
- Hard ROI deletion or hard anatomy pruning.
- Recall-heavy Focal Tversky as the main edema fix.
- Simple no-T2 scalar masking/downweighting around Round7 U1/U2.
- Simple anatomy distance attenuation.
- Scratch / near-scratch separated edema expert training.
- Whole-network checkpoint-initialized fine-tune.
- Ordinary add-only or bidirectional residual refiner training.
- Ordinary feature-only fixed rule or weak CARE-first calibrator tweaks.
- Validation package creation or upload for any Lane A candidate that has not passed fold0 gates.

## Round16 Objective

Round16 should answer:

1. Does a stronger T2/LGE intensity-prior mechanism create a clean edema signal on T2-present and CenterC cases?
2. Does a structured anatomy-pathology consistency mechanism help distinguish true edema support from remote / edge activation?
3. Can boundary/HD objectives reduce HD95/component failures without becoming another recall-heavy loss?
4. Is missing-modality representation worth escalating beyond first-party modality channels?
5. Which external methods are license/compliance/I/O compatible enough for one-case smoke and later fold0 smoke?

The goal is not to reproduce every DeepResearch repository. The goal is to map each method into a CARE mechanism slot, pass compliance and shape gates, then run comparable fold0-bounded experiments only where justified.

## Output Root And Required Files

All Round16 outputs must live under:

`results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/`

Recommended output files:

- `round16_goal_execution_readme.md`
- `round16_candidate_registry.csv`
- `round16_large_smoke_candidate_matrix.csv`
- `round16_compliance_metadata_matrix.csv`
- `round16_compliance_matrix.csv`
- `round16_repo_metadata_audit.md`
- `round16_external_repo_readiness_matrix.md`
- `round16_external_import_smoke_summary.csv`
- `round16_onecase_smoke_summary.csv`
- `round16_onecase_smoke_results.csv`
- `round16_import_shape_label_smoke.md`
- `round16_batch_job_matrix.csv`
- `round16_batch_job_submission_plan.md`
- `round16_batch_job_status.csv`
- `round16_train_commands.txt`
- `round16_job_submission_manifest.csv`
- `round16_fold0_very_short_metrics.csv`
- `round16_fold0_very_short_results.csv`
- `round16_fold0_short_metrics.csv`
- `round16_fold0_short_results.csv`
- `round16_baseline_vs_candidate_by_subset.csv`
- `round16_centerC_edema_table.csv`
- `round16_no_t2_empty_gt_fp_table.csv`
- `round16_scar_guardrail_table.csv`
- `round16_component_remote_fp_table.csv`
- `round16_case_level_failure_flags.csv`
- `round16_candidate_decision_table.md`
- `round16_decision_table.md`
- `round16_external_method_readiness_update.md`
- `round16_round17_recommendation.md`
- `round16_new_deep_research_need_assessment.md`
- `round16_deep_research_need_assessment.md`

If overlays or feature visualizations are generated later, put them under:

`results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/overlays/`

## Portfolio Hypothesis Table

| Mechanism slot | Priority | Expected benefit | Main risk | First-party implementation | External method use | Batch job permission | Fail-fast criterion |
|---|---:|---|---|---|---|---|---|
| `I_MMSeg_style_T2_LGE_intensity_prior_route` | P0 | Stronger edema support from T2/LGE intensity context; directly targets CenterC and weak T2 support failures. | Overfitting center-specific intensity, weak no-T2 handling, CLIP/GPT complexity if copied literally. | CARE-first intensity-prior feature head or lightweight support network from normalized T2/LGE features. | I-MMSeg only after metadata/import/one-case smoke. | Yes, after local smoke. | No CenterC/T2-positive signal or new remote/component failures. |
| `Cascaded_FSN_PTNet_anatomy_pathology_consistency_route` | P0/P1 | Structured lesion-anatomy support without hard deletion. | Repeating failed simple distance attenuation; deleting true lesions. | Two-stage anatomy/pathology head, anatomy probability/distance features, soft consistency penalty. | Cascaded FSN / PT-Net only after readiness gates. | Yes, after local smoke. | Hard-pruning behavior, scar regression, or no CenterC improvement. |
| `Boundary_HD_InverseForm_surface_auxiliary_route` | P1 | Reduce HD95, remote edge activation, and component split. | Boundary loss dominates recall or improves HD by over-pruning edema. | Small-weight surface/distance auxiliary or component penalty on top of baseline Dice/CE/support losses. | InverseForm/surface loss as loss-level smoke. | Yes only as auxiliary to P0/P1 candidates. | Dice/HD95 trade-off becomes severe, or component count worsens. |
| `Missing_modality_representation_route` | P1 | Addresses no-T2 supervision ambiguity and modality-conditioned representation. | Complete-case teacher unreliable; external data/pretraining risk; complex repo integration. | Small first-party modality-conditioned MoE/head or FiLM route. | UniME, AdaMM, CoPeDiT, MoE, MMPL-Seg metadata/one-case first. | Yes only for small first-party route; external routes need one-case pass. | no-T2 FP increases, or T2-positive signal absent. |
| `Pretrained_backbone_feature_route` | P1/P2 | Stronger representation for CenterC/T2 edema. | External data compliance and weight provenance. | MedNeXt-like first-party compatible smoke or feature extractor readiness. | MedNeXt, nnU-Net Task114/M&Ms, BiomedParse readiness only. | No fold0 train until compliance is clear. | License/weights/data source unclear or input-output mismatch. |
| `CAA_Seg_SSA_alignment_route` | P2/watch | Could help if CenterC failure is sequence mismatch. | Round5 did not show strong geometry mismatch; low expected immediate return. | CenterC-focused alignment feasibility check. | CAA-Seg/SSA metadata/one-case only. | Watch; not in largest batch. | No mismatch evidence or heavy integration required. |

## Round16 Mechanism Routes

### Main Route 1: `I_MMSeg_style_strong_intensity_prior_route`

Goal: turn the weak Round13-Round15 T2/LGE intensity signal into a stronger edema-support representation.

CARE-first layer:

- Build local T2/LGE patch features instead of only scalar support summaries.
- Use within-myocardium T2 ranking, robust z-score/percentile T2 support, LGE/T2 contrast embedding, baseline edema probability, and uncertainty as a learned edema-support score.
- Keep no-T2 cases explicit: no-T2 must carry a missing-T2 state or neutral T2 support, not synthetic T2 evidence.
- Evaluate CenterB vs CenterC separately and report whether the intensity support fails specifically in CenterC.

External layer:

- Audit I-MMSeg-style intensity-prior or prompt-based mechanisms only after metadata and compliance screening.
- Record whether GPT, CLIP, text prompts, pretrained visual-language weights, or external data are required.
- Prefer a CARE-compatible reduction of the mechanism over full pipeline reproduction.
- Do not download large weights or train external code unless the next goal-mode run records compliance and the user separately authorizes any large asset.

Pass: clean T2-present or CenterC edema signal without worsening component/remote FP, no-T2 FP, or scar guardrail.

Fail: the feature behaves like Round15 A with weak Dice signal but CenterC component fragmentation, or requires disallowed external data/weights.

### Main Route 2: `Cascaded_FSN_PTNet_anatomy_pathology_cascade_route`

Goal: upgrade weak anatomy scalar features into structured anatomy-pathology consistency without hard deletion.

CARE-first layer:

- Use baseline or nnU-Net anatomy probability maps for myocardium/LV/RV support.
- Test anatomy-first / pathology-second designs where an edema/pathology head is conditioned on anatomy support, not hard-pruned by it.
- Include lesion-anatomy consistency features, component-level plausibility, and soft consistency losses.
- Do not repeat Round6 simple myocardium-distance attenuation.

External layer:

- Audit Cascaded FSN / PT-Net-style implementations for anatomy/pathology separation, label mapping, data assumptions, and dependency burden.
- Use external implementations only for metadata/import/one-case smoke until they prove compatible.

Pass: improved CenterC/T2-present lesion support with scar unchanged and no hard ROI behavior.

Fail: hard-deletes true edema, repeats simple distance attenuation, worsens scar, or gives no signal beyond baseline fallback.

### Main Route 3: `Boundary_HD_component_objective_route`

Goal: reduce HD95, component fragmentation, and remote edge activation after a candidate already has plausible edema support.

Allowed mechanisms:

- Small-weight surface distance or HD-aware auxiliary loss.
- Component-aware penalty for remote/small islands.
- Residual smoothness or boundary consistency only as secondary control.
- InverseForm/surface/HD external code only through metadata/loss-level smoke.

Forbidden:

- Letting boundary/HD objective dominate recall.
- Treating boundary loss as a standalone replacement for intensity/anatomy support.
- Accepting a Dice gain that comes with worse component count or remote FP.

Pass: improves or preserves HD95/component behavior without suppressing true GT-positive edema.

Fail: over-pruning, unstable gradients, NaN/Inf, or another Dice/HD95 trade-off failure.

### Main Route 4: `Missing_modality_representation_route`

Goal: address no-T2 supervision ambiguity and modality-conditioned representation without relying on an unreliable complete-case teacher.

CARE-first layer:

- Test a small modality-conditioned head, FiLM-like route, or small MoE conditioned on C0/LGE/T2 presence.
- Keep no-T2 empty-GT cases away from dense strong class_4 negative supervision.
- Preserve LGE-driven scar supervision and class_5 guardrails.

External layer:

- Audit UniME, AdaMM, CoPeDiT, MoE, and MMPL-Seg for teacher assumptions, missing-modality policies, external data use, and label compatibility.
- Do not directly implement full AdaMM-style distillation unless complete-case teacher reliability and compliance are proven.

Pass: T2-present edema improves while no-T2 empty-GT remains stable and scar stays clean.

Fail: no-T2 FP increases, complete-case teacher assumptions are incompatible, or external training data is required.

### Auxiliary Route 1: `Pretrained_backbone_or_feature_route`

Goal: assess whether public pretrained features can improve CenterC/T2 edema representation.

Candidates:

- MedNeXt-like backbone/feature readiness.
- nnU-Net Task114 / M&Ms pretrained asset audit.
- BiomedParse or other medical foundation features only if CMR relevance, license, weight provenance, and data source are clear.

Rules:

- Public pretrained weights are only potentially usable after license and training-data provenance are recorded.
- No weight download in this planning pass.
- No fold0 training from pretrained assets until compliance is clear.

### Auxiliary Route 2: `CAA_Seg_SSA_alignment_watch_route`

Goal: keep alignment available as a watch route without letting it dominate Round16.

Allowed:

- Metadata audit and CenterC-focused one-case feasibility.
- CARE-only alignment proxy checks if low-cost.

Forbidden:

- Full CAA-Seg/SSA integration before evidence of sequence mismatch.
- Large batch allocation unless overlays or geometry audits show alignment is a likely CenterC failure driver.

## Round16 Large-Smoke Candidate Matrix

| Candidate | Priority | Mechanism | Job type | Intended implementation | External repo or weights | Allowed first action | Batch fold0 allowed? | Fail-fast rule |
|---|---:|---|---|---|---|---|---|---|
| `R16_A_care_strong_t2_lge_intensity_prior_fold0_vs` | P0 | T2/LGE intensity prior | fold0 very-short, then fold0 short if promoted | CARE-first stronger intensity-prior head using normalized T2/LGE support, baseline probability, uncertainty, and modality presence. | No external repo; no external weights. | Implement + unit/gradient + tiny smoke. | Yes after unit/tiny pass. | No T2-present/CenterC signal or worse component/remote FP. |
| `R16_B_external_I_MMSeg_metadata_import_onecase` | P0 | Intensity-prior external readiness | metadata-only, import/one-case smoke | Audit I-MMSeg interface and determine whether its intensity-prior idea can be reduced to CARE inputs. | External repo possible only in goal-mode after compliance gate; no large weights by default. | Metadata/license/I/O audit. | No, until one-case passes and user approves any weight use. | License/data/weight source unclear, heavy GPT/CLIP dependency required, or label mismatch. |
| `R16_C_anatomy_pathology_cascade_care_fold0_vs` | P0/P1 | Anatomy-pathology consistency | fold0 very-short, then fold0 short if promoted | CARE-first cascade: baseline anatomy support features, pathology head, soft lesion-anatomy consistency loss. | No external repo. | Implement small first-party cascade smoke. | Yes after import/unit/tiny pass. | Repeats hard ROI behavior, worsens scar, or CenterC unchanged. |
| `R16_D_external_CascadedFSN_PTNet_metadata_import_onecase` | P1 | External anatomy cascade readiness | metadata-only, import/one-case smoke | Audit Cascaded FSN/PT-Net style I/O, label mapping, anatomy/pathology separation. | External repo possible only after metadata pass. | Metadata/license/I/O audit. | No. | No usable code/weights, incompatible labels, or external data requirement. |
| `R16_E_intensity_plus_component_surface_aux_fold0_vs` | P1 | Intensity + boundary/HD auxiliary | fold0 very-short | CARE-first intensity support plus small-weight component/surface auxiliary. | No external repo. | Unit/gradient/tiny smoke; verify auxiliary gradients. | Yes after smoke. | Boundary term causes over-pruning or recall-heavy remote FP. |
| `R16_F_small_modality_conditioned_moe_fold0_vs` | P1 | Missing-modality representation | fold0 very-short | Small first-party modality-conditioned head/MoE using C0/LGE/T2 presence. | No external repo. | Unit/gradient/tiny smoke. | Yes after smoke. | no-T2 FP increases or edema signal absent. |
| `R16_G_unime_adamm_copedit_metadata_import_onecase` | P1/P2 | External missing-modality readiness | metadata-only, import/one-case smoke | Audit UniME/AdaMM/CoPeDiT/MMPL-Seg for CARE-compatible missing-modality mechanisms. | External repos only after compliance gate. | Metadata/license/pretrained-data audit. | No. | Requires external training data, unreliable complete-case teacher, or incompatible training objective. |
| `R16_H_pretrained_mednext_or_mms_readiness_smoke` | P1/P2 | Pretrained backbone/feature readiness | metadata-only, one-case feature smoke | Audit MedNeXt / nnU-Net Task114 / M&Ms feature or initialization feasibility. | Public weights only if license/data source clear and user authorizes download. | Metadata/readiness audit. | No. | Unknown pretrained data, disallowed external data risk, or heavy integration. |
| `R16_I_inverseform_surface_loss_metadata_loss_smoke` | P2/watch | Boundary/HD loss | metadata/loss smoke | Isolate differentiable HD/surface loss as small-weight auxiliary. | External code only if lightweight and license clear. | Loss-level unit smoke. | Only as auxiliary in later candidate. | NaN/Inf, unstable gradients, Dice/HD95 trade-off. |
| `R16_J_caa_seg_ssa_metadata_centerc_smoke` | P2/watch | Alignment | metadata/CenterC one-case feasibility | CenterC geometry/intensity alignment smoke; no full SSA implementation. | External repo only after audit. | Metadata + CARE-only one-case feasibility. | No initial fold0 train. | No alignment evidence or heavy preprocessing burden. |
| `R16_K_biomedparse_feature_readiness_smoke` | P2/watch | Foundation feature readiness | metadata-only | Audit feasibility of BiomedParse-like features for CMR pathology support. | Weights likely high compliance/size risk. | License/weights/data audit only. | No. | License/weights/data unclear or not CMR-relevant. |

## Compliance And External Asset Rules

Round16 may use external repositories only through staged readiness checks. It may not blindly clone, build, or train them.

For each external candidate, record:

- Repository URL and commit if used.
- License and whether it permits CARE challenge research use.
- Pretrained weights availability.
- Pretrained weight data source.
- Whether any external image/label data would enter CARE training.
- Dependency burden and CUDA/PyTorch compatibility.
- Input-output shape assumptions.
- Label mapping assumptions, especially edema class 4 and scar class 5.
- Whether it supports missing modalities.
- Whether one-case smoke can run without external training data.
- Whether the candidate would use validation pseudo-label supervised training.
- Whether the candidate has commercial, research-only, or redistribution restrictions.
- Whether it can be reproduced offline after source/asset capture.
- Whether it changes CARE raw or compact label semantics.
- Whether it changes validation submission/export format.
- Compliance risk: `low`, `medium`, `high`, or `reject`.

Hard compliance rules:

- CARE training must not mix external image/label datasets.
- Public pretrained weights may be considered only after license and training-data provenance are documented.
- No validation pseudo-label supervised training.
- No external large-weight download without explicit user authorization.
- No external repo fold0 training until metadata and import/one-case gates pass.
- If license, weights, data source, or label semantics are unclear, mark `postpone` or `reject`.

## Unified Metrics And Reporting Requirements

Every fold0 candidate must be compared against the same nnU-Net501 fold0 reference on the same validation cases.

Report separately:

- `myops_edema` class 4.
- `myops_scar` class 5.
- all-case.
- T2-present.
- T2-present GT-positive.
- complete-modality.
- CenterB.
- CenterC.
- no-T2 empty-GT.
- C0+LGE no-T2.
- LGE-only.
- modality group.
- center group.
- fixed high-risk cases: `Case2031`, `Case3011`, `Case3012`, `Case3040`, and `Case3044` when present in the fold0 validation/failure tables.

Required metrics:

- Dice.
- HD.
- HD95.
- component count.
- small FP count.
- remote FP count.
- pred/GT edema volume ratio.
- no-T2 edema FP voxel count.
- no-T2 edema FP case count.
- scar Dice and HD95 guardrail.
- training stability and NaN/Inf status.
- cache, label, fold split, and evaluator integrity.
- candidate-specific diagnostics such as intensity support score, anatomy support score, component safety score, alignment score, or representation feature summary.
- case-level failure flags.

Do not use foreground mean as a success criterion. Do not claim success from all-case aggregate alone. Any gain caused only by empty-GT artifact is diagnostic, not primary.

## Promotion, Watch, Stop, And Reject Logic

Use these decision labels:

- `go`: clean positive signal on T2-present GT-positive edema or CenterC complete-case edema, no component/remote FP worsening, no no-T2 FP increase, and scar guardrail clean.
- `watch`: small or localized signal, no safety failure, but not strong enough to expand beyond fold0 short.
- `postpone`: method may be useful but needs compliance, dependency, I/O, or stronger evidence before training.
- `stop`: candidate fails the target mechanism or safety gates.
- `reject`: violates compliance, external data rules, label semantics, or requires validation pseudo-label supervised training.

Fail-fast if:

- Dice improves but HD95/component/remote FP worsens materially.
- CenterC does not improve or worsens.
- no-T2 empty-GT edema FP increases beyond a documented tiny tolerance.
- class_5 scar Dice/HD95 regresses materially.
- Training has NaN/Inf or unstable gradients.
- Candidate changes label semantics, evaluator, cache, fold split, or baseline reference silently.
- External repo requires external data training or unclear pretrained data.

## Stage 1: `round16_portfolio_reproducibility_gate`

Goal: establish a clean Round16 baseline and candidate registry before any implementation or job execution.

Allowed:

- Read Round15 outputs and current code.
- Create Round16 output root and controller README during goal-mode.
- Verify baseline nnU-Net501 fold0 reference, fold split, label mapping, and evaluator paths.
- Register candidate names, config names, expected output dirs, and planned Slurm job names.

Forbidden:

- Training.
- Slurm submission.
- External repo clone.
- Weight download.
- Validation zip creation.

Outputs:

- `round16_goal_execution_readme.md`
- `round16_candidate_registry.csv`
- `round16_large_smoke_candidate_matrix.csv`
- `round16_batch_job_matrix.csv`

Pass:

- Baseline predictions, metrics, labels, and Round15 outputs are locatable.
- Candidate names and output dirs are unique and do not overwrite prior rounds.

Fail:

- Baseline reference cannot be located.
- Fold split or label semantics are ambiguous.
- Candidate registry would overwrite existing outputs.

Next: Stage 2.

## Stage 2: `external_candidate_compliance_and_metadata_audit`

Goal: screen external and pretrained candidates before import or execution.

Allowed:

- Metadata-level audit of documentation, license, expected inputs/outputs, weights, dependency risks, and label mapping.
- Record compliance status for I-MMSeg, Cascaded FSN/PT-Net, InverseForm/surface loss, UniME/AdaMM/CoPeDiT/MoE/MMPL-Seg, MedNeXt/M&Ms/Task114, CAA-Seg/SSA, and BiomedParse.

Forbidden:

- Large clone or build.
- Downloading weights.
- Running external training.
- Using external image/label data.

Outputs:

- `round16_compliance_metadata_matrix.csv`
- `round16_compliance_matrix.csv`
- `round16_repo_metadata_audit.md`
- `round16_external_repo_readiness_matrix.md`

Pass:

- Candidate is license-compatible or clearly marked as uncertain.
- Input-output, labels, and dependency risks are understood enough for one-case smoke.

Fail:

- Candidate requires external data training.
- License or weight provenance is incompatible or unclear.
- Integration would require major unbounded rewriting.

Next:

- Passing external candidates: Stage 3.
- CARE-first candidates: Stage 4.
- Failed candidates: mark `reject` or `postpone`.

## Stage 3: `import_and_onecase_smoke_for_external_candidates`

Goal: test only the minimal compatibility of external candidates that passed metadata audit.

Allowed:

- Lightweight import checks.
- One-case shape and label mapping smoke.
- Loss-only smoke for boundary/HD components.
- CPU or tiny GPU one-case run if required and explicitly within goal-mode bounds.
- After a candidate passes metadata/compliance screening, the next goal-mode run may clone a lightweight official repository or inspect official source metadata only when needed for import/one-case smoke. This does not authorize large pretrained weight downloads, external datasets, or full repo training.

Forbidden:

- Full training.
- Fold0 training before one-case smoke passes.
- Weight downloads unless user separately authorizes them.
- Any external data.

Outputs:

- `round16_external_import_smoke_summary.csv`
- `round16_onecase_smoke_summary.csv`
- `round16_onecase_smoke_results.csv`
- `round16_import_shape_label_smoke.md`

Pass:

- Import works.
- CARE case can be shaped into expected inputs.
- Output can be mapped to class_4 edema and class_5 scar semantics without silent changes.

Fail:

- Import fails due to heavy incompatible dependency.
- Shape/label mapping is incompatible.
- Candidate needs unavailable weights or external data to even run a smoke.

Next:

- Passing candidates may become Stage 4 or later fold0 smoke candidates.
- Failing candidates are `postpone` or `reject`.

## Stage 4: `care_first_strong_mechanism_implementation`

Goal: implement CARE-first high-priority mechanisms before depending on full external repos.

Allowed:

- Add small first-party implementation files for:
  - Strong T2/LGE intensity-prior support head.
  - Anatomy-pathology consistency cascade.
  - Intensity plus component/surface auxiliary candidate.
  - Small modality-conditioned MoE/head.
- Create bounded configs and job scripts.
- Run import, py_compile, one-batch forward/backward, gradient smoke, and tiny-overfit smoke in the later goal-mode execution.

Forbidden:

- Whole-network long training.
- Fold1-4 or 5-fold.
- Validation submission.
- Class label changes.
- Evaluator changes.
- Cache pollution of baseline outputs.

Outputs:

- `round16_train_commands.txt`
- Candidate-specific configs under Round16 output root or first-party config paths.
- Unit/gradient/tiny-smoke results captured in `round16_onecase_smoke_results.csv` or candidate-specific tables.

Pass:

- No NaN/Inf.
- Scar logits/outputs are guarded.
- no-T2 behavior is explicitly handled.
- Candidate produces non-empty but bounded edema behavior in tiny smoke.

Fail:

- Gradients unstable.
- Candidate alters class_5 or label semantics.
- no-T2 edema behavior is uncontrolled.

Next: Stage 5 for candidates that pass smoke.

## Stage 5: `first_batch_large_fold0_very_short_jobs`

Goal: submit a controlled batch of fold0 very-short jobs for promoted candidates.

Allowed:

- Submit multiple fold0 very-short Slurm jobs only for candidates that passed Stages 1-4.
- Use `htzhulab` by default.
- Use independent experiment names, seeds, output dirs, configs, and job logs.
- Record all job IDs and commands.

Forbidden:

- fold1-4.
- 5-fold.
- Full schedule.
- Validation zip.
- Submission.
- Unbounded queue waiting.
- Overwriting nnU-Net501 baseline, MyoPS-Net, U-MyoPS, or previous Lane A outputs.

Outputs:

- `round16_job_submission_manifest.csv`
- `round16_batch_job_submission_plan.md`
- `round16_batch_job_status.csv`
- `round16_train_commands.txt`
- Candidate prediction and metric subdirectories under Round16 root.
- `round16_fold0_very_short_metrics.csv`
- `round16_fold0_very_short_results.csv`

Pass:

- All predictions exported for the 44 fold0 validation cases or documented expected subset for one-case/tiny candidates.
- No NaN/Inf.
- Candidate has at least one clean positive signal in T2-present GT-positive edema or CenterC complete-case edema.
- Scar guardrail clean.
- no-T2 empty-GT clean.

Fail:

- Missing predictions.
- Training instability.
- Component/remote FP worsens.
- CenterC unchanged or worse.
- Scar guardrail dirty.

Next:

- Passing candidates: Stage 6 and possible Stage 7.
- Failing candidates: stop or watch; do not expand.

## Stage 6: `automatic_result_collection_and_gate`

Goal: evaluate all first-batch jobs using one comparable result collection pipeline.

Allowed:

- Collect metrics, logs, configs, prediction manifests, and failure flags.
- Generate unified tables and overlays where useful.
- Compare to nnU-Net501 fold0 baseline and strict safety filters from prior rounds.

Forbidden:

- Changing evaluator or label semantics.
- Selecting candidates based on foreground mean.
- Ignoring missing predictions or stale cache.

Outputs:

- `round16_baseline_vs_candidate_by_subset.csv`
- `round16_case_level_failure_flags.csv`
- `round16_centerC_edema_table.csv`
- `round16_no_t2_empty_gt_fp_table.csv`
- `round16_scar_guardrail_table.csv`
- `round16_component_remote_fp_table.csv`
- Fixed-case tables or rows covering `Case2031`, `Case3011`, `Case3012`, `Case3040`, and `Case3044` where available.
- `round16_candidate_decision_table.md`
- `round16_decision_table.md`

Pass:

- Candidate has a defensible subset-level positive signal and clean safety gates.

Fail:

- Candidate improves only all-case aggregate or empty-GT artifacts.
- Candidate worsens HD95/component/remote FP.
- Candidate creates no-T2 FP or scar regression.

Next:

- `go`: Stage 7.
- `watch`: optional deeper diagnostic only.
- `stop`/`reject`: no further jobs.

## Stage 7: `promoted_fold0_short_jobs`

Goal: run fold0 short jobs only for candidates promoted from very-short jobs.

Allowed:

- Submit fold0 short jobs for `go` candidates only.
- Keep the same output isolation and metrics requirements.
- Use early stopping and bounded walltime.

Forbidden:

- fold1-4 or 5-fold unless user separately authorizes after Round16 summary.
- Validation zip.
- External data.
- Long schedules that bypass Round16 gates.

Outputs:

- `round16_fold0_short_metrics.csv`
- `round16_fold0_short_results.csv`
- Updated `round16_decision_table.md`
- Updated `round16_round17_recommendation.md`

Pass:

- Candidate preserves or improves the very-short signal.
- T2-present GT-positive edema or CenterC edema improves cleanly.
- HD95/component/remote FP and scar guardrails remain clean.

Fail:

- Signal disappears with more training.
- Safety gate fails.
- Improvement is too small or not deployment-relevant.

Next: Stage 8.

## Stage 8: `round17_recommendation_and_deep_research_need_assessment`

Goal: decide whether Round17 should narrow around a promoted mechanism or commission a more focused DeepResearch pass.

Allowed:

- Summarize candidate status.
- Recommend `promote`, `watch`, `postpone`, `stop`, or `reject`.
- Define whether Round17 should focus on:
  - stronger T2/LGE intensity support,
  - anatomy-pathology cascade,
  - boundary/HD auxiliary,
  - missing-modality representation,
  - pretrained backbone feature,
  - or new deep research.

Forbidden:

- Validation submission.
- 5-fold expansion without user authorization.
- Claiming leaderboard readiness from fold0 smoke only.

Outputs:

- `round16_round17_recommendation.md`
- `round16_external_method_readiness_update.md`
- `round16_new_deep_research_need_assessment.md`
- `round16_deep_research_need_assessment.md`

Pass:

- Round17 direction is specific, evidence-backed, and names exact mechanisms and candidates.

Fail:

- Recommendation is only a generic “try more methods” statement.
- Evidence is based on aggregate mean rather than target subsets and guardrails.

## Batch Job Policy For Goal-Mode Execution

The next goal-mode run may be aggressive because token, Slurm, and GPU resources are available, but it must be staged and gated:

- It may prepare multiple candidates.
- It may submit several fold0 very-short jobs after metadata/import/one-case/unit/tiny gates pass.
- It may collect and compare all results in one run.
- It may submit fold0 short jobs only for candidates with a clean very-short gate.
- It must stop failed candidates immediately.
- It must not submit fold1-4, 5-fold, validation zip, or upload without separate user authorization.

Every job must record:

- candidate ID,
- config path,
- command,
- random seed,
- fold split,
- output dir,
- checkpoint policy,
- epoch/iteration budget,
- expected walltime,
- Slurm job ID if submitted,
- log path,
- evaluator path,
- baseline reference path.

## Controlled External Method Readiness

External methods should be integrated by mechanism slot, not by repository enthusiasm:

- I-MMSeg: intensity-prior mechanism. First reduce to CARE T2/LGE intensity support and one-case input/output smoke.
- Cascaded FSN / PT-Net: anatomy-pathology consistency mechanism. First test first-party cascade and label compatibility.
- InverseForm / surface / HD loss: boundary mechanism. First run loss-level gradient smoke as a small-weight auxiliary.
- UniME / AdaMM / CoPeDiT / MoE / MMPL-Seg: missing-modality representation. First audit teacher assumptions, no-T2 policy, external data risks, and one-case behavior.
- MedNeXt / nnU-Net Task114 / M&Ms / BiomedParse: pretrained representation. First audit license, training data, weights, and CMR relevance.
- CAA-Seg / SSA: alignment watch. Only elevate if CenterC overlays or geometry audit show sequence mismatch.

Do not clone or train all repos. Do not treat external data-trained repos as CARE training data. Do not download large weights without explicit approval.

## Next Goal Execution Prompt Draft

你现在在 `/overflow/htzhu/CARE` 中工作。请按 `docs/plans/laneA_round16_next_external_mechanism_integration_large_smoke_execution.md` 执行 Lane A Round16。资源充足，可以尽可能推进，但必须 staged/gated/compliance-checked。

请先执行 `round16_portfolio_reproducibility_gate`：复核 Round15 输出、nnU-Net501 fold0 baseline、fold split、label semantics、evaluator、cache isolation，并在 `results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/` 下建立 candidate registry、batch job matrix 和 execution README。

然后执行 `external_candidate_compliance_and_metadata_audit`：对 I-MMSeg、Cascaded FSN/PT-Net、InverseForm/surface loss、UniME/AdaMM/CoPeDiT/MoE/MMPL-Seg、MedNeXt/M&Ms/Task114、CAA-Seg/SSA、BiomedParse 等按机制槽位做 license、weights、pretrained data、external data risk、input-output shape、label mapping、dependency 风险审计。外部候选只有通过 metadata gate 才能进入 import/one-case smoke；不得无差别 clone/train 所有 repo，不得下载大权重，除非我另行明确批准。

对通过 metadata 的外部候选执行 import/one-case/shape/label smoke，不训练。对 CARE-first 高优先候选尽可能实现并 smoke：`R16_A_care_strong_t2_lge_intensity_prior_fold0_vs`、`R16_C_anatomy_pathology_cascade_care_fold0_vs`、`R16_E_intensity_plus_component_surface_aux_fold0_vs`、`R16_F_small_modality_conditioned_moe_fold0_vs`。先做 import / py_compile / one-batch forward-backward / gradient smoke / tiny-overfit；通过后才允许生成并提交 fold0 very-short Slurm jobs。

可以一次性提交多个通过 gate 的 fold0 very-short jobs，但每个 candidate 必须有独立 config、seed、experiment name、output dir、job name、log、train command，不得覆盖 nnU-Net501 baseline 或任何旧 round 输出。默认使用 `htzhulab`。不要提交 fold1-4、不要 5-fold、不要 validation zip、不要上传。

作业完成后统一收集结果，输出 `round16_fold0_very_short_metrics.csv`、`round16_baseline_vs_candidate_by_subset.csv`、`round16_centerC_edema_table.csv`、`round16_no_t2_empty_gt_fp_table.csv`、`round16_scar_guardrail_table.csv`、`round16_component_remote_fp_table.csv`、`round16_case_level_failure_flags.csv` 和 `round16_decision_table.md`。必须分别报告 `myops_edema` class_4 和 `myops_scar` class_5，并按 all-case、T2-present GT-positive、complete-modality、CenterB、CenterC、no-T2 empty-GT、modality group 和 center group 分层。必须报告 Dice、HD、HD95、component count、remote FP、small FP、pred/GT volume ratio、no-T2 FP voxel/case count、scar guardrail。

只有 very-short gate clean 的候选才允许进入 fold0 short jobs。若任一候选出现 HD95/component/remote FP 恶化、CenterC 不改善、no-T2 FP 增加、scar guardrail 不干净、NaN/Inf、cache/label/evaluator silent change、external data training 风险或只靠 empty-GT artifact 获益，必须停止该候选，不得自动扩大规模。

最后生成 `round16_round17_recommendation.md` 和 `round16_deep_research_need_assessment.md`，明确哪些机制 `go/watch/postpone/stop/reject`，以及 Round17 应收窄到哪个方向，或者是否需要围绕 CenterC/T2 edema representation、T2 intensity prior、edema label ambiguity、missing-modality supervision 做新一轮更窄 DeepResearch。
