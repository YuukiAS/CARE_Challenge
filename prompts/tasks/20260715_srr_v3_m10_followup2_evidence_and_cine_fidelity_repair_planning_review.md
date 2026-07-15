---
task_key: 20260715_srr_v3_m10_followup2_evidence_and_cine_fidelity_repair
milestone_id: M10
role: critic
reviewed_prompt_path: prompts/shared/M10_srr_v3_followup2_evidence_and_cine_fidelity_repair.md
reviewed_contract_sha256: b8f5b95e34e045f8ff4d664f8c281337d82b8569d389b08cfedbfb3b3d44a3fd
canonical_executor_prompt_path: prompts/shared/EXECUTOR_PROMPTS.md#M10 follow-up2 executor/controller: Wave 2 evidence repair and full Cine fidelity re-execution
canonical_reviewer_prompt_path: prompts/shared/REVIEWER_PROMPTS.md#M10 follow-up2 reviewer: Wave 2 evidence repair and full Cine fidelity re-execution
canonical_contract_sha256: 5ca46f2b7d6899f23e98ccf39829cca865b651d26b58434ed150d22fdde12252
planner_draft_commit: 27def0c22a07c530bd81f2ce9bcd375ad48541e7
critic_decision: READY_FOR_CODEX_MERGE
critic_token: PLANNING_CRITIC_READY_FOR_CODEX_MERGE
reviewed_at: "2026-07-15T05:14:00Z"
files_read:
  - START_HERE_FOR_GPT.md
  - GPT_PLANNER_CARE_PROTOCOL.md
  - AGENTS.md
  - prompts/AGENT_FLOW_V2_PROTOCOL.md
  - prompts/HANDOFF_GATE_POLICY.md
  - prompts/GPT_HARD_GATE_PROMPT.md
  - prompts/MILESTONE_REVIEW_PROTOCOL.md
  - prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
  - prompts/schemas/planning_review.schema.yaml
  - prompts/schemas/milestone_staging.schema.yaml
  - prompts/schemas/executor_plan.schema.yaml
  - .agents/skills/slurm-routing-partition/SKILL.md
  - .agents/skills/care-mapper/SKILL.md
  - wiki/current_state.yaml
  - wiki/history/COMPARISON.md
  - wiki/history/M09/README.md
  - wiki/history/M09/COMPONENTS.csv
  - wiki/history/M09/components/availability-no-t2.md
  - wiki/history/M09/components/retrieval-dictionary.md
  - wiki/history/M09/components/prototype-memory.md
  - wiki/history/M09/components/anatomy-prior.md
  - wiki/history/M09/components/proposal.md
  - wiki/history/M09/components/refiner.md
  - wiki/history/M09/components/arbitration.md
  - wiki/history/M09/components/losses.md
  - wiki/history/M09/components/checkpoint-selection.md
  - wiki/history/M09/components/cine-temporal.md
  - wiki/history/M09/components/training-evidence.md
  - wiki/history/M10/README.md
  - prompts/tasks/20260715_srr_v3_m10_followup2_evidence_and_cine_fidelity_repair_critic_request.md
  - prompts/tasks/20260715_srr_v3_m10_followup2_planner_audit.md
  - prompts/shared/M10_srr_v3_followup2_evidence_and_cine_fidelity_repair.md
  - prompts/tasks/20260715_srr_v3_m10_followup2_evidence_and_cine_fidelity_repair_executor_plan.yaml
  - results/20260714_srr_v3_m10_continuation_reconciliation/review.md
  - results/20260714_srr_v3_m10_followup_wave2_reconciliation/commands_run.md
  - results/20260714_srr_v3_m10_followup_wave2_reconciliation/runtime_manifest.json
  - results/20260714_srr_v3_m10_followup_cine_fidelity/freeze_receipt.json
  - scripts/evaluation/evaluate_srr_v3_m10_followup_all_checkpoints.py
  - scripts/evaluation/run_srr_v3_m10_followup_interventions.py
  - scripts/evaluation/validate_srr_v3_m10_followup_wave2.py
  - scripts/evaluation/validate_cine_m10_followup.py
  - src/care_myocardium/tests/test_m10_followup_cine_fidelity.py
  - scripts/training/run_cinema_adapter_m10_followup.py
  - scripts/training/run_cine_registration_m10_followup.py
  - scripts/training/run_cine_temporal_m10_followup.py
  - jobs/src/run_srr_v3_m10_followup_cine_adapter.sh
  - jobs/src/run_srr_v3_m10_followup_cine_random_init.sh
  - jobs/src/run_srr_v3_m10_followup_cine_registration.sh
  - jobs/src/run_srr_v3_m10_followup_cine_temporal.sh
  - src/care_myocardium/cine/registration_model.py
  - scripts/training/run_cinema_adapter_m10.py
  - scripts/training/run_cine_registration_m10.py
  - scripts/training/run_cine_temporal_model_m10.py
  - scripts/validation/hash_milestone_contract.py
  - scripts/validation/validate_handoff_policy.py
blocking_findings: []
---

# M10 follow-up2 planning-period critic review

## Review boundary

本审查只核验并修订 M10 follow-up2 规划合同。未执行 follow-up2，未训练，未提交 Slurm，未生成 runtime packet 或 runtime `review.md`，未合并默认分支，未进行 validation packaging/upload、route promotion、scientific stop 或 M11。

## Remote lineage

- repository default branch: `main`
- default HEAD observed at review: `30a4da8d5307fff8f0a9b8f0857d2e1812de844b`
- Planner branch: `agent/m10-followup2-planner-draft`
- exact Planner HEAD: `27def0c22a07c530bd81f2ce9bcd375ad48541e7`
- Planner branch versus requested Planner HEAD: identical
- Planner branch versus default: ahead by 4, behind by 0
- Critic branch was created directly from exact Planner HEAD and must remain a descendant after the review commits.

## Route objective recovered from project diagrams

SRR-MyoPS remains availability-aware modality handling plus shared/private/interaction semantic retrieval, real prototypes, anatomy-guided scar/edema proposal, pathology-specific soft-ROI refinement and explicit negative-space/no-T2-safe objectives. nnU-Net is an anchor/context/evidence/safety source rather than a substitute route. Cine must use trustworthy multiclass anatomy, bidirectional integrated registration and registration-conditioned temporal retrieval; contract declarations, binary frame0 priors and proxy registration are not implementations.

## Independent findings against the Planner draft

The Planner audit correctly identified the prior follow-up shortcuts, and independent source/evidence inspection confirmed them:

1. F1 interventions did not execute model inference. The old script wrote `NEEDS_EVIDENCE` rows, while the old validator checked mostly file existence and could still report PASS.
2. The old evaluator only replayed checkpoints when `--evaluate` was supplied; tracked `commands_run.md` omitted that flag. It could copy old best/final metrics, and the runtime manifest admitted only 11 new evaluations despite 125 inventory rows.
3. The old selector replaced the reviewed anchor-relative Dice/HD95/remote-FP formula with a simplified absolute score and omitted material eligibility gates.
4. F2 tests validated dataclasses/synthetic declarations rather than actual CineMA asset loading, multiclass outputs, integrated registration, real SyN or registered temporal flow.
5. The three follow-up scripts were contract-only, while all four formal wrappers delegated to old M10 trainers. Adapter and random-init wrappers did not distinguish initialization.
6. The old registration path directly used predicted velocity as displacement, used incomplete loss/proxy QC/fake SyN/pair-level non-worse, and did not clean-reload the selected checkpoint.
7. The old temporal path did not consume selected CineMA features or registered anatomy/velocity/Jacobian/uncertainty.
8. The temporal single-job design was incompatible with observed throughput and did not provide durable cumulative resume.

The Planner draft moved in the correct direction but still left new bypasses: no per-checkpoint raw-output freshness proof, no deterministic baseline/no-op/known-bad intervention gate, declaration tests could still support R2 readiness, R2 could self-author the final freeze, R3 preflight covered too little, staging and plan used inconsistent follow-up entrypoint names, and adapter/registration numeric minimum-effective-training budgets were not fully mirrored.

## Integrator rejection and repair

The first Critic publication was not integration-safe. The planning review recorded `dbcfb117...`, while the exact final Critic-HEAD staging evaluated by the repository hasher did not match that value. This was a real planning-review binding defect, so the previous token could not authorize integration.

The candidate validator also exposed three contract-format gaps:

1. The staging mentioned `FINALIZER_A/B` but did not contain the literal and sufficiently explicit durable finalizer contract required for a long Slurm task.
2. `architecture_impact: system` listed only predecessor summaries and did not record that every M09 component analysis file had been dynamically read.
3. `diagnostic_publication_scope` and `blocked_after_diagnostic_publication` were written as multiline YAML lists. The repository candidate parser treats an empty key line as an empty scalar and does not attach subsequent list items, so both gates were machine-empty despite being human-readable.

The repaired staging now uses parser-compatible inline lists, records `wiki/history/M09/COMPONENTS.csv` and every file under `wiki/history/M09/components/*.md`, summarizes the resulting component constraints, and adds a concrete durable finalizer contract with backend, dependency semantics, job-ID capture, paths, aggregation commands, validation commands, failure states and local-commit boundary. The exact repaired remote staging content hashes to `b8f5b95e34e045f8ff4d664f8c281337d82b8569d389b08cfedbfb3b3d44a3fd` under `scripts/validation/hash_milestone_contract.py`.

## Critic revisions

### R1 fresh replay and selector

The revised contract now requires every recoverable scheduled checkpoint to execute a fresh 44-case reload under a new runtime root with explicit `--evaluate --force`, a per-checkpoint job/argv/checkpoint/state-dict/hash receipt and a raw prediction/probability-or-logit manifest. Historical candidate metrics may not be copied, linked, rewritten or used for selection. The immutable nnU-Net anchor is allowed only with path and SHA256.

The exact reviewed anchor-relative formula, all eligibility fields, pre-evaluation calibration freeze, tie-breakers and a clean-process selected-checkpoint repeat are mandatory. Validators must reject copied/stale/partial/preliminary evidence and source paths that implement the former shortcut.

### R1 real D2/D3 interventions

The revised plan requires two deterministic clean baselines, real graph-node interventions, baseline/intervention proposal/refiner/final-logit and final-label manifests, case-level metric deltas, a no-op invariant control and a known-bad positive/negative swap. A known-bad intervention with no final-output effect is `PIPELINE_BUG`, not no signal. If the real existing graph cannot expose an intervention without forbidden source changes, R1 returns `NEEDS_REVISION`; it cannot substitute a surrogate, stub, post-hoc CSV or disconnected tensor.

### R2 real implementation and smoke

All formal names are unified to new `*_m10_followup2.py` entrypoints. Old M10 trainers are forbidden as imports/delegates except explicitly allowlisted data-I/O primitives with symbol/hash audit.

R2 readiness now requires actual CineMA weight and license provenance, one real CARE frame producing multiclass logits/features/uncertainty, distinct pretrained/random initialization checksums, an optimizer-step frozen/trainable parameter audit, one real bidirectional seven-step registration pair with true Jacobian/composition, one real ANTs pair and a temporal smoke that consumes registered artifacts and changes final logits. Mock/dataclass/contract-only tests can supplement but cannot satisfy readiness. Missing assets produce `BLOCKED_EXTERNAL_RESOURCE` or `NEEDS_EVIDENCE`.

### Freeze and wrapper identity

R2 writes only a freeze candidate. After R2 merge, the controller independently creates the final freeze on the merged commit, including transitive first-party imports, weight/environment/ANTs identity, exact resolved commands and smoke/test receipt hashes. R3 recomputes it before any job. This prevents the prior pattern where reviewed files and executed wrappers were different.

### R3 full runtime and preflight

All old F3 attempts receive zero follow-up2 credit. R3 must rerun pretrained adapter, matched random-init, all-checkpoint selection/reload, faithful registration, real SyN, registration selection/reload/gate and conditional temporal execution.

The preflight is now a phase matrix covering pretrained, random, adapter selector, registration, ANTs, registration gate, temporal resume and controls. Temporal preflight must open the exact selected adapter/registration artifacts and a real batch. The controller conditionally submits temporal only after parsing a passed registration gate; an adequate faithful gate failure enters the registration-negative closure without pre-submitting temporal.

### Minimum-effective training and cumulative resume

The unchanged minima are explicit:

- pretrained adapter: `10000 steps / 3600 seconds / 8 validations / 3 full-case events / 12 cases`;
- random-init: identical;
- registration: `25000 / 7200 / 10 / 4 / 12` and at least 60 pairs;
- temporal: `20000 / 7200 / 10 / 4 / 12`.

Every trainable phase also requires overfit, prediction sanity, loss decrease, matched baseline/control and cache isolation.

The `4000 -> 8000 -> 12000 -> 16000 -> 20000` cumulative schedule is acceptable only with a launch-time throughput guard capped at 6.5 estimated hours per chunk. Based on the old 6000-step/8-hour observation, 4000 steps would nominally be about 5.3 hours, but faithful implementation can change throughput; the controller may reduce, never increase, the next chunk target. Atomic saves occur at most every 500 steps and on `SIGUSR1/TERM`. Failed/timeout/preempted attempts, partial checkpoints and the historical 6000-step timeout receive zero credit; replacements resume only from the last credited completed checkpoint. Validators reject reset, overlap, gap, duplicate events, fabricated time and missing parent hashes.

### Controller anti-token gate

Executor completion tokens are advisory. Before each merge, the controller must independently parse receipts and recompute sampled selector, eligibility, intervention, wrapper/freeze and cumulative-counter facts. Token/evidence conflict blocks merge. This directly repairs the previous “subexecutor says ready, controller accepts” failure.

## Executor graph and boundaries

The final graph remains three serial executors with `executor_slots=1`, non-overlapping write scopes and controller-only merge:

1. R1: fresh MyoPS evidence and interventions; no training or MyoPS source/config changes.
2. R2: new Cine implementation/tests/config/wrappers and zero-credit real smoke; no formal training and no final freeze authority.
3. R3: frozen runtime/evidence only; no source/config/job edits.

The controller produces `completion_check.md` and `review_request.md`, commits only the lightweight packet, does not push and stops before independent runtime review. `wiki/current_state.yaml` remains M09; M10 remains candidate/unreviewed.

## Hashes and decision

- reviewed stable staging SHA256: `b8f5b95e34e045f8ff4d664f8c281337d82b8569d389b08cfedbfb3b3d44a3fd`
- revised executor-plan SHA256: `1d3d618446acec69824e484565107e3ee0a21fac047656fd8517fdce8ab1015f`
- canonical executor/reviewer section SHA256: `5ca46f2b7d6899f23e98ccf39829cca865b651d26b58434ed150d22fdde12252`
- planner draft commit: `27def0c22a07c530bd81f2ce9bcd375ad48541e7`
- candidate-validator repair: durable finalizer, dynamic predecessor component files, and parser-compatible publication gates added
- unresolved blocking findings after Critic revisions: none
- critic decision: `READY_FOR_CODEX_MERGE`
- critic token: `PLANNING_CRITIC_READY_FOR_CODEX_MERGE`

This token authorizes only later Codex planning integration of the reviewed follow-up2 contract. It does not authorize execution, training, Slurm submission, runtime review, validation packaging/upload, hosted claims, route decisions, default-branch merge, automatic push or M11.
