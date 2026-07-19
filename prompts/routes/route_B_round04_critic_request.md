---
route_id: route_B
portfolio_round: round04
date: 2026-07-19
role: critic
status: REQUESTED
planner_base_main: 7042135a4cc5be44b090fee93d4d1ee25b72fc0e
route_evidence_ref: b9c7664da7cb1f1892fff37a4497722f31a0a96d
inherited_review_token: ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE
planner_plan_path: prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md
planner_prompt_path: prompts/routes/route_B_round04_planner_prompt.md
controller_contract_path: prompts/routes/route_B_round04_controller_contract.md
executor_plan_path: prompts/routes/route_B_round04_executor_plan.yaml
planner_audit_path: prompts/routes/route_B_round04_planner_audit.md
critic_output_path: prompts/routes/route_B_round04_critic_review.md
controller_start_authorized: false
ready_token: ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
revision_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# Route B Round04 Critic Request

You are the independent CARE Route B Round04 Critic. Review planning only. Do not implement code, train, submit or monitor Slurm, write runtime reviewer output, package or upload validation, start M11, promote a route, merge across routes, claim hosted metrics, or make a final scientific decision.

## 1. Exact sources to re-fetch

Re-fetch current main and `origin/route_B`, then read:

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
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
wiki/current_state.yaml
wiki/history/README.md
wiki/history/COMPARISON.md
docs/notes/deep_research/care_2026_myocardium_round02_targeted_deep_research_cleaned.md
```

Read the exact Round03 Route B evidence from `origin/route_B`:

```text
results/route_B/review.md
results/route_B/result.md
results/route_B/controller_report.md
results/route_B/completion_check.md
results/route_B/round03/executors/B0/*
results/route_B/round03/executors/B1/*
results/route_B/round03/executors/B2/*
results/route_B/round03/executors/B3/completion.json
results/route_B/round03/executors/B3/training_adequacy.csv
results/route_B/round03/executors/B10/completion.json
results/route_B/round03/executors/B10/validator_packet_report.json
prompts/routes/route_B.md
prompts/routes/route_B_executor_plan.yaml
```

Visually read the Project-background SRR-v2, SRR-v2.5, and SRR-v3 diagrams. Repository filenames alone do not satisfy this requirement.

Then review the six Round04 planning files on the exact planning commit.

## 2. Required factual baseline

The Critic must preserve these facts:

- Round03 B3 was adequately trained and terminally accounted.
- The final sampler was corrected and exact.
- `anatomy_union_overfit` remained false.
- B4-B9 did not execute.
- The Round03 reviewer token is `ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE`.
- That token reviews the B3-blocked Round03 packet and does not establish a full Route B scientific stop.

A review that calls B3 monitor-only, undertrained, or proof that proposal/refiner/Cine failed is invalid.

## 3. Core scientific question

Judge whether the Round04 revision solves the old gate error without hiding a real implementation defect.

The planning is acceptable only when all of the following are true:

1. Anatomy target semantics are explicit and correct for compact labels, including scar/edema in the union target.
2. A strict train-only micro-overfit remains an implementation gate.
3. Failure of that repaired micro-overfit returns `NEEDS_REVISION`, not a scientific negative.
4. B3 still requires adequate runtime, routing, gradient, no-T2, provenance, and localization evidence.
5. B3 alone cannot classify the whole route adequate negative.
6. B4 and B5 execute after valid B3 readiness, including the prescribed conservative-ROI continuation for a weak but valid proposal.
7. B6 is the first complete MyoPS scientific classification point.
8. B7-B9 form a real Cine lane after B2 and cannot be skipped because of a MyoPS auxiliary-stage metric.
9. A registration miss has a fixed learned/SyN decision branch rather than an invented temporal substitute.
10. The final reviewer, not the controller, classifies candidate, adequate negative, blocker, monitor, evidence gap, or revision.

Reject a document that merely changes the B3 token while leaving anatomy label/optimization ambiguity unresolved.

## 4. Deep-research coverage audit

Check that the contract maps every research requirement to code, stage, evidence, and validator:

- observed-modality inputs and no zero filling;
- four-scale shared/private/interaction retrieval;
- spatial/pathology-conditioned routing;
- optimized Pattern-SIP;
- train/OOF frozen prototypes;
- safe hard-negative queues;
- corrected anatomy union/LV/RV targets;
- separate scar and edema proposals;
- pathology-specific soft ROI and refiners;
- bounded final correction;
- same-split nnU-Net baseline;
- case-wise help/harm and hard subgroups;
- official CineMA source and matched random control;
- faithful seven-step SVF and real SyN;
- registered temporal aggregation;
- full MyoPS and Cine ablation;
- clean reload and official label/export round trip.

Reject any requirement that remains a name without a final-path tensor, training stage, evidence product, or fail-closed validator.

## 5. Leaderboard-facing metric audit

Verify exact coverage of:

```text
myops_scar
myops_edema
myocardium_cinemyops
```

MyoPS must compare against a same-split nnU-Net baseline and report case-wise Dice, HD95, remote-FP, component count, volume ratio, lesion-wise recall, changed voxels, changed components, and help/harm. Required groups are scar-positive, T2-present edema-positive, no-T2 safety, CenterB, CenterC, complete tri-modal, remote-FP-positive, and high-component-burden.

No-T2 cases are safety evidence, not edema-negative training evidence. Both-empty rows cannot earn improvement credit. Compact-label proxy means cannot decide candidate status.

Cine must compare reference-only, unregistered multi-frame, registered temporal full, node-off variants, pretrained/random, and learned-SVF/real-SyN on the same cases and decode.

## 6. Controller executability audit

Check every B0-B10 executor for:

- exact dependency;
- exact input and output paths;
- isolated branch/worktree/result/runtime/log/lock roots;
- explicit write scope;
- one deterministic command;
- environment preflight;
- minimum effective training;
- validator and known-bad matrix;
- success token and failure branch;
- terminal accounting and retry lineage;
- reviewer input.

The controller must not be asked to invent architecture, target semantics, training budget, thresholds, cases, source assets, registration source, temporal inputs, checkpoint selector, Slurm route, retry behavior, evidence naming, or reviewer thresholds.

## 7. Slurm and anti-laziness audit

Verify:

- formal wrappers resolve to `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`;
- compute-node preflight records interpreter, torch/CUDA, optimizer, semantic config, hashes, and writable roots;
- long compatible waits use isolated `htzhulab` plus `a100-gpu` race;
- V100 credit requires exact-config peak memory at or below `14.5 GiB` and never changes scientific semantics;
- training dependencies are `afterok`;
- B10 is `afterany` across every started attempt;
- pending/running/monitor/submitted-only/awaiting-accounting/partial states cannot complete a stage;
- loser and failed attempts receive zero credit and remain in ledgers;
- post-completion aggregation and strict semantic validation are mandatory;
- B10 runs for success, adequate negative, blocker, timeout, preemption, cancellation, and early local gate failure.

Reject validators that only check file presence or completion strings.

## 8. Full ablation and causal evidence audit

Check that every item called an ablation is a real same-checkpoint node intervention with final-output deltas. MyoPS must cover anatomy, anchor support floor, prototypes, hard-negative refresh, interactions, Pattern-SIP, proposal, scar refiner, edema refiner, both refiners, bounded correction, and nnU-Net context. Cine must cover reference-only, unregistered, registered temporal, temporal router, motion/Jacobian, anatomy, uncertainty/quality, matched random, learned SVF, and real SyN.

Reject summary tables relabeled as causal evidence.

## 9. Reviewer-state audit

The reviewer prompt draft must distinguish:

```text
ROUTE_B_ROUND04_REVIEW_EVIDENCE_COMPLETE
ROUTE_B_ROUND04_REVIEW_ADEQUATE_NEGATIVE
ROUTE_B_ROUND04_REVIEW_EXTERNAL_RESOURCE_BLOCKER
ROUTE_B_ROUND04_REVIEW_NEEDS_MONITOR
ROUTE_B_ROUND04_REVIEW_NEEDS_EVIDENCE
ROUTE_B_ROUND04_REVIEW_NEEDS_REVISION
```

An adequate negative requires faithful implementation, adequate training, terminal accounting, and execution of the full available scientific path. A B3 auxiliary metric cannot earn this token.

## 10. Required executable checks

Run at minimum:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/routes/route_B_round04_executor_plan.yaml
git diff --check
```

Run semantic scans for blank execution authority, bare-interpreter formal wrappers, wording that postpones CineMA, registration, or temporal execution, missing Round04 path binding, and missing prohibited-authority flags. Record commands, exits, and findings in the critic review.

## 11. Critic decision

Write exactly one token to `prompts/routes/route_B_round04_critic_review.md`:

```text
ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
```

A ready token must bind the exact planning commit and the blob SHA of all six planning files. Planner push is not critic passage. A later blob or commit change invalidates the token.

## 12. Authority boundary

Critic review authorizes only a later Route B controller start when the ready token is exact and current. It does not authorize validation packaging/upload, route promotion, M11, hosted metric claims, cross-route merge, or final scientific decision.
