---
route_id: route_B
branch: route_B
status: CRITIC_REVISED_PLANNING_READY_FOR_CONTROLLER
not_a_milestone: true
planner_base_commit: dfea8e1bb22de1bbcf3ff062359f1dd086f56c38
critic_reviewed_planner_commit: 7303ef937793e47f5bac562e3c2c796654acc7fa
contract_path: prompts/routes/route_B.md
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
critic_request_path: prompts/routes/route_B_critic_request.md
critic_decision: APPROVE_AFTER_REVISION
critic_token: ROUTE_B_PLANNING_READY_FOR_CONTROLLER
prompts_shared_modified: false
---

# Route B Planner and Critic audit

## Remote synchronization

The Planner started from common setup commit `dfea8e1bb22de1bbcf3ff062359f1dd086f56c38`. At Critic review, remote `route_A`, `route_B` and `route_C` were each four planning commits ahead of that same `main` baseline and zero commits behind. The route diffs contained only their corresponding four planning artifacts. Shell `git fetch` was unavailable in the current runtime because DNS could not resolve GitHub; the connected GitHub source was therefore used to read the current remote refs and files directly. No stale local checkout was used.

Recent main context included route workspace setup, route-local docs, tmux/environment clarification, route watchboard addition/merge, portfolio Planner prompts, route handoff documentation, partial M10 follow-up2 evidence preservation and prompt-copy organization. These commits establish that Route B must be isolated, implementation-first and independent of old submitted/pending M10 packets.

## Repository files read

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`
- `routes/README.md`
- `prompts/routes/README.md`
- `prompts/routes/route_portfolio_planner_prompt.md`
- `configs/routes/partition_routing.yaml`
- `docs/route_watchboard.md`
- `wiki/README.md`
- Route B's four Planner artifacts
- Route A/C executor-plan namespace sections for isolation comparison

## Independent SRR visual read

Visual source: current ChatGPT Project background/current-conversation visual channel.

Versions: `SRR-v2`, `SRR-v2.5`, `SRR-v3`.

Recovered evolution:

1. v2 defines availability-aware selective retrieval from observed LGE/C0/T2, anatomy-guided proposals and scar/edema soft-ROI refinement.
2. v2.5 makes scar and edema proposal decoders and refinement scales explicitly separate.
3. v3 adds semantically constrained multi-slot train/OOF prototypes, nnU-Net logits/components/uncertainty/anatomy context and per-pathology bounded residual correction whose closed gates preserve the anchor.
4. Cine is an ED/key-frame, reference-space registration and temporal-retrieval path with frame-wise anatomy prior and aggregation; it cannot be replaced by frame0, descriptors, LCC or proxy motion.

## Planning boundary

No code was executed, no model was trained, no Slurm job was submitted, no runtime `review.md` was written, no validation package/upload was performed, no route was promoted, no M11 was started and no cross-route merge occurred. `prompts/shared/` remains unchanged.

## Critic review delta

The Critic reviewed Planner commit `7303ef937793e47f5bac562e3c2c796654acc7fa` and found the route scientifically positioned correctly but mechanically incomplete. The following deltas were applied:

| finding | revision |
| --- | --- |
| heavy artifact write ban contradicted save/reload/export | allowed untracked runtime artifacts only under Route B runtime; Git publication remains forbidden |
| no concrete effective-training thresholds | added optimizer-step, train-time, validation-event and case-count minima plus overfit/sanity/loss/cache/baseline gates |
| incomplete controller lifecycle receipts | added context, ledger, bootstrap, mapper draft/final, architecture delta and finalizer state requirements |
| residual correction underspecified | added exact per-pathology gated equation, closed-gate anchor identity, bounded delta and help/harm checks |
| prototype leakage/safe-negative rules incomplete | added self-case/fold/validation leakage prohibition and T2-present edema-safe-negative rule |
| Cine honest blocker could be treated as continuation | changed blocker to implementation failure; complete Cine gate is required before formal training |
| missing-modality semantics weakly testable | added unavailable-tensor perturbation invariance and no-gradient tests |
| validator requirements were generic | added exact validator paths, report paths and known-bad fixture root |
| system mapper/root wiki tension | required route-local mapping/fingerprints while deferring root wiki to portfolio reconciliation |

## Ten requested Critic checks

1. Portfolio position: pass after revision; Route B remains the complete architecture route between compressed Route A and evidence-heavy Route C.
2. SRR-v3 fidelity: pass after revision; every required diagram module has a causal implementation/evidence gate.
3. MyoPS and Cine coverage: pass after revision; Cine cannot be skipped or passed through a blocker.
4. Implementation-before-training: pass; the full MyoPS+Cine gate and freeze precede formal training.
5. Anti-placeholder/bypass: pass; exact semantic known-bad cases are required.
6. Monitor packet: pass; pending/submitted/watcher/accounting states cannot be completion.
7. Namespace isolation: pass; branch/worktree/result/runtime/log/lock paths are route-specific, and heavy runtime artifacts are untracked.
8. Slurm routing: pass; `htzhulab -> a100-gpu -> volta-gpu` with correct QOS/GRES and explicit V100 compatibility.
9. Terminology: pass; Route B is explicitly not a milestone.
10. Validator/reviewer independence: pass after revision; exact strict validators, lifecycle receipts, known-bad fixtures and pinned read-only reviewer are required.

## Critic disposition

`critic_decision: APPROVE_AFTER_REVISION`

`critic_token: ROUTE_B_PLANNING_READY_FOR_CONTROLLER`

The token authorizes only the later Route B controller start. It does not authorize validation upload, route promotion, hosted metric claims, final scientific conclusions, M11, package submission or cross-route merge.

## Remaining risks

The full architecture remains expensive to implement under the competition schedule. Cine registration may fail on some cases; prototype banks may collapse or leak if validators are poorly implemented; V100 may be incompatible without changing semantics; and an eight-hour first wave may remain scientifically undertrained. The revised plan forces these outcomes to be reported as revision, evidence, monitor or undertraining states rather than false completion.
