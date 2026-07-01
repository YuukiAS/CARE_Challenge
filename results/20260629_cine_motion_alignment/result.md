# Result 20260629 Cine Motion Alignment

## Summary

- safe cases evaluated: `59`
- mismatch cases held out: `5`
- selected status: `SELECT_MOTION_DESCRIPTOR_ONLY`
- candidates tested: `simpleitk_translation` and `motion_descriptor`.
- SimpleITK warp types: `slice2d_translation=32, translation=84`.

## Evidence

- `registration_metrics.csv`: per-case/per-frame anatomy consistency against frame0 CineMA anatomy proxy.
- `warp_sanity.csv`: runtime, image similarity, transform displacement, and status for each candidate.
- `summary_metrics.csv` and `metrics_summary.md`: aggregate method/class summaries.
- `selection.md`: decision-gate status.
- `resource_audit.md`: dependencies, external resources, and candidate coverage.
- `failure_interpretation.md`: why the selected output remains descriptor-only.

## Caveats

- This preflight validates anatomy-prior propagation and motion descriptors, not scar/pathology performance.
- Learning-based registration is recorded as deferred rather than selected because no local licensed/pretrained candidate was used in this pass.
