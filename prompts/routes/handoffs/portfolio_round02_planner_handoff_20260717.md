# CARE Route Portfolio Round 02 - GPT Planner Handoff

You are the single GPT planner thread responsible for Route A, Route B, and
Route C. This is a planning handoff, not a Codex execution prompt.

Round02 must produce controller-forward work for all three routes. A
status-only response, read-only audit round, or "wait for another review" round
is not acceptable. If a route cannot train immediately, the planner must specify
the concrete unblock, repair, validation, and then the bounded train/eval or
equivalent execution step that moves the route forward.

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
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/handoffs/CURRENT.md
prompts/routes/handoffs/portfolio_round02_planner_handoff_20260717.md
routes/README.md
wiki/README.md
```

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

If a file exists on a route branch but not on `main`, use the route branch copy
as source of truth for that route. If `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`
is missing on a route branch, read the `main` copy and treat the missing route
copy as a handoff defect to repair.

For SRR / MyoPS / Cine planning, visually read the ChatGPT Project background
SRR diagrams at v2 and later. Repository image paths are version references only.

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
- permitted write scope for each route;
- forbidden actions for each route;
- concrete controller objectives, required files, validators, and reviewer pass
  requirement for each route;
- whether any route-specific critic handoff is needed before controller work;
- a statement that Round02 does not authorize validation upload, route
  promotion, M11, cross-route merge, hosted metric claims, or final scientific
  decisions.

The plan must not contain only read-only audit, status reporting, or "wait for
planner/critic" work. Every route needs a controller-forward path in Round02.

If the planner decides a route-specific critic is needed, it must request a
handoff file named:

```text
prompts/routes/handoffs/route_A_round02_critic_handoff_20260717.md
prompts/routes/handoffs/route_B_round02_critic_handoff_20260717.md
prompts/routes/handoffs/route_C_round02_critic_handoff_20260717.md
```

Until `CURRENT.md` points to one of those files, route-specific critic threads
must stop and report that no current critic prompt exists.
