---
portfolio_round: round02
date: 2026-07-17
status: PLANNER_PLAN_COMMITTED_FOR_ROUTE_CRITIC_REVIEW
main_base_commit: 3f0e78706653da2eeeb3453ed992628a7c0eee70
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_PROJECT_BACKGROUND_CURRENT_CONVERSATION
route_A_planner_commit: bb522e1b2be7ce671db0026a4b94cc1d18937780
route_B_planner_commit: 77fbde2e1936d19c9f0d6dc711ea37b4ae077eac
route_C_planner_commit: fbf02a5883b0f08c0f2d9268a68dc486ae956d8e
route_A_critic_handoff: prompts/routes/handoffs/route_A_round02_critic_handoff_20260717.md
route_B_critic_handoff: prompts/routes/handoffs/route_B_round02_critic_handoff_20260717.md
route_C_critic_handoff: prompts/routes/handoffs/route_C_round02_critic_handoff_20260717.md
controller_start_authorized: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# CARE Route Portfolio Round02 Planner Plan

## Portfolio judgment

Round02 is a controller-forward planning round for all three routes. Route A receives a new compressed-SRR gate-opening experiment because its adequate prior run produced zero changed voxels. Route B remains the full SRR-v3 implementation route and receives a new metric-facing run because the prior ten-case evaluation contained no edema-positive case and the Cine path lacked real CineMA evidence. Route C retains the entire M10/follow-up/follow-up2 burden: it repairs evidence naming and final-path intervention semantics, completes fresh all-checkpoint replay, and builds the full CineMA–registration–temporal chain.

The recovered route objective is availability-aware selective retrieval over live modality evidence, a semantic shared/private/interaction representation bank, anatomy-guided scar and edema proposal, pathology-specific soft-ROI refinement, negative-space/no-T2-safe learning, and a final output whose mechanism can be intervened on. The v3 nnU-Net path is anchor/context/teacher/safety evidence, not permission to replace SRR with an identity wrapper. Cine requires ED/reference handling, real non-reference frames, registration, registered CineMA anatomy/features/uncertainty, and temporal aggregation.

Every route targets `myops_scar`, `myops_edema`, and `myocardium_cinemyops`. Same-split nnU-Net comparison, case-wise help/harm, T2-present edema, no-T2 safety, scar-positive cases, CenterB/CenterC when present, remote false positives, component count, `Dice`, `HD95`, and volume ratio are mandatory. `foreground_mean`, empty-GT improvement, compact-label-only proxies, runnable status, or validator status cannot support a route claim.

## Bound route contracts

| Route | Bound branch commit | Contract | Executor plan | Core Round02 intervention |
| --- | --- | --- | --- | --- |
| A | `bb522e1b2be7ce671db0026a4b94cc1d18937780` | `prompts/routes/route_A.md` | `prompts/routes/route_A_executor_plan.yaml` | Replace the zero-effect compressed path with a two-scale live-evidence SRR and supervised bounded pathology gates; add frozen real CineMA + SyN + temporal refiner. |
| B | `77fbde2e1936d19c9f0d6dc711ea37b4ae077eac` | `prompts/routes/route_B.md` | `prompts/routes/route_B_executor_plan.yaml` | Preserve the full four-scale/16-slot SRR-v3 causal chain, add T2-positive-balanced evaluation, and run real frozen CineMA against a matched frozen random source. |
| C | `fbf02a5883b0f08c0f2d9268a68dc486ae956d8e` | `prompts/routes/route_C.md` | `prompts/routes/route_C_executor_plan.yaml` | Preserve all M10 requirements; repair off-path residual evidence naming, complete fresh all-checkpoint replay, and execute full CineMA adapter/random-control/registration/SyN/temporal runtime. |

A controller may start only after the corresponding current Round02 critic writes the route-specific planning review, binds the exact branch commit and contract/plan blobs, and emits the exact ready token. A prior Round01 planning token is stale and grants no authority.

## Route A next controller work

Route A's scientific hypothesis is that a live-evidence compressed SRR can open a bounded pathology correction only at anatomically plausible anchor-error opportunities. Its fixed MyoPS design has two scales, one shared plus three private experts per scale, separate anatomy/scar/edema routers, pathology-specific proposals and refiners, and pathology-only correction around the same-case nnU-Net anchor. No-T2 Route A edema correction is exactly zero.

Its Cine branch uses the official CineMA weight with required SHA256, emits four-class logits, a decoder feature tensor, and normalized entropy, registers six frames to ED using real ANTsPy SyN, and trains a small temporal refiner. The formal MyoPS budget is at least `5000` steps and `1800` seconds over 44 cases plus at least six T2-positive edema-positive cases. The Cine budget is at least `4000` steps and `1800` seconds over twelve cases. Candidate readiness requires all safety gates and a positive threshold on at least one target while the other targets are non-worse; otherwise the packet remains an honest negative/incomplete packet.

## Route B next controller work

Route B's scientific hypothesis is that the complete v3 mechanism, not a reduced residual head, can improve the worst pathology while retaining no-T2 safety and producing a real Cine temporal effect. The fixed architecture uses four scales `[32,64,128,256]`, sixteen experts per scale, two-pass spatial entmax routing, Pattern-SIP, four train-only OOF shards, pathology memories, anatomy decoder, separate proposals/soft ROIs/refiners, and bounded final pathology correction. The formal MyoPS run is `25000` steps and `3600` seconds with a frozen 44-case list and at least eight T2-positive edema-positive cases.

The Cine branch consumes real frozen CineMA logits/features/entropy and a matched frozen random architecture under identical cases, frames, augmentations, optimizer, trainable heads, budget, validation cadence, checkpoint schedule, and selection rule. Each control is `8000` steps and `3600` seconds over twelve cases. Real SyN registration and an eight-slot temporal dictionary are mandatory. Downstream evidence always uses the clean-reloaded pretrained checkpoint; the random run is a control and cannot replace the CineMA path.

## Route C next controller work

Route C uses five serial executor waves: C0 instrumentation/fingerprint repair, C0B exact phase recovery when a train-time fingerprint differs, R1 complete fresh MyoPS replay/selection/interventions, R2 full Cine implementation/freeze candidate, and R3 frozen formal Cine runtime. Finalization, mapper, validation, local lightweight commit, and independent reviewer follow.

R1 executes every recoverable scheduled checkpoint on all 44 cases with `--evaluate --force`, freezes calibration before evaluation, records raw-output/state-dict and all code/data/decode/metric hashes, applies the inherited anchor-relative eligibility/selector, clean-reloads selected D2/D3 checkpoints, and performs real graph interventions. The previous `residual_gate` row is renamed `anchor_residual_control_off_path`: it is expected to have zero final effect because M10 uses SRR-owned final logits. Required causal interventions instead target nodes that truly feed final probability composition and final labels. Any required causal intervention with zero effect is a pipeline bug, not no-signal evidence.

Route C CineMA is not deferrable. R2 atomically fetches and verifies the official MIT-licensed weight, exact code/HF revisions, SHA256, environment, loader, real data root, and output shapes. A failure yields `BLOCKED_EXTERNAL_RESOURCE` or `NEEDS_EVIDENCE` with the exact missing path, failed command, expected SHA, retry command, and data deficit; it does not permit a fake/binary/frame0 replacement. R3 trains the matched pretrained/random adapters for `10000` steps and `3600` seconds each, learned registration for `25000` steps and `7200` seconds with seven-step scaling-and-squaring plus real SyN control, and—only after the case-level registration gate—temporal cumulative training to `20000` credited steps and `7200` seconds. Selected checkpoints must be clean-reloaded before downstream use.

## Slurm, finalizer, validator, and reviewer rules

All formal wrappers use the verified CARE Python executable and print Python, torch, CUDA, package, entrypoint, code/config/split, runtime/cache, and asset/data receipts. Bare `python` is forbidden. `htzhulab` is primary and `a100-gpu` is the declared mirror/fallback. Route plans exclude V100. Training-to-training dependencies use `afterok`; accounting and finalizers use `afterany`. A monitor, submitted, pending, running, timed-out, partial, or awaiting-accounting packet is not completion.

Each route has route-local runtime/cache/log/lock namespaces, strict content-validating scripts, executable semantic known-bad fixtures, route-local mapper/fingerprint receipts, and a deterministic finalizer. The finalizer performs terminal accounting, post-completion aggregation, mapper final, strict validation, `git diff --check`, and one local lightweight commit. Runtime roles do not push and do not write `review.md`. The post-commit reviewer remains independent and read-only.

## M9/M10 inherited hard gates applied

Mechanism evidence names must match the actual intervention. Proposal, memory, refiner, dictionary, registration, and temporal claims require a real tensor-to-final-label chain, final-output deltas, and identical-case controls. Old runtime can be inherited only after a complete fingerprint audit. Contracts, executor plans, critic handoffs, selected checkpoints, external assets, and runtime receipts bind hashes/commits. Cine/registration negative evidence is valid only after faithful implementation, adequate training, selected-checkpoint reload, full denominators, real SyN/control, terminal accounting, strict aggregation, and independent review.

No controller may decide model structure, losses, sampling, budget, cases/frames, paths, Slurm partition/race, checkpoint selector, eligibility thresholds, validator semantics, known-bad fixtures, completion states, finalizer behavior, or reviewer pass/fail. Mechanical code organization is the only controller-local discretion, and it may not alter contract semantics.

## Prohibited actions

Round02 grants no validation packaging or upload, route promotion, M11, cross-route merge, hosted metric claim, fold expansion outside the exact route contracts, or final scientific decision. Critic readiness authorizes only the corresponding controller start. Controller completion authorizes only an independent review. Reviewer acceptance authorizes only later portfolio reconciliation.
