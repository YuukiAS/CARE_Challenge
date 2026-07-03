# Reference Frame Contract

reference_frame_selection: `frame0 / ED-like adapter t00`

Frame 0 is used as the reference because prior geometry preflight established that safe-case labels match raw Cine frame0 metadata and the frozen CineMA adapter produced frame0 anatomy predictions on that geometry. This run treats frame0/reference-only as a control only.

Non-reference frame usage:

- `cine_deformable_or_feature_warp`: uses the first adapter-selected non-reference frame per case, estimates a dense 2D slice-wise optical-flow displacement into frame0 space, warps the non-reference anatomy prediction, and fuses it with the frame0 anatomy prediction before local proxy scoring.
- `cine_motion_descriptor_temporal_refiner`: uses frame0 plus adapter-selected non-reference keyframes, computes frame agreement and center-of-mass/motion descriptors, and fuses frame predictions by descriptor-derived temporal weights. This is descriptor/aggregation evidence, not completed registration.

Target-head availability:

- Local source anatomy prior has myocardium/LV outputs only after remapping CineMA labels `2 -> compact 1` and `3 -> compact 2`.
- Pathology/scar class `compact 3` remains a sanity negative control; hosted `myocardium_cinemyops` evidence is `evidence not found` because validation upload/package generation was forbidden.
