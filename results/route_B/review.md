# Route B Round03 Independent Review

decision: `ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE`

reviewed_head: `8dfa40f8c4cedb2507f35a482bd46244a7a1c94c`
reviewed_origin_route_B: `8dfa40f8c4cedb2507f35a482bd46244a7a1c94c`
review_date: `2026-07-19`

## Scope

This is a separate read-only reviewer pass over the Route B Round03 terminal packet. I did not start a controller, submit Slurm work, run training, package or upload validation, promote a route, start M11, merge across routes, claim hosted metrics, or make a final scientific decision.

`prompts/routes/handoffs/CURRENT.md` was requested as a prerequisite source, but that path is absent at the reviewed commit. I did not substitute a neighboring handoff file as source-of-truth. The review below is therefore bound to the exact fetched commit, the manifest-listed Route B terminal packet, `review_request.md`, the strict validator output, and the B10/B3 Slurm/accounting evidence.

## Evidence Checked

1. Repository state was current after `git fetch --all --prune`: `pwd` was `/users/a/e/aereinh/CARE_worktrees/route_B`, and both `HEAD` and `origin/route_B` resolved to `8dfa40f8c4cedb2507f35a482bd46244a7a1c94c`.
2. The requested strict validator passed:

   ```text
   /users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round03/validate_packet.py --strict --require-all-attempt-accounting results/route_B/round03/executors/B10
   status: PASS
   completion_token: ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW
   errors: []
   ```

3. The terminal packet is not a monitor packet. B10 `routing_ledger.csv` accounts for every listed B3 attempt, and B10 `finalizer_state.json` records `afterany_all_started_attempts` coverage for the same job IDs. The final credited rerun, job `59490811` on `htzhulab`, reached terminal `FAILED`, exit `2:0`, with runtime output `results/route_B/runtime/round03/B3/attempt_htzhulab_samplerfix_1`.
4. The B3 terminal scientific gate failure is supported by current evidence. `results/route_B/round03/executors/B3/completion.json` reports `43003` optimizer steps, `1800.7964860140346` train-loop seconds, and `22` validation events against requirements of `6000`, `1800.0`, and `3`. It passed finite-loss, loss-decrease, invalid-weight, no-T2 edema-zero, frozen sampler count, and frozen sampler sequence checks, but failed `anatomy_union_overfit`.
5. The sampler defect from the old review is closed in the reviewed terminal packet. The final B3 sampler receipt uses draw cycle `E,E,S,R`, `numpy.random.Philox`, seed `26071821`, with replacement, `cycle_mismatch_count: 0`, and counts `E=21502`, `S=10751`, `R=10750`, matching expected counts.
6. Missing B4-B9 packets are justified by the executor plan and B10 packet only because B3 is a blocking terminal scientific gate. The current B10 packet records `terminal_negative_packet: true`, `blocked_at_stage: B3`, and `blocked_completion_token: ROUTE_B_ROUND03_B3_SCIENTIFIC_GATE_FAILED`.
7. Forbidden authority boundaries are intact in B10: route promotion, route-negative decision, final scientific decision, validation packaging/upload, hosted metric claim, M11, cross-route merge, push, and controller-authored review are all false or `NOT_REVIEWED` / `AWAITING_REVIEW`.
8. B10 heavy-artifact scan reports `PASS` with no tracked heavy artifacts. B10 validator evidence includes successful `git diff --check`, architecture wiki validation, and strict packet validation.
9. Legacy first-level Route B files still contain earlier `ROUTE_B_SCIENTIFIC_UNDERTRAINED` / `ROUTE_B_READY_FOR_REVIEW` text, but they are not listed in the current `MANIFEST.md` review target except where explicitly superseded by `result.md`, `completion_check.md`, `controller_report.md`, `review_request.md`, and `round03/executors/B10/*`. I did not use those legacy files as current terminal evidence.

## Decision

`ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE` is the supported reviewer token.

This means the terminal packet is reviewable and non-candidate: Route B Round03 produced faithful B3 runtime evidence, satisfied the B3 minimum runtime/sampler/accounting gates, and then failed the B3 scientific gate because `anatomy_union_overfit` remained false. It does not authorize validation upload, route promotion, M11, cross-route merge, hosted metric claims, or a final scientific conclusion. It only provides reviewed evidence for later portfolio reconciliation.
