# CARE Route Portfolio Round 02 - GPT Planner Handoff

You are the single GPT planner thread responsible for Route A, Route B, and
Route C. This is a planning handoff, not a Codex execution prompt.

Round02 must produce controller-forward work for all three routes. A
status-only response, read-only audit round, or "wait for another review" round
is not acceptable. If a route cannot train immediately, the planner must specify
the concrete unblock, repair, validation, and then the bounded train/eval or
equivalent execution step that moves the route forward.

Round02 must be leaderboard-facing, not merely runnable. For every route, the
planner must state how the proposed work targets `myops_scar`, `myops_edema`,
and `myocardium_cinemyops`, why the design has plausible upside over the
current nnU-Net baseline, and what evidence would reject the route. Engineering
cleanup is allowed only when it directly unlocks reviewer acceptance or the next
metric-facing controller step.

Do not run code, submit Slurm jobs, upload validation packages, claim hosted
metrics, promote a route, start M11, merge routes, or make a final scientific
decision.

## Source Branches

Read handoff and shared policy from `main` first:

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/README.md
prompts/routes/route_portfolio_planner_prompt.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
prompts/routes/handoffs/portfolio_round02_planner_handoff_20260717.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
routes/README.md
wiki/README.md
```

If the plan includes Slurm execution, also read
`.agents/skills/slurm-routing-partition/SKILL.md`. If the plan touches model
architecture, loss wiring, dataflow, export, Cine temporal paths, mapper output,
or architecture fingerprints, also read `.agents/skills/care-mapper/SKILL.md`.

Then read route evidence from the route branches, not from `main`:

```text
route_A: prompts/routes/route_A.md, prompts/routes/route_A_executor_plan.yaml,
         results/route_A/result.md, controller_report.md,
         completion_check.md, review.md, validator outputs

route_B: prompts/routes/route_B.md, prompts/routes/route_B_executor_plan.yaml,
         results/route_B/result.md, controller_report.md,
         completion_check.md, review.md, validator outputs

route_C: prompts/routes/route_C.md, prompts/routes/route_C_executor_plan.yaml,
         results/route_C/result.md, controller_report.md,
         completion_check.md, review.md, validator outputs
```

For Route C, additionally read the inherited M10 / follow-up / follow-up2
planning and history sources before writing any Round02 plan:

```text
prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_planning_review.md
prompts/tasks/20260714_srr_v3_m10_continuation_reconciliation_planning_review.md
prompts/tasks/20260715_srr_v3_m10_followup2_evidence_and_cine_fidelity_repair_planning_review.md
prompts/routes/route_c_m10_followup2_partial_evidence_note.md
wiki/current_state.yaml
wiki/history/COMPARISON.md
wiki/history/M09/**
wiki/history/M10/**
```

If a file exists on a route branch but not on `main`, use the route branch copy
as source of truth for that route. If `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`
is missing on a route branch, read the `main` copy and treat the missing route
copy as a handoff defect to repair.

For SRR / MyoPS / Cine planning, visually read the ChatGPT Project background
SRR diagrams at v2 and later. Repository image paths are version references only.

## Round02 Hard-Requirement Inheritance Matrix

The planner must carry forward prior anti-laziness and scientific-design
requirements. Do not drop an old requirement merely because this portfolio loop
no longer uses the single-route milestone numbering.

The permanent source of truth for these requirements is:

```text
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
```

The matrix below is the Round02 application of that permanent file. Future
rounds must keep using the permanent matrix, even if they do not copy this
section verbatim.

### Shared requirements for Route A, Route B, and Route C

All three routes must remain leaderboard-facing and must target the three CARE
Myocardium leaderboard metrics: `myops_scar`, `myops_edema`, and
`myocardium_cinemyops`. They must not use `foreground_mean`, empty-GT
improvement, compact-label proxy metrics, local proxy-only metrics, or
engineering pass/fail status to hide failure on those three tasks.

Each route plan must include:

- the target metric or metrics for this round and the expected gain mechanism;
- same-split nnU-Net baseline comparison and case-wise help/harm matrix;
- hard subgroup checks: T2-present edema, no-T2 safety, CenterB/CenterC when
  available, scar-positive cases, remote false positives, component count,
  `Dice`, `HD95`, and volume-ratio guardrails;
- `diagram_versions_read`, `visual_read_status`, and the route objective
  recovered from the SRR diagrams;
- exact ordered controller task graph, write scopes, required files, validators,
  known-bad fixtures, finalizer behavior, and reviewer pass requirement;
- minimum-effective-training or evidence-classification fields, including
  optimizer steps, train-loop seconds, validation events, eval-case counts,
  overfit/prediction sanity, loss decrease, same-split baseline, and cache
  isolation where training is planned;
- Slurm preflight for environment, Python executable, `torch` import, CUDA
  visibility, and route-specific entrypoint; bare `python` is not acceptable in
  formal Slurm wrappers;
- Slurm dependency semantics: training-to-training dependencies use `afterok`,
  finalizer/accounting dependencies use `afterany`;
- terminal accounting and post-completion aggregation before review;
- strict validators that fail closed and known-bad fixtures that cover semantic
  bypasses, not only file existence;
- route-local mapper/fingerprint receipts when architecture, loss, dataflow,
  export, or Cine temporal behavior changes;
- lightweight publication only: small Markdown/CSV/JSON and required
  first-party source/helper/test files; no checkpoints, NIfTI outputs, raw data,
  large logs, secrets, upload packages, or hosted submission artifacts.

Every route still forbids validation upload, route promotion, M11, cross-route
merge, hosted metric claims, and final scientific decisions in Round02.

### Route A retained requirements

Route A must retain requirements 1-24 and 34 from the strong-requirement audit.
It does not inherit Route C's old M10 checkpoint replay, anchor-relative selector
formula, D2/D3 follow-up2 intervention burden, learned-registration fidelity
contract, or M10 large-budget training floors as hard requirements.

The planner must write Route A as a fast but real leaderboard-facing compressed
SRR candidate. It must preserve live modality evidence, availability-aware
retrieval, anatomy-guided scar/edema proposal, pathology-specific refinement,
bounded nnU-Net-anchored correction, no-T2 safety, same-split help/harm, and
real multi-frame Cine evidence or an honest negative/incomplete packet.

Critic must reject any Route A plan that is nnU-Net-only, postprocess-only,
wrapper-only, proxy-only, validator-only, or candidate-ready while Cine remains
frame0-only, fake-temporal, or unresolved.

### Route B retained requirements

Route B must retain requirements 1-24 and 30-34 from the strong-requirement
audit. It does not inherit Route C's old M10 all-checkpoint replay,
anchor-relative selector, D2/D3 follow-up2 evidence repair, or M10 aggregate
large-budget floors as Round02 hard requirements.

The planner must keep Route B as the complete SRR-v3 implementation route, not a
Route A compressed variant. It must preserve the full MyoPS SRR-v3 causal chain:
modality-specific stems, availability-aware router, shared/private/interaction
dictionary or explicit optional-interaction handling, train/OOF prototype
provenance, anatomy decoder, scar proposal, edema proposal, soft ROI, scar and
edema refiners, bounded residual correction, final-output interventions,
save/reload/export, strict validation, and known-bad semantic regressions.

For Cine, Route B must retain real anatomy-source provenance, multiclass logits
/ features / uncertainty, ED/reference and key-frame handling, real registration
or a declared fixed/classical control, temporal aggregation that consumes
registered evidence, and final-output intervention. If it uses pretrained
CineMA, it must define a matched random-init or equivalent control before
claiming pretraining benefit. If it uses learned registration, it must keep the
scaling-and-squaring, Jacobian, inverse-consistency, real SyN/control, and
selected-checkpoint reload checks. If it enters long temporal training, it must
define cumulative resume, zero-credit partial/timeout handling, and parent-hash
receipts.

Critic must reject any Route B plan that downgrades the architecture to a
minimal residual head, skips Cine as optional, treats an honest blocker as an
implementation pass, or repeats already-passed long train/eval without a
validator-proven need or a training-semantics change.

### Route C retained requirements

Route C must retain all 34 strong requirements and all old M10 / follow-up /
follow-up2 requirements. No requirement is retired for Route C unless the user
explicitly approves that removal.

The planner must preserve the old M10/follow-up2 obligations, including fresh
all-checkpoint replay with `--evaluate --force`, per-checkpoint raw-output and
state-dict/hash receipts, anchor-relative checkpoint selection with `Dice`,
`HD95`, remote-FP and eligibility gates, calibration freeze, D2/D3 real
final-output interventions, deterministic clean baselines, no-op controls,
known-bad positive/negative swaps, CineMA provenance and matched random-init
control, faithful registration with real Jacobian/inverse/SyN evidence,
registration-negative adequacy boundaries, temporal evidence that consumes
selected CineMA and registered anatomy/motion/uncertainty, cumulative temporal
resume, strict validators, durable finalizer, and independent reviewer boundary.

Critic must reject any Route C plan that relies only on the Round02 summary,
does not read the listed M10/follow-up2 sources, downgrades old hard gates,
treats prior partial runtime or monitor packets as completion, or turns Route C
into a generic Route A/B repair.

## Current Evidence Summary

### Route A

```text
branch: route_A
controller_commit: b8f05521500971953a2fc9f286de8520f1ea5b4f
review_commit: 05a6102073c8bb200fd4c84d6d0dff64e5a75f78
review_file: results/route_A/review.md
review_decision: ROUTE_A_REVIEW_NEEDS_REVISION
```

Reviewer-supported evidence:

- Slurm job `59164420` completed with `ExitCode=0:0`, elapsed `00:33:36`.
- Formal adequacy passed: `169694` optimizer steps,
  `1800.0097081299173` train-loop seconds, `44` MyoPS eval cases.
- Negative/no-candidate signal is credible: `myops_scar =
  0.022727272727272728`, local Cine proxy `0.02004644182029281`, all 44 MyoPS
  rows have `route_changed_voxels == 0`, and the only T2-present
  edema-positive case has edema Dice `0.0`.

Reviewer blockers:

- Validator and known-bad coverage are below the Route A contract.
- Final receipts are stale or contradictory:
  `controller_context.json`, `mapper_report_final.md`, and
  `architecture_delta_final.md` still contain earlier smoke/gate-failed
  statements.

Round02 planner must give Route A a controller task that at least repairs the
packet/validator/receipt issues and then sends Route A back to an independent
reviewer. If the planner wants more Route A experimentation, it must define a
bounded train/eval or equivalent execution step; a read-only re-audit is not
enough.

### Route B

```text
branch: route_B
controller_commit: 0200e86f7a95ff9753f9c425419052e878d342f4
review_commit: cde0e0b658893b327aa5fb3129d37a99f1cf7c47
review_file: results/route_B/review.md
review_decision: ROUTE_B_REVIEW_NEEDS_REVISION
```

Reviewer-supported evidence:

- Slurm race is terminal: winner `59364846` on `htzhulab` completed with
  `ExitCode=0:0`, elapsed `00:32:02`; losers `59364845` and `59364847` were
  cancelled.
- Bounded train/eval adequacy passed: `25000` optimizer steps,
  `1908.338` train-loop seconds, `2` validation events, `10` MyoPS eval cases,
  `5` Cine eval cases, loss decrease, and cache isolation.
- Terminal aggregation is present in tracked lightweight packet files.

Reviewer blockers:

- `validate_route_b_packet.py` does not check adequacy rows, Slurm terminal
  accounting, aggregation outputs, or controller/finalizer consistency.
- Known-bad fixtures do not cover the semantic bypasses required by the Route B
  contract.
- `validator_implementation_report.json` still reports
  `ROUTE_B_SCIENTIFIC_UNDERTRAINED`, which conflicts with the final ready
  packet after adequacy recovery.
- The route branch must have access to `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`.

Round02 planner should prioritize a narrow Route B controller revision. The
controller should not repeat the already passed long train/eval unless the
repair changes training semantics or the revised validator proves the existing
evidence insufficient.

### Route C

```text
branch: route_C
controller_commit: 789ee4d
review_commit: 7b6c2d36bceefc5eb0f64f4977fd43f4194cc7b4
review_file: results/route_C/review.md
review_decision: ROUTE_C_REVIEW_NEEDS_REVISION_CONFIRMED
```

Reviewer-supported evidence:

- The non-ready controller conclusion is supported.
- MyoPS residual-gate intervention is disconnected from final output:
  `changed_voxels=0`, `final_output_changed=false`.
- Cine evidence is blocked by missing CineMA/anatomy weights and missing real
  CineMyoPS case inputs.
- No Slurm monitor packet or submitted-only state is being treated as completion.

Round02 planner must give Route C a controller task that repairs or re-scopes the
MyoPS residual-gate path and obtains real Cine evidence inputs before rerunning
lane gates. It must not authorize formal runtime, validation packaging, upload,
M11, or route promotion from the current non-ready packet.

## Required Planner Output

Write a Round02 plan with all of the following:

- exact next actor for each route: `route_A controller`, `route_B controller`,
  and `route_C controller`;
- target leaderboard metrics for each route: `myops_scar`, `myops_edema`, and
  `myocardium_cinemyops`;
- expected gain mechanism, same-split baseline comparison, help/harm matrix, and
  failure threshold for each route;
- `diagram_versions_read`, `visual_read_status`, and the SRR route objective
  recovered from Project background diagrams;
- permitted write scope for each route;
- forbidden actions for each route;
- exact controller task graph, concrete controller objectives, required files,
  validators, known-bad fixtures, finalizer behavior, and reviewer pass
  requirement for each route;
- minimum effective training or evidence classification for each route;
- Slurm preflight, partition/race policy, Python/torch/CUDA environment proof,
  and `afterok`/`afterany` dependency policy for any planned Slurm work;
- a route-specific critic handoff or critic-ready request for Route A, Route B,
  and Route C before controller work;
- a statement that Round02 does not authorize validation upload, route
  promotion, M11, cross-route merge, hosted metric claims, or final scientific
  decisions.

The plan must not contain only read-only audit, status reporting, or "wait for
planner/critic" work. Every route needs a controller-forward path in Round02.
The plan must also not be runnable-only, engineering-only, proxy-only,
validator-only, or nnU-Net-only. A route task that only repairs files must name
the reviewer acceptance it unlocks and the next bounded metric-facing step.

Planner must request route-specific critic handoffs named:

```text
prompts/routes/handoffs/route_A_round02_critic_handoff_20260717.md
prompts/routes/handoffs/route_B_round02_critic_handoff_20260717.md
prompts/routes/handoffs/route_C_round02_critic_handoff_20260717.md
```

Until `CURRENT.md` points to one of those files, route-specific critic threads
must stop and report that no current critic prompt exists.

## Required Critic Rejection Checks

When `CURRENT.md` later points a route critic to a current handoff, that critic
must reject a planner output that:

- is status-only, read-only-only, wait-only, runnable-only, engineering-only,
  proxy-only, validator-only, or lacks leaderboard upside;
- substitutes `foreground_mean`, empty-GT improvement, compact-label proxy, or
  local proxy-only metrics for the three CARE Myocardium leaderboard metrics;
- allows nnU-Net-only, postprocess-only, wrapper-only, placeholder, mock,
  dataclass, config-only, or contract-JSON-only completion;
- lacks same-split baseline, hard subgroup matrix, no-T2 safety, or real Cine
  evidence / honest blocker classification;
- lets pending, monitor, submitted-only, undertrained, or stale-token states
  stop a controller while Slurm, monitoring, aggregation, receipt repair, or
  reviewer handoff obligations remain;
- leaves validators checking only file existence or omits known-bad fixtures for
  semantic bypasses;
- fails to generate a route-specific controller-forward task graph and
  reviewer pass requirement;
- weakens Route C by omitting old M10/follow-up2 source reading or dropping any
  inherited Route C hard requirement without explicit user approval.
