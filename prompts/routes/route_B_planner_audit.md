---
route_id: route_B
branch: route_B
status: PLANNER_AUDIT_COMPLETE_FOR_CRITIC
not_a_milestone: true
planner_base_commit: dfea8e1bb22de1bbcf3ff062359f1dd086f56c38
contract_path: prompts/routes/route_B.md
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
critic_request_path: prompts/routes/route_B_critic_request.md
prompts_shared_modified: false
---

# Route B Planner audit

## Remote synchronization

Before writing this Route B draft, the remote repository `YuukiAS/CARE_Challenge` was read through the GitHub connector. The synchronized setup state was:

| ref | sync observation before writing |
| --- | --- |
| `main` | HEAD `dfea8e1bb22de1bbcf3ff062359f1dd086f56c38` |
| `route_A` | identical to `main`, ahead 0 / behind 0 before Route A planning writes |
| `route_B` | identical to `main`, ahead 0 / behind 0 before Route B planning writes |
| `route_C` | identical to `main`, ahead 0 / behind 0 before Route C planning writes |

Recent commit context included route prompt copy organization, partial M10 follow-up2 evidence preservation, route prompt handoff workflow, route portfolio GPT planning prompts, route watchboard merge/addition, tmux/env clarifications, and route workspace setup. The planning implication is that Route B starts from the shared portfolio setup commit but must use its own branch/worktree/results namespace and must not reuse old M10/follow-up2 submitted or pending packets as completion.

## Required repository files read

Read before drafting Route B:

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `README.md`
- `prompts/CHATGPT_RULES.md`
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`
- `routes/README.md`
- `routes/route_A/README.md`
- `routes/route_B/README.md`
- `routes/route_C/README.md`
- `prompts/routes/README.md`
- `prompts/routes/route_portfolio_planner_prompt.md`
- `configs/routes/partition_routing.yaml`
- `docs/route_watchboard.md`
- `wiki/README.md`

## SRR visual-read audit

Visual-read status: `READ_FROM_PROJECT_BACKGROUND_OR_CURRENT_CONVERSATION_UPLOAD`.

Versions visually read:

- `SRR-v2`
- `SRR-v2.5`
- `SRR-v3`

Canonical repository references used only as identifiers:

- `images/SRR-v2.png`
- `images/SRR-v2.5.png`
- `images/SRR-v3.png`

Recovered route structure from the diagrams:

1. Inputs and availability: LGE/C0/T2 are paired with an availability mask; unavailable modalities must not be treated as observed zero-valued channels.
2. Encoder/router: multi-scale features feed an availability plus pooled-image router. It emits anatomy, scar and edema gates.
3. Representation bank: shared dictionary, modality-private dictionaries and optional interaction dictionary operate at each scale. v3 emphasizes semantic multi-slot dictionaries and prototype groups with train/OOF provenance.
4. nnU-Net anchor/context: v3 adds probabilities/logits, hard predictions, scar/edema components, uncertainty/confidence and anatomy context. This is for baseline-preserving residual correction, not for hiding a fallback-only route.
5. Anatomy-guided proposal: union/LV/RV anatomy, anatomy priors, distance maps, uncertainty and nnU-Net components feed scar and edema proposals.
6. Pathology-specific soft-ROI refinement: scar is small-ROI/high-resolution/high-precision; edema is large-ROI/context-preserving/T2-conditioned.
7. Training losses include anatomy, proposal, refinement, residual/gate, negative-space, prior/ROI, dictionary/prototype regularization and optional alignment.
8. Cine branch is registration-aware anatomy-first temporal retrieval: ED/reference/key frames, registration/warping, temporal representation dictionary, frame-quality/motion-saliency router, frame-wise anatomy prior and temporal aggregation.

## Route objective statement

Route B recovers the complete SRR-v3 objective: implement every diagram-defined MyoPS and Cine module as a real executable path, prove the path affects final outputs through interventions, verify gradients/save-reload/export, then freeze implementation before formal training.

## Planning boundary checks

| boundary | Route B planner status |
| --- | --- |
| code executed | No |
| training run | No |
| Slurm submitted | No |
| runtime `review.md` written | No |
| validation package/upload | No |
| M11 started | No |
| route promotion/final conclusion | No |
| `prompts/shared/` modified | No |

## Why Route B is isolated

Route B has its own branch, worktree, result root, runtime root, log root, lock root, controller tmux and reviewer tmux. The contract blocks writes to Route A/C namespaces, shared prompts, root current-state wiki, validation upload directories, raw data, checkpoints, predictions, large logs and secrets.

## Key anti-shortcut requirements embedded

- Implementation-before-training gate is mandatory and ordered.
- Every required SRR-v3 module must be real or explicitly disabled by Critic-reviewed revision.
- Placeholder, mock, dataclass-only, fake URL/hash, config-only and CSV-only completion are forbidden.
- Old wrapper bypass is a failure.
- Intervention must change final logits/labels or route-specific output.
- Gradients must reach target modules.
- Save/reload/export must pass before implementation freeze.
- Cine must consume real multi-frame registered evidence; frame0-only or descriptor-only is invalid.
- Pending Slurm/monitor packets are not completion.
- Formal route evidence requires adequate train/eval after implementation freeze; smoke-scale evidence is diagnostic only.

## Files created by this planner on `route_B`

- `prompts/routes/route_B.md`
- `prompts/routes/route_B_executor_plan.yaml`
- `prompts/routes/route_B_critic_request.md`
- `prompts/routes/route_B_planner_audit.md`

## Next required action

A separate GPT Critic must review `route_B`. Only if the Critic issues `ROUTE_B_PLANNING_READY_FOR_CONTROLLER` may a Route B controller be started. This Planner draft alone does not authorize controller execution.
