---
route_id: route_B
portfolio_round: round03
executor_id: B10_FINALIZE_VALIDATE_REVIEW_REQUEST
lane: tooling
wave: 11
role: executor
status: TERMINAL_FINALIZER_AFTER_CRITIC_READY_FAST_REPAIR_REVIEW
---

# B10 — terminal accounting, packet validation, and reviewer request

This executor does not run new science. It finalizes every started B0-B9 attempt and every terminal early gate, including success, implementation/data/validator failure, startup failure, timeout, preemption, adequate-negative evidence, cancelled pending race losers, and bounded retry replacements. It is not a B9-success-only path.

Submit the exact `afterany` finalizer command in the executor plan with every required started job ID from the controller ledger. If no Slurm job was started because an early local gate failed, run the local deterministic finalizer path instead. The finalizer must automatically retry `sacct`, perform post-completion aggregation, run the bound mapper/architecture validation command, strict implementation/packet/partition-race validators, execute all known-bad fixtures, scan for heavy or forbidden tracked artifacts, run `git diff --check`, create one local lightweight packet commit, write `review_request.md`, and stop the Controller. Runtime code does not push and does not write `review.md`.

The final packet must bind code/config/split/manifest/asset/checkpoint/evaluator hashes; all stage adequacy; complete case/subgroup denominators; MyoPS and Cine selected reloads; all intervention reports; all routing attempts and atomic-lock outcomes; terminal accounting; mapper/fingerprint outputs; and authority fields.

The only merge-ready completion token is:

```text
ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW
```

It requires strict validators and known-bad tests to pass, all started attempts and all terminal early gates to be accounted for, and no stale or contradictory receipt. `NEEDS_MONITOR`, `AWAITING_SACCT`, undertraining, missing aggregation, stale metrics, unresolved control, missing all-attempt coverage, or validator failure cannot use it.

The independent read-only reviewer—not this executor—selects exactly one of:

```text
ROUTE_B_ROUND03_REVIEW_CANDIDATE_READY
ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE
ROUTE_B_ROUND03_REVIEW_EXTERNAL_RESOURCE_BLOCKER
ROUTE_B_ROUND03_REVIEW_UNDERTRAINED
ROUTE_B_ROUND03_REVIEW_NEEDS_MONITOR
ROUTE_B_ROUND03_REVIEW_NEEDS_EVIDENCE
ROUTE_B_ROUND03_REVIEW_NEEDS_REVISION
```

Candidate-ready requires all mechanism/safety/adequacy/validator gates, nonzero MyoPS effect, at least two positive targets, and a non-worse third. Adequate-negative requires faithful complete runtime but no candidate gate. External blocker requires exact failed resource command/path/SHA and an unblock recipe. Undertrained requires terminal accounting plus failed minimum-effective-training. Needs-monitor requires real nonterminal jobs and cannot be a completed packet. Needs-evidence covers missing denominators or causal evidence. Needs-revision covers implementation, stale, semantic, or validator failure.

Reviewer acceptance permits only future Portfolio reconciliation. Do not upload validation, promote, start M11, cross-route merge, claim hosted metrics, or make a final scientific decision.