---
route_id: route_B
portfolio_round: round02
date: 2026-07-17
status: CURRENT_CRITIC_HANDOFF_READY
planner_main_base_commit: 3f0e78706653da2eeeb3453ed992628a7c0eee70
planner_plan_path: prompts/routes/portfolio_round02_planner_plan_20260717.md
route_branch: route_B
route_planner_commit: cae72e41b08cbf2a7e2b0d137b62eed13fab66c7
contract_path: prompts/routes/route_B.md
contract_blob_sha: 0608f6570d7bbb7aeaa919294abb2210eecbb327
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
executor_plan_blob_sha: 49fecee5bd77572392096e94f0c1e823570076d5
critic_output_path: prompts/routes/route_B_round02_critic_review.md
allowed_ready_token: ROUTE_B_ROUND02_PLANNING_READY_FOR_CONTROLLER
allowed_revision_token: ROUTE_B_ROUND02_PLANNING_NEEDS_REVISION
controller_start_authorized_before_critic: false
critic_must_not_execute: true
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# route_B Round02 Critic Handoff

This is a planning-only, route-specific Critic assignment. Read the current remote `main` policies and this handoff, then read the contract and executor plan from `route_B` at exactly `cae72e41b08cbf2a7e2b0d137b62eed13fab66c7`. Re-fetch both files and require the blob SHAs in the frontmatter. A changed branch head, contract blob, or plan blob makes this handoff stale; stop with `ROUTE_B_ROUND02_PLANNING_NEEDS_REVISION` rather than reviewing another revision under this token.

The prior runtime review decision was `ROUTE_B_REVIEW_NEEDS_REVISION`. The Planner's new controller-forward hypothesis is: full four-scale/16-slot SRR-v3 causal chain, T2-positive-balanced MyoPS run, and real frozen CineMA versus a matched frozen random source feeding identical registration/temporal heads.

Before judgment, independently visually read the Project-background SRR-v2, SRR-v2.5, and SRR-v3 diagrams. Read `AGENTS.md`, `START_HERE_FOR_GPT.md`, `GPT_PLANNER_CARE_PROTOCOL.md`, `prompts/AGENT_FLOW_V2_PROTOCOL.md`, `prompts/HANDOFF_GATE_POLICY.md`, `prompts/GPT_HARD_GATE_PROMPT.md`, `prompts/routes/README.md`, `prompts/routes/route_portfolio_planner_prompt.md`, `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`, `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`, `.agents/skills/slurm-routing-partition/SKILL.md`, `.agents/skills/care-mapper/SKILL.md`, `routes/README.md`, and `wiki/README.md`. Read the route's latest `result.md`, `controller_report.md`, `completion_check.md`, `review.md`, validators, and every lightweight packet file cited by the new contract.

The Critic must independently verify that the random source differs only in representation-source initialization and that downstream evidence remains bound to the clean-reloaded pretrained source.

## Required rejection checks

Reject the plan when any of the following is true:

- the full SRR-v3 chain is reduced to the Route A compressed design or a generic residual head.
- Pattern-SIP, OOF memory, spatial retrieval, proposals, refiners, or final interventions are declaration/config/CSV-only.
- the new evaluation can again contain no positive edema ground truth.
- CineMA logits/features/uncertainty are absent, the random control is unmatched, or Cine is treated as future work.
- the already-passed prior long run is repeated without the specified changed architecture/evaluation semantics.
- training budgets, paths, Slurm/checkpoint selection, validator semantics, or reviewer judgment are left for the controller.

Also reject status-only, audit-only, wait-only, runnable-only, engineering-only, proxy-only, validator-only, placeholder/mock/dataclass/contract-JSON-only work; substitution of `foreground_mean` or compact proxies for the three leaderboard metrics; missing same-split baseline or help/harm matrix; monitor/submitted-only completion; semantic validators that check only existence; omitted mechanism naming/fingerprint/hash binding; non-durable finalization; runtime push; or non-independent review.

## Critic output contract

Write only `prompts/routes/route_B_round02_critic_review.md` on `route_B`. It must record the exact reviewed commit and file hashes, diagram versions/visual-read status, every required source read, findings, revisions required, and one decision token. Emit `ROUTE_B_ROUND02_PLANNING_READY_FOR_CONTROLLER` only when the controller can execute the task without deciding model structure, loss, sampling, budget, paths, Slurm strategy, checkpoint rules, validator semantics, known-bad fixtures, stop conditions, completion states, finalizer behavior, or reviewer pass/fail.

The ready token authorizes only the corresponding controller start. It does not authorize validation packaging/upload, route promotion, M11, cross-route merge, hosted metric claims, or a final scientific decision.
