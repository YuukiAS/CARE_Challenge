# M9 Cine Architecture Contract

status: `FOUND_LOCAL_TEMPORAL_FINAL_OUTPUTS`

mode: `mode_A_registration_temporal_dictionary`

Pipeline:

```text
Cine input sequence
-> frame 0 reference anchor
-> safe-case descriptor-selected non-reference frame
-> existing local CineMA frame-wise anatomy predictions
-> ANTsPy SyNOnly registration when available, SimpleITK Demons fallback otherwise
-> temporal representation slots: reference_frame, registered_nonreference_anatomy, quality_weighted_union
-> deterministic temporal compact-label proxy output
-> local same-subset metrics vs frame0/reference control
```

Caveat: this is a local final-output proxy run, not a hosted myocardium_cinemyops metric claim.
