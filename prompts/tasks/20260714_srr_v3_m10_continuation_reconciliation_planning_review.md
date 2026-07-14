---
task_key: 20260714_srr_v3_m10_continuation_reconciliation
milestone_id: M10
role: critic
reviewed_prompt_path: prompts/shared/M10_srr_v3_continuation_reconciliation.md
reviewed_contract_sha256: 04dcaaf34ce6731dcebb8b2c4ce66da1e4802f084b7f0b3a14f307db47035b7a
canonical_executor_prompt_path: prompts/shared/EXECUTOR_PROMPTS.md#M10 follow-up executor/controller: contract reconciliation, Wave 2 evidence completion, and Cine fidelity repair
canonical_reviewer_prompt_path: prompts/shared/REVIEWER_PROMPTS.md#M10 follow-up reviewer: contract reconciliation, Wave 2 evidence completion, and Cine fidelity repair
canonical_contract_sha256: 5644dc97bda392c7524485eb879d25736e3063082d451741a6cb89e08f4b49e4
planner_draft_commit: ce8e33d1f0c5a95c2e9d5a0c6b862dad8218cba1
critic_decision: READY_FOR_CODEX_MERGE
critic_token: PLANNING_CRITIC_READY_FOR_CODEX_MERGE
reviewed_at: 2026-07-14T07:22:43Z
files_read: [START_HERE_FOR_GPT.md, GPT_PLANNER_CARE_PROTOCOL.md, AGENTS.md, prompts/AGENT_FLOW_V2_PROTOCOL.md, prompts/HANDOFF_GATE_POLICY.md, prompts/GPT_HARD_GATE_PROMPT.md, prompts/MILESTONE_REVIEW_PROTOCOL.md, prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md, prompts/schemas/planning_review.schema.yaml, prompts/schemas/executor_plan.schema.yaml, prompts/schemas/milestone_staging.schema.yaml, prompts/schemas/agent_flow_policy.yaml, scripts/validation/hash_milestone_contract.py, scripts/ops/validate_executor_plan.py, .agents/skills/slurm-routing-partition/SKILL.md, .agents/skills/care-mapper/SKILL.md, wiki/current_state.yaml, wiki/history/COMPARISON.md, wiki/history/M09/README.md, wiki/history/M09/COMPONENTS.csv, SRR-v2, SRR-v2.5, SRR-v3, current Planner staging and executor plan, old M10 planning review, old M10 controller/result/validator/finalizer packets, old Wave 2 ledgers and checkpoint selection, old component causal audit, old CineMA adapter and registration source]
blocking_findings: []
resolved_blocking_findings: [missing experiment_adequacy_gate, missing controller-supervised body headings and incomplete frontmatter mirror, adapter/random-init comparison lacked selected-checkpoint reload and controlled outcome classification, freeze/output/negative-registration requirements were not fully machine-checkable]
---

# M10 follow-up independent planning review

## Review target, remote synchronization, and ancestry

The remote repository was refreshed through the connected GitHub service before review. The reviewed lineage is:

```text
default branch: main
default branch HEAD: 04c548fb2cdff7eaba5ab54413625f964be97103
Planner branch: agent/m10-followup-planner-draft
Planner branch HEAD: ce8e33d1f0c5a95c2e9d5a0c6b862dad8218cba1
Planner/main merge-base: 04c548fb2cdff7eaba5ab54413625f964be97103
Critic branch: agent/m10-followup-planning-critic-repair
Critic branch base: ce8e33d1f0c5a95c2e9d5a0c6b862dad8218cba1
revised staging/plan snapshot commit before this review: 43a2328d2bbec59dfefd9704d1a4c56878a865ee
```

Remote comparison showed the Planner branch is exactly at the requested Planner HEAD, is three commits ahead of `main`, and is not behind it. The Critic branch was created directly from that exact Planner HEAD before applying any critic changes. The final branch must retain `ce8e33d...` as an actual ancestor; the final remote comparison is part of the completion check, not a prose-only SHA substitution.

No M10 execution, training, Slurm submission, runtime `review.md`, default-branch merge, validation packaging/upload, route promotion, push by runtime roles, or M11 work was performed in this planning review.

## Recovered route objective

The SRR-v2, SRR-v2.5, and SRR-v3 diagrams were visually reread in this thread. The route remains availability-aware modality-specific processing without zero-filling semantics; a semantic shared/private/interaction retrieval bank with real train/OOF prototype memory; anatomy-guided scar and edema proposal; pathology-specific soft-ROI refinement; explicit negative-space, proposal, refinement, dictionary, anatomy, and no-T2-safe objectives; and an SRR-owned final output. A strong nnU-Net may supply anchor, context, evidence, or safety but cannot replace the SRR path. The Cine branch remains reference-frame registration-aware anatomy-first temporal retrieval.

The revised follow-up preserves that objective. It does not downgrade M10 into evidence cleanup around nnU-Net and does not use Cine to reinterpret a failed MyoPS mechanism.

## Contract-hash adjudication

The three relevant historical facts are:

```text
old planning-reviewed canonical hash:
5030af7d74e35a423dd7e782ed0d55dffc1c1e78335c4016bb75920c17da0e64

observed parent canonical hash after operational repair:
955f6ab31e523123ba339e5b1732b78b304f099b9ce92bc896dfbb1e5d76653f

operational repair commit:
c53fa06
```

`c53fa06` added compute-node preflight, fingerprint-preserving bounded retries, `afterok` training dependencies, `afterany` accounting/finalizer dependencies, old/replacement job retention, and zero-credit failed starts. These rules are consistent with the current Slurm skill and close real operational gaps. They are not a scientific route redesign, but they are an execution-contract increment that was never bound by the old planning review.

The correct action is therefore a new M10 follow-up contract and stable hash. Editing the old `5030af...` review in place would falsify historical provenance. Reverting `c53fa06` would remove valid fail-closed continuity repairs. Both alternatives are rejected.

## Independent decisions on the required questions

| Question | Critic decision | Reason and binding condition |
|---|---|---|
| New follow-up hash versus old-review edit/rollback | **New hash required.** | Old review remains immutable; `955f6a...` and `c53fa06` are recorded as parent provenance. Codex integration must create a new canonical follow-up section. |
| Inherit old Wave 2 MyoPS runs | **Yes, conditionally and without discretionary retraining.** | The tracked ledgers show terminal aggregated budgets were met for D0, D1, D2, D3, hard-negative refresh, no-context, and alignment. Inheritance still requires an exact code/config/split/case/label/preprocess/decode/checkpoint/runtime fingerprint audit. Only a mismatched phase is blocked; the executor cannot silently retrain it. |
| Formal checkpoint selection | **All recoverable scheduled checkpoints must be reloaded and evaluated.** | D2 explicitly records `legacy_val_patch_loss`, which violates the original challenge-facing rule. Prior `checkpoint_best` names receive no formal privilege. The revised score, eligibility, calibration freeze, exclusion reasons, and tie-breakers are machine-checkable and sufficient. |
| D2/D3 component evidence | **New true final-output interventions are mandatory.** | The old audit contains placeholder fields such as `SEE_RUNTIME_TABLES` and `OUTPUT_EFFECT_REQUIRES_REVIEW`; this is not a causal intervention. The revised contract requires same-case/same-selected-checkpoint interventions, proposal/refiner/final-logit deltas, changed voxels/components, challenge metrics, and controlled state classification. |
| Old CineMA adapter and registration | **Implementation-fidelity failure, not an adequate scientific negative.** | The old adapter binarized a prior, fed it with the image to a separate small CNN, silently fell back to frame0 for missing frames, and lacked verifiable weight provenance and a capacity-matched random control. Registration directly used a bounded velocity tensor as displacement, optimized only NCC plus smoothness, emitted proxy Jacobian/inverse/SyN values, computed a pair rate as a case rate, and gated the final in-memory model rather than a reloaded selected checkpoint. |
| Completeness of the new Cine contract | **Complete after critic revision.** | The revision binds asset provenance and SHA256, multiclass logits/features/uncertainty, pretrained adaptation, matched random-init control, all-checkpoint selection and reload, symmetric velocities, explicit unit conversion, seven-step scaling-and-squaring, the full loss, true Jacobian/inverse metrics, real ANTs SyN, case aggregation, failure denominators, and conditional temporal launch. |
| Three serial executors and freeze boundary | **Approved.** | F1 is inherited-evidence evaluation only; F2 is Cine code/tests only; F3 is frozen runtime only. `executor_slots=max_parallel=1`, separate branches/worktrees/results/runtime/logs/locks, deterministic merge order, and return-to-F2 on implementation defects prevent hot-patching after adverse evidence. |
| Adequately trained registration still fails | **Allow `READY_FOR_REVIEW_CINE_REGISTRATION_NEGATIVE`.** | This is a fail-closed operational completion state, not route-negative approval. It is permitted only after faithful selected-checkpoint testing, real SyN, full denominators, unchanged thresholds, terminal accounting, aggregation, and strict validation. Temporal receives zero training credit and remains unrun. The separate runtime reviewer decides adequacy. |

## Evidence supporting Wave 2 inheritance

The old Wave 2 ledgers report the following terminal evidence:

| Phase | Job | Steps / floor | Train seconds / floor | Validation events / floor | Cases |
|---|---:|---:|---:|---:|---:|
| D0 static matched | 58706293 | 36746 / 20000 | 7200.02 / 7200 | 16 / 12 | 44 |
| D1 spatial BR2 | 58775065 | 31778 / 25000 | 9000.15 / 9000 | 19 / 15 | 44 |
| D2 hierarchical PSIP | 58775066 | 31810 / 25000 | 9000.03 / 9000 | 19 / 15 | 44 |
| D3 full memory PropRef | 58775067 | 50820 / 45000 | 14400.14 / 14400 | 26 / 22 | 44 |
| Hard-negative refresh | 58775068 | 20000 / 20000 | 5684.54 / 5400 | 10 / 10 | 44 |
| No-context control | 58775069 | 20000 / 20000 | 5488.04 / 5400 | 10 / 10 | 44 |
| Alignment control | 58775070 | 12501 / 10000 | 3600.22 / 3600 | 11 / 8 | 44 |

The retry-11 finalization packet records every effective phase as `COMPLETED(0:0)` and aggregation success. This supports inheritance of training adequacy when the follow-up fingerprint audit agrees. It does not validate the old checkpoint choice or component audit, so those decisions are intentionally recomputed.

## Cine fidelity adjudication

The old registration gate miss at `0.888888... < 0.90` cannot be interpreted as a mature registration negative because the measured quantity was accumulated per frame pair while labeled as a case rate, the transformation was not produced by scaling-and-squaring, inverse consistency and folding were proxies, the SyN value was manufactured from the learned score, and the selected checkpoint was not reloaded. Keeping the numerical threshold unchanged is correct; changing the implementation and measurement to satisfy the original contract is the required repair.

The critic revision also closes a gap in the Planner draft's random-init control. The adapted and random-initialized models now use the same architecture, cases, frames, augmentation, optimizer, budgets, validation cadence, and selection rule. Every scheduled checkpoint is evaluated and the selected checkpoint is reloaded. The result is classified as pretrained benefit, random-init noninferiority, or undertraining. Adequately trained random-init noninferiority does not permanently block registration, but it forbids any claim that CineMA pretraining helped and makes the selected source explicit. This separates architecture adequacy from external-pretraining benefit without manufacturing a positive result.

## Three-wave plan review

The revised executor plan has three waves and `max_parallel: 1`:

1. F1 owns only inherited MyoPS fingerprint validation, all-checkpoint 44-case evaluation, D2/D3 interventions, aggregation, and validator fixtures. It cannot train or edit implementation.
2. F2 owns only new Cine follow-up implementation, tests, configs, entrypoints, jobs, and a source/config/test/job freeze receipt. It cannot submit formal Slurm training.
3. F3 validates the freeze receipt, runs preflight and formal adapter/control/registration/SyN/conditional-temporal work, and writes only new follow-up runtime/evidence paths. It cannot edit code, config, scripts, jobs, or wiki.

The plan uses `afterok` for stages requiring upstream success and `afterany` for terminal accounting/finalizers. Bounded retries require unchanged code/config/split hashes and preserve all attempt IDs. The controller/global finalizer, mapper final, strict validators, review request, and one local lightweight packet commit are explicit. Negative-registration closure is reviewable instead of permanently goal-blocking only when implementation and evidence are fully adequate.

## Blocking findings found and repaired

| Finding in Planner draft | Why blocking | Critic revision |
|---|---|---|
| Missing `experiment_adequacy_gate` | Required by the milestone staging schema. | Added a gate separating inherited Wave 2 fingerprint/budget validation from new Cine minimum-effective training. |
| Missing exact controller-supervised headings and incomplete body mirror | Long controller tasks require `Execution Contract`, `Controller Prompt`, `Executor Worker Contract`, `Mapper Contract`, and `Reviewer Prompt`; a frontmatter/body mismatch is a hard failure. | Reorganized the staging under all five exact headings and mirrored the required contract fields. |
| CineMA/random-init comparison did not fully bind checkpoint enumeration, selection, reload, or allowed scientific interpretation | A nominal control could be trained but ignored, or CineMA benefit could be claimed from an unreloaded/unequal model. | Added matched budgets/cases/capacity, all-checkpoint anatomy-facing selection, selected-checkpoint reload, per-case/class deltas, selected downstream source, and three controlled outcome states. |
| Freeze and final evidence requirements were not fully explicit in the executor plan | F3 could otherwise drift from F2 or omit review-critical files. | Added F2 freeze receipt, F3 validation, explicit required outputs, no-code F3 write scope, strict return-to-F2 state, and selected-source/checkpoint receipts. |
| Negative-registration state needed sharper adequacy boundaries | A pipeline bug or proxy metric could be mislabeled a scientific negative. | Limited the state to faithful, adequately trained, selected-and-reloaded registration with real SyN, true metrics, full denominators, terminal aggregation, strict validation, and zero temporal credit. |

No blocking finding remains after these revisions.

## Stable hashes and binding

The revised staging stable hash, computed with `scripts/validation/hash_milestone_contract.py`, is:

```text
04dcaaf34ce6731dcebb8b2c4ce66da1e4802f084b7f0b3a14f307db47035b7a
```

The revised executor-plan file SHA256 is:

```text
3c98e34fc6e41a5daac19701d3ced2ed89799dd72c1e81d02e25895124a5aeed
```

The reviewed-contract commit must contain the revised staging, revised plan, and this planning review. A following metadata-only commit sets `planning_reviewed_commit` in the staging to that reviewed-contract commit; the metadata field is excluded from the stable staging hash. Codex planning integration must later compute and bind a new canonical executor/reviewer section hash. It must not reuse either historical canonical hash as the new follow-up binding.

Codex planning integration bound the merged canonical follow-up prompt sections as:

```text
canonical_executor_prompt_path:
prompts/shared/EXECUTOR_PROMPTS.md#M10 follow-up executor/controller: contract reconciliation, Wave 2 evidence completion, and Cine fidelity repair

canonical_reviewer_prompt_path:
prompts/shared/REVIEWER_PROMPTS.md#M10 follow-up reviewer: contract reconciliation, Wave 2 evidence completion, and Cine fidelity repair

canonical_contract_sha256:
5644dc97bda392c7524485eb879d25736e3063082d451741a6cb89e08f4b49e4
```

## Decision and controlled token

```text
critic_decision: READY_FOR_CODEX_MERGE
critic_token: PLANNING_CRITIC_READY_FOR_CODEX_MERGE
```

This token authorizes only later Codex planning integration and planning validators. It does not authorize M10 follow-up execution, training, Slurm submission, runtime review, push by runtime roles, default-branch merge, route promotion, validation packaging/upload, hosted metric claims, scientific stop, or M11.
