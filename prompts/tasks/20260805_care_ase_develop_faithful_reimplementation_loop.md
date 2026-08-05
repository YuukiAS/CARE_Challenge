---
task_key: 20260805_care_ase_develop_faithful_reimplementation_loop
task_kind: scientific_milestone
task_type: faithful_implementation_rebuild
status: AUTHORIZED_BY_USER_FOR_DEVELOP_ONLY
risk_level: high
agent_flow_version: v3
integration_branch: develop
main_merge_authorized: false
route_change: false
scientific_decision_scope: none
planning_review_required: true
critic_mode: scheduled_gpt_direct_repair_and_freeze
planner_reentry_required: true
controller_executor_separation_required: true
verifier_executor_separation_required: true
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator_only: true
verifier_count: 1
executor_count: 1
parallel_execution_allowed: false
slurm_runtime_continuity_required: false
continuity_backend: persistent_codex_sessions_and_local_watcher
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
training_authorized: false
outer_access_authorized: false
validation_upload_authorized: false
docker_build_or_upload_authorized: false
organizer_email_send_authorized: false
human_gate_after_planner_pass: true
max_repair_rounds: 12
---

# CARE-ASE faithful reimplementation on develop

## 1. Motivation

The current CARE-ASE run became progressively worse by approximately step 6000 according to the user-observed diagnostic trend. This is not accepted as proof that the architecture is scientifically invalid. Given the repeated history of downgrade implementations and the current Controller directly performing Executor work, the first priority is to rebuild and verify implementation fidelity under separated roles before any further formal training.

This task must not rewrite the historical run or claim a corrected score. It creates an isolated `develop` implementation candidate and stops after Planner confirms that the exact implementation faithfully matches the frozen CARE-ASE contract.

## 2. Scientific source of truth

Before freezing the implementation contract, Planner and Critic must read and reconcile at minimum:

```text
prompts/blueprints/CARE_ASE_final_model_blueprint_20260801.md
prompts/blueprints/CARE_ASE_exact_implementation_contract_20260801.yaml
prompts/routes/handoffs/CURRENT.md
wiki/README.md
results/20260801_care_nnunet_mosaic_complementarity_closure/**
results/20260801_care_four_lane_evidence_reconciliation/**
results/20260730_care_failure_forensics_deep_research_packet/**
```

They must visually inspect the required CARE-ASE and historical architecture diagrams through stable directly accessible visual sources. A filename, text summary or GitHub metadata is not sufficient. If scheduled GPT cannot visually read the diagrams, stop at `BLOCKED_VISUAL_SOURCES`.

The Critic may directly repair and freeze the Planner contract when the repair follows deterministically from these sources. It must not leave architecture, loss, sampling, training budget, inference, evaluation, deployment or validator semantics for Codex to choose.

## 3. Branch and isolation

Remote integration branch:

```text
develop
```

Stable branch:

```text
main
```

Only the Controller may push `develop`. Verifier and Executor use local-only branches and isolated worktrees. No experimental implementation commit may enter `main` without a later explicit user decision.

The active or historical CARE-ASE training checkout, Slurm jobs, permits, checkpoints, caches, results and Docker artifacts must not be modified.

## 4. Required role topology

The Controller must create and prove three distinct persistent Codex sessions:

```text
controller
verifier
executor
```

Each requires a unique exact thread ID, `CODEX_HOME`, worktree, local branch, process/log/state receipt and write scope. A single Codex goal that changes role labels but performs all work itself is invalid.

Controller responsibilities:

- capture the frozen contract;
- launch and resume exact Verifier/Executor sessions;
- maintain state and receipts;
- integrate local commits into `develop`;
- push `develop`;
- route Planner findings;
- run deterministic orchestration and notifier;
- never edit implementation or verification source.

Verifier responsibilities:

- implement validators, tests, mutation cases and known-bad fixtures first;
- prove that declared architecture components affect the real forward/loss/final-output path;
- test missing-modality, labels, sampling, gradient ownership, checkpoint/resume, full-volume inference, evaluation fairness and deployment loading;
- maintain protected adversarial fixtures separately from the Executor prompt;
- never edit model, training, inference or deployment implementation.

Executor responsibilities:

- implement the exact frozen CARE-ASE architecture and runtime;
- repair only implementation findings;
- never modify or weaken frozen verification code;
- never change the scientific contract;
- never start formal training or protected evaluation in this task.

## 5. Verifier-first gate

Executor must not begin implementation until Verifier has produced and Controller has frozen:

```text
verification_contract.json
public_test_manifest.json
protected_known_bad_manifest.json
verifier_fingerprint.json
verifier_session_receipt.json
```

The verification system must fail at least these downgrade families:

1. Controller and Executor are the same session or worktree.
2. CARE-ASE branches/heads exist in config but do not affect final logits.
3. A module receives no gradient despite being required by the contract.
4. nnU-Net output bypasses CARE-ASE and becomes the effective final prediction.
5. no-T2 cases receive edema supervision that the contract forbids.
6. T2-present edema path does not consume real T2 evidence.
7. checkpoint save/reload changes output or loses optimizer/schedule state.
8. early checkpoint inference silently uses final-step schedule values.
9. full-volume inference differs from the frozen deployment semantics.
10. CARE and baseline comparisons use different TTA, cases, decode or metric populations.
11. static/canned receipts pass without executing real forward/backward/inference paths.
12. training budget, cases, patch semantics, microbatch semantics or model width are reduced.
13. protected outer data is accessed before authorization.
14. hidden host dependencies or old wrappers bypass the new implementation.

## 6. Executor implementation gate

Before requesting Planner review, the integrated `develop` candidate must provide real evidence for:

- all declared CARE-ASE modules instantiated from the frozen configuration;
- required modules present in optimizer ownership;
- nonzero finite losses and expected gradients on real training cases;
- graph-node interventions that change the intended logits/final labels;
- all required input-availability modes;
- exact no-T2 safety behavior;
- sampler categories backed by real coordinates and physical definitions;
- save/reload and exact-resume continuity;
- full-volume sliding-window inference using the frozen step and TTA semantics;
- self-contained deployment loading without untracked host assets;
- strict tracked and protected validator PASS.

Short smoke or syntax success alone cannot satisfy this gate.

## 7. GitHub Actions and server-local checks

After Controller integrates and pushes `develop`, GitHub Actions runs deterministic repository-safe checks. It must reject malformed state, role-session overlap, stale hashes, contract drift, verifier drift, syntax failures and public unit-test failures.

Private-data, GPU, Slurm and protected adversarial tests run server-side under the Verifier/Controller environment. Their exact command, exit code, input fingerprint and output receipt hashes must be tracked for Planner review.

GitHub Actions PASS is required but not sufficient.

## 8. Planner repair loop

When all deterministic checks pass, Controller publishes an exact Planner review request bound to:

```text
frozen_contract_sha256
integration_commit_sha
implementation_fingerprint_sha256
verifier_fingerprint_sha256
ci_run_id_and_status
runtime_receipt_manifest_sha256
review_round
request_nonce
```

The scheduled Planner independently reviews the complete current implementation first, then checks closure of prior findings. It returns exactly one decision:

```text
PLANNER_REVISE_EXECUTOR
PLANNER_REVISE_VERIFIER
PLANNER_REVISE_BOTH
PLANNER_PASS
```

Controller resumes the exact named Codex session within one polling interval, integrates the repair, reruns all checks and republishes the next request. No manual independent review is required during these rounds.

The loop stops fail-closed when:

- the same blocking finding remains unresolved for three rounds;
- 12 repair rounds are exhausted;
- visual sources become unavailable;
- role isolation cannot be proved;
- the frozen scientific contract would need to change;
- a user scientific decision is required.

## 9. PASS meaning and final boundary

`PLANNER_PASS` means only that the exact `develop` implementation is judged faithful to the frozen CARE-ASE architecture and implementation contract with no remaining blocking downgrade finding.

It does not mean that CARE-ASE is scientifically superior, adequately trained or ready for submission.

After PASS, Controller must:

1. write `AWAIT_HUMAN_DECISION`;
2. commit/push lightweight receipts to `develop`;
3. send the existing notifier;
4. stop all automated roles.

The task must not automatically merge to `main`, start training, access outer data, build/upload Docker, send email or authorize the next experiment.

## 10. Required outputs

```text
automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json
automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json
results/agent_flow_v3/care-ase-faithful/critic_freeze_receipt.json
results/agent_flow_v3/care-ase-faithful/controller_session_receipt.json
results/agent_flow_v3/care-ase-faithful/verifier_session_receipt.json
results/agent_flow_v3/care-ase-faithful/executor_session_receipt.json
results/agent_flow_v3/care-ase-faithful/verifier_fingerprint.json
results/agent_flow_v3/care-ase-faithful/implementation_fingerprint.json
results/agent_flow_v3/care-ase-faithful/integration_receipt.json
results/agent_flow_v3/care-ase-faithful/ci_receipt.json
results/agent_flow_v3/care-ase-faithful/runtime_receipt_manifest.json
results/agent_flow_v3/care-ase-faithful/planner_reviews/round_<NNN>.json
results/agent_flow_v3/care-ase-faithful/final_state.json
```
