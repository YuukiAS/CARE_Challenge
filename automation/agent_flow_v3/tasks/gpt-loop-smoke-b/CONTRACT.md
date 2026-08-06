# CARE Agent-Flow v3 Smoke B Toy Contract

This task is a minimal GPT-to-Codex-to-GPT orchestration smoke. It is not
CARE-ASE implementation and must not touch model, training, inference, outer
evaluation, Docker, validation upload, organizer email, or `develop` to `main`
promotion.

## Objective

Prove that Agent-Flow v3 can move from a frozen toy contract to isolated Codex
Verifier and Executor sessions, integrate their commits, wait asynchronously for
Scheduled Planner review through GitHub, and route a later
`PLANNER_REVISE_*` decision through exact-session resume.

## Toy Behavior

The toy implementation exposes one deterministic function:

```text
automation.agent_flow_v3.smoke_b.toy_gate.evaluate_payload(payload, expected_nonce)
```

It must return an object with:

- `accepted: true` only when `payload` is a mapping, `payload["nonce"]` exactly
  equals `expected_nonce`, `payload["mode"] == "safe"`, and
  `payload["value"]` is an integer greater than or equal to 1.
- `accepted: false` otherwise.
- `reason` explaining the first fail-closed rejection.

## Required Separation

The Verifier must write public fail-closed tests before Executor implementation.
The Executor must not edit the verifier test file. The first Executor
implementation intentionally leaves one safe, repairable contract gap for
Scheduled Planner to catch after deterministic CI passes.

The intended repairable gap is documentation/provenance level, not a runtime
safety hole: the implementation may pass public tests while omitting the
`planner_review_gap_marker` field in the implementation receipt. Scheduled
Planner should return `PLANNER_REVISE_EXECUTOR` for that missing marker.

## Forbidden Scope

No training, no outer access, no CARE-ASE source implementation, no Docker, no
upload, no organizer email, no `main` merge, no hand-written Planner decision,
and no fabricated review artifact.
