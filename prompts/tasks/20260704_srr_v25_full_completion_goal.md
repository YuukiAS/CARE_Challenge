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
required_evidence: ["full_gap_matrix", "source_line_evidence", "code_diff", "unit_tests", "one_batch_overfit", "prototype_cache", "dictionary_ablation", "loss_mapping", "formal_fold0_metrics", "same_split_nnunet_context_comparison", "cine_registration_matrix", "read_only_audit"]
forbidden_substitutes: ["rerunning current anchored packet", "diagnostic-only pass for full implementation", "random or deterministic bootstrap prototypes as final prototype bank", "dictionary structure without semantic/ablation evidence", "generic DiceCE-only loss", "Cine without CineMA/SyN/TPS/VoxelMorph attempt", "claiming STOP from partial implementation", "validation packaging/upload"]
allowed_next_states: ["READY_FOR_USER_REVIEW", "EXECUTION_PLANNED", "EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "AUDITED_DIAGNOSTIC", "STOP"]
auto_git_commit: false
auto_git_push: false
---

# Full SRR-v2.5 Completion Goal For User Review

## Purpose

The current anchored SRR packet is `PARTIAL_REPRODUCIBLE` and should not be treated as a complete test of the SRR-v2.5 idea. This controller goal prepares a stricter implementation-completion round. The goal is not to return to a plain nnU-Net solution. nnU-Net may provide anatomy, uncertainty, probability, and component context, but the SRR method must build its own context-aware representation, retrieval, proposal, and refinement path.

## Current Negative Evidence To Carry Forward

The current packet proves that a partial anchored SRR implementation with nnU-Net context, multi-slot retrieval structure, crop refinement, and no-T2 safety still underperforms same-split nnU-Net. It does not prove that the full SRR-v2.5 design is exhausted. The forensic audit identified incomplete data-derived prototype banks, partial diagram-consistent loss, incomplete CineMA/registration evidence, and the absence of a broad scientific stop for SRR.

## Required Subtasks

Execute only after user review. The intended order is:

1. `prompts/tasks/20260704_srr_v25_gap_matrix_and_contract.md`
2. `prompts/tasks/20260704_srr_v25_encoder_context_interface.md`
3. `prompts/tasks/20260704_srr_v25_dictionary_semantic_retrieval.md`
4. `prompts/tasks/20260704_srr_v25_prototype_bank_cache.md`
5. `prompts/tasks/20260704_srr_v25_pathology_proposal_decoders.md`
6. `prompts/tasks/20260704_srr_v25_crop_refiner_training.md`
7. `prompts/tasks/20260704_srr_v25_full_loss_stack.md`
8. `prompts/tasks/20260704_srr_v25_training_ablation_matrix.md`
9. `prompts/tasks/20260704_srr_v25_failure_analysis_overlay.md`
10. `prompts/tasks/20260704_cine_full_cinema_registration.md`
11. `prompts/tasks/20260704_cine_temporal_dictionary_integration.md`
12. `prompts/tasks/20260704_srr_v25_final_readonly_audit.md`

MyoPS tasks 1-8 are the main chain. The Cine registration task may run in parallel after task 1 if it does not block MyoPS resources. The final audit must be read-only.

## Controller Rules

No subtask may mark full success by presence of files alone. Every implementation claim must include source-line evidence, a unit or forward test, diagnostic metrics, and an ablation or explicit reason why ablation is impossible. The current anchored packet is a negative baseline, not a reusable success template. Do not validate-package or upload anything.
