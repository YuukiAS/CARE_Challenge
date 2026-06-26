# Decision 20260625 Cine Geometry

status: `GO_CINE_TEMPORAL_PREFLIGHT`

## Evidence

- safe reference-frame preflight cases: 59
- prediction and label metadata match frame0 for all safe cases: True
- safe subset myocardium Dice mean: 0.5626
- frozen CineMA anatomy prior has no scar output, so class-3 scar sanity remains a negative control.

## Next Step

Run a temporal/anatomy retrieval preflight on the 59-case safe subset. Keep the five metadata mismatch cases in the repair queue until explicit header or nearest-neighbor resampling policy is accepted.
