# CARE Route A Round 01 - Critic Handoff

You are the Route A critic thread. You are not the portfolio planner and you are
not a Codex controller/reviewer.

This critic handoff belongs to:

```text
portfolio_round: round01
route: route_A
portfolio_planner_thread: single GPT planner for Route A/B/C
critic_thread: Route A only
```

Do not reason about Route B or Route C except to note that portfolio-level
prioritization belongs to the GPT planner.

## Required Context

Read first:

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`
- `prompts/routes/README.md`
- `prompts/routes/handoffs/CURRENT.md`
- `prompts/routes/handoffs/portfolio_round01_planner_handoff_20260716.md`
- `prompts/routes/route_A.md`
- `prompts/routes/route_A_executor_plan.yaml`

Then inspect the Route A evidence on branch/worktree `route_A`:

```text
/users/a/e/aereinh/CARE_worktrees/route_A
```

Relevant commits:

```text
controller_packet_commit: b8f05521500971953a2fc9f286de8520f1ea5b4f
review_commit: 05a6102073c8bb200fd4c84d6d0dff64e5a75f78
review_file: results/route_A/review.md
review_decision: ROUTE_A_REVIEW_NEEDS_REVISION
```

## Question For Route A Critic

Decide whether the Route A reviewer findings require an immediate narrow
controller revision before the portfolio planner can compare Route A against
Route B/C.

The reviewer found credible terminal negative evidence:

- Slurm job `59164420` completed with `COMPLETED`, `ExitCode=0:0`, elapsed
  `00:33:36`.
- Formal adequacy passed with `169694` optimizer steps,
  `1800.0097081299173` train-loop seconds, and `44` MyoPS eval cases.
- Negative/no-candidate interpretation is supported by metrics and case matrix:
  `myops_scar = 0.022727272727272728`, local Cine proxy
  `0.02004644182029281`, all 44 MyoPS rows have `route_changed_voxels == 0`,
  and the only T2-present edema-positive case has edema Dice `0.0`.

The reviewer also found blocking revision issues:

1. Validator and known-bad coverage are narrower than the Route A contract.
   Existing known-bad tests cover only forbidden authority token,
   ready-monitor packet, and formal metrics before gate. The required
   `tests/route_A/fixtures/known_bad/` directory is absent.
2. Final receipts are stale or contradictory:
   - `results/route_A/controller_context.json` still reflects earlier
     gate-failed/smoke-phase state.
   - `results/route_A/mapper_report_final.md` says real-case MyoPS/Cine evidence
     is missing.
   - `results/route_A/architecture_delta_final.md` says candidate readiness is
     blocked by missing real-case evidence.

## Allowed Critic Decisions

Return exactly one of these decision tokens:

```text
ROUTE_A_CRITIC_REQUIRES_REVISION_BEFORE_PORTFOLIO_COMPARISON
ROUTE_A_CRITIC_ALLOWS_PORTFOLIO_COMPARISON_WITH_REVIEW_CAVEAT
ROUTE_A_CRITIC_NEEDS_MORE_EVIDENCE
```

## Decision Boundaries

The critic may recommend a narrow Route A revision, but must not authorize:

- new training;
- new Slurm submission;
- validation packaging or upload;
- route promotion;
- final route-negative/stop conclusion;
- M11;
- Route B/C writes;
- cross-route merge.

If revision is required, scope it narrowly to:

- validator/known-bad coverage alignment with the Route A contract;
- stale controller/mapper/final receipt reconciliation;
- a new Route A reviewer pass after the revision.

## Required Critic Output

Write a concise decision for the portfolio planner with:

- the selected token;
- whether Route A can be compared now or must be revised first;
- exact evidence references;
- exact blocked actions;
- whether the next actor should be `route_A controller`, `route_A reviewer`, or
  `portfolio planner`;
- no route promotion, upload, M11, or final scientific conclusion.
