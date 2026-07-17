---
route_id: route_B
portfolio_round: round02
role: planner_to_critic
status: CRITIC_REVIEW_REQUESTED
branch: route_B
planner_main_base_commit: 3f0e78706653da2eeeb3453ed992628a7c0eee70
contract_path: prompts/routes/route_B.md
contract_sha256: ba64db456f8c7df9b788f319963324f12d1f659956f47d9dc49f96a17784bcf4
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
executor_plan_sha256: 5f83034e8f126c468f810bbfcf659c79e87fcc7352d29e1288f56767b08480ab
planner_audit_path: prompts/routes/route_B_planner_audit.md
planner_audit_sha256: 32933549ab5e807de72fcc441d01dd26aa205cb23dab7e450448f1083c64862e
critic_review_output_path: prompts/routes/route_B_round02_critic_review.md
allowed_pass_token: ROUTE_B_ROUND02_PLANNING_READY_FOR_CONTROLLER
controller_start_before_pass_forbidden: true
critic_must_not_execute: true
---

# Route B Round02 independent Critic request

Review the exact Route B branch commit named by the current main handoff and recompute the bound hashes. Independently read the current main hard matrix and anti-laziness protocol, the prior Route B result/controller/completion/review/validator evidence, and SRR-v2/v2.5/v3 visually.

Reject the plan when it:

1. reduces Route B to the Route A two-scale compressed architecture, a residual-only head, an nnU-Net wrapper, or a validator repair;
2. omits any of modality stems, sixteen-slot shared/private/interaction dictionary, two-pass spatial router, real Pattern-SIP, OOF memory, anatomy decoder, pathology proposals, soft ROIs, separate refiners, bounded correction, save/reload/export, or final-output interventions;
3. permits old-wrapper, mock, dataclass, config, or CSV-only completion;
4. repeats the previous MyoPS run without the declared pathology-balanced sampling and positive-edema evaluation;
5. can become ready with fewer than eight T2-present edema-positive cases;
6. treats Cine as future work, uses frame0/binary CineMA output, omits weight/license/SHA, omits matched random control, or fails to feed registered logits/features/uncertainty into the temporal path;
7. leaves architecture, budget, paths, Slurm routing, selection, validator, known-bad, stop states, or reviewer criteria to the controller;
8. repeats already adequate runtime without a changed training semantic;
9. lets pending, monitor, undertrained, stale-token, or inconsistent packets stop execution before required accounting/aggregation;
10. authorizes upload, promotion, M11, hosted claims, cross-route merge, or final scientific resolution.

The Critic must verify the exact optimizer/budgets, checkpoint schedule, lexicographic selector, pretrained/random classification, downstream pretrained source rule, metric gates, help/harm matrix, per-batch invalid-slot evidence, memory provenance, Pattern-SIP gradients, implementation/packet validators, semantic known-bad fixtures, route-local mapper/fingerprint receipts, durable finalizer, no-push, and independent reviewer.

The only passing token is:

`ROUTE_B_ROUND02_PLANNING_READY_FOR_CONTROLLER`

It authorizes only a Route B controller start on the reviewed commit.
