---
portfolio_round: round03
date: 2026-07-18
role: GPT_Planner
status: PLANNER_YAML_REPAIR_PUBLISHED_CRITIC_VALIDATION_PENDING
not_a_milestone: true
planner_main_base_commit: f15cbcfa7b7f9f699d33abcf4f3ac0c359f06c22
deep_research_commit: 28c8aac80b7f18f3441c495dc9f2625fc10c460f
active_routes: [route_B, route_C]
deferred_routes: [route_A]
route_A_status: DEFERRED_FALLBACK_NOT_ACTIVE
route_A_current_critic_handoff: NO_CURRENT_CRITIC_HANDOFF
current_controller_authorizations: 0
slurm_partitions: [htzhulab, a100-gpu, volta-gpu]
v100_user_approved: true
three_way_race_user_approved: true
prefer_distinct_work_over_duplicate_race: true
race_when_single_critical_job_pending: true
validator_not_run_by_planner: true
visual_route_diagrams: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_PROJECT_BACKGROUND_CURRENT_CONVERSATION
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# CARE Myocardium Route Portfolio Round03 Planner plan — machine-readable repair revision

## Portfolio decision

```text
Route A: DEFERRED_FALLBACK_NOT_ACTIVE
Route B: ACTIVE_FULL_SRR_V3
Route C: ACTIVE_M10_FORENSIC_EVIDENCE_AND_CINE_FIDELITY
current_controller_authorizations: 0
```

This revision does not reopen scientific route design. It repairs invalid YAML representation in the Route B/C executor plans and refreshes every remote commit/blob handoff. Route A remains dormant, has no Round03 Critic handoff, and has no Controller or Slurm authority. It may be reactivated only by explicit user authorization or a later Portfolio Planner decision after a documented Route B pre-training implementation blocker.

## Visual route interpretation retained

SRR-v2, SRR-v2.5, and SRR-v3 were visually reread from the Project/current-conversation image channel. V2 establishes availability-aware modality evidence, selective retrieval, anatomy-guided proposal, pathology-specific soft-ROI refinement, and Cine reference-frame temporal evidence. V2.5 separates scar and edema proposal/refinement geometry. V3 adds nnU-Net anchor/context, components/uncertainty, train/OOF prototypes, and bounded correction. Stems, routers, dictionaries and prototypes select evidence; proposals, ROIs, refiners and final composition form lesions. Dictionary-only nonidentity can still damage Dice, HD95, remote false positives and component count because output change does not prove valid lesion formation.

The permanent `ROUTE_HARD_REQUIREMENTS_MATRIX.md`, anti-laziness protocol, M9/M10 inheritance, monitor-not-completion rule, durable finalizer, no-push runtime boundary and independent reviewer gate remain fully active.

## Exact route bindings after YAML repair

### Route A — unchanged dormant fallback

```text
head: a91ba0eef8dff4600e16331aea99d043e1f4339b
contract blob: 370c25de0e35dbd5c854bbdfb81589ee8c0a4368
executor-plan blob: c681d761cfa145d68ba906f5eb33607843af8b80
critic-request blob: 227c8f69f69e2b07b72f5df5f3323b2f03136bd1
planner-audit blob: 61d8cb48fab3728d1330975fb1bc2178446313f9
current Critic handoff: NO_CURRENT_CRITIC_HANDOFF
```

### Route B — repaired full SRR-v3 plan

```text
head: 0d7e0d295ca94f23c39767506bd711890ae6022e
contract blob: 2d82b8bb5d05e521adb87281a663fd7fe38582c6
executor-plan blob: 83494fbf40df7b79c26c3be3c00d51e23830208c
critic-request blob: 50fba61a5512e4ba7b124fd2355ca84c2a688ed8
planner-audit blob: 3a0d422ed81695f77750f59ebfdca38700c69516
Critic handoff: prompts/routes/handoffs/route_B_round03_critic_handoff_20260718.md
Critic-handoff blob: 20b63e09aba621a05d9a3d175071bca4c41ddde4
```

The plan keeps canonical `[LGE,T2,C0]`, four scales `[32,64,128,256]`, sixteen experts, pathology-specific two-pass routing, numerical Pattern-SIP/full loss, four-shard OOF-fitted inference-frozen prototypes, safe negatives, separate scar/edema proposal/ROI/refiners, bounded final correction, no-T2 exact-zero semantics, B2 implementation gate before long training, official CineMA matched random control with common downstream initialization, seven-step SVF plus real SyN, registered temporal consumption, fresh selector/interventions, semantic known-bad fixtures and terminal finalizer/reviewer gates.

### Route C — repaired M10 forensic/fidelity plan

```text
head: 8c2f4fef4f25805e8eac1a44628045bbb2875a5a
contract blob: 0f04a06dce5ebaaaa0e0f84ce317b88123fd1a26
executor-plan blob: 9b5d0bd369dd95d926337ef2d8c315e7fdbfb982
evidence-mapping blob: 2b5a068ee807c5f622dcd5b1732fdc05e144b960
evidence-mapping row count required: 37
critic-request blob: 0beb1ef72cc8fb1e712be76a57c11b0fdc04043e
planner-audit blob: f703decf4b8480da467f7f3387a273fe3b66d3eb
Critic handoff: prompts/routes/handoffs/route_C_round03_critic_handoff_20260718.md
Critic-handoff blob: 32c67840e9c8f73c6af280534b126e8012de5a0d
```

Route C preserves historical M10 SRR-owned final logits and selector. `anchor_residual_control_off_path` remains a required zero-effect control, not a causal intervention. C0 fingerprints the historical graph; C0B cannot waive any train-time mismatch; R1 performs fresh forced all-checkpoint replay and real final-path interventions; R2 only implements official CineMA/SVF/temporal smoke and a freeze candidate; R3 reproduces the Controller final freeze and cannot edit frozen source. The unchanged mapping remains exactly `C_MAP_001` through `C_MAP_037`.

## YAML repair and validation boundary

All unsafe flow mappings in Route B/C `preflight`, partition matrices, routing/race policies, job compatibility and race constraints were converted to block mappings. Scalars containing `${SLURM_JOB_PARTITION}`, `{phase}`, `{checkpoint_sha}`, `{partition}`, `{attempt}`, nested quotes or `&&` are explicit strings. Every B0–B10 and C0/C0B/R1/R2/R3 prompt path was remotely re-fetched and exists.

The Planner environment has no `/users` shell. No repository validator or `git diff --check` exit is claimed. Local ChatGPT-sandbox checks found:

```text
Route B yaml.safe_load: PASS, executors=11
Route C yaml.safe_load: PASS, executors=5
Route B mirrored executor-plan schema findings: 0
Route C mirrored executor-plan schema findings: 0
server executor-plan validators: NOT_RUN_NO_USERS_SERVER_SHELL
server Route C mapping parse: NOT_RUN_NO_USERS_SERVER_SHELL
git diff --check: NOT_RUN_NO_USERS_SERVER_SHELL
```

Before a Critic ready token, a Codex coordinator must run on each exact bound route commit:

```bash
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/routes/route_B_executor_plan.yaml
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/routes/route_C_executor_plan.yaml
```

It must also run `yaml.safe_load` for B/C, assert Route C mapping row count `37`, execute the route-specific partition/race checks, and run `git diff --check`. Any unavailable or nonzero result requires the route's `PLANNING_NEEDS_REVISION` token and cannot be deferred to the Controller.

## Three-partition policy retained

`htzhulab` remains the default CARE partition. `a100-gpu` is fallback/race partner. `volta-gpu` must be used for exact-compatible implementation gates, replay, extraction, controls, registration/SyN evaluation, selected reload/evaluation or validators; heavy full MyoPS/full temporal jobs cannot be scientifically downscaled for 16 GB. Distinct ready work precedes duplicate race. A single critical compatible job may race immediately. Every race requires identical scientific hashes, isolated output/log/checkpoint/cache roots, atomic winner lock, pending-loser cancellation, loser zero credit, retry lineage and all-attempt finalizer coverage. Formal wrappers use `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`; bare `python` is forbidden.

Controllers must later run as Codex goals or goal resumes and retain responsibility through terminal accounting, allowed same-scope retry, aggregation, mapper final, strict validation, lightweight local packet commit and reviewer handoff. Submitted, pending, running, awaiting-accounting, undertrained or monitor packets are not completion.

## Decision checkpoints

```text
2026-07-20: Route B B0-B2 terminal; Route C C0/C0B decision terminal.
2026-07-21: Route B warmup/proposal gate; Route C fresh replay majority and real intervention path.
2026-07-22: Route B first formal MyoPS and CineMA/control evidence; Route C R1 terminal/blocker and R2 freeze candidate.
2026-07-23: evidence-directed same-scope repair only.
2026-07-24: no new scientific design or loss.
2026-07-25: route-local packets and independent reviews.
2026-07-26: runtime/review/Docker/packaging/paper/submission QA only.
2026-07-27: final submission; no new experiment.
```

Route B and C Critics may run in parallel. Controllers remain blocked until the corresponding exact ready token appears.

## Authority boundary

```text
controller_authorized_now: 0
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
```

Planner publication, commit or push is not Critic passage.
