# CARE Route Portfolio Current Round

This is the stable entrypoint for GPT planner and route-specific critic threads.
Read this file first when working on the active CARE route portfolio round.

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

The single portfolio GPT planner should read:

```text
prompts/routes/handoffs/portfolio_round02_planner_handoff_20260717.md
```

Planner scope:

- reason across Route A, Route B, and Route C together;
- decide the next portfolio move;
- decide whether any route-specific critic handoff should run;
- produce controller-forward work for every route in Round02; a status-only or
  read-only-audit-only round is not acceptable;
- produce a leaderboard-facing, critic-reviewable, controller-forward plan; do
  not stop at engineering cleanup, runnable-only work, validator-only work, or a
  low-target design that lacks plausible metric upside;
- specify all design and execution details needed by controllers; do not leave
  model structure, training budget, paths, Slurm strategy, validator semantics,
  known-bad fixtures, stop conditions, or reviewer pass/fail for Codex/controller
  to decide during execution;
- preserve the Round02 hard-requirement inheritance matrix from the planner
  handoff: Route C keeps all old M10 / follow-up / follow-up2 hard
  requirements, Route A keeps the compressed leaderboard-facing SRR subset, and
  Route B keeps the complete SRR-v3 implementation/training subset;
- also preserve the permanent hard-requirements matrix in
  `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`; future rounds must not
  treat the Round02 hardening as one-off;
- explicitly apply the matrix sections inherited from M9/M10: mechanism-closure
  evidence naming, machine-readable contract binding, runtime fingerprint
  inheritance, faithful Cine/registration boundaries, durable finalizer, and
  independent reviewer boundaries;
- never execute code, submit Slurm, upload validation packages, start M11, or
  make final scientific decisions without required review/critic evidence.

## Critic Entries

Each critic thread must read only its own route's current critic handoff.

```text
route_A critic current prompt:
NO_CURRENT_CRITIC_HANDOFF

route_B critic current prompt:
NO_CURRENT_CRITIC_HANDOFF

route_C critic current prompt:
NO_CURRENT_CRITIC_HANDOFF
```

If a route critic sees `NO_CURRENT_CRITIC_HANDOFF`, it must stop and report that
the planner has not issued a current critic prompt for that route.

Round02 planner must prepare a new route-specific critic handoff or explicit
critic-ready request for Route A, Route B, and Route C. Until `CURRENT.md` points
to one of those handoffs, each route critic remains stopped.

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

- controller packet commit: `0200e86f7a95ff9753f9c425419052e878d342f4`
- reviewer commit: `cde0e0b658893b327aa5fb3129d37a99f1cf7c47`
- reviewer decision: `ROUTE_B_REVIEW_NEEDS_REVISION`
- planner-facing state: bounded train/eval evidence is credible and adequacy
  passed, but validator/known-bad coverage and stale token reporting require
  revision before reviewer acceptance.

Route C:

- controller packet commit: `789ee4d`
- reviewer commit: `7b6c2d36bceefc5eb0f64f4977fd43f4194cc7b4`
- reviewer decision: `ROUTE_C_REVIEW_NEEDS_REVISION_CONFIRMED`
- planner-facing state: non-ready controller packet is supported; MyoPS
  residual-gate disconnection and Cine evidence inputs must be repaired before
  formal runtime or route comparison.
