---
document_type: route_C_round04_followup_decision
route_id: route_C
portfolio_round: round04
date: 2026-07-19
role: gpt_planner
planning_source: authenticated_github_repository
planning_main_commit: 6c8d6f26ed4907ee59023795265ee4e1c53fb2b8
route_B_context_commit: b9c7664da7cb1f1892fff37a4497722f31a0a96d
route_C_evidence_commit: 17062b00edc3443aacefe8583568797a9f2655ba
reviewed_controller_repair_commit: 1e663cfa64f00413f005bef26310290fd43ec8ab
review_token: ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
current_portfolio_status: EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION
decision_token: ROUTE_C_PORTFOLIO_STOP_AND_HOLD
route_C_critic_required: false
route_C_controller_required: false
controller_start_authorized: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_CURRENT_CONVERSATION_PROJECT_MATERIALS
---

# Route C Round04 follow-up decision

## 1. Decision

```text
ROUTE_C_PORTFOLIO_STOP_AND_HOLD
```

Route C does not open a new Round04 Controller task now. Its Round03 assignment has reached reviewer-accepted evidence completeness, all recorded runtime obligations are terminal, and no current Route C critic, reviewer or controller handoff exists. Route C remains an evidence input for portfolio reconciliation rather than an active model-development lane.

This is a portfolio hold, not route promotion, scientific closure or a claim that every Route C mechanism is useful. The hold preserves the reviewed packet and prevents a new high-cost Route C goal from duplicating Route B or degenerating into evidence maintenance without a new leaderboard-facing hypothesis.

## 2. Source boundary and exact refs

This Planner runtime did not have the server worktree `/users/a/e/aereinh/CARE` mounted. The decision therefore uses authenticated GitHub files at the exact remote refs below and does not claim a local shell receipt:

```text
origin/main:    6c8d6f26ed4907ee59023795265ee4e1c53fb2b8
origin/route_B: b9c7664da7cb1f1892fff37a4497722f31a0a96d
origin/route_C: 17062b00edc3443aacefe8583568797a9f2655ba
```

The current Route C remote still matches the known reviewer commit. The reviewed controller repair remains:

```text
1e663cfa64f00413f005bef26310290fd43ec8ab
```

The accepted review token remains:

```text
ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
```

`prompts/routes/handoffs/CURRENT.md` already records Route C as `EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION`, with `NO_CURRENT_CRITIC_HANDOFF` and `NO_CURRENT_REVIEWER_HANDOFF`. This decision does not alter the current Route B critic rereview binding or any of its six planning blobs.

## 3. Rules and evidence read

The decision was made after reading the required governance, route, architecture and skill files:

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
docs/figures/round03_route_architecture/round03_route_architecture_report.md
docs/figures/round03_route_architecture/round03_routeC_structure.d2
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
```

The latest Route C packet and implementation sources were also read at the bound Route C commits:

```text
results/route_C/review.md
results/route_C/controller_report.md
results/route_C/completion_check.md
results/route_C/review_request.md
results/route_C/MANIFEST.md
results/route_C/finalizer_state.json
src/care_myocardium/route_C/myops/evidence_contract.py
src/care_myocardium/route_C/cine/fidelity.py
src/care_myocardium/cine/cinema_adapter.py
src/care_myocardium/cine/registration_model.py
src/care_myocardium/cine/temporal_dictionary.py
src/care_myocardium/cine/temporal_model.py
src/care_myocardium/cine/temporal_output.py
src/care_myocardium/models/proposal_prototypes.py
src/care_myocardium/models/srr_propref.py
```

The current-conversation Project images for SRR-v2, SRR-v2.5 and SRR-v3 were visually read. The recovered route invariant is availability-aware multi-scale retrieval, anatomy-guided separate scar and edema proposals, pathology-specific soft-ROI refinement, bounded anchor-aware composition, and a Cine path that uses official anatomy evidence, reference-space registration and registered temporal evidence. The hold does not redefine or weaken this architecture.

## 4. What Route C completed

### 4.1 R1 evidence and known-bad repair

The Round03 Controller repaired the real `positive_negative_prototype_swap` intervention rather than editing a result table. The accepted review records:

```text
positive_negative_prototype_swap rows: 88
harmful detections: 88/88
changed-voxel rows: 88/88
total changed voxels: 17633
rows with changed components: 80/88
no-op nonzero rows: 0
anchor-residual off-path nonzero rows: 0
```

Strict R1, R2 and final validators exited zero, the declared known-bad tests passed, and the previous fail-open packet is no longer accepted. This evidence must remain immutable unless a new Route C commit deliberately reopens the reviewer binding.

### 4.2 Terminal accounting

The fresh repair job `59530203` completed with exit `0:0`; the superseded failed attempt `59530017` is retained with zero credit. The R3 runtime and finalizer jobs are terminal, aggregation exited zero, mapper final completed, strict validation exited zero, and the packet contains no pending, submitted, running or awaiting-accounting state.

Therefore, stopping does not abandon a live Slurm obligation, a monitor packet, a partial checkpoint or an unaggregated runtime result.

### 4.3 Cine fidelity chain

The reviewed packet contains official CineMA provenance and the pinned weight SHA, MIT license, real logits/probabilities/features/entropy evidence, a matched random source, seven-step SVF receipts, true Jacobian fields, inverse consistency, real SyN evidence, 60 pair receipts, a 12-case denominator, registered temporal inputs and final-output changes.

These facts satisfy the Round03 evidence/fidelity assignment. They do not establish that the resulting Cine candidate is superior to its controls.

## 5. Why a new Route C Controller is not justified

### 5.1 The MyoPS evidence is predominantly negative against the anchor

The anchor-relative `help_harm_matrix.csv` shows that D2 and D3 change the final output but generally reduce scar and edema performance and often increase remote false positives, component burden and pathological volume ratios. The failures are especially severe in T2-present CenterB/CenterC cases. Examples include:

```text
D2 Case2002: edema Dice 0.5376 -> 0.3836; scar Dice 0.5603 -> 0.4608
D2 Case3004: edema Dice 0.4530 -> 0.0148; scar Dice 0.6247 -> 0.4497
D3 Case3004: edema Dice 0.4530 -> 0.0633; scar Dice 0.6247 -> 0.2137
D3 Case3023: edema Dice 0.1629 -> 0.0088; scar Dice 0.6613 -> 0.1558
```

A small number of cases improve, proving that the path is not an identity transform, but the current Route C evidence does not identify a reproducible subgroup selector that can turn those isolated gains into a candidate. Opening another full M10-burden Controller without such a selector would repeat a known negative experiment family.

### 5.2 Component causality is verified, but several mechanisms are not candidate-ready

`component_state_classification.csv` verifies many real final-output effects and the repaired harmful prototype swap. It also retains explicit pipeline defects, including challenge-decode disconnection for `final_probability_composition_off` and defect classifications attached to edema proposal/refiner interventions. Evidence completeness truthfully records these states; it does not convert them into a leaderboard gain mechanism.

### 5.3 Cine controls do not show a differentiated gain

The matched-control packet uses the same downstream architecture and training contract, but the selected pretrained and random checkpoints both reach the same reported score `0.60000`. The current evidence therefore supports correct control construction, not a CineMA pretraining-benefit claim.

The registered temporal rows prove input consumption and output change, but the recorded case rows use the same `17` changed voxels, `1` changed component, `0.721` myocardium Dice and `8.4 mm` HD95. In addition, the older first-party temporal helper explicitly labels its final source as `deterministic_temporal_union_compact_label_proxy`. These receipts are sufficient for the reviewed fidelity/effect question, but they do not define a new case-sensitive leaderboard improvement hypothesis for another Route C round.

### 5.4 Reopening Route C would duplicate Route B or become status maintenance

Route C was created to inherit the complete M10/follow-up/follow-up2 forensic and Cine-fidelity burden. That burden has now been executed and independently reviewed. Route B is the active route for full SRR-v3 scientific implementation and training, including OOF prototypes, hard negatives, proposal/refiner, bounded correction, official CineMA matched control, faithful registration and registered temporal aggregation.

A new Route C task limited to validators, packet reconciliation, report generation or replay bookkeeping would violate the requirement that every active route be leaderboard-facing. A new Route C model redesign using the same scientific chain would duplicate Route B while carrying Route C's larger historical replay burden. Neither action is an efficient or scientifically distinct follow-up.

## 6. Why the hold is not execution avoidance

The hold is justified by completed obligations and negative scientific evidence, not by compute avoidance:

1. The assigned R1/R2/R3 task graph reached terminal accounting and post-completion aggregation.
2. The independent reviewer accepted the exact repaired packet.
3. Minimum declared adapter, registration and temporal evidence budgets were met.
4. No pending or monitor state remains.
5. The known-bad fail-open was fixed and regression-tested.
6. The MyoPS candidate evidence is mostly harmful relative to the anchor.
7. The Cine matched control does not show a differentiated source benefit.
8. Route B now owns the non-duplicative full SRR-v3 candidate-development lane.

Continuing merely because compute is available would be the anti-laziness failure in reverse: it would spend resources on a route without a new falsifiable leaderboard hypothesis.

## 7. Exact reactivation gates

Route C may be reactivated only after one of the following machine-identifiable events:

### Gate C-1: reviewer binding becomes stale

A new `route_C` commit changes the reviewed packet, first-party validator semantics, R1/R2/R3 implementation, source fingerprints or bound evidence files. The next Planner must bind the new commit and issue a fresh Route C critic handoff before any Controller start.

### Gate C-2: portfolio reconciliation identifies a named Route C-only evidence gap

The portfolio reconciliation document identifies the exact missing file, field, denominator, intervention, hash or accounting receipt whose absence prevents comparison among reviewed routes. The follow-up may repair only that named gap while preserving the full Route C inherited contract.

### Gate C-3: Route B review exposes a forensic defect owned uniquely by Route C

A Route B critic or post-controller reviewer returns a controlled revision/evidence token and names a defect in checkpoint replay, D2/D3 intervention semantics, CineMA provenance, SVF/Jacobian/SyN fidelity, temporal registered-input consumption or finalizer accounting that requires the Route C forensic lane rather than Route B implementation work.

### Gate C-4: a distinct leaderboard hypothesis is approved

The user or portfolio Planner approves a hypothesis that is not a duplicate of Route B and supplies all of these fields before critic review:

```text
target metric
same-split baseline
expected gain mechanism
fixed model/dataflow delta
minimum effective training budget
case-wise help/harm and hard-subgroup gates
failure threshold
validator and known-bad semantics
```

The hypothesis must explain how it addresses the observed anchor-relative harm or the absence of pretrained/temporal differentiation. A new architecture search or another evidence-only replay does not satisfy this gate.

### Gate C-5: explicit downstream authority is granted

A later user decision authorizes a new Route C scientific task after portfolio reconciliation. Such authorization still requires a complete planning bundle, separate critic review and an exact current binding; it does not automatically authorize upload, promotion, M11 or a final conclusion.

## 8. Current actor routing

```text
Route C critic required now: no
Route C Controller required now: no
Route C reviewer required now: no
Route C packet role: portfolio reconciliation evidence
next active actor: portfolio Planner/reconciler and the current Route B planning critic
```

No Codex Route C goal should be started from this decision. The next Route C actor appears only after one of Gates C-1 through C-5 is recorded in the repository.

## 9. Authority boundary

This decision does not authorize:

```text
Route C Controller start
validation packaging or upload
route promotion
M11
hosted metric claims
cross-route merge
final scientific decision
```

The reviewed Route C packet remains evidence-complete and held for portfolio reconciliation.
