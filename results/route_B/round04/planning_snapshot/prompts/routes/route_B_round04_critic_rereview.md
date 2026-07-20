---
route_id: route_B
portfolio_round: round04
date: 2026-07-20
role: independent_planning_critic_rereview
status: PLANNING_READY_FOR_CONTROLLER
reviewed_main_commit: 172171c9598170bcd9a26e31f6404e33e5f35774
planning_commit: 38551ed98a42b005a1a3f0b793efdef700037ee8
coordinator_receipt_fix_commit: 172171c9598170bcd9a26e31f6404e33e5f35774
reviewed_route_B_evidence_commit: b9c7664da7cb1f1892fff37a4497722f31a0a96d
route_C_context_commit: 17062b00edc3443aacefe8583568797a9f2655ba
route_C_reviewed_controller_commit: 1e663cfa64f00413f005bef26310290fd43ec8ab
handoff_blob: 7759cbf99d374022dce6013c5b4f411d49d1f294
coordinator_receipt_blob: d8ff48a577e1ff752bbb1c7ed5f0739e153ac416
planner_plan_blob: a537e0e86e3059efa27d128ac3a018a22a6a40aa
planner_prompt_blob: 1ea2277d20f9e4eab1711c767274204342c372e2
controller_contract_blob: 3087283d65dbb6eeca697a393fc545528fe7fada
executor_plan_blob: c5e437a0cd847ade5244727a43c239da9825c737
critic_request_blob: fcac92428b38d4b10e21e3ff594b83cac7eeba60
planner_audit_blob: 7a7964867557fb8f43a236d4aefecfd6174a7b4c
all_bound_planning_blobs_match: true
origin_main_match: true
origin_route_B_match: true
origin_route_C_match: true
coordinator_receipt_status_pass: true
coordinator_all_required_exit_codes_zero: true
coordinator_working_tree_clean: true
critic_local_users_worktree_available: false
critic_local_fetch_exit_code: 1
critic_used_bound_coordinator_receipt: true
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_CURRENT_CONVERSATION_PROJECT_MATERIALS
route_C_hold_context_only_pass: true
controller_planning_materialization_pass: true
b0_current_gate_inputs_pass: true
tested_commit_policy_consistent_pass: true
scientific_contract_preserved: true
round03_b3_only_interpretation_pass: true
b4_b5_b6_progression_pass: true
b7_b8_b9_mandatory_cine_lane_pass: true
b10_terminal_accounting_structure_pass: true
per_executor_validator_structure_pass: true
slurm_hardening_pass: true
controller_start_authorized: true
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
decision_token: ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
---

# Route B Round04 Independent Planning Critic Rereview

## 1. Scope

This was a planning-only rereview. I did not implement code, run model code, train, submit or monitor Slurm, start a Controller, start a Reviewer, write runtime `review.md`, upload validation, promote a route, start M11, merge routes, claim hosted metrics or make a final scientific decision.

The decision is bound to current `origin/main` `172171c9598170bcd9a26e31f6404e33e5f35774`, Route B evidence `b9c7664da7cb1f1892fff37a4497722f31a0a96d`, and Route C context `17062b00edc3443aacefe8583568797a9f2655ba`.

## 2. Local and coordinator execution evidence

The required local path `/users/a/e/aereinh/CARE` is not mounted in this ChatGPT runtime. The direct local attempt to run:

```text
cd /users/a/e/aereinh/CARE && git fetch --all --prune
```

returned exit `1` because the directory is unavailable in this runtime.

The current handoff explicitly permits the independent critic to rely on the bound Codex coordinator receipt when the receipt is current, complete and exit-zero. The receipt at `prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md` has blob `d8ff48a577e1ff752bbb1c7ed5f0739e153ac416` and records:

```text
status: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
working_tree_clean: true
all_required_exit_codes_zero: true
completion_token: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
```

Its required command table records exit `0` for fetch, branch/status, ref assertions, executor-plan validator, six-blob assertions, materialization assertions, B0 current-input assertions, unified ancestor policy, B10 terminal-finalizer assertions, B0-B10 validator/known-bad assertions, `git diff --check`, blank-authority scan, forbidden-path scan and clean-tree scan.

The receipt tested commit `41decbb95ebe1b02d9d5d836ae3455dfb0469f1f`; current `origin/main` is its direct descendant through only `prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md`, which is explicitly allowlisted. The six planning blobs are unchanged, so the tested-commit rule is satisfied.

## 3. Exact binding

The exact refs match the rereview request:

```text
origin/main:    172171c9598170bcd9a26e31f6404e33e5f35774
origin/route_B: b9c7664da7cb1f1892fff37a4497722f31a0a96d
origin/route_C: 17062b00edc3443aacefe8583568797a9f2655ba
```

The six planning blobs are byte-identical to the requested binding:

| File | Observed blob | Result |
|---|---|---|
| `prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md` | `a537e0e86e3059efa27d128ac3a018a22a6a40aa` | MATCH |
| `prompts/routes/route_B_round04_planner_prompt.md` | `1ea2277d20f9e4eab1711c767274204342c372e2` | MATCH |
| `prompts/routes/route_B_round04_controller_contract.md` | `3087283d65dbb6eeca697a393fc545528fe7fada` | MATCH |
| `prompts/routes/route_B_round04_executor_plan.yaml` | `c5e437a0cd847ade5244727a43c239da9825c737` | MATCH |
| `prompts/routes/route_B_round04_critic_request.md` | `fcac92428b38d4b10e21e3ff594b83cac7eeba60` | MATCH |
| `prompts/routes/route_B_round04_planner_audit.md` | `7a7964867557fb8f43a236d4aefecfd6174a7b4c` | MATCH |

`CURRENT.md` is now Round04 source of truth, points Route B critic to `prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md`, and allows only the two Route B Round04 planning tokens. It also records that `controller_authorized_now` remains `0` before this critic token.

## 4. Visual SRR rereview and scientific contract

SRR-v2, SRR-v2.5 and SRR-v3 were visually read from the current conversation/project materials. The recovered Route B invariant remains:

```text
observed [LGE,T2,C0] with explicit availability
-> four-scale [32,64,128,256] modality-specific encoding
-> shared/private/interaction retrieval with spatial/pathology-conditioned routing
-> optimized Pattern-SIP
-> learned anatomy plus fold-safe OOF prototype evidence
-> safe hard negatives
-> separate scar and edema proposals
-> pathology-specific soft ROI and separate refiners
-> bounded correction over nnU-Net anchor/context/safety evidence
-> official-label reconstruction, same-split evaluation and real final-output interventions
```

The Cine invariant remains:

```text
official CineMA pretrained source and architecture-matched random control
-> multiclass logits/features/probabilities/uncertainty
-> ED/reference and fixed key frames
-> seven-step SVF plus independently generated real SyN
-> true Jacobian and inverse consistency
-> registered anatomy/features/motion/Jacobian/quality evidence
-> registered temporal aggregation and same-case controls
```

The plan does not reduce Route B to Route A, nnU-Net-only, postprocess-only, wrapper-only, validator-only, proxy-only, single-frame-only or declaration-only.

## 5. Prior blockers rereview

### 5.1 Route C follow-up decision

`prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md` is now explicitly allowlisted. Its token is `ROUTE_C_PORTFOLIO_STOP_AND_HOLD`, with `route_C_controller_required: false`, `controller_start_authorized: false`, and all downstream authorities false. It is portfolio context only: it does not authorize a Route C Controller, change Route B authority, remove Route B Cine work or make a downstream scientific decision.

### 5.2 Controller planning materialization

The controller planning materialization contract is complete and machine-bound. It fixes:

```text
controller worktree: /users/a/e/aereinh/CARE_worktrees/route_B
read-only planning source: /users/a/e/aereinh/CARE
snapshot root: results/route_B/round04/planning_snapshot
manifest: results/route_B/round04/planning_snapshot/MANIFEST.json
hash audit: results/route_B/round04/planning_snapshot/hash_audit.json
descendant audit: results/route_B/round04/planning_snapshot/descendant_diff_audit.json
receipt: results/route_B/round04/planning_snapshot/materialization_receipt.json
failure token: ROUTE_B_ROUND04_B0_STALE_PLANNING_BINDING
```

The future Controller must materialize the planning snapshot before preparing executor waves, editing code, submitting Slurm, training or requesting review. The snapshot includes the six planning files, current rereview, CURRENT, handoff, coordinator receipt and Route C hold decision. It must be atomically published and read-only after publication. Any source unreadability, disallowed descendant path, hash mismatch, non-ready critic token, stale receipt, incomplete snapshot or writable final snapshot returns `ROUTE_B_ROUND04_B0_STALE_PLANNING_BINDING` and launches no executor.

### 5.3 B0 current gate inputs

B0 now points to the planning snapshot rather than directly to main-relative files in the Route B worktree. Its exact inputs include:

```text
results/route_B/round04/planning_snapshot/prompts/routes/route_B_round04_critic_rereview.md
results/route_B/round04/planning_snapshot/prompts/routes/handoffs/CURRENT.md
results/route_B/round04/planning_snapshot/prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
results/route_B/round04/planning_snapshot/prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
results/route_B/round04/planning_snapshot/prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md
```

The old `prompts/routes/route_B_round04_critic_review.md` is only a superseded historical input and cannot satisfy the current gate.

### 5.4 Tested-commit policy consistency

CURRENT, handoff, coordinator receipt, critic request, controller contract and executor plan now use the same tested-commit policy: accept the tested commit only when it equals current `origin/main`, or when it is an ancestor and every descendant path is allowlisted while the six planning blobs remain unchanged. Non-ancestor relation, unreadable diff, disallowed path or changed planning blob is stale.

### 5.5 Coordinator receipt completeness

The coordinator receipt frontmatter is complete and ready: `status: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW`, `working_tree_clean: true`, `all_required_exit_codes_zero: true`, and `completion_token: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW`.

## 6. Stage and evidence semantics

Round03 B3 remains B3-only adequate negative. B3 reached `43003` optimizer steps, `1800.7964860140346` train-loop seconds and `22` validation events; it passed finite loss, loss decrease, exact sampler, invalid-slot zero and no-T2 edema zero, but failed `anatomy_union_overfit`. B4-B9 did not execute and cannot be described as failed.

The revised Route B progression is correct:

- B3 is representation readiness only and cannot terminate the full route.
- Valid B3 proceeds to B4.
- Valid weak B4 proceeds to B5 through conservative soft-ROI control.
- Faithful weak B5 proceeds to B6.
- B6 is the first MyoPS full-route scientific classification stage.
- B7-B9 remain mandatory after B2 and run independently of B3 and Route C hold.

B10 remains a controller-owned terminal finalizer with `depends_on: []`, `prepare_wave_helper_exempt: true`, `depends_on_successful_merge_receipts: false`, `all_started_attempt_ids_source: results/route_B/round04/controller_ledger.csv`, and `finalizer_dependency_policy: afterany_all_started_attempts`. Its known-bad keys cover early terminal branch reachability, B1/B2/B7/B8 blockers, timeout/preemption/cancelled loser accounting, successful B6/B9 accounting, pending/running-as-complete, aggregation failure, superseded receipt reconciliation, authority violation, heavy artifacts and file-existence-only validation.

## 7. Validators, Slurm and authority boundary

B0-B10 each have an exact validator command using `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`, fixed input path, fixed report path, expected exit `0`, required success token, known-bad matrix command, expected known-bad runner exit `0`, expected validator exit `1` per fixture, exact failure keys, `all_keys_required: true`, and `unexpected_pass_is_failure: true`.

Slurm hardening passes planning review:

- `htzhulab` is default.
- Long compatible waits require isolated `htzhulab+a100-gpu` race.
- V100 credit requires unchanged scientific configuration and peak memory at most `14.5 GiB`.
- Training dependencies use `afterok`; B10 uses `afterany` over all started attempts.
- Pending, submitted, running, awaiting-accounting, monitor, undertrained, timeout, preemption and partial states are not completion.
- The Controller must run as Codex goal/goal resume and remains responsible through accounting, aggregation, mapper final, packet commit and reviewer handoff.

## 8. Decision

All hard gates passed for planning handoff. This ready token authorizes only the exact future Route B Controller as a Codex goal or explicit goal resume, bound to the current handoff, current six blobs, current coordinator receipt and current Route B evidence commit.

It does not authorize validation upload, route promotion, M11, hosted metric claims, cross-route merge or a final scientific decision.

```text
ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
```