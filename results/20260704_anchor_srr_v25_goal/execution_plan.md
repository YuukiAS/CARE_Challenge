# Execution Plan: 20260704_anchor_srr_v25_goal

controller_state: EXECUTOR_RUNNING
controller_role: Codex execution controller
task: prompts/tasks/20260704_anchor_srr_v25_goal.md

## Scope

This controller coordinates the GPT-authored anchored SRR-v2.5 repair goal. It must not act as the same-session executor or auditor for high-risk subtasks. It may launch separate executor/auditor sessions, collect their artifacts, and write the controller report.

Forbidden throughout this controller run:

- validation packaging or upload;
- fold expansion beyond authorized fold0 work;
- training the old tiny from-scratch `SRRProposeRefineMyoPS` as the main fix;
- treating no-T2 cases as edema dense negatives;
- calling frame0, translation-only, or descriptor-only Cine evidence complete;
- route promotion without separate audit.

## Phase Dependency Plan

1. Phase 0: `20260704_v25_contract_lock`
   - status: complete
   - required output: `results/20260704_v25_contract_lock/result.md`
   - gate: `contract_decision: LOCKED`

2. Phase 0B: `20260704_external_assets_cinema_registration`
   - status: complete
   - may run in parallel with Phase 1 after contract lock
   - gate: `external_asset_decision: PARTIAL_ASSETS_FOUND`

3. Phase 1: `20260704_myops_anchor_inputs_decode_qc`
   - status: complete after targeted revision
   - gate: `anchor_contract_decision: PASS_PREFLIGHT`

4. Phase 2: `20260704_myops_dictionary_retrieval_bank_impl`
   - status: complete
   - gate: `dictionary_decision: PASS_PREFLIGHT`

5. Phase 3: `20260704_myops_proposal_proto_hardneg_impl`
   - status: complete
   - gate: `proposal_proto_decision: PASS_PREFLIGHT`

6. Phase 4: `20260704_myops_soft_roi_no_t2_guardrails`
   - status: complete
   - gate: `soft_roi_guardrail_decision: PASS_PREFLIGHT`

7. Phase 5: `20260704_myops_loss_variant_schedule`
   - status: complete
   - gate: `loss_variant_decision: PASS_PREFLIGHT`

8. Phase 6: `20260704_myops_anchor_srr_fold0_formal`
   - status: executor complete with `NEEDS_MONITOR`; Slurm array still running
   - gate: pending formal fold0 checkpoint, prediction, metrics, and adequacy report

9. Phase 7: `20260704_cine_temporal_motion_resume`
   - status: complete
   - may run in parallel with MyoPS formal training if resources do not conflict

10. Phase 8: `20260704_anchor_srr_readonly_audit`
    - status: pending executor results
    - required output: controller-level audit summary and any subtask reviews

## Active Subagent Sessions

| phase | task | role | agent_id | status |
|---|---|---|---|---|
| 0 | `20260704_v25_contract_lock` | executor | `019f2b64-dbab-7d62-9f1a-074ca6b97979` | complete: `contract_decision: LOCKED` |
| 0B | `20260704_external_assets_cinema_registration` | executor | `019f2b67-d8b1-76a0-8aaf-604b7b24cf81` | complete: `external_asset_decision: PARTIAL_ASSETS_FOUND` |
| 1 | `20260704_myops_anchor_inputs_decode_qc` | executor | `019f2b68-0012-78b0-9a69-a114efacc270` | complete: `anchor_contract_decision: NEEDS_REVISION` |
| 1R | `20260704_myops_anchor_inputs_decode_qc` revision | executor | `019f2b6f-f3a1-7e92-80e6-986c46edeb4f` | complete: `anchor_contract_decision: PASS_PREFLIGHT` |
| 2 | `20260704_myops_dictionary_retrieval_bank_impl` | executor | `019f2b76-f6b7-7dc0-8dad-cdca6beeb0fb` | complete: `dictionary_decision: PASS_PREFLIGHT` |
| 3 | `20260704_myops_proposal_proto_hardneg_impl` | executor | `019f2b83-84f3-7d12-85b0-f3813e0e7ec4` | complete: `proposal_proto_decision: PASS_PREFLIGHT` |
| 4 | `20260704_myops_soft_roi_no_t2_guardrails` | executor | `019f2b8d-cfdb-7561-a55a-38721a5c5161` | complete: `soft_roi_guardrail_decision: PASS_PREFLIGHT` |
| 5 | `20260704_myops_loss_variant_schedule` | executor | `019f2b99-5237-7cf1-a00e-f471e5bc8c4a` | complete: `loss_variant_decision: PASS_PREFLIGHT` |
| 6 | `20260704_myops_anchor_srr_fold0_formal` | executor | `019f2ba4-29e8-7ae0-9541-4a5bc851cd59` | complete: `self_assessed_status: NEEDS_MONITOR`; Slurm array `57778764` running |
| 7 | `20260704_cine_temporal_motion_resume` | executor | `019f2b7f-62cc-7290-adf1-fe70f14ea3e7` | complete: `cine_temporal_decision: PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP` |

## Current Gate State

controller_run_status: INCOMPLETE
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: PENDING_OR_RUNNING
route_promotion_decision: NOT_EVALUABLE
route_negative_decision: NOT_EVALUABLE
scientific_resolution_status: SCIENTIFIC_UNRESOLVED
diagnostic_publication_decision: NOT_APPLICABLE
git_commit_decision: SKIP_COMMIT
git_push_decision: SKIP_PUSH
