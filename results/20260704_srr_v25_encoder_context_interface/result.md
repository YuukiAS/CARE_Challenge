# Result 20260704 SRR-v2.5 Encoder Context Interface

status: `EXECUTED_UNAUDITED`
self_assessed_status: `BOUNDED_BASE4_OVERFIT_VERIFIED_NEEDS_FORMAL_ABLATION`
domain_evidence_label: `PARTIAL_MECHANISM_INCOMPLETE`

## Summary

Implemented a formal, selectable strong encoder path for SRR PropRef. The model supports `encoder_profile=strong_4scale`, producing four modality-private scales `[base, 2base, 4base, 8base]`. The formal runner exposes `--encoder-profile` and defaults to `strong_4scale` with `--base-channels 32`, matching the intended `[32,64,128,256]` capacity family.

A bounded real-runner one-batch overfit comparison now exists at base4. It proves that both `tiny_3scale` and `strong_4scale` connect real train batches, nnU-Net anchor context, component context, runtime prototype banks, forward loss, and optimizer updates. It does not prove fold0 metric improvement or full `[32,64,128,256]` training viability.

## Files Changed

- `src/care_myocardium/models/srr_v2_unet.py`
- `src/care_myocardium/models/srr_propref.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `src/care_myocardium/tests/test_srr_encoder_context_interface.py`

## One-Batch Overfit Evidence

| profile | params | scales | case | anchor fold | steps | first loss | last loss | decrease | status |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `tiny_3scale` | 367312 | `[4, 8, 16]` | `Case1004` | 1 | 3 | 3.541034 | 3.342433 | 0.198601 | `PASS` |
| `strong_4scale` | 1456416 | `[4, 8, 16, 32]` | `Case1004` | 1 | 3 | 3.591522 | 3.447380 | 0.144142 | `PASS` |

The strong profile has 3.97x the base4 parameter count of the tiny profile and still decreases one-batch loss on the same real case.

## Evidence Artifacts

- `context_contract.md`
- `shape_alignment_sanity.md`
- `encoder_capacity_report.md`
- `one_batch_overfit_comparison.csv`
- `metadata_alignment_audit.md`
- `unit_test_report.md`
- `ablation_plan.md`

## Verification

- Targeted unit tests: exit `0`, `Ran 27 tests`, `OK` in the latest recorded run.
- Py compile: exit `0` in the latest recorded run.
- Parameter/shape smoke: `tiny_3scale` base4 has `367312` params and 3 scales; `strong_4scale` base4 has `1456416` params and 4 scales.
- Bounded overfit: both profiles return `PASS`; no prediction export because `skip_export: true`.
- Anti-laziness validator: exit `0`, still reports only legacy `CLAIM_WITHOUT_RUNTIME_EVIDENCE` findings in older reports.
- `git diff --check`: exit `0` in the latest recorded run.

## Missing For PASS

- Formal fold0 same-split metrics comparing tiny/strong and nnU-Net help/harm.
- Full-capacity `[32,64,128,256]` memory/runtime training evidence.
- Physical spacing/orientation metadata audit across the evaluated split, not only tensor-level batch/context alignment.
- Separate read-only audit.

## Gate Decision

decision: `BOUNDED_BASE4_OVERFIT_VERIFIED_NEEDS_FORMAL_ABLATION`

No validation package, external upload, git commit, git push, or prediction export was performed.
