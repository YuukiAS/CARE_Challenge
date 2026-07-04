---
task_key: "20260704_anchor_srr_readonly_audit"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "20260704_anchor_srr_v25_goal controller"
executor: "Codex read-only auditor session"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "medium"
allow_code_change: false
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: false
mechanism_class: "read-only audit / route promotion gate / experiment adequacy gate"
target_metric: "myops_scar, myops_edema, myocardium_cinemyops diagnostic proxy if Cine ran"
required_evidence: ["review.md", "claim_ledger", "experiment_adequacy_decision", "route_promotion_decision", "route_negative_decision", "blocked_actions", "MANIFEST.md"]
forbidden_substitutes: ["executor self-review", "promotion without same-split nnU-Net comparison", "STOP_NO_* without adequacy PASS", "audit based only on artifact presence", "publishing heavy outputs or predictions"]
promotion_gate: "Audit may support promotion, diagnostic publication only, needs revision, or evidence missing. It does not authorize validation packaging/upload by itself."
minimum_effective_training:
  min_optimizer_steps: 0
  min_train_loop_seconds: 0
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  allow_stop_without_training: false
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: Read-Only Audit Of Anchored SRR-v2.5 Repair And Formal Fold0 Evidence

## Goal

Audit the anchored SRR-v2.5 repair packet after executors stop. This task is read-only. It may support diagnostic publication, route promotion, no promotion, or evidence/revision need, but it must not edit model/training code or run new training.

## Required Audit Scope

Audit available results from `results/20260704_v25_contract_lock/`, `results/20260704_myops_anchor_inputs_decode_qc/`, `results/20260704_myops_dictionary_retrieval_bank_impl/`, `results/20260704_myops_proposal_proto_hardneg_impl/`, `results/20260704_myops_soft_roi_no_t2_guardrails/`, `results/20260704_myops_anchor_srr_fold0_formal/`, and `results/20260704_cine_temporal_motion_resume/` if run.

## Required Decisions

Write decisions for architecture compliance against the locked contract, nnU-Net anchor consumption, dictionary slot/gate/collapse sanity, data-derived prototype and safe-negative policy, no-T2 edema safety, proposal/refinement sanity, experiment adequacy, same-split nnU-Net comparison, route promotion, route-negative stop support, diagnostic publication scope, and blocked actions.

The audit must explicitly reject promotion if the implementation only renames the old `ScaleRetrieval`, uses random-only prototypes, uses full-volume residual refinement as crop refinement, lacks no-T2 inference/export guardrails, or relies on an undertrained run. It must also reject `STOP_NO_*` route-negative conclusions when the formal run fails the adequacy gate.

## Required Outputs

Write `results/20260704_myops_anchor_srr_fold0_formal/review.md` if formal MyoPS result exists, optionally `results/20260704_cine_temporal_motion_resume/review.md` if Cine result exists, and `results/20260704_anchor_srr_v25_goal/audit_summary.md` as controller-level audit summary. Include a `MANIFEST.md` for any audit result directory written.

## Completion Definition

The audit is complete only if it states explicitly whether this is route promotion, diagnostic-only publication, evidence missing, revision needed, undertrained, pipeline bug, or scientifically unresolved. Validation packaging/upload remains blocked.
