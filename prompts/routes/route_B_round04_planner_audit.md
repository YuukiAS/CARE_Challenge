---
route_id: route_B
portfolio_round: round04
date: 2026-07-19
role: planner_audit
planning_mode: GITHUB_ONLY
planner_base_main: 30098813522cecd98e60bcb99e2676b28c1a5461
origin_main_verified: 30098813522cecd98e60bcb99e2676b28c1a5461
origin_route_B_verified: b9c7664da7cb1f1892fff37a4497722f31a0a96d
origin_route_C_verified: 17062b00edc3443aacefe8583568797a9f2655ba
route_C_review_token: ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
route_B_revision_source_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
status: PLANNING_REVISION_PUBLISHED_PENDING_COORDINATOR_RECEIPT_AND_CRITIC_REREVIEW
controller_start_authorized: false
coordinator_receipt_path: prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
critic_output_path: prompts/routes/route_B_round04_critic_rereview.md
required_critic_token: ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
local_users_checks_claimed_by_planner: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
---

# Route B Round04 Planner Audit

## 1. Operating boundary

This planning pass used authenticated GitHub repository reads and writes only. It did not require or claim access to server shell, tmux, Slurm or a local `/users` worktree. It did not execute model code, train a model, submit a job, produce a runtime reviewer decision or access `the prohibited overflow CARE workspace`.

Executable checks on `/users/a/e/aereinh/CARE` are delegated to the Codex coordinator through `prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md`. The receipt is a hard prerequisite for the next critic and is not pre-filled by this Planner.

## 2. Exact remote bindings

At planning start, authenticated repository refs matched:

```text
origin/main: 30098813522cecd98e60bcb99e2676b28c1a5461
origin/route_B: b9c7664da7cb1f1892fff37a4497722f31a0a96d
origin/route_C: 17062b00edc3443aacefe8583568797a9f2655ba
```

The revision is based on:

```text
Route B planning critic file: prompts/routes/route_B_round04_critic_review.md
Route B planning critic token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
Route C review file: results/route_C/review.md
Route C review token: ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
Route C reviewed controller repair: 1e663cfa64f00413f005bef26310290fd43ec8ab
```

A later Route B evidence or planning-file change invalidates the handoff. A later Route C packet change invalidates its evidence-complete reviewer binding.

## 3. Required governance and evidence read

The Planner read the exact-main versions of:

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/README.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
docs/notes/deep_research/care_2026_myocardium_round02_targeted_deep_research_cleaned.md
```

It also read the Route C reviewer packet at `17062b00edc3443aacefe8583568797a9f2655ba`, the Route B Round04 critic review at `30098813522cecd98e60bcb99e2676b28c1a5461`, and all six pre-revision Route B Round04 planning files.

## 4. Visual route recovery

SRR-v2, SRR-v2.5 and SRR-v3 were visually read from current Project/current-conversation materials.

Recovered invariant:

```text
explicit observed-modality availability
-> four-scale shared/private/interaction retrieval
-> anatomy-guided scar and edema proposal
-> separate pathology-specific soft ROI refinement
-> bounded final correction
```

Cine invariant:

```text
official per-frame anatomy features
-> reference-space registration and motion/Jacobian evidence
-> registered temporal aggregation
-> final-output effect
```

The revision does not reduce either invariant.

## 5. Route C portfolio audit

The Route C reviewer accepted the repaired controller packet. The former `positive_negative_prototype_swap` fail-open is fixed and re-reviewed: harmful swaps are detected, no-op/off-path controls remain zero-effect, strict validators pass and known-bad tests pass.

Planner state:

```text
route_C_status: EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION
route_C_reviewer_required_now: false
route_C_reviewer_required_if_binding_stale: true
```

This status provides portfolio evidence only. It does not authorize promotion/upload/M11/hosted metrics/cross-route merge/final decision.

## 6. Route B critic blockers and exact repairs

### `CURRENT_NOT_ADVANCED_TO_ROUND04`

Repair: `prompts/routes/handoffs/CURRENT.md` is advanced to Round04 and points to `prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md`. The handoff binds the exact planning commit, `b9c7664da7cb1f1892fff37a4497722f31a0a96d`, all six planning blobs, coordinator receipt, critic output path, allowed tokens and authority boundary.

### `B10_TERMINAL_FINALIZER_UNREACHABLE_ON_EARLY_TERMINAL_BRANCHES`

Repair: B10 has `depends_on: []`, `controller_terminal_finalizer: true`, `prepare_wave_helper_exempt: true` and `depends_on_successful_merge_receipts: false`. The controller terminal registry has global and lane terminal classes. B10 launches from the registry and controller ledger, not from successful B6/B9 merge receipts. Static regression cases explicitly cover B1 failure, B2 external blocker, B7 blocker, B8 registration blocker, timeout, preemption, cancelled race loser and successful B6/B9.

### `PER_EXECUTOR_VALIDATOR_COMMANDS_NOT_MACHINE_BOUND`

Repair: every B0-B10 executor has an exact `validator` block and exact `known_bad_contract`, including script, command, input, report, exit, success token, matrix path, runner command, expected validator exit `1`, exact failure keys, all-keys-required and unexpected-pass-is-failure.

### `REQUIRED_USERS_EXECUTABLE_CHECKS_NOT_EXIT_ZERO`

Planning action: the exact coordinator command set is written into `prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md`. Current state remains pending. The next critic must reject a missing, stale or nonzero receipt.

## 7. Scientific and routing non-regression

The revision preserves:

- Round03 B3 as B3-only adequate negative;
- strict B1 micro-overfit implementation gate;
- mandatory B4/B5/B6 after valid predecessors and B6 first full MyoPS judgment;
- mandatory independent B7/B8/B9 after B2;
- full four-scale SRR-v3, OOF bank, hard negatives, proposals, refiners and bounded correction;
- same-split baseline and lesion-centric case/subgroup evidence;
- official CineMA matched random control, seven-step SVF, real SyN and registered temporal aggregation;
- all fixed training budgets and clean reload;
- `htzhulab` default, isolated long-wait `htzhulab+a100-gpu` race, V100 unchanged-config/`<=14.5 GiB` gate;
- monitor states not completion and controller goal continuity;
- no runtime push and independent reviewer boundary.

## 8. Planner-side static preparation

The generated executor plan was parsed as YAML in the Planner's isolated formatting environment. This is a syntax preparation check only; it is not the required repository validator receipt.

Generated-file SHA256 before GitHub publication:

- `portfolio_round04_route_B_planner_plan_20260719.md`: `cccc7af5477d43cff6fd9053e496c4d23cbff41dc8a67e35421af26222aca592`
- `route_B_round04_planner_prompt.md`: `4cd6479500005bfa2cf878795015ee6997cf3c0e0f7efd931321e4ed7a6e6755`
- `route_B_round04_controller_contract.md`: `a467b8bc25d8d07853c3159c09a8f79f360c2834308a6ac59f9c48edaa149a19`
- `route_B_round04_executor_plan.yaml`: `1e5b9d932cfac35cf8aa3e66dbcefd25064e5b4ccbb5df3adc27b9f8d22fa10f`
- `route_B_round04_critic_request.md`: `d65d65117fc0fbb31ca15d4f3b2c5fa1ae2d78b655fd011963ceb45e9c4808d8`

Git blob SHAs and the exact containing planning commit are recorded later in the current handoff after GitHub publication.

## 9. Required Codex coordinator checks

The coordinator receipt must record exit `0` for:

```text
git fetch --all --prune
git status --short --branch
exact HEAD/origin ref assertions
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/routes/route_B_round04_executor_plan.yaml
PyYAML structural and B0-B10 validator-binding assertions
B10 early-terminal reachability regression assertions
git diff --check
blank-authority scan
forbidden-path scan
formal bare-interpreter scan
CineMA/registration/temporal non-deferral scan
```

The tested commit must equal current `origin/main`, and the working tree must be clean.

## 10. Publication and authority

Planner publication and push are not critic passage. Until a new independent critic writes `ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER` for the exact current binding:

```text
controller_start_authorized: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
```
