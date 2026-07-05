# M0 Review Request

status: `REQUEST_READ_ONLY_REVIEW`

Please start a separate read-only Codex reviewer/auditor session for:

```text
results/20260705_srr_v3_m0_architecture_master_contract/
```

The reviewer must inspect the M0 task, hard-gate policy files, required inputs, and all M0 outputs. The reviewer must not fix missing artifacts, must not train, must not package validation, must not upload, and must not start M1.

`review.md` is intentionally absent at executor stop. The reviewer should write only:

```text
results/20260705_srr_v3_m0_architecture_master_contract/review.md
```

Allowed review decisions:

- `M0_AUDITED_GO`
- `M0_AUDITED_NEEDS_REVISION`
- `M0_AUDITED_NEEDS_EVIDENCE`

M1 remains blocked until `review.md` exists and contains `M0_AUDITED_GO`.
