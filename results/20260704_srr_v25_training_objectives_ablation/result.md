# Result 20260704 SRR-v2.5 Training Objectives Ablation

status: `EXECUTED_UNAUDITED`
self_assessed_status: `ACTIVE_OBJECTIVE_SWITCHES_VERIFIED_NEEDS_FORMAL_METRIC_ABLATION`
domain_evidence_label: `PARTIAL_MECHANISM_INCOMPLETE`

## Summary

Connected additional SRR-v2.5 objectives to the formal PropRef runner and verified bounded ablation switches. Semantic retrieval weights are now configurable, component-level proposal ranking is configurable, and a baseline-preserving harm objective now penalizes unnecessary deviation from high-confidence correct nnU-Net anchor voxels.

This still does not pass the task. The evidence is objective-path and switch sanity, not formal hard-subgroup metric impact.

## What Changed

- `propref_loss` now uses `--semantic-retrieval-weight`, `--semantic-coverage-weight`, and `--semantic-integrative-weight` instead of fixed constants.
- Added `_baseline_preservation_loss` with `--baseline-preservation-weight`, `--baseline-preservation-confidence`, and `--baseline-gate-harm-weight`.
- Training logs now include `baseline_preservation_loss`, `baseline_preserve_voxels`, and `baseline_preserve_gate_mean`.
- Existing component proposal ranking is controlled by `--component-proposal-weight` and included in ablation smoke.

## Evidence

- `objective_mapping.md`
- `code_paths.md`
- `loss_switches.md`
- `sanity_report.md`
- `ablation.csv`
- `metric_impact.md`

## Gate Decision

decision: `ACTIVE_OBJECTIVE_SWITCHES_VERIFIED_NEEDS_FORMAL_METRIC_ABLATION`

No validation package, external upload, git commit, git push, or prediction export was performed.
