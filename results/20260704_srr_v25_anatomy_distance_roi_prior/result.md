# Result 20260704 SRR-v2.5 Anatomy Distance ROI Prior

status: `EXECUTED_UNAUDITED`
self_assessed_status: `NEEDS_FORMAL_ABLATION`
domain_evidence_label: `PARTIAL_MECHANISM_INCOMPLETE`

## Summary

Implemented a real anatomy distance/soft-ROI mechanism in the formal SRR PropRef model path. The model now derives `P_union`, `P_LV`, `P_RV`, soft distance/proximity maps, anatomy/anchor uncertainty, and task-specific scar/edema anatomy gates. These gates are consumed by both pathology proposal dictionaries and crop ROI refinement.

This does not complete the subtask. Formal fold0 ROI metrics, overlays, and union-only-vs-full ablation are still missing.

## Files Changed

- `src/care_myocardium/models/srr_propref.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `src/care_myocardium/tests/test_srr_anatomy_distance_roi_prior.py`

## Evidence

- `anatomy_output_contract.md`
- `roi_generator_contract.md`
- `distance_map_sanity.csv`
- `roi_ablation.csv`
- `overlay_manifest.md`
- `unit_test_report.md`

## Verification

- Targeted unit tests: exit `0`, `Ran 22 tests`, `OK`.
- Py compile: exit `0`.
- Forward smoke: exit `0`, output shape `[1, 6, 5, 16, 16]`.
- Anti-laziness validator: exit `0`, still reports only 10 legacy `CLAIM_WITHOUT_RUNTIME_EVIDENCE` findings in older reports.
- `git diff --check`: exit `0`.

## Missing For PASS

- Formal same-split ROI GT coverage, outside-myocardium ROI ratio, crop-volume ratio, remote FP, component count, HD95, and final Dice linkage.
- Union-only versus full `P_union/P_LV/P_RV + distance + uncertainty` ablation.
- Overlay export/review on hard scar and CenterC T2-present edema cases.
- Separate read-only audit.

## Gate Decision

decision: `NEEDS_FORMAL_ABLATION`

No validation package, external upload, git commit, git push, or new training run was performed.
