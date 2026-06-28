# Resource Audit

- Candidate class 1, classical registration: `SimpleITK` translation registration using in-repo Python environment.
- 3D-safe volumes use `translation`; thin volumes with fewer than four z-slices use `slice2d_translation` to avoid ITK recursive-Gaussian failures.
- Classical warp types observed: `slice2d_translation=32, translation=84`.
- Candidate class 3, motion descriptor: no external dependency; reports frame-to-reference intensity similarity and anatomy center-of-mass displacement.
- Learning-based registration was not run in this pass because no challenge-appropriate pretrained cardiac weights were already available locally; no external upload or private-weight download was performed.
- Command output directory: `results/20260628_cine_register`
- Max registration iterations: `40`
- Max non-reference frames per case: `2`
- External repositories cloned: none.
- External uploads: none.
