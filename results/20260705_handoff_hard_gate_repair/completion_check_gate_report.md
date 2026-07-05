# Completion Check Gate Report

## Gate

When a controller task orders a `*_completion_check` before a `*_final_readonly_audit` or equivalent final review, final review requires:

```text
results/<completion_check_task>/decision.md
```

The decision file must include `READY_FOR_FINAL_AUDIT` or `FINAL_AUDIT_READY`.

## Regression Finding

For `20260704_srr_v25_full_completion_goal`, the ordered task graph contains:

- `20260704_srr_v25_completion_check`
- `20260704_srr_v25_final_readonly_audit`

Strict/default validation reports:

```text
COMPLETION_CHECK_READINESS_MISSING
```

Evidence:

```text
results/20260704_srr_v25_completion_check/decision.md
```

## Decision

completion_check_gate: `FAILS_KNOWN_BAD_PACKET_AS_REQUIRED`

The final read-only audit cannot satisfy the repaired gate without completion-check readiness.
