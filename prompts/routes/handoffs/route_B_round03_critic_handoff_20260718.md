---
route_id: route_B
portfolio_round: round03
date: 2026-07-18
role: independent_planning_critic_handoff
status: CURRENT_CRITIC_HANDOFF
reviewed_branch: route_B
required_route_head: 4c2f2ec146f5cc7a026cf4d5369c79b863f88ad2
contract_path: prompts/routes/route_B.md
required_contract_blob: 2d82b8bb5d05e521adb87281a663fd7fe38582c6
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
required_executor_plan_blob: e95757507c1025ae9e7538f64c4143ead899d05f
critic_request_path: prompts/routes/route_B_critic_request.md
required_critic_request_blob: e9917375f549368a99348a91ca4dd0d1aa9a8932
planner_audit_path: prompts/routes/route_B_planner_audit.md
required_planner_audit_blob: e0f0cca68bd27db0b452a5f35270d57afd8fbf54
critic_output_path: prompts/routes/route_B_round03_critic_review.md
allowed_pass_token: ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
allowed_revision_token: ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
controller_start_authorized_before_ready: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# Route B Round03 independent Planning Critic handoff

## Binding gate

Re-fetch and verify exactly:

```text
route_B head: 4c2f2ec146f5cc7a026cf4d5369c79b863f88ad2
route_B.md blob: 2d82b8bb5d05e521adb87281a663fd7fe38582c6
route_B_executor_plan.yaml blob: e95757507c1025ae9e7538f64c4143ead899d05f
route_B_critic_request.md blob: e9917375f549368a99348a91ca4dd0d1aa9a8932
route_B_planner_audit.md blob: e0f0cca68bd27db0b452a5f35270d57afd8fbf54
```

Any mismatch makes this handoff stale. Stop and request a new Planner binding.

## Required review

Read current main governance, schemas, route policies, Slurm and mapper skills, Round02 comprehensive analysis, Deep Research commit `28c8aac80b7f18f3441c495dc9f2625fc10c460f`, Route B Round02 Critic review, latest Route B packet/validators, all eleven Round03 executor prompts, the first-party source files named in the contract, and pinned official CineMA source/config/API.

Independently visually read Project SRR-v2, SRR-v2.5, and SRR-v3. Planner prose and repository image filenames are not substitutes.

On the exact bound commit, record real exit codes for:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/routes/route_B_executor_plan.yaml
git diff --check
```

Also parse B2-B10 and verify all three partitions, per-partition preflight commands/receipts, V100 alternatives, agreement of `routing_policy` and `routing_race_policy`, identical race hashes, isolated roots, atomic lock, loser zero credit, pending-loser cancellation, retry lineage, finalizer coverage, and existence of every prompt path. Any nonzero or unavailable required check yields `ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION`.

Reject the plan if the Controller can choose architecture, modality order, expert topology, Pattern-SIP/losses, OOF fitting, safe negatives, proposal/ROI/refiner/gate, training budget, CineMA hook/control, registration math/gates, temporal inputs/resume, selector, partition assignment, retry/finalizer, known-bad behavior, or reviewer criteria.

Explicitly close the ten Round02 blockers: exact phase contracts; manifests/hashes/sampler; numeric Pattern-SIP/full loss/experts; fixed write scope; verified CineMA/registration interface; common downstream initialization; executable known-bad fixtures; stop/continuation states; compute preflight/durable finalizer; machine-bound reviewer tokens.

Write only `prompts/routes/route_B_round03_critic_review.md`. Allowed tokens:

```text
ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
```

A ready token authorizes only the exact Route B Controller revision. It does not authorize validation upload, promotion, M11, cross-route merge, hosted claims, or a final scientific decision. The Critic does not implement, train, submit/monitor Slurm, or write runtime `review.md`.