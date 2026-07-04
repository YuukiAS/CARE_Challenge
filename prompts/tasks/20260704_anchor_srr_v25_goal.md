---
task_key: "20260704_anchor_srr_v25_goal"
project: "CARE_Challenge"
status: "READY"
task_type: "controller"
controller_mode: true
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "Codex controller session"
executor: "separate Codex executor sessions/subagents"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: true
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "controller / nnU-Net-anchored SRR-v2.5 repair / MyoPS primary / Cine temporal secondary"
target_metric: "myops_scar, myops_edema, myocardium_cinemyops diagnostic proxy"
same_split_baseline: "MyoPS nnU-Net fold0 Dataset501 reference plus audited SRR-v2.5 compliance audit; Cine frame0/topology reference plus usable external anatomy/registration assets if available; evidence not found if unavailable"
required_subgroups: ["MyoPS all-case", "MyoPS T2-present/complete", "MyoPS GT-positive", "MyoPS no-T2 empty-GT stability", "MyoPS CenterB/CenterC", "Cine reference-frame baseline", "Cine non-reference-frame temporal evidence"]
required_secondary_metrics: ["Dice", "HD95", "component_count", "remote_FP", "outside_myocardium_FP", "volume_ratio", "dictionary_slot_usage", "gate_entropy", "proposal_recall", "proposal_precision", "lesion_wise_recall", "no_T2_edema_voxels", "registration_warp_sanity", "loss_plateau_or_convergence_status", "label_export_QC"]
required_evidence: ["executor_result", "auditor_review", "controller_report", "experiment_adequacy_report", "one_batch_overfit", "checkpoint", "prediction_path", "metric_csv", "same_split_baseline", "cache_isolation", "label_export_QC", "dictionary_stats", "proposal_sanity", "no_T2_decode_sanity", "loss_variant_schedule", "external_asset_registry", "cine_registration_option_matrix"]
forbidden_substitutes: ["training the current tiny from-scratch SRRProposeRefineMyoPS again as the main fix", "name-compatible SRR without diagram-compliant mechanisms", "old ScaleRetrieval as completed multi-slot dictionary", "random trainable prototypes as completed prototype retrieval", "full-volume residual head as soft-ROI crop refinement", "generic loss stack ignoring SRR-v2/v2.5 and scar/edema differences", "short fixed run presented as adequate training", "time-budget exhaustion without plateau presented as convergence", "zero-filled missing modality as evidence", "no-T2 cases as edema dense negatives", "frame0-only Cine as temporal completion", "translation-only alignment as registration completion", "skipping CineMA or stronger registration without blocker evidence", "compact-label proxy as challenge-facing improvement", "validation packaging or upload"]
route_promotion_gate: "Every claim audited. MyoPS promotion requires same-split nnU-Net comparison, no-T2 edema safety, label/export QC, convergence or justified early stopping evidence, and at least one primary or critical secondary metric improving without catastrophic scar/edema regression. Improvement over old SRR only is insufficient."
minimum_effective_training:
  train_until: "validation/target loss plateau, justified early stopping, or <=8h budget exhaustion"
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  require_validation_curve: true
  allow_stop_without_training: false
experiment_adequacy_gate: "For trainable MyoPS repair, use the staged schedule and train within the normal <=8h job budget until validation/target losses plateau or early stopping is justified. If the run stops while curves are still moving, report undertrained/needs monitor instead of route failure."
route_negative_gate: "STOP_NO_* conclusions require convergence or justified plateau evidence, absent forbidden substitutes, same-split baseline comparison, failure not explained by undertraining/pipeline/decode/cache/label/log issues, and explicit auditor support."
scientific_completion_gate: "Scientific completion requires SCIENTIFIC_PROMOTED or SCIENTIFIC_STOP_SUPPORTED. Operational completion or diagnostic publication alone is not scientific completion."
network_policy: "Network is allowed only for public code/model assets needed by this goal. Do not upload CARE data, predictions, credentials, or private files. Record source, version, local path, and license/compliance status for every asset used."
diagnostic_publication_gate: "Reviewed diagnostic-only code/report artifacts may be committed/pushed if no route is promoted and publication scope is respected."
diagnostic_publication_scope: ["controller_report", "execution_plan", "subtask result/review", "small reviewed Markdown decision packets", "reviewed first-party scripts", "compact diagnostic CSV/JSON summaries"]
blocked_after_diagnostic_publication: ["validation_upload", "validation_packaging", "fold_expansion", "hosted_metric_claim", "label_or_evaluator_or_fold_split_change", "unauthorized_next_stage_training"]
failure_escalation_policy: "If nnU-Net anchors, external assets, or required prediction/probability/component artifacts are missing, return NEEDS_EVIDENCE with concrete blocker evidence. If a new scientific route is required, return NEEDS_GPT_PLANNER."
executor_subtasks:
  - "prompts/tasks/20260704_v25_contract_lock.md"
  - "prompts/tasks/20260704_external_assets_cinema_registration.md"
  - "prompts/tasks/20260704_myops_anchor_inputs_decode_qc.md"
  - "prompts/tasks/20260704_myops_dictionary_retrieval_bank_impl.md"
  - "prompts/tasks/20260704_myops_proposal_proto_hardneg_impl.md"
  - "prompts/tasks/20260704_myops_soft_roi_no_t2_guardrails.md"
  - "prompts/tasks/20260704_myops_loss_variant_schedule.md"
  - "prompts/tasks/20260704_myops_anchor_srr_fold0_formal.md"
  - "prompts/tasks/20260704_cine_temporal_motion_resume.md"
  - "prompts/tasks/20260704_anchor_srr_readonly_audit.md"
controller_report_path: "results/20260704_anchor_srr_v25_goal/controller_report.md"
allowed_next_states: ["EXECUTION_PLANNED", "EXECUTOR_RUNNING", "EXECUTED_UNAUDITED", "AUDITOR_RUNNING", "AUDITED_GO", "AUDITED_DIAGNOSTIC_PUBLISH", "NEEDS_MONITOR", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_SUBAGENT_LAUNCH", "NEEDS_HUMAN_APPROVAL", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: true
allow_git_push: true
allow_diagnostic_commit: true
allow_diagnostic_push: true
---

# CARE Controller Goal: Full nnU-Net-Anchored SRR-v2.5 Repair With CineMA And Registration Evidence

## Purpose

MyoPS remains primary. The latest SRR-v2.5 compliance audit already says the current formal route is not diagram-compliant: it is a small three-scale from-scratch approximation, lacks nnU-Net anchor inputs, uses random prototypes, uses full-volume residual refinement, and leaks edema under no-T2 inference. This controller goal authorizes a full bounded repair that treats SRR-v2.5 as an nnU-Net-anchored evidence / dictionary / proposal / refinement system.

Cine is secondary but not optional-lazy. It must make a serious attempt to use CineMA or another vetted cine anatomy prior and compare meaningful registration/warping options. It must move beyond reference-only, descriptor-only, and translation-only evidence. It must not block MyoPS GPU work.

## Strategic Decision

Use Option A from the v2.5 audit, but implement the actual dictionary, proposal, loss, refinement, training, and external-evidence mechanisms needed for a fair test.

The route must consume nnU-Net probabilities, logits, compact predictions, and/or components as anchor evidence. Original LGE/C0/T2 tensors remain available for local refinement, but missing modalities must never be treated as observed evidence. The retrieval dictionary must be upgraded into a true multi-slot shared/private/interaction bank with slot-usage, gate-entropy, SIP/load-balance/coverage diagnostics, and no missing-modality slot leakage. Scar and edema prototype banks must be data-derived from train/OOF evidence, not only random trainable parameters. Proposal heads must combine nnU-Net components, dictionary-routed features, positive-vs-negative prototype similarity, anatomy/distance priors, and no-T2 edema gating. Soft-ROI crop refiners must use original LGE/T2 crops and anatomy/distance/uncertainty/proposal maps. Losses must follow the v2/v2.5 design: anatomy, scar proposal/refinement, T2-conditioned edema proposal/refinement, negative-space discrimination, soft anatomy/ROI prior, dictionary sparsity/coverage/load-balancing/prototype diversity, and optional alignment only when evidence supports it.

Training must be normal model training, not a token-budget exercise. Within the <=8h per-job round budget, train until validation/target losses plateau or early stopping is justified. If the budget expires before plateau, report undertrained or needs-monitor instead of scientific failure.

## Workflow

Phase 0 runs `20260704_v25_contract_lock`. Phase 0B runs `20260704_external_assets_cinema_registration` and may proceed in parallel with Phase 1 after the contract is locked. Phase 1 runs `20260704_myops_anchor_inputs_decode_qc`. Phase 2 runs `20260704_myops_dictionary_retrieval_bank_impl`. Phase 3 runs `20260704_myops_proposal_proto_hardneg_impl`. Phase 4 runs `20260704_myops_soft_roi_no_t2_guardrails`. Phase 5 runs `20260704_myops_loss_variant_schedule`. Phase 6 runs `20260704_myops_anchor_srr_fold0_formal` only after all preflight contracts pass. Phase 7 runs `20260704_cine_temporal_motion_resume`; it may run in parallel with MyoPS formal training if it uses separate resources and does not block MyoPS. Phase 8 runs `20260704_anchor_srr_readonly_audit`, then the controller writes `results/20260704_anchor_srr_v25_goal/controller_report.md`.

If the runtime cannot launch separate executor/auditor sessions, write subagent prompts under `results/20260704_anchor_srr_v25_goal/subagents/`, set `NEEDS_SUBAGENT_LAUNCH`, and stop. Do not pretend separation happened.

## Anti-Laziness Contract

These are not completion: renaming current `SRRProposeRefineMyoPS` and training it longer; a three-scale toy backbone for the final repair; old-style routers without multi-slot dictionary usage statistics; random prototypes as completed pathology dictionary; full-volume residual refinement as soft-ROI crop refinement; a generic loss stack that ignores the SRR-v2/v2.5 diagram and scar/edema differences; an arbitrary short run or an 8h timeout without plateau called adequate training; edema emission on no-T2 cases because the loss was T2-masked but inference was not; compact-label local sanity as challenge-facing progress; Cine completion from frame0/reference-only, descriptor-only, translation-only, or one weak warp proxy with poor sanity; skipping CineMA/registration attempts without documented blockers.

## Required Controller Report Ending

End `controller_report.md` with `controller_run_status`, `operational_completion_status`, `experiment_adequacy_decision`, `route_promotion_decision`, `route_negative_decision`, `scientific_resolution_status`, `diagnostic_publication_decision`, `git_commit_decision`, `git_push_decision`, `published_files`, `blocked_actions`, `next_required_action`, `reason_if_not_published`, and `reason_if_no_route_promotion`.
