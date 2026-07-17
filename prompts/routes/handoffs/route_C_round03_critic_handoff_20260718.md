---
route_id: route_C
portfolio_round: round03
date: 2026-07-18
role: independent_planning_critic_handoff
status: CURRENT_CRITIC_HANDOFF
reviewed_branch: route_C
required_route_head: e9966da52b65367a248dbcc746879fcac2422961
contract_path: prompts/routes/route_C.md
required_contract_blob: 0f04a06dce5ebaaaa0e0f84ce317b88123fd1a26
executor_plan_path: prompts/routes/route_C_executor_plan.yaml
required_executor_plan_blob: 7e3bd792bf15d1778a227df6e5216d4b440c868d
evidence_mapping_path: prompts/routes/route_C_round03_evidence_mapping.yaml
required_evidence_mapping_blob: 2b5a068ee807c5f622dcd5b1732fdc05e144b960
critic_request_path: prompts/routes/route_C_critic_request.md
required_critic_request_blob: 314a479e98d2af888cfd945092ab6aef09860a83
planner_audit_path: prompts/routes/route_C_planner_audit.md
required_planner_audit_blob: 623216e8f1b1ecc64f3d6fb8d17b9f1f8711e595
critic_output_path: prompts/routes/route_C_round03_critic_review.md
allowed_pass_token: ROUTE_C_ROUND03_PLANNING_READY_FOR_CONTROLLER
allowed_revision_token: ROUTE_C_ROUND03_PLANNING_NEEDS_REVISION
controller_start_authorized_before_ready: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# Route C Round03 independent Planning Critic handoff

## Binding gate

Re-fetch and verify exactly:

```text
route_C head: e9966da52b65367a248dbcc746879fcac2422961
route_C.md blob: 0f04a06dce5ebaaaa0e0f84ce317b88123fd1a26
route_C_executor_plan.yaml blob: 7e3bd792bf15d1778a227df6e5216d4b440c868d
route_C_round03_evidence_mapping.yaml blob: 2b5a068ee807c5f622dcd5b1732fdc05e144b960
route_C_critic_request.md blob: 314a479e98d2af888cfd945092ab6aef09860a83
route_C_planner_audit.md blob: 623216e8f1b1ecc64f3d6fb8d17b9f1f8711e595
```

Any mismatch makes this handoff stale. Stop and request a new Planner binding.

## Required review

Read current main governance, schemas, route policies, Slurm and mapper skills, Round02 comprehensive analysis, Deep Research commit/path, Route C Round02 Critic review, latest Route C packet and validators, the 20260711 M10 planning review, 20260714 continuation review, 20260715 follow-up2 review, partial-evidence note, all five Round03 executor prompts, every evidence-mapping row, and pinned official CineMA source/config/API.

Independently visually read Project SRR-v2, SRR-v2.5, and SRR-v3. Verify that Route C preserves the historical SRR-owned final logits and does not adopt Route B bounded correction.

On the exact bound commit, record real exits for:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/routes/route_C_executor_plan.yaml
git diff --check
```

Also parse the plan and mapping to verify:

- legal lanes and distinct waves `C0/C0B/R1/R2/R3 = tooling1/myops2/myops3/cine4/cine5`;
- every schema-required field, singular write scope, exact prompt/command/output/token, earlier-wave dependency, and executor-local Slurm/retry/preflight fields;
- all three partitions with per-partition preflight commands/receipts, V100 alternatives, matching `routing_policy`/`routing_race_policy`, race isolation/lock/cancellation/zero-credit/finalizer rules;
- all 37 old-requirement rows have exact file, required fields, producer, validator, and reviewer check;
- every declared executor prompt exists.

Any nonzero or unavailable required check yields `ROUTE_C_ROUND03_PLANNING_NEEDS_REVISION`.

Reject if Route C can redesign MyoPS, copy Route B, replace the historical selector, treat `anchor_residual_control_off_path` as causal, credit old `18/125`/one-case/placeholder/monitor evidence, waive train-time fingerprint mismatches, permit R1 model edits, let R2 self-freeze/formally train, let R3 edit frozen source, substitute fake CineMA/proxy registration/`temporal_z`, credit partial temporal runtime, omit mapped evidence, or leave reviewer/finalizer/authority rules ambiguous.

Explicitly close the Round02 blockers: schema-valid five-executor graph; exact inherited evidence mapping; and machine-bound runtime reviewer tokens with required evidence, validator/adequacy/accounting gates, rejection criteria, next actor, and blocked authorities.

Write only `prompts/routes/route_C_round03_critic_review.md`. Allowed tokens:

```text
ROUTE_C_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_C_ROUND03_PLANNING_NEEDS_REVISION
```

A ready token authorizes only the exact Route C Controller revision. It does not authorize validation upload, promotion, M11, cross-route merge, hosted claims, or a final scientific decision. The Critic does not implement, train, submit/monitor Slurm, or write runtime `review.md`.