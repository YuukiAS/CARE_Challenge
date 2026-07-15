# Route B Implementation Snapshot Continuation

Status: `ROUTE_B_NEEDS_EVIDENCE`

Implemented code paths:

- `src/care_myocardium/route_B/myops.py`: availability-masked modality stems, image/availability-aware router, shared/private/interaction dictionaries, prototype bank, anatomy/proposal/soft-ROI/refiner path, bounded nnU-Net residual, finite loss.
- `src/care_myocardium/route_B/cine.py`: frame adapter, learned registration/warp path, tensor classical registration control, temporal dictionary/refiner, finite loss.
- `src/care_myocardium/route_B/export.py`: compact-to-raw label mapping and tensor hash QA.

Gate evidence:

- MyoPS code gate: `PASS`
- Cine code gate: `PASS`
- real data preflight: `FAIL_EXTERNAL_DATA_MISSING`
