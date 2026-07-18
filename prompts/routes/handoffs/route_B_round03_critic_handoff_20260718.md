---
route_id: route_B
portfolio_round: round03
date: 2026-07-18
role: independent_planning_critic_handoff
status: CURRENT_CRITIC_HANDOFF_READY_FOR_FAST_REPAIR_REVIEW
reviewed_branch: route_B
required_route_head: 11d5c3d90028fa19ccd1c709d9ce5d4e90f5b96f
contract_path: prompts/routes/route_B.md
required_contract_blob: 1d58d7a37eacaee8cc15c159758e5074e794de8b
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
required_executor_plan_blob: 082e2641d8fdf693e929d1aa460ae689b80ce0d2
critic_request_path: prompts/routes/route_B_critic_request.md
required_critic_request_blob: a1b03b7366df14bf9ca9628b309ced55dbf6db47
planner_audit_path: prompts/routes/route_B_planner_audit.md
required_planner_audit_blob: 5f8764c08908e725830817d42ed3dc606971cda9
critic_output_path: prompts/routes/route_B_round03_critic_review.md
allowed_pass_token: ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
allowed_revision_token: ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
validator_not_run_by_planner: true
coordinator_local_receipts_recorded: true
coordinator_repair_scope: B10_finalizer_mapper_ancestry_only
controller_start_authorized_before_ready: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
coordinator_partition_race_static_check: PASS_EXIT_0_COORDINATOR_20260718
---

# Route B Round03 independent Planning Critic handoff

## Exact binding

Re-fetch and verify exactly:

```text
route_B head: 11d5c3d90028fa19ccd1c709d9ce5d4e90f5b96f
route_B.md blob: 1d58d7a37eacaee8cc15c159758e5074e794de8b
route_B_executor_plan.yaml blob: 082e2641d8fdf693e929d1aa460ae689b80ce0d2
route_B_critic_request.md blob: a1b03b7366df14bf9ca9628b309ced55dbf6db47
route_B_planner_audit.md blob: 5f8764c08908e725830817d42ed3dc606971cda9

B10 prompt blob: ad48d04aeac2a69fb99d41ec4fa73d159138d269
```

Any mismatch makes this handoff stale and requires a new Planner binding.

## Coordinator local executable receipts

The Planner had no `/users` shell, but the coordinator has now run the required local checks on `/users/a/e/aereinh/CARE_worktrees/route_B` at the exact bound head without starting a controller, Slurm job, or training. The Critic may re-run them, but must not fail this handoff merely because the original Planner server was unavailable. Recorded exits:

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

Coordinator path/mapper check: exit 0. It parsed B0-B10, verified all 11 prompt paths exist, confirmed `scripts/architecture/care_mapper.py` is absent from the bound plan, confirmed the replacement mapper/architecture command paths exist, and confirmed both `scripts/architecture/validate_care_architecture_wiki.py --help` and `scripts/architecture/generate_care_architecture_wiki.py --help` exit 0. The Critic should review the repair diff and inherited hardening gates; any new nonzero executable check still requires `ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION`.

Coordinator partition/race static check: `PASS_EXIT_0`. Receipt from `/users/a/e/aereinh/CARE_worktrees/route_B`: `PASS route_B critic_equivalent_partition_race_static_check slurm_executors=9 prompt_paths=11`. This check verified three-partition declarations, preflight receipt locations, isolated attempt roots, atomic locks, loser zero credit, pending-loser cancellation, retry lineage, all-attempt finalizer coverage, B10 `depends_on: []`, terminal coverage for every listed terminal class, and absence of `scripts/architecture/care_mapper.py`.


## Fast repair review scope

This handoff supersedes the previous Round03 handoff only for coordinator unlock repair. The Critic should review the exact diff from the prior bound Route B head to this head and the inherited M9/M10/Round02 hardening requirements. Required focus: B10 terminal finalizer DAG covers every started attempt and every success/failure/timeout/preemption/adequate-negative/early-gate terminal class; B10 is not dependent on B9 success; mapper command no longer references nonexistent `scripts/architecture/care_mapper.py`; stale ancestry metadata no longer contradicts CURRENT-bound blobs. Do not reopen unrelated Route B scientific design unless this repair weakened a hard requirement.

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
