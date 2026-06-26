# CineMyoPS Geometry Audit

## Summary

- train cases audited: 64
- strict safe cases: 59
- metadata mismatch cases: 5
- origin mismatch cases: `['center_alpha_Case1009', 'center_alpha_Case1018', 'center_alpha_Case1020', 'center_alpha_Case1024']`
- spacing mismatch cases: `['center_beta_Case2023']`
- crop foreground failures: `[]`
- exact label roundtrip failures: `[]`

## Contract

- Frame 0 is the supervised reference frame for this gate.
- `safe_cases.csv` requires size, spacing, origin, and direction match between extracted frame 0 and the raw label under the recorded tolerances.
- `mismatch_cases.csv` keeps cases with metadata discrepancies out of the first supervised reference-control subset; they are not discarded.
- `crop_roundtrip.csv` uses the train-label foreground bounding box with an in-plane margin as a protocol check for heart-ROI crop/inverse safety.
- Model outputs should be inverse-mapped into the original frame array and written with `frame0` metadata via `CopyInformation(frame0)`.

## Interpretation

The safe subset is large enough to continue a reference-frame control without waiting for mismatch repair.
The five mismatch cases should remain in a separate repair queue for explicit header or nearest-neighbor resampling review.

## Mismatch Cases

- `center_alpha_Case1009`: origin
- `center_alpha_Case1018`: origin
- `center_alpha_Case1020`: origin
- `center_alpha_Case1024`: origin
- `center_beta_Case2023`: spacing
