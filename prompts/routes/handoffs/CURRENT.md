# CARE Route Portfolio Current Round

This is the stable entrypoint for the active CARE route portfolio round. Read this file first, then read only the handoff named for the current role and route.

## Active Round

```text
round_id: round03
date: 2026-07-18
planner_thread_model: one GPT planner thread owns Route A, Route B, and Route C
critic_thread_model: one separate critic thread for each active route
milestone_model: retired for this route portfolio loop
route_round_model: portfolio planning round with route-specific critic handoffs
planner_environment: remote GitHub connector plus local ChatGPT syntax sandbox
validator_not_run_by_planner: true
```

Round03 is not a scientific milestone, route promotion, validation authorization, M11 authorization, cross-route merge, hosted-metric claim, or final scientific decision.

## Planner Entry

```text
source Planner prompt:
prompts/routes/handoffs/portfolio_round03_planner_prompt_20260717.md

current Planner plan:
prompts/routes/portfolio_round03_planner_plan_20260718.md
blob: 61ae3117137b42b38fbd1a3112ea77a019cd87f5

current Planner handoff:
prompts/routes/handoffs/portfolio_round03_planner_handoff_20260718.md
blob: c7024ee99f1a3135f02f893b053bad8b63bf5208
```

Portfolio state:

```text
Route A: DEFERRED_FALLBACK_NOT_ACTIVE
Route B: ACTIVE_FULL_SRR_V3
Route C: ACTIVE_M10_FORENSIC_EVIDENCE_AND_CINE_FIDELITY
current_controller_authorizations: 0
```

## Bound Route Planner Revisions

### Route A — dormant fallback

```text
route head: fae8a732bbf625db367e0b68c04f1490d0c97be3
contract blob: 370c25de0e35dbd5c854bbdfb81589ee8c0a4368
executor-plan blob: c681d761cfa145d68ba906f5eb33607843af8b80
critic-request blob: 227c8f69f69e2b07b72f5df5f3323b2f03136bd1
planner-audit blob: 61d8cb48fab3728d1330975fb1bc2178446313f9
```

Route A has no current Round03 Critic, Controller, training or Slurm authority. It may be reactivated only by explicit user authorization or a later Portfolio Planner decision after a documented Route B pre-training implementation blocker.

### Route B — full SRR-v3

```text
route head: 11d5c3d90028fa19ccd1c709d9ce5d4e90f5b96f
contract blob: 1d58d7a37eacaee8cc15c159758e5074e794de8b
executor-plan blob: 082e2641d8fdf693e929d1aa460ae689b80ce0d2
critic-request blob: a1b03b7366df14bf9ca9628b309ced55dbf6db47
planner-audit blob: 5f8764c08908e725830817d42ed3dc606971cda9
B10-finalizer prompt blob: ad48d04aeac2a69fb99d41ec4fa73d159138d269
round03 critic-review blob: 8da317c22fc915bb6ba880f561f18d93d7218d70
Critic-handoff blob: e444320bdb6bb04007a937d5728892f7b5ce9d08
```

### Route C — M10 forensic evidence and Cine fidelity

```text
route head: d8dddfad9dbbe9089f12f452ea9c4ab65aabf633
contract blob: 0f04a06dce5ebaaaa0e0f84ce317b88123fd1a26
executor-plan blob: b521620e5b93ce5974882df8bad745b17a3968f9
evidence-mapping blob: 2b5a068ee807c5f622dcd5b1732fdc05e144b960
evidence-mapping required row count: 37
critic-request blob: 5670bde5b2c7da12a3b2a89d6c98677119ca89b7
planner-audit blob: 753398354cd65f45cb96f2ccd2636553be755cb6
R3-finalizer prompt blob: bc0576e09bb5998b272487fe002c39030c862b83
round03 critic-review blob: 6636b29426ff3823177fa59555e09b13281cfa38
Critic-handoff blob: 73b5bbd5e8519ce34c83b5114ce0356c3ca75b43
```

Any later route head or bound blob change makes the corresponding Critic handoff stale and requires a new Planner binding.

## Critic Entries

```text
route_A critic current prompt:
NO_CURRENT_CRITIC_HANDOFF

route_B critic current prompt:
prompts/routes/handoffs/route_B_round03_critic_handoff_20260718.md

route_C critic current prompt:
prompts/routes/handoffs/route_C_round03_critic_handoff_20260718.md
```

Route A Critic must stop and must not reuse a Round02 prompt or issue a Round03 token.

Route B and Route C Critics must independently re-fetch their exact route heads/blobs, visually read Project SRR-v2/v2.5/v3, read current main governance and route-local evidence, and run the required executable checks before a ready token.

Allowed Route B planning tokens:

```text
ROUTE_B_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND03_PLANNING_NEEDS_REVISION
```

Allowed Route C planning tokens:

```text
ROUTE_C_ROUND03_PLANNING_READY_FOR_CONTROLLER
ROUTE_C_ROUND03_PLANNING_NEEDS_REVISION
```

A ready token authorizes only the corresponding exact-route Controller as a Codex goal or goal resume. It does not authorize validation packaging/upload, route promotion, M11, cross-route merge, hosted metric claims, or a final scientific decision.

## YAML Repair and Validation Boundary

The Route B/C executor plans were rewritten from unsafe YAML flow mappings to block mappings. Commands/templates containing `${SLURM_JOB_PARTITION}`, `{phase}`, `{checkpoint_sha}`, `{partition}`, `{attempt}`, nested quotes or `&&` are explicit strings. All B0–B10 and C0/C0B/R1/R2/R3 prompt paths were re-fetched and exist.

The Planner had no `/users` shell and did not claim repository validator exits. The coordinator has now run local `/users` executable checks on the bound Route B and Route C worktrees without starting controllers, Slurm jobs, or training. Recorded receipts:

```text
Route B executor-plan validator: PASS_EXIT_0
Route B PyYAML parse: PASS_EXECUTORS_11
Route B git diff --check: PASS_EXIT_0
Route B path/mapper check: PASS_B0_B10_PROMPTS_11_AND_ARCHITECTURE_COMMANDS_EXIST
Route B mapper command help: PASS_EXIT_0_FOR_VALIDATE_AND_GENERATE_ARCHITECTURE_ENTRYPOINTS
Route B partition/race static check: PASS_EXIT_0
Route C executor-plan validator: PASS_EXIT_0
Route C PyYAML parse: PASS_EXECUTORS_5
Route C evidence mapping parse: PASS_ROWS_37
Route C git diff --check: PASS_EXIT_0
Route C partition/race/evidence/static finalizer mapper-command check: PASS_EXIT_0
Route C mapper command help: PASS_EXIT_0_FOR_VALIDATE_AND_GENERATE_ARCHITECTURE_ENTRYPOINTS
Route C R3 mapper/finalizer chain static check: PASS_EXIT_0
Route C care_mapper.py absent from executable commands: PASS_EXIT_0
Route C finalizer not success-only after runtime command: PASS_EXIT_0
```

These receipts are not Controller authorization. They allow fast independent Critic review of the current repair deltas and inherited hardening gates. Any later route head/blob mismatch, unavailable check, or nonzero re-run requires the route-specific `PLANNING_NEEDS_REVISION` token. Controller start remains forbidden until the corresponding Critic writes the exact READY token for the bound head.

## Three-Partition Portfolio Policy

Round03 retains all three partitions:

```text
htzhulab
a100-gpu
volta-gpu
```

`htzhulab` is default, `a100-gpu` is fallback/race partner, and `volta-gpu` is used for exact-compatible or independent compatible work. The user has approved V100 use, V100 race and three-way race. Distinct ready work has priority over duplicate routing. A single critical compatible job may race immediately. Exact scientific hashes, isolated output/log/checkpoint/cache roots, atomic winner lock, pending-loser cancellation, loser zero credit, retry lineage and all-attempt finalizer coverage are mandatory. V100 semantic downscaling is forbidden.

Formal wrappers must use `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`; bare `python` is forbidden. Submitted, pending, running, awaiting-accounting, undertrained and monitor packets are not completion.

## Controller Terminal Packet / Reviewer Targets

This section records the post-controller terminal packet handoff for the current
Round03 route work. It supersedes the planner/critic binding only for dashboard
phase display and reviewer-target routing. It is not a route promotion,
validation upload authorization, M11 authorization, hosted metric claim,
cross-route merge, or final scientific decision.

```text
route_B reviewer_target_head: 8dfa40f8c4cedb2507f35a482bd46244a7a1c94c
route_B terminal_token: ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW
route_B reviewer_output_path: results/route_B/review.md
route_B route_promotion_decision: NOT_REVIEWED
route_B route_negative_decision: NOT_REVIEWED
route_B scientific_resolution_status: AWAITING_REVIEW
route_B validation_upload: false
route_B hosted_metric_claim: false
route_B m11_started: false
route_C reviewer_target_head: 72750c431c0a1cc728928b01b5883102153dbd4b
route_C terminal_token: ROUTE_C_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW
route_C reviewer_output_path: results/route_C/review.md
route_C route_promotion_decision: NOT_REVIEWED
route_C route_negative_decision: NOT_REVIEWED
route_C scientific_resolution_status: AWAITING_REVIEW
route_C validation_upload: false
route_C hosted_metric_claim: false
route_C m11_started: false
```

Reviewer source-of-truth remains the route-local terminal packet, target commit,
review request, validator evidence and Slurm/accounting records. The watchboard
is an ops view for users, not reviewer evidence.

## Round03 Decision Checkpoints

```text
2026-07-20:
- Route B B0-B2 implementation/manifest/validator/preflight gate terminal.
- Route C C0/C0B fingerprint/evidence-map and exact recovery decision terminal.

2026-07-21:
- Route B evidence-warmup/proposal gate.
- Route C fresh replay majority, immutable-anchor selector receipts and real intervention path.

2026-07-22:
- Route B first formal MyoPS evidence and official CineMA/control evidence.
- Route C R1 terminal evidence or exact blocker and R2 real Cine fidelity freeze candidate.

2026-07-23: evidence-directed same-scope repair only.
2026-07-24: no new scientific design or loss.
2026-07-25: route-local packets, independent reviews and Portfolio reconciliation input.
2026-07-26: runtime/review/Docker/packaging/paper/submission QA only.
2026-07-27: final submission; no new experiment.
```

Route B and Route C do not wait for one another. Their Critics may run in parallel after coordinator validation; each Controller may start only after its own exact ready token.

## Authority Boundary

```text
controller_authorized_now: 0
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
```

Planner publication, commit or push is not Critic passage. Round03 planning does not execute implementation, training, Slurm submission/monitoring, runtime `review.md`, validation upload, route promotion, M11, cross-route merge, hosted metric claims or final scientific decisions.
