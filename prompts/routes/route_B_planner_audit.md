---
route_id: route_B
portfolio_round: round03
date: 2026-07-18
role: planner
status: DRAFT_FOR_ROUND03_CRITIC_REVIEW
branch: route_B
planner_main_base_commit: f15cbcfa7b7f9f699d33abcf4f3ac0c359f06c22
remote_route_base_commit: 4c2f2ec146f5cc7a026cf4d5369c79b863f88ad2
contract_path: prompts/routes/route_B.md
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
critic_request_path: prompts/routes/route_B_critic_request.md
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_PROJECT_BACKGROUND_CURRENT_CONVERSATION
validator_not_run_by_planner: true
planner_local_yaml_safe_load: PASS_IN_CHATGPT_SANDBOX
planner_schema_mirror_check: PASS_IN_CHATGPT_SANDBOX
server_executor_plan_validator: NOT_RUN_NO_USERS_SERVER_SHELL
server_git_diff_check: NOT_RUN_NO_USERS_SERVER_SHELL
final_planner_commit_binding: EXTERNAL_MAIN_HANDOFF_BINDS_FINAL_ROUTE_HEAD_AND_BLOBS
PROPOSAL_REFINER_RESEARCH_STATUS: READY_WITH_EXPLICIT_FALLBACK
PROTOTYPE_MEMORY_RESEARCH_STATUS: READY_WITH_EXPLICIT_FALLBACK
CINEMA_ADAPTER_RESEARCH_STATUS: READY_WITH_EXPLICIT_FALLBACK
REGISTRATION_TEMPORAL_RESEARCH_STATUS: TARGETED_CODE_PROBE_COMPLETED_FOR_PLANNING_CONTRACT
PLANNER_REVISION_READINESS: READY_FOR_COORDINATOR_VALIDATION_THEN_INDEPENDENT_CRITIC
---

# Route B Round03 Planner audit — YAML representation repair

## Revision scope

This revision does not redesign Route B. It repairs the machine-readable representation of the already frozen Round03 full SRR-v3 contract. The Portfolio state remains `ACTIVE_FULL_SRR_V3`, and Controller authorization remains false.

The prior executor plan used YAML flow mappings for `preflight`, `partition_compatibility`, `routing_policy`, and `routing_race_policy`. Commands contained `${SLURM_JOB_PARTITION}`, template braces such as `{partition}` and `{attempt}`, nested quotes, and `&&`; PyYAML could stop at the first unsafe flow mapping. The repaired plan converts every such structure to block mappings and stores command/template scalars as explicit YAML strings. B6's compound command is explicitly quoted. No model, loss, budget, path, token, dependency, partition assignment, race rule, V100 policy, CineMA requirement, or reviewer boundary was intentionally changed.

## Recovered architecture objective

The current Project images were visually reread. SRR-v2 defines availability-aware modality evidence, selective shared/private retrieval, anatomy-guided lesion proposal, pathology-specific soft-ROI refinement, and registered Cine temporal evidence. SRR-v2.5 separates scar and edema proposal/refinement geometry. SRR-v3 adds nnU-Net anchor/context, component and uncertainty evidence, train/OOF prototypes, and bounded correction. Evidence selection belongs to stems, routers, dictionaries, prototypes, and context; lesion formation belongs to proposal, ROI, refiner, bounded delta, and final composition. Dictionary-only paths can be nonidentity yet harmful because they change evidence without reliably controlling lesion geometry, remote false positives, component burden, and HD95.

## Hard requirements retained

The plan still fixes canonical `[LGE,T2,C0]`, four scales `[32,64,128,256]`, sixteen experts per scale, two-pass pathology routing, numerical Pattern-SIP and full-loss contracts, fold-safe OOF-fitted inference-frozen prototypes, safe negatives, separate scar/edema proposal/ROI/refiner paths, bounded final correction, exact no-T2 edema zero semantics, official CineMA with matched random control and common downstream initialization, seven-step SVF with real SyN, registered temporal input consumption, B2 implementation gate before long training, semantic known-bad fixtures, durable finalizer, mapper/fingerprint receipts, and independent reviewer tokens.

Slurm policy remains: `htzhulab` default, `a100-gpu` fallback/race partner, and `volta-gpu` used only for exact-compatible work or independent compatible work. Distinct ready work precedes duplicate races. Race attempts require identical scientific hashes, isolated output/log/checkpoint/cache roots, atomic winner lock, pending-loser cancellation, loser zero credit, retry lineage, and all-attempt finalizer coverage. Full MyoPS and full temporal work cannot be semantically downscaled for V100. Formal wrappers use `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`; bare `python` remains forbidden. Controller execution must be a Codex goal or goal resume and cannot stop at submitted, pending, running, awaiting-accounting, undertrained, or monitor state.

## Prompt and schema coverage

All B0–B10 prompt paths were re-fetched from `route_B` and exist. The plan has eleven distinct integer waves, legal lanes, unique branch/worktree/result/runtime/log/lock namespaces, singular `write_scope`, earlier-wave dependencies, integer merge order, required completion file/token, executor-local retry/dependency/preflight fields, and explicit partition/race matrices.

## Validation boundary

The Planner environment has no `/users` shell. Therefore no server exit code is claimed. In a local ChatGPT Python sandbox, `yaml.safe_load` parsed the repaired file into eleven executors, and a mirror of the current `scripts/ops/validate_executor_plan.py` checks returned zero findings. These are syntax/static evidence only, not the required repository validator.

Before the Route B Critic may issue a ready token, the Codex coordinator must run on the exact bound Route B commit and record exit `0` for:

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

The coordinator must also run the first-party or Critic-equivalent partition/race static check over all B2–B10 declarations. Any unavailable or nonzero check requires `ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION`; it cannot be deferred to the Controller.

## Files and evidence read

Current main governance, Agent-Flow, handoff gates, anti-laziness protocol, permanent hard-requirements matrix, route/current/wiki entries, Slurm and mapper skills, executor-plan validator/helpers, Round02 evidence and Critic conclusions, Deep Research commit `28c8aac80b7f18f3441c495dc9f2625fc10c460f`, Route B route-local packets, first-party SRR/proposal/memory/loss/ROI/Cine/registration/temporal source, pinned CineMA source/config/API, and the three Project SRR images were read.

## Authority boundary

No Controller, Slurm job, training, runtime review, validation upload, route promotion, M11, cross-route merge, hosted metric claim, or final scientific decision is authorized. The final main handoff binds the final Route B head and blobs; a planning Critic ready token authorizes only the Route B Controller on that exact revision.
