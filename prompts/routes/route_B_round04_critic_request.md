---
route_id: route_B
portfolio_round: round04
date: 2026-07-19
role: planning_critic_request
planner_base_main: 30098813522cecd98e60bcb99e2676b28c1a5461
route_B_evidence_ref: b9c7664da7cb1f1892fff37a4497722f31a0a96d
revision_source_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
status: PENDING_COORDINATOR_RECEIPT_AND_CRITIC_REREVIEW
critic_handoff_path: prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
coordinator_receipt_path: prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
critic_output_path: prompts/routes/route_B_round04_critic_rereview.md
allowed_decision_tokens:
  - ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
  - ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
controller_start_authorized: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
---

# Route B Round04 Independent Planning Critic Rereview Request

This is a separate planning critic task. It is not a controller task, runtime reviewer task, implementation task or Slurm task.

## Entry and binding

Read `prompts/routes/handoffs/CURRENT.md` first, then read only the current Route B Round04 critic handoff named there. Stop with `ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION` when:

- the handoff does not bind an exact planning commit and all six planning blobs;
- current `origin/main` is not a descendant of the planning commit through only declared handoff/receipt commits;
- any of the six planning blobs differs;
- `origin/route_B` does not equal `b9c7664da7cb1f1892fff37a4497722f31a0a96d` or no longer contains the reviewed Round03 packet;
- `prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md` is absent, pending, stale, has a nonzero exit, or tested a commit other than current `origin/main`;
- a later commit changed the route contract, executor plan, critic request, planner audit, planner prompt or portfolio plan.

The critic must independently visually read SRR-v2/v2.5/v3 from Project/current-conversation materials and recover the full Route B objective.

## Route C portfolio context

Confirm only as portfolio context:

```text
origin/route_C: 17062b00edc3443aacefe8583568797a9f2655ba
reviewed controller repair: 1e663cfa64f00413f005bef26310290fd43ec8ab
review token: ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
portfolio status: EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION
```

Route C must not be sent to another reviewer unless its binding is stale. Route C evidence completeness neither authorizes downstream actions nor removes the Route B Cine lane.

## Required Route B checks

### Scientific scope

Reject any reduction of:

- full four-scale `[32,64,128,256]` SRR-v3;
- canonical `[LGE,T2,C0]` and explicit availability;
- shared/private/interaction experts and spatial/pathology-conditioned routing;
- optimized Pattern-SIP;
- fold-safe train/OOF frozen prototype banks;
- training-only safe hard-negative queues and no-T2 edema exclusion;
- separate scar/edema proposal, soft ROI and refiner;
- bounded final correction and real final-output intervention;
- same-split nnU-Net baseline, case-wise help/harm, scar-positive, T2-present edema-positive, no-T2, CenterB/CenterC, remote-FP, component count, HD95 and volume ratio;
- official CineMA pretrained/matched-random control;
- seven-step SVF, true Jacobian/inverse consistency, real SyN, case denominators;
- registered temporal aggregation and full controls;
- declared training budgets and selected-checkpoint clean reload.

Confirm that Round03 B3 remains B3-only adequate negative, B4/B5/B6 continue after valid predecessors, B6 is the first MyoPS full-route classification, and B7/B8/B9 remain mandatory after B2.

### Terminal finalizer

Parse `terminal_finalizer_contract` and the B10 executor. B10 must:

- have `depends_on: []`;
- be controller-launched and exempt from the successful wave-preparation helper;
- consume `controller_terminal_registry.json` and all started attempt IDs in `controller_ledger.csv`;
- use `afterany` over every started attempt;
- use a local deterministic path when none started;
- launch immediately for B0/B1/B2 global terminals;
- launch after both lane terminals post-B2;
- account B1 failure, B2 external blocker, B7 blocker, B8 registration blocker without B9, timeout, preemption, failed startup, cancelled/started race loser and successful B6/B9;
- prevent duplicate launch with an atomic lock.

Reject any plan where an authorized early terminal class cannot reach B10.

### Per-executor validators

For B0-B10, require machine-readable:

```text
validator.script_path
validator.command
validator.input_path
validator.report_file
validator.expected_exit_code == 0
validator.success_token
known_bad_contract.matrix_path
known_bad_contract.matrix_command
known_bad_contract.report_file
known_bad_contract.runner_expected_exit_code == 0
known_bad_contract.validator_expected_exit_code_per_fixture == 1
known_bad_contract.expected_failure_keys
known_bad_contract.all_keys_required == true
known_bad_contract.unexpected_pass_is_failure == true
```

The exact commands must use `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`. A generic executor-plan validator cannot substitute for stage semantic validators.

### Slurm and continuity

Confirm `htzhulab` default, isolated long-wait `htzhulab+a100-gpu` race, V100 unchanged-config/`<=14.5 GiB` credit gate, zero-credit failed/partial/losing attempts, `afterok` training, `afterany` finalizer, and controller goal/goal-resume responsibility through accounting, aggregation, mapper final, packet commit and reviewer handoff. Monitor-like states are not completion.

### Coordinator receipt

Independently inspect the exact commands and exit codes in the coordinator receipt. A remote statement that checks “should pass” is insufficient. All required exits must be `0`, the tested commit must equal current `origin/main`, and the working tree must be clean.

## Allowed decisions

`ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER` may be written only when every requirement passes and is bound to the exact current main commit, exact planning commit, six blobs and coordinator receipt blob.

Otherwise write `ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION` with exact paths, fields and failed commands.

Neither token authorizes validation upload, route promotion, M11, hosted metrics, cross-route merge or a final scientific decision. The ready token authorizes only a future exact Route B Controller as a Codex goal/goal resume.
