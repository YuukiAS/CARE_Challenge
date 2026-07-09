# M9 Follow-up Validator Repair Summary

status: `PASS_FAIL_CLOSED_REPAIR`

HISTORICAL_NONREADY_STATE_RESOLVED

The prior reviewer found a validator bug: the ready-state check could pass a packet whose Markdown looked ready while required CSV or JSON evidence still carried stale runtime-state values. The validator now scans required Markdown, CSV, and JSON evidence files, excluding validator self-test reports, before accepting a ready or follow-up-ready packet.

The validator now also accepts the existing previous `review.md` as prerequisite input only when it contains `M9_AUDITED_NEEDS_REVISION`; this avoids treating the prior read-only review as executor self-review while still failing unexpected review content.

The self-test set now contains one good fixture and 37 known-bad fixtures. The new follow-up fixtures cover stale dictionary-fidelity CSV state, stale code-patch summary state, stale BR2 contract state, stale nnU-Net control evidence state, stale pathology-refiner state, stale prototype-memory JSON state, generic stale CSV state, and generic stale JSON state.

Real-packet validation after reconciliation exits with `error_count=0`. This validates packet consistency only. It does not authorize route promotion, validation packaging, validation upload, hosted metric claims, fold expansion, or M10.

