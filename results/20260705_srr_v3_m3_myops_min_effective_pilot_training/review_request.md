# Review Request

Please audit this M3 executor packet as a separate read-only review. `review.md` is intentionally absent at executor stop.

Reviewer should verify minimum-effective training budget, one-batch overfit, loss decrease, prediction sanity including no-T2 edema safety, prototype T2-present coverage, gate/residual stats, same-split nnU-Net help/harm, hard subgroup metrics, and cache/provenance isolation.

M4 remains blocked until a separate read-only reviewer writes `M3_AUDITED_GO`.
