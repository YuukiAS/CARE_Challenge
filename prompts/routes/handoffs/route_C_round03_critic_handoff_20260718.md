---
route_id: route_C
portfolio_round: round03
date: 2026-07-18
role: independent_planning_critic_handoff
status: CURRENT_CRITIC_HANDOFF_PENDING_EXECUTABLE_VALIDATION
reviewed_branch: route_C
required_route_head: 8c2f4fef4f25805e8eac1a44628045bbb2875a5a
contract_path: prompts/routes/route_C.md
required_contract_blob: 0f04a06dce5ebaaaa0e0f84ce317b88123fd1a26
executor_plan_path: prompts/routes/route_C_executor_plan.yaml
required_executor_plan_blob: 9b5d0bd369dd95d926337ef2d8c315e7fdbfb982
evidence_mapping_path: prompts/routes/route_C_round03_evidence_mapping.yaml
required_evidence_mapping_blob: 2b5a068ee807c5f622dcd5b1732fdc05e144b960
required_evidence_mapping_row_count: 37
critic_request_path: prompts/routes/route_C_critic_request.md
required_critic_request_blob: 0beb1ef72cc8fb1e712be76a57c11b0fdc04043e
planner_audit_path: prompts/routes/route_C_planner_audit.md
required_planner_audit_blob: f703decf4b8480da467f7f3387a273fe3b66d3eb
critic_output_path: prompts/routes/route_C_round03_critic_review.md
allowed_pass_token: ROUTE_C_ROUND03_PLANNING_READY_FOR_CONTROLLER
allowed_revision_token: ROUTE_C_ROUND03_PLANNING_NEEDS_REVISION
validator_not_run_by_planner: true
controller_start_authorized_before_ready: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# Route C Round03 independent Planning Critic handoff

## Exact binding

Re-fetch and verify exactly:

```text
route_C head: 8c2f4fef4f25805e8eac1a44628045bbb2875a5a
route_C.md blob: 0f04a06dce5ebaaaa0e0f84ce317b88123fd1a26
route_C_executor_plan.yaml blob: 9b5d0bd369dd95d926337ef2d8c315e7fdbfb982
route_C_round03_evidence_mapping.yaml blob: 2b5a068ee807c5f622dcd5b1732fdc05e144b960
route_C_critic_request.md blob: 0beb1ef72cc8fb1e712be76a57c11b0fdc04043e
route_C_planner_audit.md blob: f703decf4b8480da467f7f3387a273fe3b66d3eb
```

Any mismatch makes this handoff stale and requires a new Planner binding.

## Mandatory executable checks

The Planner repaired the YAML representation but had no `/users` shell. A ready token is forbidden until the exact bound commit produces real exit `0` for:

```bash
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python \
  scripts/ops/validate_executor_plan.py \
  prompts/routes/route_C_executor_plan.yaml

/users/a/e/aereinh/CARE/envs/env_CARE/bin/python - <<'PY'
from pathlib import Path
import yaml
plan = yaml.safe_load(Path('prompts/routes/route_C_executor_plan.yaml').read_text(encoding='utf-8'))
assert isinstance(plan, dict)
assert len(plan['executors']) == 5
mapping = yaml.safe_load(Path('prompts/routes/route_C_round03_evidence_mapping.yaml').read_text(encoding='utf-8'))
assert isinstance(mapping, dict)
assert len(mapping['rows']) == 37
print('PASS', len(plan['executors']), len(mapping['rows']))
PY

git diff --check
```

Also run a first-party or Critic-equivalent partition/race/evidence-mapping check. It must prove legal C0/C0B/R1/R2/R3 lanes and waves, every schema field, all three partitions, V100 alternatives, identical evaluator/checkpoint/anchor/scientific hashes, isolated attempt roots, atomic lock, loser zero credit, pending-loser cancellation, retry lineage, all-attempt finalizer coverage, exactly 37 mapping rows, and existence of every executor prompt. Any nonzero or unavailable check requires `ROUTE_C_ROUND03_PLANNING_NEEDS_REVISION`.

## Scientific review boundary

Independently read current main governance, anti-laziness and permanent hard requirements, Slurm and mapper skills, Round02 evidence analysis, Deep Research commit `28c8aac80b7f18f3441c495dc9f2625fc10c460f`, Route C Round02 Critic review, current Route C evidence, M10/follow-up/follow-up2 planning and packets, every C0/C0B/R1/R2/R3 prompt and mapping row, pinned official CineMA source/config/API, and Project SRR-v2/v2.5/v3.

Confirm that Route C remains retrospective: historical M10 SRR-owned final logits and selector are preserved; Route B bounded correction is forbidden; `anchor_residual_control_off_path` remains a required zero-effect off-path control; all architecture/loss/config/split/case/label/preprocess/augmentation/optimizer/budget/checkpoint/decode mismatches require exact historical recovery; R1 is fresh forced all-checkpoint replay with real final-path interventions; R2 only implements official CineMA/SVF/temporal smoke and a freeze candidate; R3 reproduces the Controller final freeze and edits no frozen source.

Reject any credit for old `18/125`, one-case, placeholder, copied, submitted, pending, monitor, partial, or timed-out evidence; any missing immutable anchor, historical selector, clean reload, subgroup, challenge metric, 37-row mapping, official CineMA provenance, matched random control, seven-step SVF, true Jacobian/inverse/SyN, registered temporal consumption, parent continuity, finalizer/mapper/known-bad/reviewer gate; unsafe race; V100 semantic downscaling; or forbidden authority claim.

Write only `prompts/routes/route_C_round03_critic_review.md`. Allowed tokens:

```text
ROUTE_C_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_C_ROUND03_PLANNING_NEEDS_REVISION
```

A ready token authorizes only the Route C Controller as a Codex goal or goal resume on this exact revision. It does not authorize validation upload, route promotion, M11, cross-route merge, hosted metric claims, or a final scientific decision. The Critic does not implement, train, submit or monitor Slurm, or write runtime `review.md`.
