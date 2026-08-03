# Collaborator MyoPS Reference Interface Comparison

Status: PASS

The collaborator reference image was checked only for the official Docker interface: `/input` root mount, `/output/myops` outputs, case naming, readable NIfTI files, label set, and reference-space geometry. Voxel equality and model-quality comparison are intentionally not required.

Reference image ID: `sha256:e3f9b5759bfa870363a8144577031d39f32129a63fa2b0f8c2b98552378cfebc`
Final MyoPS tag restored: `True`
Elapsed seconds: `17.20`

| case_id | status | geometry_matches_lge | labels | dtype |
|---|---:|---:|---|---|
| Case1001 | PASS | True | `[0, 200, 500, 600, 1220, 2221]` | `int16` |
| Case1004 | PASS | True | `[0, 200, 500, 600, 1220, 2221]` | `int16` |
| Case1012 | PASS | True | `[0, 200, 500, 600, 1220, 2221]` | `int16` |
