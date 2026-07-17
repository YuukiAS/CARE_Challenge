# CARE Route Portfolio Current Round

This is the stable entrypoint for GPT planner and route-specific critic threads. Read this file first when working on the active CARE route portfolio round.

## Active Round

```text
round_id: round02
date: 2026-07-17
planner_thread_model: one GPT planner thread owns Route A, Route B, and Route C
critic_thread_model: one separate critic thread per route
milestone_model: retired for this route portfolio loop
route_round_model: portfolio round with route-specific critic handoffs
```

## Planner Entry

The Round02 planning prompt remains:

```text
prompts/routes/handoffs/portfolio_round02_planner_handoff_20260717.md
```

The committed Planner output is:

```text
prompts/routes/portfolio_round02_planner_plan_20260717.md
```

Bound route planner commits:

```text
route_A: 94240ffb5e91953b0ade81137ce5042568ddd28f
route_B: cae72e41b08cbf2a7e2b0d137b62eed13fab66c7
route_C: a68b7413775e00b96634219ee9453ba47e73d4e0
```

Round02 has produced controller-forward work for all three routes. It remains leaderboard-facing and preserves `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`, the M9/M10 inherited gates, strict validators/known-bad fixtures, durable finalizers, runtime no-push, and independent reviewer boundaries.

No controller is authorized merely by this Planner publication. Each route requires its current Critic ready token first.

## Critic Entries

Each critic thread reads only its route's current handoff:

```text
route_A critic current prompt:
prompts/routes/handoffs/route_A_round02_critic_handoff_20260717.md

route_B critic current prompt:
prompts/routes/handoffs/route_B_round02_critic_handoff_20260717.md

route_C critic current prompt:
prompts/routes/handoffs/route_C_round02_critic_handoff_20260717.md
```

The Critic must bind the exact route planner commit and contract/executor-plan blob SHAs listed in its handoff. A changed route head or file hash makes that handoff stale and requires a new Planner handoff.

Allowed planning-ready tokens are:

```text
ROUTE_A_ROUND02_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_ROUND02_PLANNING_READY_FOR_CONTROLLER
ROUTE_C_ROUND02_PLANNING_READY_FOR_CONTROLLER
```

These tokens authorize only the corresponding route controller to start. They do not authorize validation packaging/upload, route promotion, M11, cross-route merge, hosted metric claims, or a final scientific decision.

## Round Semantics

`roundNN` replaces the old milestone-as-round convention for the route portfolio. It is not a scientific milestone number and does not imply route promotion.

A new round starts when at least one of these happens:

- a route controller commits a new packet;
- a route reviewer commits a new review;
- the portfolio planner makes a new route-level decision;
- a planner decision requires one or more route-specific critic passes;
- Route A/B/C need to be compared after fresh evidence.

All files derived from the same planner decision should share the same `roundNN`.

## Naming

Portfolio planner handoff:

```text
portfolio_roundNN_planner_handoff_YYYYMMDD.md
```

Route critic handoffs:

```text
route_A_roundNN_critic_handoff_YYYYMMDD.md
route_B_roundNN_critic_handoff_YYYYMMDD.md
route_C_roundNN_critic_handoff_YYYYMMDD.md
```

## Current Route States Before Round02 Controller Work

Route A:

- prior controller packet commit: `b8f05521500971953a2fc9f286de8520f1ea5b4f`
- prior reviewer commit: `05a6102073c8bb200fd4c84d6d0dff64e5a75f78`
- prior reviewer decision: `ROUTE_A_REVIEW_NEEDS_REVISION`
- Round02 planner commit: `94240ffb5e91953b0ade81137ce5042568ddd28f`
- next actor: Route A Critic; controller remains blocked until the current ready token.

Route B:

- prior controller packet commit: `0200e86f7a95ff9753f9c425419052e878d342f4`
- prior reviewer commit: `cde0e0b658893b327aa5fb3129d37a99f1cf7c47`
- prior reviewer decision: `ROUTE_B_REVIEW_NEEDS_REVISION`
- Round02 planner commit: `cae72e41b08cbf2a7e2b0d137b62eed13fab66c7`
- next actor: Route B Critic; controller remains blocked until the current ready token.

Route C:

- prior controller packet commit: `789ee4d`
- prior reviewer commit: `7b6c2d36bceefc5eb0f64f4977fd43f4194cc7b4`
- prior reviewer decision: `ROUTE_C_REVIEW_NEEDS_REVISION_CONFIRMED`
- Round02 planner commit: `a68b7413775e00b96634219ee9453ba47e73d4e0`
- next actor: Route C Critic; controller remains blocked until the current ready token.

## Authority Boundary

Round02 planning does not execute code, submit Slurm, package or upload validation data, promote a route, start M11, merge routes, claim hosted metrics, or make a final scientific decision.
