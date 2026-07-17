# CARE Route Handoffs

This directory stores post-execution handoff prompts for the route portfolio loop.
It is separate from the initial route contracts in `prompts/routes/route_A.md`,
`prompts/routes/route_B.md`, and `prompts/routes/route_C.md`.

## Thread Model

- One GPT planner thread owns the portfolio-level state for all three routes.
- Three separate critic threads own route-specific review of planner decisions:
  one for Route A, one for Route B, and one for Route C.
- Codex controllers and reviewers do not make final route-level scientific
  decisions. They produce committed evidence packets and reviews for GPT.

## Current Round Entry

Always start from:

```text
prompts/routes/handoffs/CURRENT.md
```

`CURRENT.md` records the active `roundNN`, the single portfolio planner prompt,
and the current route-specific critic prompt for each route. If a route critic
entry is `NO_CURRENT_CRITIC_HANDOFF`, that critic thread must stop and report
that no current prompt has been issued for its route.

The current round handoff is not only a status index. It is also the active
requirements entry for the route portfolio round. Planner and critic threads
must read `CURRENT.md`, then the current round handoff, then the route-branch
contracts, packets, and reviews named by that handoff.

Every round handoff must state how old milestone or route-specific hard
requirements carry forward into Route A, Route B, and Route C. Do not silently
drop M10 / follow-up / follow-up2 gates when translating the old single-route
workflow into the three-route portfolio.

## Round Semantics

`roundNN` replaces the older milestone-as-round convention for this route
portfolio loop. A route portfolio round is a reporting/decision cycle across
Route A, Route B, and Route C; it is not a scientific milestone number and does
not authorize promotion by itself.

A new round starts when at least one route has a new controller packet, reviewer
result, planner decision, or route-specific critic pass requirement.

## Naming

Portfolio planner handoffs:

```text
portfolio_roundNN_planner_handoff_YYYYMMDD.md
```

Route-specific critic handoffs:

```text
route_A_roundNN_critic_handoff_YYYYMMDD.md
route_B_roundNN_critic_handoff_YYYYMMDD.md
route_C_roundNN_critic_handoff_YYYYMMDD.md
```

Use the same `roundNN` for the planner handoff and any critic handoffs derived
from that planner decision. Increment the round when at least one route has a new
controller packet, reviewer result, or planner decision requiring a new critic
pass.

## Scope

These files are prompts for GPT/critic threads. They should point to committed
source-of-truth evidence and ask for decisions. They should not contain runtime
logs, NIfTI outputs, checkpoints, upload packages, credentials, or large copied
artifacts.
