# CARE Route Portfolio Round 01 - GPT Planner Handoff

You are the single GPT planner thread responsible for the full CARE route
portfolio: Route A, Route B, and Route C.

This is a portfolio-level planning handoff, not a Codex execution prompt. Do not
run code, submit Slurm jobs, upload validation packages, claim hosted metrics,
promote a route, start M11, or make a final scientific stop decision without the
required reviewer/critic evidence.

## Thread Model

- GPT planner: one thread owns all three routes and portfolio-level decisions.
- Critics: three separate route-specific threads, one each for Route A, Route B,
  and Route C.
- Codex route sessions: one tmux session per route, plus one watchboard session.
  Controller/reviewer/monitor work is separated by tmux windows inside each route
  session.

Current tmux convention:

```text
care_watchboard
care_route_A
care_route_B
care_route_C
```

## Must Read First

Refresh remote branches before reasoning:

```text
main
route_A
route_B
route_C
```

Then read:

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`
- `prompts/routes/README.md`
- `prompts/routes/handoffs/README.md`
- `prompts/routes/route_portfolio_planner_prompt.md`
- `wiki/README.md`

For route-specific evidence, read from the corresponding branch/worktree, not
only from `main`.

## Current Portfolio State

### Route A

Route A has completed one controller-to-reviewer cycle.

Controller packet:

```text
branch: route_A
worktree: /users/a/e/aereinh/CARE_worktrees/route_A
controller_commit: b8f05521500971953a2fc9f286de8520f1ea5b4f
controller_commit_subject: Finalize Route A terminal packet
controller_token: ROUTE_A_NEGATIVE_PACKET_READY_FOR_REVIEW
```

Independent reviewer packet:

```text
review_commit: 05a6102073c8bb200fd4c84d6d0dff64e5a75f78
review_commit_subject: Review Route A terminal packet
review_file: results/route_A/review.md
review_decision: ROUTE_A_REVIEW_NEEDS_REVISION
```

Route A evidence that the reviewer considered credible:

- Slurm job `59164420` completed: `COMPLETED`, `ExitCode=0:0`, elapsed
  `00:33:36`, node `g141603`.
- Post-completion aggregation exists and records `adequacy: PASS`.
- Formal adequacy evidence records `169694` optimizer steps,
  `1800.0097081299173` train-loop seconds, and `44` MyoPS eval cases.
- Negative/no-candidate interpretation is supported:
  - `myops_scar = 0.022727272727272728`
  - local Cine class-1 proxy `myocardium_cinemyops = 0.02004644182029281`
  - all 44 MyoPS rows have `route_changed_voxels == 0`
  - only T2-present edema-positive case is `Case2001`, with route edema Dice
    `0.0`

Route A reviewer blocking findings:

1. Validator and known-bad regression coverage are narrower than the Route A
   contract. Existing known-bad tests cover only forbidden authority token,
   ready-monitor packet, and formal metrics before gate. The required
   `tests/route_A/fixtures/known_bad/` directory is absent.
2. Several final receipts are stale or contradictory relative to the terminal
   packet:
   - `results/route_A/controller_context.json` still records earlier
     gate-failed/smoke-phase state.
   - `results/route_A/mapper_report_final.md` says real-case MyoPS/Cine evidence
     is missing.
   - `results/route_A/architecture_delta_final.md` says candidate readiness is
     blocked by missing real-case evidence.
   - Those statements conflict with later implementation-gate and real-evidence
     summaries that record real MyoPS/Cine receipts.

Route A current planner-facing interpretation:

```text
terminal Slurm and negative metric evidence: credible
scientific signal: no candidate signal
review acceptance: not accepted; needs revision
route promotion: not authorized
validation upload: not authorized
M11: not authorized
final route-negative conclusion: not yet authorized
```

### Route B

No new controller/reviewer result is included in this Round 01 handoff. Treat
Route B state as requiring fresh live inspection from branch/worktree before any
decision.

### Route C

No new controller/reviewer result is included in this Round 01 handoff. Treat
Route C state as requiring fresh live inspection from branch/worktree before any
decision.

## Planner Decision Requested

Decide the next portfolio move. Choose one of the following, or write a more
specific decision with equivalent boundaries:

1. Route A revision first:
   - Ask Codex Route A controller to perform a narrow packet/validator revision.
   - Scope should be limited to reviewer findings: validator/known-bad coverage,
     stale controller/mapper/final receipts, and a new reviewer pass.
   - No new training, no Slurm submission, no validation upload, no Route B/C
     writes, no route promotion.

2. Defer Route A revision and continue Route B/C:
   - Record Route A as having credible terminal negative evidence but no accepted
     review packet yet.
   - Continue Route B and/or Route C controller work to obtain their comparable
     packets before spending time on Route A cleanup.

3. Ask Route A critic first:
   - Send a route-specific critic handoff for Route A to decide whether the
     reviewer findings require immediate controller revision or can be treated as
     non-blocking for portfolio comparison.
   - Use a file named like
     `prompts/routes/handoffs/route_A_round01_critic_handoff_20260716.md`.

4. Portfolio status-only:
   - Produce a planner status note without authorizing any new Codex work.
   - Use this if Route B/C state must be inspected before choosing the next
     execution target.

## Required Planner Output

Write a concise decision with:

- selected option;
- exact next actor: `route_A controller`, `route_A critic`, `route_B controller`,
  `route_C controller`, or `no execution`;
- permitted write scope;
- forbidden actions;
- whether a new route-specific critic handoff is required;
- whether a new reviewer pass is required;
- whether the decision changes Route A scientific status.

Use strict language:

- Do not call Route A accepted.
- Do not call Route A promoted.
- Do not call Route A finally negative/stopped unless critic/reviewer and planner
  rules explicitly support that final scientific decision.
- Do not authorize validation packaging/upload or M11.
