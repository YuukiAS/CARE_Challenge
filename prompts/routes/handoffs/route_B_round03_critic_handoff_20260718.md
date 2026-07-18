---
route_id: route_B
portfolio_round: round03
date: 2026-07-18
role: independent_planning_critic_handoff
status: CURRENT_CRITIC_HANDOFF_PENDING_EXECUTABLE_VALIDATION
reviewed_branch: route_B
required_route_head: a282007ecab44274699ab49a389ba107ac04d5b2
contract_path: prompts/routes/route_B.md
required_contract_blob: 2d82b8bb5d05e521adb87281a663fd7fe38582c6
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
required_executor_plan_blob: 83494fbf40df7b79c26c3be3c00d51e23830208c
critic_request_path: prompts/routes/route_B_critic_request.md
required_critic_request_blob: 50fba61a5512e4ba7b124fd2355ca84c2a688ed8
planner_audit_path: prompts/routes/route_B_planner_audit.md
required_planner_audit_blob: 3a0d422ed81695f77750f59ebfdca38700c69516
critic_output_path: prompts/routes/route_B_round03_critic_review.md
allowed_pass_token: ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
allowed_revision_token: ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
validator_not_run_by_planner: true
controller_start_authorized_before_ready: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# Route B Round03 independent Planning Critic handoff

## Exact binding

Re-fetch and verify exactly:

```text
route_B head: a282007ecab44274699ab49a389ba107ac04d5b2
route_B.md blob: 2d82b8bb5d05e521adb87281a663fd7fe38582c6
route_B_executor_plan.yaml blob: 83494fbf40df7b79c26c3be3c00d51e23830208c
route_B_critic_request.md blob: 50fba61a5512e4ba7b124fd2355ca84c2a688ed8
route_B_planner_audit.md blob: 3a0d422ed81695f77750f59ebfdca38700c69516
```

Any mismatch makes this handoff stale and requires a new Planner binding.

## Mandatory executable checks

The Planner repaired the YAML representation but had no `/users` shell. A ready token is forbidden until the exact bound commit produces real exit `0` for:

```bash
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python \
  scripts/ops/validate_executor_plan.py \
  prompts/routes/route_B_executor_plan.yaml

/users/a/e/aereinh/CARE/envs/env_CARE/bin/python - <<'PY'
from pathlib import Path
import yaml
p = Path('prompts/routes/route_B_executor_plan.yaml')
data = yaml.safe_load(p.read_text(encoding='utf-8'))
assert isinstance(data, dict)
assert len(data['executors']) == 11
print('PASS', len(data['executors']))
PY

git diff --check
```

Also run a first-party or Critic-equivalent partition/race static check. It must parse B2–B10 and prove all three partitions, per-partition preflight commands/receipts, explicit V100 alternatives, identical scientific hashes, isolated output/log/checkpoint/cache roots, shared atomic winner locks, loser zero credit, pending-loser cancellation, retry lineage, all-attempt finalizer coverage, and existence of every B0–B10 prompt path. Any nonzero or unavailable check requires `ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION`.

## Scientific review boundary

Independently read current main governance, anti-laziness and permanent hard requirements, Slurm and mapper skills, Round02 evidence analysis, Deep Research commit `28c8aac80b7f18f3441c495dc9f2625fc10c460f`, Route B Round02 Critic review, current Route B evidence, every B0–B10 prompt, first-party source named in the contract, pinned official CineMA source/config/API, and Project SRR-v2/v2.5/v3.

Confirm the repair did not weaken canonical `[LGE,T2,C0]`, four scales `[32,64,128,256]`, sixteen experts per scale, pathology-specific two-pass routing, numerical Pattern-SIP/full loss, fold-safe OOF-fitted inference-frozen prototypes, safe negatives, separate scar/edema proposal/ROI/refiners, bounded final correction, no-T2 exact-zero semantics, official CineMA matched random control with common downstream initialization, seven-step SVF and real SyN, registered temporal consumption, B2 implementation gate before long training, semantic known-bad fixtures, durable finalizer, mapper/fingerprint receipts, or reviewer tokens.

Reject any nnU-Net/wrapper/postprocess/two-scale downgrade, bootstrap/EMA formal memory, OOF leakage, no-T2 edema negative, disconnected final path, zero MyoPS effect hidden by Cine, unsafe race, V100 semantic downscaling, monitor/undertrained/stale completion, or forbidden authority claim.

Write only `prompts/routes/route_B_round03_critic_review.md`. Allowed tokens:

```text
ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
```

A ready token authorizes only the Route B Controller as a Codex goal or goal resume on this exact revision. It does not authorize validation upload, route promotion, M11, cross-route merge, hosted metric claims, or a final scientific decision. The Critic does not implement, train, submit or monitor Slurm, or write runtime `review.md`.
