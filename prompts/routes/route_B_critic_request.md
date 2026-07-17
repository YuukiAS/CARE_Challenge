---
route_id: route_B
portfolio_round: round03
date: 2026-07-18
role: planner_to_critic
status: CRITIC_REVIEW_REQUESTED
branch: route_B
planner_main_base_commit: 6ed0a3bac82aa0ee8cb44250da0c2648965c6b42
contract_path: prompts/routes/route_B.md
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
planner_audit_path: prompts/routes/route_B_planner_audit.md
critic_review_output_path: prompts/routes/route_B_round03_critic_review.md
allowed_pass_token: ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
allowed_revision_token: ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
controller_start_before_pass_forbidden: true
critic_must_not_execute_model_or_training: true
---

# Route B Round03 independent Planning Critic request

Review only the exact Route B commit and contract/executor-plan/audit/request blobs named by the current main Round03 handoff. Re-fetch the branch and blobs before review; any mismatch makes the handoff stale.

Independently read current main governance, anti-laziness, hard matrix, Slurm and mapper skills, Round02 comprehensive evidence analysis, Deep Research commit `28c8aac80b7f18f3441c495dc9f2625fc10c460f`, Route B Round02 Critic review, latest Route B result/review/controller/completion/finalizer/implementation/validator/metrics/safety evidence, every Round03 executor prompt, the first-party source files named in the contract, pinned official CineMA source/config/API, and SRR-v2/v2.5/v3 through the Project visual channel.

The Critic must run, on the exact bound commit, and record real exit codes for:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/routes/route_B_executor_plan.yaml
<first-party Round03 partition/race static validator command after B0 assets exist, or a Critic-side equivalent that verifies every declared field>
git diff --check
```

The Planner did not execute shell by user instruction. A static review is not enough for a ready token. Any nonzero or unavailable required validator yields `ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION`.

Reject the plan if any of the following remains possible:

1. legacy `[LGE,C0,T2]`, old two-scale wrapper, nnU-Net-only, residual-only, config/mock/CSV-only, or shared-source scope expansion;
2. fewer than four scales or sixteen experts, incomplete pathology routing, Pattern-SIP alias/no gradient, invalid-slot activity, or Controller-selected model/loss choices;
3. bootstrap/EMA formal memory, OOF leakage, no-T2 edema negatives, missing eight-case edema-positive/CenterB/CenterC coverage, or unresolved sampler overlap;
4. proposal/refiner/gate not affecting final labels, hard ROI deletion, zero MyoPS effect masked by Cine, or missing lesion-centric Dice/HD95/remote-FP/component/volume evidence;
5. formal stage without exact steps/time/validation/checkpoints/entry/exit/failure rules, or a stage advancing after a failed gate;
6. fake official CineMA, wrong code/HF/weight/license/SHA/class/feature-hook/preprocessing provenance, frame0/binary output, or unmatched pretrained/random control;
7. direct velocity displacement, missing seven-step integration, proxy Jacobian/inverse/SyN, pair-as-case credit, missing denominators, or unreloaded registration;
8. abstract `temporal_z`, unconsumed fields, unregistered/frame0 fallback, broken cumulative resume/parent hashes, or partial/timeout credit;
9. pending/monitor/awaiting-accounting/undertrained/stale/validator-failed packet treated as ready;
10. inconsistent race hashes, shared output/cache/checkpoints, missing atomic lock, loser credit, uncancelled pending loser, V100 semantic downscaling, or unproven V100 compatibility claim;
11. incomplete finalizer, mapper/fingerprint, strict semantic known-bad, reviewer token rules, or authority boundary;
12. any validation upload, promotion, M11, cross-route merge, hosted metric, or final scientific authorization.

The Critic must specifically adjudicate all ten Round02 blockers: exact per-phase contracts; manifests/hashes/sampler strata; numeric Pattern-SIP/loss/experts; fixed write scope; verified CineMA/registration API; common downstream-init artifact; executable fixtures; state/continuation rules; compute-node preflight/durable finalizer; and machine-bound reviewer tokens.

Only these planning tokens are valid:

```text
ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
```

A ready token authorizes only the Route B Controller to start on the exact reviewed commit. It does not authorize validation upload, route promotion, M11, cross-route merge, hosted claims, or a final scientific decision.