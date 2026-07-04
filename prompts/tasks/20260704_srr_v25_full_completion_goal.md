---
task_key: "20260704_srr_v25_full_completion_goal"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "controller"
controller_mode: true
planner: "ChatGPT/GPT thread"
executor: "Codex controller plus separate subagents"
auditor: "separate read-only auditor"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: true
allow_external_upload: false
requires_human_approval: true
review_required: true
mechanism_class: "full SRR-v2.5 implementation completion / MyoPS primary / Cine registration secondary"
target_metric: "myops_scar, myops_edema, myocardium_cinemyops diagnostic"
required_evidence: ["visual_contract", "anti_laziness_tests", "full_gap_matrix", "source_line_evidence", "code_diff", "unit_tests", "one_batch_overfit", "baseline_preserving_residual_gate", "prototype_cache", "dictionary_ablation", "loss_mapping", "formal_fold0_metrics", "same_split_nnunet_context_comparison", "failure_overlays", "cine_registration_matrix", "read_only_audit"]
forbidden_substitutes: ["rerunning current anchored packet", "diagnostic-only pass for full implementation", "random or deterministic bootstrap prototypes as final prototype bank", "dictionary structure without semantic/ablation evidence", "generic DiceCE-only loss", "plain nnU-Net copy as SRR", "weak from-scratch SRR replacing nnU-Net", "Cine without CineMA/SyN/TPS/VoxelMorph attempt", "claiming STOP from partial implementation", "validation packaging/upload"]
allowed_next_states: ["READY_FOR_USER_REVIEW", "EXECUTION_PLANNED", "EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "AUDITED_DIAGNOSTIC", "STOP"]
auto_git_commit: false
auto_git_push: false
---

# Full SRR-v2.5 Completion Goal For User Review

## Purpose

The current anchored SRR packet is `PARTIAL_REPRODUCIBLE` and should not be treated as a complete test of the SRR-v2.5 idea. This controller goal prepares a stricter implementation-completion round based on the actual SRR-v2/v2.5 visual diagrams. The goal is not to return to a plain nnU-Net solution. nnU-Net may provide anatomy, uncertainty, probability, component, and teacher context, but the SRR method must build its own availability-aware representation retrieval, anatomy-guided proposal, residual/gated correction, and pathology-specific refinement path.

## Strategic Interpretation

The visual design implies that SRR should not be a tiny from-scratch toy segmenter. It should either use a strong nnU-Net-equivalent encoder or preserve the same-split nnU-Net baseline through a bounded residual/gated correction path. A fair SRR-v2.5 test must answer whether selective retrieval can improve nnU-Net where nnU-Net is uncertain or wrong, without destroying cases nnU-Net already handles correctly.

## Current Negative Evidence To Carry Forward

The current packet proves that a partial anchored SRR implementation with nnU-Net context, multi-slot retrieval structure, crop refinement, and no-T2 safety still underperforms same-split nnU-Net. It does not prove that the full SRR-v2.5 design is exhausted. The forensic audit identified incomplete data-derived prototype banks, partial diagram-consistent loss, incomplete CineMA/registration evidence, and the absence of a broad scientific stop for SRR.

## Required Subtasks And Order

Execute only after user review. The intended order is:

1. `prompts/tasks/20260704_srr_v25_visual_contract_lock.md`
2. `prompts/tasks/20260704_srr_v25_anti_laziness_acceptance_tests.md`
3. `prompts/tasks/20260704_srr_v25_gap_matrix_and_contract.md`
4. `prompts/tasks/20260704_srr_v25_failure_analysis_overlay.md`
5. `prompts/tasks/20260704_srr_v25_encoder_context_interface.md`
6. `prompts/tasks/20260704_srr_v25_baseline_preserving_residual_gate.md`
7. `prompts/tasks/20260704_srr_v25_anatomy_distance_roi_prior.md`
8. `prompts/tasks/20260704_srr_v25_dictionary_semantic_retrieval.md`
9. `prompts/tasks/20260704_srr_v25_prototype_bank_cache.md`
10. `prompts/tasks/20260704_srr_v25_pathology_proposal_decoders.md`
11. `prompts/tasks/20260704_srr_v25_local_refinement_ablation.md`
12. `prompts/tasks/20260704_srr_v25_training_objectives_ablation.md`
13. `prompts/tasks/20260704_srr_v25_training_ablation_matrix.md`
14. `prompts/tasks/20260704_cine_full_cinema_registration.md`
15. `prompts/tasks/20260704_cine_temporal_dictionary_integration.md`
16. `prompts/tasks/20260704_srr_v25_completion_check.md`
17. `prompts/tasks/20260704_srr_v25_final_readonly_audit.md`

MyoPS tasks 1-13 are the main chain. Cine tasks 14-15 may run in parallel after task 3 if they do not block MyoPS resources. The final audit must be read-only.

## Controller Rules

No subtask may mark full success by presence of files alone. Every implementation claim must include source-line evidence, a unit or forward test, diagnostic metrics, and an ablation or explicit reason why ablation is impossible. Any module defined but not called by the formal model/runner is `UTILITY_ONLY`, not implemented. Any task that silently replaces a required filename with a similar filename is `NEEDS_REVISION`. The current anchored packet is a negative baseline, not a reusable success template. Do not validate-package or upload anything.
