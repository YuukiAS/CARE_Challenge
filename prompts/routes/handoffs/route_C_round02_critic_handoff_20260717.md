---
route_id: route_C
portfolio_round: round02
date: 2026-07-17
status: CURRENT_CRITIC_HANDOFF_READY
planner_main_base_commit: 3f0e78706653da2eeeb3453ed992628a7c0eee70
planner_plan_path: prompts/routes/portfolio_round02_planner_plan_20260717.md
route_branch: route_C
route_planner_commit: a68b7413775e00b96634219ee9453ba47e73d4e0
contract_path: prompts/routes/route_C.md
contract_blob_sha: cc91ceba82dc6056d75ea904107ac8ba22e93186
executor_plan_path: prompts/routes/route_C_executor_plan.yaml
executor_plan_blob_sha: 7c154736004912f0bfd31d5eef9c129158ed48f5
critic_output_path: prompts/routes/route_C_round02_critic_review.md
allowed_ready_token: ROUTE_C_ROUND02_PLANNING_READY_FOR_CONTROLLER
allowed_revision_token: ROUTE_C_ROUND02_PLANNING_NEEDS_REVISION
controller_start_authorized_before_critic: false
critic_must_not_execute: true
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# route_C Round02 Critic Handoff

This is a planning-only, route-specific Critic assignment. Read the current remote `main` policies and this handoff, then read the contract and executor plan from `route_C` at exactly `a68b7413775e00b96634219ee9453ba47e73d4e0`. Re-fetch both files and require the blob SHAs in the frontmatter. A changed branch head, contract blob, or plan blob makes this handoff stale; stop with `ROUTE_C_ROUND02_PLANNING_NEEDS_REVISION` rather than reviewing another revision under this token.

The prior runtime review decision was `ROUTE_C_REVIEW_NEEDS_REVISION_CONFIRMED`. The Planner's new controller-forward hypothesis is: complete M10/follow-up/follow-up2 inheritance: fingerprint recovery, fresh all-checkpoint replay, faithful graph interventions, real CineMA adapter/random control, diffeomorphic registration plus SyN, and registration-gated cumulative temporal runtime.

Before judgment, independently visually read the Project-background SRR-v2, SRR-v2.5, and SRR-v3 diagrams. Read `AGENTS.md`, `START_HERE_FOR_GPT.md`, `GPT_PLANNER_CARE_PROTOCOL.md`, `prompts/AGENT_FLOW_V2_PROTOCOL.md`, `prompts/HANDOFF_GATE_POLICY.md`, `prompts/GPT_HARD_GATE_PROMPT.md`, `prompts/routes/README.md`, `prompts/routes/route_portfolio_planner_prompt.md`, `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`, `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`, `.agents/skills/slurm-routing-partition/SKILL.md`, `.agents/skills/care-mapper/SKILL.md`, `routes/README.md`, and `wiki/README.md`. Read the route's latest `result.md`, `controller_report.md`, `completion_check.md`, `review.md`, validators, and every lightweight packet file cited by the new contract.

The Critic must read all three M10 planning reviews, the partial-evidence note, current_state, COMPARISON, and every M09/M10 history file listed by the handoff before judging this plan.

## Required rejection checks

Reject the plan when any of the following is true:

- any old M10/follow-up/follow-up2 requirement is removed, weakened, or made future work.
- old partial, submitted, timed-out, synthetic, contract-only, or 18/125 replay evidence receives completion credit.
- the off-path anchor residual control is mislabeled as a causal intervention or used to avoid real final-path interventions.
- fresh replay lacks --evaluate --force, all 44 cases, hashes, exact selector, clean reload, or D2/D3 real interventions.
- CineMA asset/data unblock lacks exact URL/revisions/license/SHA/path/commands or permits a fake/binary/frame0 substitute.
- pretrained/random controls are unmatched, selected checkpoints are not reloaded, registration is proxy/direct-velocity, SyN is not real, or temporal does not consume selected registered evidence.
- R3 may edit source or the controller can waive budgets, gates, paths, Slurm rules, validators, known-bad, or reviewer criteria.

Also reject status-only, audit-only, wait-only, runnable-only, engineering-only, proxy-only, validator-only, placeholder/mock/dataclass/contract-JSON-only work; substitution of `foreground_mean` or compact proxies for the three leaderboard metrics; missing same-split baseline or help/harm matrix; monitor/submitted-only completion; semantic validators that check only existence; omitted mechanism naming/fingerprint/hash binding; non-durable finalization; runtime push; or non-independent review.

## Critic output contract

Write only `prompts/routes/route_C_round02_critic_review.md` on `route_C`. It must record the exact reviewed commit and file hashes, diagram versions/visual-read status, every required source read, findings, revisions required, and one decision token. Emit `ROUTE_C_ROUND02_PLANNING_READY_FOR_CONTROLLER` only when the controller can execute the task without deciding model structure, loss, sampling, budget, paths, Slurm strategy, checkpoint rules, validator semantics, known-bad fixtures, stop conditions, completion states, finalizer behavior, or reviewer pass/fail.

The ready token authorizes only the corresponding controller start. It does not authorize validation packaging/upload, route promotion, M11, cross-route merge, hosted metric claims, or a final scientific decision.
