# CARE Route Portfolio Current Round

This is the stable entrypoint for GPT planner and route-specific critic threads.
Read this file first when working on the active CARE route portfolio round.

## Active Round

```text
round_id: round01
date: 2026-07-16
planner_thread_model: one GPT planner thread owns Route A, Route B, and Route C
critic_thread_model: one separate critic thread per route
milestone_model: retired for this route portfolio loop
route_round_model: portfolio round with route-specific critic handoffs
```

## Planner Entry

The single portfolio GPT planner should read:

```text
prompts/routes/handoffs/portfolio_round01_planner_handoff_20260716.md
```

Planner scope:

- reason across Route A, Route B, and Route C together;
- decide the next portfolio move;
- decide whether any route-specific critic handoff should run;
- never execute code, submit Slurm, upload validation packages, start M11, or
  make final scientific decisions without required review/critic evidence.

## Critic Entries

Each critic thread must read only its own route's current critic handoff.

```text
route_A critic current prompt:
prompts/routes/handoffs/route_A_round01_critic_handoff_20260716.md

route_B critic current prompt:
NO_CURRENT_CRITIC_HANDOFF

route_C critic current prompt:
NO_CURRENT_CRITIC_HANDOFF
```

If a route critic sees `NO_CURRENT_CRITIC_HANDOFF`, it must stop and report that
the planner has not issued a current critic prompt for that route.

## Round Semantics

`roundNN` replaces the old milestone-as-round convention for the route portfolio.
It is not a scientific milestone number and does not imply route promotion.

A new round starts when at least one of these happens:

- a route controller commits a new packet;
- a route reviewer commits a new review;
- the portfolio planner makes a new route-level decision;
- a planner decision requires one or more route-specific critic passes;
- Route A/B/C need to be compared after fresh evidence.

All files derived from the same planner decision should share the same
`roundNN`.

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

## Current Route States

Route A:

- controller packet commit: `b8f05521500971953a2fc9f286de8520f1ea5b4f`
- reviewer commit: `05a6102073c8bb200fd4c84d6d0dff64e5a75f78`
- reviewer decision: `ROUTE_A_REVIEW_NEEDS_REVISION`
- planner-facing state: credible terminal negative evidence, but packet not
  review-accepted because revision is required.

Route B:

- no Round 01 controller/reviewer packet included in this current handoff.

Route C:

- no Round 01 controller/reviewer packet included in this current handoff.
