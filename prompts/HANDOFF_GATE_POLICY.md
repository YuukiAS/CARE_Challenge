# CARE Handoff Gate Policy

This policy defines how future CARE controller goals should be accepted or blocked. It is intentionally mechanical: a requirement is a gate only when it can be checked from exact paths, parsed fields, command exits, metrics, provenance, or an audit decision.

## Gate Principles

A controller task must expose its full ordered task graph. Every required subtask must have an exact `results/<task_key>/` directory and the exact required output filenames declared by its task file. A missing required result directory is a blocking error.

A controller report must not replace a missing required subtask with a similar name, a diagnostic summary, or a later final review. If a subtask is optional, that optional status must be explicit in the controller task before execution.

A final review must be preceded by a completion check when the controller task lists one. The completion check must write a decision file declaring readiness. Without that readiness file, the final review is blocked.

Validation scripts used for completion decisions must fail closed. If errors are reported, the command must return failure unless it is explicitly invoked as a non-completion diagnostic scan. Historical tolerated findings require a named allowlist with reason, expiry, and owner.

Trainable model evidence must be classified by adequacy. Small probes and smoke runs can support debugging, but not route promotion or scientific stop. Adequacy requires training budget, validation events, loss behavior, prediction sanity, provenance paths, cache isolation, and same-split baseline comparison.

Operational completion and scientific route status are separate. A controller may finish its assigned workflow while the model route remains undertrained, unresolved, or in need of evidence.

## Required Controller Report Ending

Every high-risk controller report should end with these fields:

```text
controller_run_status:
operational_completion_status:
experiment_adequacy_decision:
route_promotion_decision:
route_negative_decision:
scientific_resolution_status:
diagnostic_publication_decision:
git_commit_decision:
git_push_decision:
published_files:
blocked_actions:
next_required_action:
reason_if_not_published:
reason_if_no_route_promotion:
```

## Regression Case

The current regression case is `20260704_srr_v25_full_completion_goal`. Its task graph listed 17 required subtasks, including `20260704_cine_temporal_dictionary_integration` and `20260704_srr_v25_completion_check`, but those result directories were absent while final review still ran.

Any repaired gate must fail this case until the missing evidence is supplied or the controller task is explicitly revised.

## Required Behavior For Future Goals

Before any future SRR, Cine, missing-modality, registration, proposal/refinement, external-adapter, fold-expansion, validation-packaging, or submission-related controller goal starts, the executor must first enforce:

1. exact task graph extraction;
2. exact result-directory checks;
3. exact required-output filename checks;
4. completion-check-before-final-review;
5. strict validator behavior;
6. minimum effective training classification;
7. controller report schema validation;
8. known-bad-packet regression.

If any of these gates fail, the controller must stop with `NEEDS_EVIDENCE` or `NEEDS_REVISION`. It must not continue to final review, route promotion, fold expansion, validation packaging, validation upload, or scientific stop.
