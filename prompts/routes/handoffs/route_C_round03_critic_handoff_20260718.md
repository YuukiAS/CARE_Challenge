---
route_id: route_C
portfolio_round: round03
date: 2026-07-18
role: independent_planning_critic_handoff
status: CURRENT_CRITIC_HANDOFF_READY_FOR_FAST_RECEIPT_REVIEW
reviewed_branch: route_C
required_route_head: 1a019100f3379104b00e3d2e49a3c78a2fbfe575
contract_path: prompts/routes/route_C.md
required_contract_blob: 0f04a06dce5ebaaaa0e0f84ce317b88123fd1a26
executor_plan_path: prompts/routes/route_C_executor_plan.yaml
required_executor_plan_blob: 9b5d0bd369dd95d926337ef2d8c315e7fdbfb982
evidence_mapping_path: prompts/routes/route_C_round03_evidence_mapping.yaml
required_evidence_mapping_blob: 2b5a068ee807c5f622dcd5b1732fdc05e144b960
required_evidence_mapping_row_count: 37
critic_request_path: prompts/routes/route_C_critic_request.md
required_critic_request_blob: a291cc4a93c557623a019b136dc588f68731359f
planner_audit_path: prompts/routes/route_C_planner_audit.md
required_planner_audit_blob: 320b87fbf7e6f5352561823eaf671ab15be71a56
critic_output_path: prompts/routes/route_C_round03_critic_review.md
allowed_pass_token: ROUTE_C_ROUND03_PLANNING_READY_FOR_CONTROLLER
allowed_revision_token: ROUTE_C_ROUND03_PLANNING_NEEDS_REVISION
validator_not_run_by_planner: true
coordinator_local_receipts_recorded: true
coordinator_repair_scope: server_unavailable_receipts_only
controller_start_authorized_before_ready: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
coordinator_partition_race_evidence_mapping_static_check: PASS_EXIT_0_COORDINATOR_20260718
---

# Route C Round03 independent Planning Critic handoff

## Exact binding

Re-fetch and verify exactly:

```text
route_C head: 1a019100f3379104b00e3d2e49a3c78a2fbfe575
route_C.md blob: 0f04a06dce5ebaaaa0e0f84ce317b88123fd1a26
route_C_executor_plan.yaml blob: 9b5d0bd369dd95d926337ef2d8c315e7fdbfb982
route_C_round03_evidence_mapping.yaml blob: 2b5a068ee807c5f622dcd5b1732fdc05e144b960
route_C_critic_request.md blob: a291cc4a93c557623a019b136dc588f68731359f
route_C_planner_audit.md blob: 320b87fbf7e6f5352561823eaf671ab15be71a56
```

Any mismatch makes this handoff stale and requires a new Planner binding.

## Coordinator local executable receipts

The Planner had no `/users` shell, but the coordinator has now run the required local checks on `/users/a/e/aereinh/CARE_worktrees/route_C` at the exact bound head without starting a controller, Slurm job, or training. The Critic may re-run them, but must not fail this handoff merely because the original Planner server was unavailable. Recorded exits:

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

Coordinator evidence-mapping check: exit 0. PyYAML parsed `executors=5` and `route_C_round03_evidence_mapping.yaml` `rows=37`; `git diff --check` exit 0. This removes only the server-unavailable validation blocker and does not change the Route C scientific contract. The Critic should review the recorded receipts and inherited hardening gates; any new nonzero executable check still requires `ROUTE_C_ROUND03_PLANNING_NEEDS_REVISION`.

Coordinator partition/race/evidence-mapping static check: `PASS_EXIT_0`. Receipt from `/users/a/e/aereinh/CARE_worktrees/route_C`: `PASS route_C critic_equivalent_partition_race_evidence_mapping_static_check slurm_executors=4 prompt_paths=5 mapping_rows=37`. This check verified legal prompt paths, three-partition declarations, preflight receipt locations, isolated attempt roots, atomic locks, loser zero credit, pending-loser cancellation, retry lineage, all-attempt finalizer coverage, and actual evidence mapping rows `C_MAP_001_*` through `C_MAP_037_*` with required fields, producer, validator and reviewer checks.


## Fast receipt review scope

This handoff supersedes the previous Round03 handoff only to bind coordinator receipts. Route C science is unchanged. The Critic should review the existing Route C contract plus the local receipt diff and inherited hardening requirements, and should not reject solely because Planner-side `/users` server validation was unavailable.

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
