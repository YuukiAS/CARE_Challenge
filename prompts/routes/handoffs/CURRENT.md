# CARE Current Development State

This is the stable source of truth for current CARE work. Read this file first before writing or executing any CARE plan, goal, route judgment, controller prompt, reviewer prompt, or handoff.

## Active state

```text
state_id: srr_mainline_production_sprint_20260720
round_id: post_round04_main_only
date: 2026-07-20
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
portfolio_mode: SUSPENDED_BY_USER_FOR_FIVE_DAY_SPRINT
single_active_scientific_line: SRR_MyoPS_Cine_from_historical_Route_B
next_required_batch: BATCH_0_CURRENT_IMPLEMENTATION_TRUTH_AND_AUTHORITY
controller_authorized_now: 0
route_worktree_development_authorized: false
formal_training_authorized_today: false
slurm_authorized_today: false
validation_upload_authorized: false
```

Default future GPT/Codex work is `main`-only. Do not start Route A/B/C controllers, do not continue route worktree development, do not open Round05, and do not use `/users/a/e/aereinh/CARE_worktrees/route_A`, `route_B`, or `route_C` for new implementation.

Remote route branches remain read-only provenance.

## User-authorized sprint model

The user explicitly decided that only the scientific line inherited from Route B remains active. Route A is dormant; Route C remains historical stop/hold evidence. The old cycle is suspended:

```text
portfolio planner -> route critic -> route controller -> staged Slurm -> reviewer -> next round
```

Current development model:

```text
one main integrator writes main
+ exact-SHA read-only model/data/Cine/red-team audits
+ small sequential code commits
+ append-only change ledger
+ code freeze before real training
```

Today, 2026-07-20, formal training and Slurm are forbidden. Allowed: code tracing/repair, real-case load, one forward/backward step, checkpoint save/reload, real inference/evaluator reproduction, tests, commit and push.

## Active documents, authority order

Read in this order:

```text
1. docs/plans/laneB_round04_active_srr_plan_correction_addendum.md
2. docs/plans/laneB_round04_active_srr_code_completion_todo.md
3. docs/plans/laneB_round04_active_srr_mainline_production_execution.md
4. docs/plans/laneB_round04_active_srr_change_review_ledger.md
```

Bindings:

```text
plan correction addendum:
1e01d5f8658431b3e76b2d268720ca34808782b7

refocused code TODO:
7d326d64f9628a0266ea3afc63a6eb10e1d0a5a5

original five-day plan:
8b801e80472dba54c1bcee008f5c2525e9636723

change ledger bootstrap/finalization:
05e566f0d3dc6d8f114d1996b8cc3e580193adf3
```

The correction addendum overrides conflicting parent-plan instructions. In particular:

- do not default to creating a second full `srr_production` network package;
- first converge and repair existing `srr_propref.py`, spatial dictionary, memory, training and evaluator code;
- any new production package is a thin facade unless current code is proven unrepairable;
- do not attempt all C0-C14 in one opaque goal;
- execute Batch 0 first, then Batch 1, Batch 2 and Batch 3 sequentially.

## Immediate task: Batch 0

Batch 0 must trace and bind the current implementation before major edits:

```text
real data
-> Dataset/DataLoader
-> SRR variant/final-output semantics
-> nnU-Net anchor source
-> prototype/memory source and loading
-> losses/backward
-> checkpoint continuity
-> inference
-> prediction-derived evaluator
-> CineMA/registration/temporal/export
```

It must also create the sole formal entrypoint configuration and fail if formal authority points to old Round04 synthetic/proxy B3-B8 scripts. Batch 0 does not train and does not claim the model is complete.

Required Batch 0 outputs are defined in the active TODO, including:

```text
results/srr_production/code_maturity/current_implementation_truth.md
results/srr_production/code_maturity/canonical_call_graph.json
results/srr_production/code_maturity/variant_final_output_matrix.csv
results/srr_production/code_maturity/anchor_prototype_loss_checkpoint_matrix.csv
results/srr_production/code_maturity/cine_call_graph.md
results/srr_production/code_maturity/legacy_path_inventory.csv
configs/srr_production/entrypoints.yaml
scripts/srr_production/audit_formal_entrypoints.py
tests/srr_production/test_formal_entrypoint_authority.py
```

Every commit must append the human-readable change ledger. A bare `PASS`, test count, validator result, token or packet state is not an acceptable explanation.

## Scientific invariants

The production candidate must preserve:

```text
[LGE,T2,C0] + explicit availability
modality-specific multi-scale encoders
shared/private/interaction retrieval
spatial/pathology-conditioned routing
real train/OOF prototypes and safe negatives
anatomy union/LV/RV
separate scar/edema proposals and soft-ROI refiners
no-T2 edema exact safety
pathology-specific bounded SRR correction
same-case nnU-Net anchor as segmentation basis/safety
real NIfTI inference
fair same-split Dice/HD/HD95/component/remote-FP evaluation
real multi-frame Cine + registration + temporal aggregation
```

The candidate must not become nnU-Net-only postprocessing: SRR must consume raw modalities and own retrieval, proposal, refiner and final correction. `anchor_identity_control` must reproduce nnU-Net exactly. `srr_no_anchor_control` is diagnostic only, not default deployment.

## Historical evidence boundary

```text
Route B reviewed controller packet: 2e24f290e83e356fbfba5f73da4fde98b657390b
Route B operational reviewer commit: 3950fe10ac31ef68da20f3ef7ffb001d6b17e6d9
Route B merge on main: 078c3548645b14224b997e41995520ec865d4b62
```

The Round04 review established operational packet completion only. It did not establish real training, valid Dice/HD/HD95, scientific superiority, hosted readiness or first-place capability. Old B3-B6/B8 scripts and proxy metrics are historical/known-bad until explicitly deauthorized or repaired.

## Current route status

```text
Route A: HISTORICAL_DORMANT_NOT_ACTIVE
Route B: HISTORICAL_EVIDENCE_MERGED_TO_MAIN_NOT_ACTIVE_AS_ROUTE
Route C: HISTORICAL_STOP_AND_HOLD_NOT_ACTIVE
SRR mainline: ACTIVE_BATCH_0_NO_TRAINING_TODAY
```

No route has a current critic/controller/reviewer handoff. Old route handoff files cannot authorize new work.

## Authority boundary

```text
controller_authorized_now: 0
formal_training_authorized_today: false
slurm_authorized_today: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
route_worktree_development_authorized: false
route_branch_deletion_authorized: false
```
