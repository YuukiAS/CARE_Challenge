# Registration Option Matrix

status: `PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP`

| option | transform family | current local status | required next evidence | can pass full Cine registration gate now? |
| --- | --- | --- | --- | --- |
| No warp / frame0 | none | Existing control evidence in prior Cine diagnostics | Keep as control in every table | No |
| SimpleITK translation | translation | Existing script: `scripts/evaluation/cinemyops_registration_preflight.py` | Same split control row only | No |
| SimpleITK Demons | deformable displacement fallback | Existing script: `scripts/evaluation/cine_temporal_motion_resume_20260704.py` | Same safe split, folding/Jacobian, myocardium/LV consistency, runtime | No, fallback only |
| Optical flow | dense flow / feature-warp proxy | Existing script: `scripts/evaluation/cine_motion_hardmode_20260703.py` | Same split proxy metrics and warp sanity | No, proxy only |
| TPS / B-spline | classical deformable | Not yet run in this subtask | Implement or document blocker; include interpolation policy, plausibility, downstream metrics | No |
| ANTsPy SyN | diffeomorphic/SyN-class deformable | Bounded smoke completed: `Case1001` frame 9 -> frame 0, NCC 0.9483 -> 0.9627 | Expand to same safe split; add Jacobian/folding and downstream metrics | No, smoke only |
| VoxelMorph | learned deformable registration | PyTorch `voxelmorph.nn.models.VxmPairwise` adapter probe completed on `Case1001` frame 9 -> 0; no cardiac pretrained weights loaded; near-identity output | Add trained or public-weight learning-based registration row, or document weight/domain blocker; compare against SyN and controls on the same safe subset | No, untrained adapter probe only |
| CineMA anatomy prior | anatomy prior / external adapter | Historical adapter outputs exist | Use as frame-wise anatomy source, not as registration itself; document no pathology head | No |

Required same-split comparison columns for the eventual full matrix:

- case id and center
- fixed frame and moving frame
- transform family
- image interpolation and label interpolation
- runtime and failure reason
- image NCC/MAE before and after
- myocardium/LV consistency to reference
- component count before and after
- folding voxels or Jacobian proxy
- displacement magnitude summary
- downstream myocardium proxy Dice caveat

The bounded SyN probe closes the narrow `ANTsPy available but untried` gap. It
does not close the full Cine registration gate.
