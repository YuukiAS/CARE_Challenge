---
route_id: route_B
branch: route_B
status: PLANNER_REQUESTS_INDEPENDENT_CRITIC
not_a_milestone: true
contract_path: prompts/routes/route_B.md
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
planner_audit_path: prompts/routes/route_B_planner_audit.md
critic_allowed_token: ROUTE_B_PLANNING_READY_FOR_CONTROLLER
critic_must_not_execute: true
---

# Route B independent Critic request

You are the independent GPT Critic for `route_B`. This is a planning review only. Do not execute code, do not train, do not submit Slurm, do not write runtime `review.md`, do not package or upload validation, do not start a controller, and do not start M11.

Route B is not a milestone. Reject or revise any wording that calls Route A or Route B a milestone.

## Required files to read

Read the latest `route_B` branch:

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`
- `routes/README.md`
- `routes/route_B/README.md`
- `prompts/routes/README.md`
- `prompts/routes/route_portfolio_planner_prompt.md`
- `configs/routes/partition_routing.yaml`
- `docs/route_watchboard.md`
- `wiki/README.md`
- `prompts/routes/route_B.md`
- `prompts/routes/route_B_executor_plan.yaml`
- `prompts/routes/route_B_planner_audit.md`

You must independently visually read SRR v2/v2.5/v3 diagrams from project-background/current visual materials. Do not rely on the Planner summary.

## Critic scope

Check whether Route B truly implements complete SRR-v3 architecture before formal training:

- modality-specific stems;
- availability-aware router reading mask and pooled image features;
- shared/private/interaction dictionaries;
- prototype memory or OOF prototype bank with positive/negative/safe-negative definitions;
- anatomy decoder;
- scar and edema proposal decoders;
- soft ROI generator;
- scar and edema refiners;
- bounded nnU-Net residual correction;
- full loss family;
- save/reload/export;
- real CineMA or anatomy source, ED/key frames, registration, temporal dictionary and aggregation/refiner.

## Required fail-closed checks

Return `NEEDS_PLANNING_REVISION` unless all of these hold:

1. The contract and YAML executor plan agree on route_B branch, worktree, result/runtime/log/lock namespaces, write scopes and forbidden scopes.
2. `implementation-before-training gate` blocks formal training until forward, losses, gradients, intervention, save/reload and export checks pass.
3. Each SRR-v3 diagram module has a required code/evidence mapping or an explicit Critic-reviewed disabled state.
4. Placeholders, mocks, dataclass-only components, fake URLs/hashes, config-only modules, CSV-only diagnostics and no-op wrappers are forbidden.
5. Old nnU-Net or old Cine wrapper bypass cannot satisfy final-output evidence.
6. No-T2 edema safety is explicit.
7. Cine cannot pass as frame0-only, descriptor-only, topology-only, proxy registration, untrained VoxelMorph, or temporal output that does not consume registered evidence.
8. Training adequacy distinguishes implementation smoke from scientific evidence.
9. `prompts/shared/**`, Route A/C namespaces, validation upload, route promotion, final scientific conclusion and M11 are forbidden.
10. The reviewer is independent and read-only.

## Revision authority

If issues are found, revise only Route B planning files on `route_B`:

- `prompts/routes/route_B.md`
- `prompts/routes/route_B_executor_plan.yaml`
- `prompts/routes/route_B_critic_request.md`
- `prompts/routes/route_B_planner_audit.md` if an erratum is needed

Do not edit implementation code, shared prompts, route_A, route_C, result packets, runtime outputs, validation packages, or root wiki current state.

## Passing decision

If the plan is acceptable, write a concise Critic decision and use exactly:

```text
ROUTE_B_PLANNING_READY_FOR_CONTROLLER
```

This token authorizes only a later Route B controller start. It does not authorize validation upload, route promotion, final scientific conclusion, M11, cross-route merge, or package submission.

## Required Critic report fields

- `critic_decision:`
- `critic_token:` if passing
- `contract_path:`
- `executor_plan_path:`
- `planner_audit_path:`
- `branch:`
- `commit_sha:`
- `visual_read_status:`
- `prompts_shared_modified:`
- `remaining_risks:`
