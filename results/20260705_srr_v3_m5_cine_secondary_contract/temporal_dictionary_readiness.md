# Temporal Dictionary Readiness

temporal_dictionary_status: `TEMPORAL_DICTIONARY_NOT_READY`
registration_status: `CINE_REGISTRATION_GAP_REMAINS`

## Evidence Present

- Frame0/ED anatomy prior exists from the CineMA adapter pilot.
- Non-reference optical-flow proxy rows and descriptor-router rows exist for a strict-safe subset.
- SimpleITK/Demons fallback rows exist for 8 safe cases.
- One ANTsPy SyN smoke row exists for `Case1001` frame 9 to frame 0.
- One untrained VoxelMorph adapter probe exists for the same pair.

## Missing Runtime Contract

- No runtime temporal dictionary artifact stores reference anatomy plus validated non-reference warped features.
- No same-safe-subset SyN/VoxelMorph/Demons/control matrix exists across the same cases.
- No trained or public-weight VoxelMorph row exists.
- No temporal aggregation metrics against a frame0/ED control exist for a validated registration path.
- No hosted `myocardium_cinemyops` metric is claimed.

Conclusion: router inputs are partially available, but temporal dictionary integration must not start as a full method until the registration matrix and runtime dictionary are produced.
