# Result 20260625 Cine Geometry

status: `GO_CINE_TEMPORAL_PREFLIGHT`

## Summary

- Audited 64 CineMyoPS train cases.
- Wrote 59 strict safe cases to `safe_cases.csv`.
- Wrote 5 metadata mismatch cases to `mismatch_cases.csv`: `['center_alpha_Case1009', 'center_alpha_Case1018', 'center_alpha_Case1020', 'center_alpha_Case1024', 'center_beta_Case2023']`.
- Crop/inverse protocol check is recorded in `crop_roundtrip.csv`.
- Re-evaluated existing CineMA frame0 predictions on the 59-case safe subset in `case_metrics.csv` and `metrics_summary.md`.
- Safe-subset frame0 preflight: class_1 myocardium Dice mean `0.5626`, class_2 LV Dice mean `0.7709`; class_3 scar sanity remains `0.0000` because the frozen CineMA anatomy prior has no scar head.
- No validation submission, upload package, network access, or training job was used by this script.

## Caveat

The crop proof uses train labels as an oracle protocol check. A training/inference entrypoint should replace that oracle with a CineMA anatomy union or another non-GT heart prior before model evaluation.

## Artifacts

- `geometry_audit.md`
- `safe_cases.csv`
- `mismatch_cases.csv`
- `crop_roundtrip.csv`
- `case_metrics.csv`
- `metrics_summary.md`
- `decision.md`
- `MANIFEST.md`
