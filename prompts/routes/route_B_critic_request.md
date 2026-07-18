---
route_id: route_B
portfolio_round: round03
date: 2026-07-18
role: planner_to_critic
status: CRITIC_REVIEW_REQUESTED_AFTER_COORDINATOR_VALIDATION
branch: route_B
round03_current_binding_source: prompts/routes/handoffs/CURRENT.md
contract_path: prompts/routes/route_B.md
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
planner_audit_path: prompts/routes/route_B_planner_audit.md
critic_review_output_path: prompts/routes/route_B_round03_critic_review.md
allowed_pass_token: ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
allowed_revision_token: ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
controller_start_before_pass_forbidden: true
validator_not_run_by_planner: true
critic_must_not_execute_model_or_training: true
coordinator_partition_race_static_check: PASS_EXIT_0_COORDINATOR_20260718
---

# Route B Round03 independent Planning Critic request

Review only the exact Route B commit and contract/executor-plan/audit/request blobs named by the current main Round03 handoff. Re-fetch them immediately before review; any mismatch makes this request stale.

The current revision repairs invalid YAML flow mappings in the executor plan. Confirm that every `preflight`, partition declaration, routing/race policy, template containing braces, and compound `&&` command is represented by valid block mappings or quoted scalars without changing the scientific contract.

The Planner had no `/users` shell and did not run the repository validator. Before issuing any ready token, the Codex coordinator or the Critic must record real exit `0` on the exact bound commit for:

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

Also run a first-party or Critic-equivalent static partition/race check proving that every Slurm executor declares all three partitions, explicit compatibility/reason/preflight receipt, V100 alternative work when incompatible, identical scientific hashes for races, isolated output/log/checkpoint/cache roots, a shared atomic winner lock, loser zero credit, pending-loser cancellation, retry lineage, and finalizer coverage of all attempts. Any unavailable or nonzero check requires `ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION`; validation cannot be deferred to the Controller.

Independently read current main governance, anti-laziness and permanent hard requirements, Slurm and mapper skills, Round02 evidence analysis, Deep Research commit `28c8aac80b7f18f3441c495dc9f2625fc10c460f`, Route B Round02 Critic review, latest Route B packet/evidence, all B0–B10 prompts, first-party source named by the contract, pinned official CineMA source/config/API, and SRR-v2/v2.5/v3 through the Project visual channel.

Reject the plan if it allows legacy modality order, a two-scale/nnU-Net/wrapper/postprocess reduction, fewer than four scales or sixteen experts, incomplete Pattern-SIP/full-loss wiring, invalid slots, bootstrap/EMA formal memory, OOF leakage, no-T2 edema negatives, disconnected proposal/refiner/gate, zero MyoPS effect hidden by Cine, unbound stage budgets or advancing through a failed gate, fake/unmatched CineMA controls, direct velocity displacement, proxy Jacobian/inverse/SyN, abstract or unconsumed temporal input, unreloaded selected checkpoints, monitor/undertrained/stale completion, unsafe race semantics, V100 scientific downscaling, incomplete finalizer/mapper/known-bad/reviewer gates, or any forbidden authority claim.

The Critic must verify that the complete Route B design remains machine-bound: canonical `[LGE,T2,C0]`; `[32,64,128,256]`; sixteen experts; pathology-specific two-pass routing; numerical Pattern-SIP/full loss; four-shard OOF-fitted inference-frozen prototypes and safe negatives; separate scar/edema proposal, ROI and refiners; bounded final correction; exact no-T2 zero semantics; official CineMA matched random control with common downstream initialization; seven-step SVF and real SyN; registered temporal consumption; implementation gate before long training; terminal finalizer; and independent reviewer tokens.

Only these planning tokens are valid:

```text
ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
```

A ready token authorizes only the Route B Controller to start as a Codex goal or goal resume on the exact reviewed commit. It does not authorize validation upload, route promotion, M11, cross-route merge, hosted metric claims, or a final scientific decision.

## Coordinator unlock repair evidence

This coordinator revision is intentionally narrow. It removes stale ancestry metadata, hardens B10 so terminal finalization covers every started attempt and every success/failure/timeout/preemption/adequate-negative/early-gate terminal class instead of depending on B9 success, and replaces the nonexistent `scripts/architecture/care_mapper.py` reference with existing first-party architecture validator/generator entrypoints. The Critic should review only these repair diffs plus inherited hardening requirements; the Route B scientific contract is otherwise unchanged.

Required coordinator receipts before ready: executor-plan validator exit 0, PyYAML `executors=11`, `git diff --check` exit 0, every B0-B10 prompt path exists, and the bound mapper/architecture command path exists.
## Coordinator partition/race static receipt

Route B critic-equivalent partition/race static check was run on `/users/a/e/aereinh/CARE_worktrees/route_B` after rebase to `origin/route_B=e893624bb3f3addaa87378e640125e15102dc6f2`. Receipt: exit 0, `PASS route_B critic_equivalent_partition_race_static_check slurm_executors=9 prompt_paths=11`. The Critic may re-run it, but this request no longer lacks coordinator partition/race evidence.
