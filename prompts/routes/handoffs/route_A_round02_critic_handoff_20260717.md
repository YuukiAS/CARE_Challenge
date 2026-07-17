---
route_id: route_A
portfolio_round: round02
date: 2026-07-17
status: CURRENT_CRITIC_HANDOFF_READY
planner_main_base_commit: 3f0e78706653da2eeeb3453ed992628a7c0eee70
planner_plan_path: prompts/routes/portfolio_round02_planner_plan_20260717.md
route_branch: route_A
route_planner_commit: bb522e1b2be7ce671db0026a4b94cc1d18937780
contract_path: prompts/routes/route_A.md
contract_blob_sha: 5a847ab00db5a3f2670b7cd518fc2d489f10cd14
executor_plan_path: prompts/routes/route_A_executor_plan.yaml
executor_plan_blob_sha: 59bfcd0b8100eac38f14af72a5a27c1abadc61e6
critic_output_path: prompts/routes/route_A_round02_critic_review.md
allowed_ready_token: ROUTE_A_ROUND02_PLANNING_READY_FOR_CONTROLLER
allowed_revision_token: ROUTE_A_ROUND02_PLANNING_NEEDS_REVISION
controller_start_authorized_before_critic: false
critic_must_not_execute: true
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# route_A Round02 Critic Handoff

This is a planning-only, route-specific Critic assignment. Read the current remote `main` policies and this handoff, then read the contract and executor plan from `route_A` at exactly `bb522e1b2be7ce671db0026a4b94cc1d18937780`. Re-fetch both files and require the blob SHAs in the frontmatter. A changed branch head, contract blob, or plan blob makes this handoff stale; stop with `ROUTE_A_ROUND02_PLANNING_NEEDS_REVISION` rather than reviewing another revision under this token.

The prior runtime review decision was `ROUTE_A_REVIEW_NEEDS_REVISION`. The Planner's new controller-forward hypothesis is: compressed two-scale live-evidence SRR with supervised bounded pathology gates, exact no-T2 zero correction, and frozen real CineMA + SyN + temporal refiner.

Before judgment, independently visually read the Project-background SRR-v2, SRR-v2.5, and SRR-v3 diagrams. Read `AGENTS.md`, `START_HERE_FOR_GPT.md`, `GPT_PLANNER_CARE_PROTOCOL.md`, `prompts/AGENT_FLOW_V2_PROTOCOL.md`, `prompts/HANDOFF_GATE_POLICY.md`, `prompts/GPT_HARD_GATE_PROMPT.md`, `prompts/routes/README.md`, `prompts/routes/route_portfolio_planner_prompt.md`, `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`, `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`, `.agents/skills/slurm-routing-partition/SKILL.md`, `.agents/skills/care-mapper/SKILL.md`, `routes/README.md`, and `wiki/README.md`. Read the route's latest `result.md`, `controller_report.md`, `completion_check.md`, `review.md`, validators, and every lightweight packet file cited by the new contract.

The Critic must verify that the changed final-output gate is trained and intervenable on real cases; a second adequate zero-effect run cannot be described as a candidate.

## Required rejection checks

Reject the plan when any of the following is true:

- nnU-Net-only, postprocess-only, wrapper-only, or zero-changed-voxel path can reach candidate-ready.
- the validator/known-bad scope does not close the prior semantic and stale-receipt blockers.
- Cine is frame0-only, fake-temporal, binary-prior-only, postprocess-only, or lacks at least four registered non-reference frames.
- the T2-positive edema manifest has fewer than six cases but the route can still claim candidate readiness.
- training budgets, metric thresholds, paths, Slurm rules, or reviewer judgment are left for the controller.

Also reject status-only, audit-only, wait-only, runnable-only, engineering-only, proxy-only, validator-only, placeholder/mock/dataclass/contract-JSON-only work; substitution of `foreground_mean` or compact proxies for the three leaderboard metrics; missing same-split baseline or help/harm matrix; monitor/submitted-only completion; semantic validators that check only existence; omitted mechanism naming/fingerprint/hash binding; non-durable finalization; runtime push; or non-independent review.

## Critic output contract

Write only `prompts/routes/route_A_round02_critic_review.md` on `route_A`. It must record the exact reviewed commit and file hashes, diagram versions/visual-read status, every required source read, findings, revisions required, and one decision token. Emit `ROUTE_A_ROUND02_PLANNING_READY_FOR_CONTROLLER` only when the controller can execute the task without deciding model structure, loss, sampling, budget, paths, Slurm strategy, checkpoint rules, validator semantics, known-bad fixtures, stop conditions, completion states, finalizer behavior, or reviewer pass/fail.

The ready token authorizes only the corresponding controller start. It does not authorize validation packaging/upload, route promotion, M11, cross-route merge, hosted metric claims, or a final scientific decision.
