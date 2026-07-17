---
portfolio_round: round03
date: 2026-07-18
role: GPT_Planner
status: PLANNER_PUBLICATION_COMPLETE_CRITIC_REVIEW_PENDING
not_a_milestone: true
planner_main_base_commit: 6ed0a3bac82aa0ee8cb44250da0c2648965c6b42
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
remote_evidence_only: true
local_worktree_state: NOT_INSPECTED_BY_USER_INSTRUCTION
visual_route_diagrams: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_PROJECT_BACKGROUND_CURRENT_CONVERSATION
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# CARE Myocardium Route Portfolio Round03 Planner plan

## 1. Round transition and evidence baseline

`CURRENT.md` remained on Round02 when this plan began. Round03 is a new Portfolio planning revision triggered by three independent Round02 `PLANNING_NEEDS_REVISION` decisions, the Round02 comprehensive SRR evidence analysis, the targeted Deep Research, and a new user-approved Portfolio choice:

```text
Route A: DEFERRED_FALLBACK_NOT_ACTIVE
Route B: ACTIVE_FULL_SRR_V3
Route C: ACTIVE_M10_FORENSIC_EVIDENCE_AND_CINE_FIDELITY
```

Round03 is not a scientific milestone, promotion, validation authorization, M11 authorization, cross-route merge, hosted-metric claim, or final decision.

This publication uses GitHub remote evidence only because the user explicitly prohibited server/shell access. No claim is made about local clean/unpushed state. All handoffs bind the exact remote branch heads and blobs listed below; a later route-branch change makes its Critic handoff stale.

## 2. Independent visual route recovery

SRR-v2, SRR-v2.5, and SRR-v3 were read visually from the current Project/conversation images rather than inferred from repository filenames.

- v2: modality-specific LGE/T2/C0 evidence with explicit availability; selective shared/private retrieval; anatomy-guided scar and edema proposal; pathology-specific soft-ROI refinement; ED/reference-space Cine registration and temporal evidence.
- v2.5: scar and edema proposal/refinement are geometrically separate—scar is small, precision-oriented, LGE-dominant; edema is larger, recall-oriented, T2-conditioned.
- v3: nnU-Net logits/probabilities/components/uncertainty are anchor/context/safety evidence; train/OOF prototypes add class-specific evidence; bounded correction is one final-composition option.

Stems, routers, expert banks, and prototypes select evidence. Anatomy-guided proposals, ROIs, refiners, and final composition form lesions. M9 proved that dictionary-only nonidentity can still worsen Dice, HD95, remote false positives, and component count; output change is not lesion formation.

## 3. Permanent evidence judgments

The following conclusions are inherited:

1. M9 formal SRR-main candidates were adequately trained `NONIDENTITY_HARMFUL`, not smoke.
2. Prior Route A formal evidence is a 44-case zero-effect near-identity negative.
3. M10 preliminary evidence is `UNDER_REVIEWED_NONIDENTITY`; its mechanism and Cine fidelity debts are not closed.
4. Route B is prospective full-model construction.
5. Route C is retrospective M10 forensic/fidelity accounting.
6. Route A is a conditional dormant fallback.
7. Controller authorizations remain zero until separate Route B/C Critic ready tokens.
8. `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md` remains permanent for all routes.

## 4. Exact route publication bindings

### Route A — deferred fallback

```text
branch head: a91ba0eef8dff4600e16331aea99d043e1f4339b
contract: prompts/routes/route_A.md
contract blob: 370c25de0e35dbd5c854bbdfb81589ee8c0a4368
executor plan: prompts/routes/route_A_executor_plan.yaml
executor-plan blob: c681d761cfa145d68ba906f5eb33607843af8b80
critic request: prompts/routes/route_A_critic_request.md
critic-request blob: 227c8f69f69e2b07b72f5df5f3323b2f03136bd1
planner audit: prompts/routes/route_A_planner_audit.md
planner-audit blob: 61d8cb48fab3728d1330975fb1bc2178446313f9
current Critic handoff: NO_CURRENT_CRITIC_HANDOFF
```

Route A retains a schema-shaped dormant activation guard and a compressed two-scale SRR/Cine fallback, but execution, Critic, Controller, training, and Slurm are forbidden in Round03. Reactivation requires explicit user authority or a later Portfolio Planner decision after a documented Route B pre-training implementation blocker. Cine cannot mask zero MyoPS effect in any future activation.

### Route B — full SRR-v3

```text
branch head: 4c2f2ec146f5cc7a026cf4d5369c79b863f88ad2
contract: prompts/routes/route_B.md
contract blob: 2d82b8bb5d05e521adb87281a663fd7fe38582c6
executor plan: prompts/routes/route_B_executor_plan.yaml
executor-plan blob: e95757507c1025ae9e7538f64c4143ead899d05f
critic request: prompts/routes/route_B_critic_request.md
critic-request blob: e9917375f549368a99348a91ca4dd0d1aa9a8932
planner audit: prompts/routes/route_B_planner_audit.md
planner-audit blob: e0f0cca68bd27db0b452a5f35270d57afd8fbf54
Round03 Critic handoff: prompts/routes/handoffs/route_B_round03_critic_handoff_20260718.md
```

The contract freezes canonical `[LGE,T2,C0]`, a four-scale `[32,64,128,256]` sixteen-expert architecture, pathology-specific two-pass routing, numeric Pattern-SIP/full loss, deterministic four-shard OOF-frozen prototype banks, safe hard negatives, anatomy-guided conservative proposals plus prototype similarity-difference evidence, separate scar/edema ROIs/refiners, bounded final correction, exact no-T2 zero semantics, four-stage 32k-step MyoPS training, official CineMA matched control, first-party seven-step SVF plus real SyN, registered temporal aggregation, fresh lesion-centric selector/evidence, and strict known-bad/reviewer state machines.

B0–B10 have exact prompts, commands, inputs, outputs, validators, entry/success/failure states, reviewer inputs, and unique namespaces. The implementation gate precedes long training.

### Route C — M10 forensic and Cine fidelity

```text
branch head: e9966da52b65367a248dbcc746879fcac2422961
contract: prompts/routes/route_C.md
contract blob: 0f04a06dce5ebaaaa0e0f84ce317b88123fd1a26
executor plan: prompts/routes/route_C_executor_plan.yaml
executor-plan blob: 7e3bd792bf15d1778a227df6e5216d4b440c868d
evidence mapping: prompts/routes/route_C_round03_evidence_mapping.yaml
evidence-mapping blob: 2b5a068ee807c5f622dcd5b1732fdc05e144b960
critic request: prompts/routes/route_C_critic_request.md
critic-request blob: 314a479e98d2af888cfd945092ab6aef09860a83
planner audit: prompts/routes/route_C_planner_audit.md
planner-audit blob: 623216e8f1b1ecc64f3d6fb8d17b9f1f8711e595
Round03 Critic handoff: prompts/routes/handoffs/route_C_round03_critic_handoff_20260718.md
```

Route C preserves the historical M10 SRR-owned final logits and selector. It reclassifies the old residual gate as `anchor_residual_control_off_path`, requires fresh forced all-checkpoint replay and real D2/D3 final-path interventions, implements official CineMA/SVF/temporal fidelity without changing the historical MyoPS model, and maps 37 old evidence obligations to exact files/fields/producers/validators/reviewer checks.

The fixed serial graph is C0 instrumentation/fingerprint, C0B exact phase recovery, R1 replay/selector/interventions, R2 Cine implementation/tests/freeze candidate, and R3 Controller-final-freeze runtime/finalizer.

## 5. Compute and routing portfolio

### 5.1 Default independent assignments

```text
htzhulab:
- Route B full MyoPS evidence-warmup/refiner phases
- Route C exact historical phase recovery when required
- Route B/C heavy registration or temporal work when assigned

a100-gpu:
- Route B proposal/joint stages
- Route B/C heavy temporal or registration work
- matched Cine source/control lane when independent

volta-gpu:
- Route B implementation gate when exact batch-one preflight passes
- Route C non-overlapping all-checkpoint replay shards
- official CineMA extraction and matched adapter/control work
- real SyN and registration evaluation
- selected-checkpoint reload and lesion/Cine evaluation
- temporal checkpoint evaluation and validator GPU tests
```

Route B full four-scale MyoPS training and full registered temporal training are V100-incompatible until exact unchanged-config preflight proves otherwise. Width, expert count, input size, batch semantics, loss, sampler, budget, cases, and selector cannot be reduced for V100. V100 remains occupied by compatible independent work.

### 5.2 Race groups

Two-way race defaults:

```text
Route B B3/B4/B5/B6 full MyoPS: htzhulab + a100-gpu when the single critical job is pending and no distinct ready work has priority.
Route B B9 temporal: htzhulab + a100-gpu.
Route C C0B exact historical heavy phase: htzhulab + a100-gpu.
Route C R3 full temporal: htzhulab + a100-gpu.
```

Three-way race eligibility:

```text
Route B official CineMA matched lane and compatible registration job.
Route C individual replay checkpoint, adapter lane, extraction, or compatible registration/evaluation phase.
```

Every race binds identical logical-run/scientific hashes; isolated output/log/checkpoint/cache roots; one atomic winner lock; loser zero credit; pending-loser cancellation; retry lineage; and finalizer coverage. Distinct ready work always has priority over duplication.

Queue status is captured for all three partitions before submission. The 12-check/2-hour/24-hour threshold only permits a scheduler-saturation blocker; it never delays an immediate mirror or independent assignment.

## 6. Route decision checkpoints

### 2026-07-20

Route B:
- B0 source/order/manifest/fixture/partition assets terminal;
- B1 implementation merged;
- B2 real implementation gate terminal;
- no long formal training before B2 pass.

Route C:
- C0 historical graph, immutable anchor, fingerprints, and 37-row mapping terminal;
- C0B exact match/rerun decision terminal or exact recovery jobs active;
- R1 launches only after fingerprint gate.

### 2026-07-21

Route B:
- evidence warmup terminal with style/gradient gate;
- proposal stage terminal or exact scientific gate failure.

Route C:
- majority of all-checkpoint fresh replay complete;
- immutable-anchor selector receipts generated;
- real final-probability/final-logit intervention path proven.

### 2026-07-22

Route B:
- refiner/joint first formal 44-case evidence, selector, clean reload, and node interventions;
- official CineMA/control work terminal or exact external blocker.

Route C:
- R1 full replay/intervention terminal or exact needs-evidence/revision boundary;
- R2 official CineMA/SVF/temporal freeze candidate and real smoke terminal.

### Later freeze dates

```text
2026-07-23: only evidence-directed same-scope repair.
2026-07-24: no new model design or loss; freeze available candidates/evidence.
2026-07-25: route-local packets, independent reviews, Portfolio reconciliation input, paper/Docker work.
2026-07-26: runtime/review/Docker/packaging/paper/submission QA only.
2026-07-27: final submission; no new experiment.
```

Route B and Route C do not wait for one another. Their Critic threads run in parallel, and each Controller may start independently only after its own exact ready token.

## 7. Validator and known-bad status

By explicit user instruction, no shell/server command was run. The Planner performed a remote static schema/source review and recorded:

```text
Route A executor-plan validator: NOT_RUN_USER_PROHIBITED_SHELL
Route B executor-plan validator: NOT_RUN_USER_PROHIBITED_SHELL
Route C executor-plan validator: NOT_RUN_USER_PROHIBITED_SHELL
Route B partition/race validator: NOT_RUN_USER_PROHIBITED_SHELL
Route C partition/race/evidence-mapping validator: NOT_RUN_USER_PROHIBITED_SHELL
git diff --check: NOT_RUN_USER_PROHIBITED_SHELL
remote static schema review: PASS
```

The Route B/C Critic requests require actual zero exits on the exact bound commits before emitting a ready token. Therefore this publication is Critic-ready, not Controller-ready.

Known-bad coverage includes modality-order/wrapper/prototype/OOF/no-T2/Pattern-SIP/CineMA/control/SVF/Jacobian/temporal/freshness/reload/monitor/undertraining/race/V100/authority failures for Route B, plus partial 18/125/selector/anchor/intervention/residual/freeze/R3-edit/temporal-parent/evidence-mapping/replay-shard failures for Route C.

## 8. Runtime reviewer tokens

Route B reviewer tokens:

```text
ROUTE_B_ROUND03_REVIEW_CANDIDATE_READY
ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE
ROUTE_B_ROUND03_REVIEW_EXTERNAL_RESOURCE_BLOCKER
ROUTE_B_ROUND03_REVIEW_UNDERTRAINED
ROUTE_B_ROUND03_REVIEW_NEEDS_MONITOR
ROUTE_B_ROUND03_REVIEW_NEEDS_EVIDENCE
ROUTE_B_ROUND03_REVIEW_NEEDS_REVISION
```

Route C reviewer tokens:

```text
ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
ROUTE_C_ROUND03_REVIEW_ADEQUATE_NEGATIVE
ROUTE_C_ROUND03_REVIEW_EXTERNAL_RESOURCE_BLOCKER
ROUTE_C_ROUND03_REVIEW_UNDERTRAINED
ROUTE_C_ROUND03_REVIEW_NEEDS_MONITOR
ROUTE_C_ROUND03_REVIEW_NEEDS_EVIDENCE
ROUTE_C_ROUND03_REVIEW_NEEDS_REVISION
```

Each is bound in the route contract to exact evidence, adequacy, validator, accounting, rejection, next-actor, and authority rules. Reviewer acceptance permits only a future Portfolio reconciliation.

## 9. Current authority

```text
controller_authorized_now: 0
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
```

Planner publication, commit, or push does not equal Critic passage. Route B/C may start only after their separate Round03 Critics issue ready tokens bound to the exact route commits and blobs above.